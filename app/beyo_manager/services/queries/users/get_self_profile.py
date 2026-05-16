from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext


async def get_self_profile(ctx: ServiceContext) -> dict:
    user = await ctx.session.scalar(
        select(User).where(User.client_id == ctx.user_id)
    )
    if user is None:
        raise NotFound("User not found.")
    return {"user": serialize_user_profile(user)}
