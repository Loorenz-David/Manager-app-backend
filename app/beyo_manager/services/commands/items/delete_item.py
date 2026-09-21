"""CMD-4: Soft-delete an Item."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_delete_message
from beyo_manager.services.commands.items.requests import parse_delete_item_request
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_items,
    lock_stock_task_assignments,
    lock_tasks,
)
from beyo_manager.services.commands.stock_report._remove_assignment import (
    remove_assignment,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def delete_item(ctx: ServiceContext) -> dict:
    """Soft-delete an Item. Does not cascade to issues or upholstery rows. Removes
    every non-deleted stock-report assignment of the item (MC-14 row 3, master plan
    §6.1b) — the item's tasks are untouched."""
    request = parse_delete_item_request(ctx.incoming_data)
    stock_events: list = []

    async with maybe_begin(ctx.session):
        # New: Item FOR UPDATE (MC-1 order: Item -> Tasks -> rows -> assignments).
        result = await ctx.session.execute(
            select(Item)
            .where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == request.client_id,
                Item.is_deleted.is_(False),
            )
            .with_for_update()
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFound("Item not found.")

        now = datetime.now(timezone.utc)

        discovered = (
            (
                await ctx.session.execute(
                    select(StockTaskAssignment).where(
                        StockTaskAssignment.workspace_id == ctx.workspace_id,
                        StockTaskAssignment.item_id == item.client_id,
                        StockTaskAssignment.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        task_ids = {assignment.task_id for assignment in discovered}
        row_ids = {assignment.stock_report_item_id for assignment in discovered}
        await lock_tasks(ctx.session, ctx.workspace_id, task_ids)
        await lock_stock_report_items(ctx.session, ctx.workspace_id, row_ids)
        locked_assignments = await lock_stock_task_assignments(
            ctx.session, ctx.workspace_id, {a.client_id for a in discovered}
        )
        for client_id in sorted(locked_assignments):
            assignment = locked_assignments[client_id]
            if assignment.is_deleted:
                continue  # re-read after lock: a concurrent delete won here
            stock_events.extend(
                await remove_assignment(
                    ctx.session,
                    assignment,
                    workspace_id=ctx.workspace_id,
                    actor_user_id=ctx.user_id,
                    now=now,
                    trigger="delete_item",
                )
            )

        item.is_deleted = True
        item.deleted_at = now
        item.deleted_by_id = ctx.user_id

        username = ctx.identity.get("username")
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM,
            entity_client_id=item.client_id,
            change_type=HistoryRecordChangeTypeEnum.DELETED,
            description=build_delete_message(username, "item", "workspace"),
            field_name=None,
            from_value=None,
            to_value=None,
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

    events = [build_workspace_event(item, "item:deleted")]
    events.extend(stock_events)
    await event_bus.dispatch(events)
    return {}
