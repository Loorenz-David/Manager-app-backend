from sqlalchemy import select

from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.services.context import ServiceContext


async def pin_notification(ctx: ServiceContext) -> dict:
    """Upsert NotificationPin for (user_id, entity_type, entity_client_id). Idempotent."""
    data = ctx.incoming_data
    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(NotificationPin).where(
                NotificationPin.user_id          == ctx.user_id,
                NotificationPin.entity_type      == data["entity_type"],
                NotificationPin.entity_client_id == data["entity_client_id"],
            )
        )
        pin = result.scalar_one_or_none()
        if pin is None:
            pin = NotificationPin(
                user_id=ctx.user_id,
                entity_type=data["entity_type"],
                entity_client_id=data["entity_client_id"],
            )
            ctx.session.add(pin)
    return {"pin": {"client_id": pin.client_id}}
