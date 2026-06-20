from sqlalchemy import select

from beyo_manager.domain.notifications.pin_conditions import validate_pin_conditions
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.services.commands.notifications.requests import parse_edit_pin_batch_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def edit_pin_notification(ctx: ServiceContext) -> dict:
    items = parse_edit_pin_batch_request(ctx.incoming_data.get("items"))
    if not items:
        return {}

    client_ids = [item.client_id for item in items]

    async with maybe_begin(ctx.session):
        rows = await ctx.session.execute(
            select(NotificationPin).where(
                NotificationPin.user_id == ctx.user_id,
                NotificationPin.client_id.in_(client_ids),
            )
        )
        pins_by_id = {pin.client_id: pin for pin in rows.scalars().all()}

        for item in items:
            pin = pins_by_id.get(item.client_id)
            if pin is None:
                continue
            validate_pin_conditions(pin.entity_type, item.conditions)
            pin.conditions = item.conditions
            pin.fire_once = item.fire_once

    return {}
