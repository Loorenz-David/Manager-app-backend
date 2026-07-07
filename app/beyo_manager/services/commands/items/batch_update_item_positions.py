"""CMD: Batch-update item positions in one transaction."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_update_message
from beyo_manager.services.commands.location_tracker.enqueue_item_zone_push import (
    enqueue_item_zone_location_push,
)
from beyo_manager.services.commands.items.requests import parse_batch_update_item_positions_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def batch_update_item_positions(ctx: ServiceContext) -> dict:
    """Update item_position (and optionally item_zone) on multiple items atomically."""
    request = parse_batch_update_item_positions_request(ctx.incoming_data)

    ordered_ids: list[str] = []
    final_positions: dict[str, str | None] = {}
    final_zones: dict[str, str | None] = {}
    for entry in request.entries:
        if entry.client_id not in final_positions:
            ordered_ids.append(entry.client_id)
        final_positions[entry.client_id] = entry.item_position
        if "item_zone" in entry.model_fields_set:
            final_zones[entry.client_id] = entry.item_zone

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(ordered_ids),
                Item.is_deleted.is_(False),
            )
        )
        items_by_id = {item.client_id: item for item in result.scalars().all()}

        missing_ids = [client_id for client_id in ordered_ids if client_id not in items_by_id]
        if missing_ids:
            raise NotFound(f"Items not found: {', '.join(missing_ids)}")

        now = datetime.now(timezone.utc)
        username = ctx.identity.get("username")

        for client_id in ordered_ids:
            item = items_by_id[client_id]
            item.item_position = final_positions[client_id]

            zone_changed = client_id in final_zones
            if zone_changed:
                item.item_zone = final_zones[client_id]

            item.updated_at = now
            item.updated_by_id = ctx.user_id

            updated_fields = ["item_position", "item_zone"] if zone_changed else ["item_position"]
            await _create_history_record_in_session(
                session=ctx.session,
                entity_type=HistoryRecordEntityTypeEnum.ITEM,
                entity_client_id=item.client_id,
                change_type=HistoryRecordChangeTypeEnum.UPDATED,
                description=build_update_message(username, updated_fields, "item"),
                field_name=None,
                from_value=None,
                to_value=None,
                created_by_id=ctx.user_id,
                username_snapshot=username,
            )

            if zone_changed:
                await enqueue_item_zone_location_push(
                    ctx.session,
                    item,
                    username=username,
                    requested_by_user_id=ctx.user_id,
                )

    await event_bus.dispatch(
        [build_workspace_event(items_by_id[client_id], "item:updated") for client_id in ordered_ids]
    )
    return {"updated_ids": ordered_ids}
