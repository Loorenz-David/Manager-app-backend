from sqlalchemy import select

from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.services.context import ServiceContext


async def unpin_notification(ctx: ServiceContext) -> dict:
    """Hard-delete NotificationPin. No-op if it does not exist."""
    data   = ctx.incoming_data
    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(NotificationPin).where(
                NotificationPin.user_id          == ctx.user_id,
                NotificationPin.entity_type      == data["entity_type"],
                NotificationPin.entity_client_id == data["entity_client_id"],
            )
        )
        pin = result.scalar_one_or_none()
        if pin:
            await ctx.session.delete(pin)
    return {}
