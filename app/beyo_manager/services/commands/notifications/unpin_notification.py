from collections import defaultdict

from sqlalchemy import delete

from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.services.commands.notifications.requests import parse_unpin_batch_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def unpin_notification(ctx: ServiceContext) -> dict:
    """Batch hard-delete NotificationPins for the authenticated user."""
    items = parse_unpin_batch_request(ctx.incoming_data.get("items"))
    if not items:
        return {}

    client_ids = [item.client_id for item in items if item.client_id is not None]
    major_ids_by_type: dict[str, list[str]] = defaultdict(list)
    for item in items:
        if item.major_entity_type is not None and item.major_client_entity_id is not None:
            major_ids_by_type[item.major_entity_type].append(item.major_client_entity_id)

    async with maybe_begin(ctx.session):
        if client_ids:
            await ctx.session.execute(
                delete(NotificationPin).where(
                    NotificationPin.user_id == ctx.user_id,
                    NotificationPin.client_id.in_(client_ids),
                )
            )

        for major_entity_type, major_client_entity_ids in major_ids_by_type.items():
            await ctx.session.execute(
                delete(NotificationPin).where(
                    NotificationPin.user_id == ctx.user_id,
                    NotificationPin.major_entity_type == major_entity_type,
                    NotificationPin.major_client_entity_id.in_(major_client_entity_ids),
                )
            )

    return {}
