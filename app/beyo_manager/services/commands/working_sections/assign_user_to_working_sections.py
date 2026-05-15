from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.working_sections.requests.assign_user_request import (
    AssignUserRequest,
    parse_assign_user_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_user_event


async def assign_user_to_working_sections(ctx: ServiceContext) -> dict:
    request: AssignUserRequest = parse_assign_user_request(ctx.incoming_data)

    if len(request.working_section_ids) != len(set(request.working_section_ids)):
        raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        worker_membership_id = await ctx.session.scalar(
            select(WorkspaceMembership.client_id)
            .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
            .join(Role, Role.client_id == WorkspaceRole.role_id)
            .where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_id,
                WorkspaceMembership.is_active.is_(True),
                Role.name == RoleNameEnum.WORKER.value,
            )
        )
        if worker_membership_id is None:
            any_membership = await ctx.session.scalar(
                select(WorkspaceMembership.client_id).where(
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.user_id == request.user_id,
                    WorkspaceMembership.is_active.is_(True),
                )
            )
            if any_membership is None:
                raise NotFound("User not found in workspace.")
            raise ValidationError("Only workers can be assigned to working sections.")

        for section_id in request.working_section_ids:
            section = await ctx.session.scalar(
                select(WorkingSection).where(
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.client_id == section_id,
                    WorkingSection.is_deleted.is_(False),
                )
            )
            if section is None:
                raise NotFound(f"Working section '{section_id}' not found.")

            existing = await ctx.session.scalar(
                select(WorkingSectionMembership.client_id).where(
                    WorkingSectionMembership.workspace_id == ctx.workspace_id,
                    WorkingSectionMembership.working_section_id == section_id,
                    WorkingSectionMembership.user_id == request.user_id,
                    WorkingSectionMembership.removed_at.is_(None),
                )
            )
            if existing is not None:
                raise ConflictError(
                    f"User is already assigned to working section '{section_id}'."
                )

        for section_id in request.working_section_ids:
            membership = WorkingSectionMembership(
                workspace_id=ctx.workspace_id,
                working_section_id=section_id,
                user_id=request.user_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=ctx.user_id,
            )
            ctx.session.add(membership)
            await ctx.session.flush()

    await dispatch(
        [
            build_user_event(
                user_id=request.user_id,
                event_name="user:working_sections_updated",
                client_id=request.user_id,
                extra={"working_section_ids": request.working_section_ids},
            )
        ]
    )
    return {"assigned_section_ids": request.working_section_ids}
