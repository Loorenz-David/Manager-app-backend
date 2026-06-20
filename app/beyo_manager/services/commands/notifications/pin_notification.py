from sqlalchemy import select, tuple_

from beyo_manager.domain.notifications.pin_conditions import validate_pin_conditions
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.services.commands.notifications.requests import (
    PinNotificationItem,
    parse_pin_notification_batch_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def pin_notification(ctx: ServiceContext) -> dict:
    """Batch upsert NotificationPins for the authenticated user."""
    items = parse_pin_notification_batch_request(ctx.incoming_data.get("items"))
    if not items:
        return {"pins": []}

    entity_types = _validate_items(items)
    pairs = {(entity_types[index].value, item.entity_client_id) for index, item in enumerate(items)}

    async with maybe_begin(ctx.session):
        existing_result = await ctx.session.execute(
            select(NotificationPin).where(
                NotificationPin.user_id == ctx.user_id,
                tuple_(
                    NotificationPin.entity_type,
                    NotificationPin.entity_client_id,
                ).in_(pairs),
            )
        )
        existing_by_pair = {
            (pin.entity_type, pin.entity_client_id): pin
            for pin in existing_result.scalars().all()
        }

        response_items: list[dict[str, str]] = []
        for index, item in enumerate(items):
            entity_type = entity_types[index].value
            key = (entity_type, item.entity_client_id)
            pin = existing_by_pair.get(key)
            if pin is None:
                pin = NotificationPin(
                    client_id=item.client_id,
                    user_id=ctx.user_id,
                    entity_type=entity_type,
                    entity_client_id=item.entity_client_id,
                    conditions=item.conditions,
                    fire_once=item.fire_once,
                    major_entity_type=item.major_entity_type,
                    major_client_entity_id=item.major_client_entity_id,
                )
                ctx.session.add(pin)
                existing_by_pair[key] = pin
            else:
                pin.conditions = item.conditions
                pin.fire_once = item.fire_once
                pin.major_entity_type = item.major_entity_type
                pin.major_client_entity_id = item.major_client_entity_id
            response_items.append({"client_id": pin.client_id})

        await ctx.session.flush()

    return {"pins": response_items}


def _validate_items(items: list[PinNotificationItem]) -> list[EntityType]:
    pairs: set[tuple[str, str]] = set()
    entity_types: list[EntityType] = []

    for item in items:
        try:
            entity_type = EntityType(item.entity_type)
        except ValueError as exc:
            raise ValidationError(f"Unsupported entity_type: {item.entity_type}.") from exc

        pair = (entity_type.value, item.entity_client_id)
        if pair in pairs:
            raise ValidationError(
                f"Duplicate pin target in request: {entity_type.value}/{item.entity_client_id}."
            )
        pairs.add(pair)

        validate_pin_conditions(entity_type.value, item.conditions)
        entity_types.append(entity_type)

    return entity_types
