from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.update_user_admin_request import (
    parse_update_user_admin_request,
)
from beyo_manager.services.context import ServiceContext


async def update_user_admin(ctx: ServiceContext) -> dict:
    request = parse_update_user_admin_request(ctx.incoming_data)

    async with ctx.session.begin():
        membership = await ctx.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_client_id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise NotFound("User not found in workspace.")

        user = await ctx.session.scalar(
            select(User).where(User.client_id == request.user_client_id)
        )
        if user is None:
            raise NotFound("User not found.")

        if request.email is not None and request.email != user.email:
            conflict = await ctx.session.scalar(
                select(User).where(
                    User.email == request.email,
                    User.client_id != request.user_client_id,
                )
            )
            if conflict is not None:
                raise ConflictError("Email is already in use.")
            user.email = request.email

        if "phone_number" in ctx.incoming_data:
            user.phone_number = request.phone_number

        if "profile_picture" in ctx.incoming_data:
            user.profile_picture = request.profile_picture

        work_profile = await ctx.session.scalar(
            select(UserWorkProfile).where(
                UserWorkProfile.user_id == request.user_client_id,
                UserWorkProfile.workspace_id == ctx.workspace_id,
            )
        )
        if work_profile is None and any(
            f in ctx.incoming_data for f in ("salary_per_hour_before_tax", "salary_per_hour_after_tax")
        ):
            work_profile = UserWorkProfile(
                user_id=request.user_client_id,
                workspace_id=ctx.workspace_id,
                created_by_id=ctx.user_id,
            )
            ctx.session.add(work_profile)
        if work_profile is not None:
            if "salary_per_hour_before_tax" in ctx.incoming_data:
                work_profile.salary_per_hour_before_tax = request.salary_per_hour_before_tax
            if "salary_per_hour_after_tax" in ctx.incoming_data:
                work_profile.salary_per_hour_after_tax = request.salary_per_hour_after_tax

    return {"user": serialize_user_profile(user, work_profile)}
