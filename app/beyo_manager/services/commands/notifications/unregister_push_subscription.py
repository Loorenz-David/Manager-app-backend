from sqlalchemy import select

from beyo_manager.models.tables.notifications.push_subscription import PushSubscription
from beyo_manager.services.context import ServiceContext


async def unregister_push_subscription(ctx: ServiceContext) -> dict:
    """Hard-delete PushSubscription by endpoint. No-op if already deleted."""
    endpoint = ctx.incoming_data.get("endpoint")
    async with ctx.session.begin():
        result   = await ctx.session.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == ctx.user_id,
                PushSubscription.endpoint == endpoint,
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            await ctx.session.delete(sub)
    return {}
