import bcrypt
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.domain.users.validators import validate_password_policy
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.register_user_request import (
    RegisterUserRequest,
    parse_register_user_request,
)
from beyo_manager.services.context import ServiceContext


async def register_user(ctx: ServiceContext) -> dict:
    request: RegisterUserRequest = parse_register_user_request(ctx.incoming_data)
    validate_password_policy(request.password)

    # Pre-transaction: validate working_section_ids only allowed for WORKER — no DB needed yet
    if request.working_section_ids:
        if len(request.working_section_ids) != len(set(request.working_section_ids)):
            raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        # Resolve WorkspaceRole scoped to the caller's workspace.
        if request.role_id is not None:
            workspace_role = await ctx.session.scalar(
                select(WorkspaceRole).where(
                    WorkspaceRole.client_id == request.role_id,
                    WorkspaceRole.workspace_id == ctx.workspace_id,
                )
            )
        else:
            workspace_role = await ctx.session.scalar(
                select(WorkspaceRole)
                .options(selectinload(WorkspaceRole.role))
                .where(
                    WorkspaceRole.specialization.is_(None),
                    WorkspaceRole.workspace_id == ctx.workspace_id,
                    WorkspaceRole.role.has(Role.name == request.role_name),
                )
            )
        if workspace_role is None:
            raise NotFound("Workspace role not found.")

        # Validate working_section_ids only allowed for WORKER role
        if request.working_section_ids:
            role = await ctx.session.scalar(
                select(Role).where(Role.client_id == workspace_role.role_id)
            )
            if role is None or role.name != RoleNameEnum.WORKER.value:
                raise ValidationError("working_section_ids can only be provided when registering a WORKER.")

        # Email uniqueness (global)
        existing_email = await ctx.session.scalar(
            select(User.client_id).where(User.email == request.email)
        )
        if existing_email is not None:
            raise ConflictError("A user with this email already exists.")

        # Username uniqueness (global)
        existing_username = await ctx.session.scalar(
            select(User.client_id).where(User.username == request.username)
        )
        if existing_username is not None:
            raise ConflictError("Username already taken.")

        # Hash password — plaintext is never persisted
        hashed_password = bcrypt.hashpw(
            request.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Insert User
        user = User(
            username=request.username,
            email=request.email,
            password=hashed_password,
            phone_number=request.phone_number,
            created_by_id=ctx.user_id,
            online=False,
            created_at=datetime.now(timezone.utc),
        )
        ctx.session.add(user)
        await ctx.session.flush()  # get user.client_id

        now = datetime.now(timezone.utc)

        # Insert WorkspaceMembership
        membership = WorkspaceMembership(
            user_id=user.client_id,
            workspace_id=ctx.workspace_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
            joined_at=now,
        )
        ctx.session.add(membership)

        work_profile = UserWorkProfile(
            user_id=user.client_id,
            workspace_id=ctx.workspace_id,
            salary_per_hour_before_tax=request.salary_per_hour_before_tax,
            salary_per_hour_after_tax=request.salary_per_hour_after_tax,
            created_by_id=ctx.user_id,
            created_at=now,
        )
        ctx.session.add(work_profile)

        ctx.session.add(
            UserLifetimeStats(
                workspace_id=ctx.workspace_id,
                user_id=user.client_id,
                user_display_name_snapshot=user.username,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx.session.flush()  # persist membership + work_profile + lifetime_stats together

        # Insert WorkingSectionMembership rows (if any)
        if request.working_section_ids:
            # Bulk-validate all section IDs exist in this workspace
            result = await ctx.session.execute(
                select(WorkingSection.client_id).where(
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.client_id.in_(request.working_section_ids),
                    WorkingSection.is_deleted.is_(False),
                )
            )
            found_ids = {row[0] for row in result.all()}
            for section_id in request.working_section_ids:
                if section_id not in found_ids:
                    raise NotFound(f"Working section '{section_id}' not found.")

            for section_id in request.working_section_ids:
                section_membership = WorkingSectionMembership(
                    workspace_id=ctx.workspace_id,
                    working_section_id=section_id,
                    user_id=user.client_id,
                    assigned_at=now,
                    assigned_by_id=ctx.user_id,
                )
                ctx.session.add(section_membership)
            await ctx.session.flush()

    return {"user": serialize_user_profile(user, work_profile=work_profile)}
