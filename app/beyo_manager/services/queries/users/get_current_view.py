from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.presence.user_view_key import get_user_view


async def get_current_view(ctx: ServiceContext) -> dict:
    current = await get_user_view(ctx.user_id)
    return {"current_view": current}
