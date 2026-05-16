from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext


async def get_user_admin(ctx: ServiceContext) -> dict:
    user_client_id = ctx.incoming_data.get("user_client_id")

    membership = await ctx.session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.user_id == user_client_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise NotFound("User not found in workspace.")

    user = await ctx.session.scalar(
        select(User).where(User.client_id == user_client_id)
    )
    if user is None:
        raise NotFound("User not found.")

    work_profile = await ctx.session.scalar(
        select(UserWorkProfile).where(
            UserWorkProfile.user_id == user_client_id,
            UserWorkProfile.workspace_id == ctx.workspace_id,
        )
    )

    return {"user": serialize_user_profile(user, work_profile)}
