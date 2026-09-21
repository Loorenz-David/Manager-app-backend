"""`set_stock_report_item_priority_order` — MC-7's in-group move (master plan §6.5,
phase 12; intention §7A before/after rows 1–5, §6A MC-6, §14B B2, MC-17, MC-19).
"""

from __future__ import annotations

from sqlalchemy import or_, select, update

from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_updated_event,
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._ordering import shift_within_group
from beyo_manager.services.commands.stock_report._row_values import row_values
from beyo_manager.services.commands.stock_report.requests import (
    parse_set_stock_report_item_priority_order_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

_MOVER_RETURNING = (
    StockReportItem.quantity_requested,
    StockReportItem.quantity_in_queue,
    StockReportItem.quantity_in_progress,
    StockReportItem.quantity_awaiting,
    StockReportItem.priority,
    StockReportItem.priority_order,
)


async def _find_row(session, workspace_id, client_id):
    """The row lookup — the same tenancy and visibility boundary as the priority
    route's (both routes answer `NotFound` for absent, soft-deleted and foreign)."""
    row = await session.scalar(
        select(StockReportItem).where(
            StockReportItem.workspace_id == workspace_id,
            StockReportItem.client_id == client_id,
            StockReportItem.is_deleted.is_(False),
        )
    )
    if row is None:
        raise NotFound("Stock report item not found.")
    return row


async def _lock_row_and_group(session, workspace_id, client_id, priority):
    """One statement, ordered by `client_id`: the target row plus every non-deleted
    row of its group (MC-7 "Serialization")."""
    predicate = StockReportItem.client_id == client_id
    if priority is not None:
        predicate = or_(predicate, StockReportItem.priority == priority)
    rows = (
        (
            await session.execute(
                select(StockReportItem)
                .where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                    predicate,
                )
                .order_by(StockReportItem.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    return {row.client_id: row for row in rows}


async def set_stock_report_item_priority_order(ctx: ServiceContext) -> dict:
    request = parse_set_stock_report_item_priority_order_request(ctx.incoming_data)
    target = request.priority_order

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        discovered = await _find_row(ctx.session, ctx.workspace_id, request.client_id)
        locked = await _lock_row_and_group(
            ctx.session, ctx.workspace_id, request.client_id, discovered.priority
        )
        row = locked.get(request.client_id)
        if row is None or row.is_deleted:
            raise NotFound("Stock report item not found.")

        priority = row.priority
        if priority is None:
            raise ValidationError(
                "STOCK_REPORT_ROW_HAS_NO_PRIORITY: this stock report item has no "
                "priority, so it has no position to move within."
            )

        # `n` is the group size read **after** the locks (MC-7).
        n = sum(
            1 for candidate in locked.values() if candidate.priority == priority
        )
        if not 1 <= target <= n:
            raise ValidationError(
                f"STOCK_REPORT_TARGET_OUT_OF_RANGE: {target} is outside 1..{n} for "
                f"priority group '{priority.value}'."
            )

        position = row.priority_order
        initial_row_values = {
            client_id: row_values(candidate) for client_id, candidate in locked.items()
        }

        if target == position:
            # §14B B2: no write, no record, no stamp, no event.
            return {
                "stock_report_item": await _serialize(ctx.session, request.client_id)
            }

        shifted = await shift_within_group(
            ctx.session,
            workspace_id=ctx.workspace_id,
            priority=priority,
            from_order=position,
            to_order=target,
        )

        mover = (
            (
                await ctx.session.execute(
                    update(StockReportItem)
                    .where(StockReportItem.client_id == request.client_id)
                    .values(
                        priority_order=target,
                        updated_by_id=ctx.user_id or None,
                        updated_at=ctx.now,
                    )
                    .returning(*_MOVER_RETURNING)
                )
            )
            .mappings()
            .one()
        )

        # MC-6: one record for the moved row only — shifted neighbours get none —
        # inserted after all row mutations.
        ctx.session.add(
            StockReportHistoryRecord(
                workspace_id=ctx.workspace_id,
                stock_report_item_id=request.client_id,
                type=StockReportHistoryRecordTypeEnum.PRIORITY_ORDER_CHANGE,
                quantity_requested=mover["quantity_requested"],
                quantity_awaiting=mover["quantity_awaiting"],
                priority=mover["priority"],
                priority_order=mover["priority_order"],
                created_by_id=ctx.user_id or None,
                created_at=ctx.now,
            )
        )
        await ctx.session.flush()

        events = [
            build_stock_report_item_updated_event(
                client_id=request.client_id,
                workspace_id=ctx.workspace_id,
                values=mover,
            )
        ]
        events.extend(
            build_stock_report_item_updated_event(
                client_id=neighbour["client_id"],
                workspace_id=ctx.workspace_id,
                values=neighbour,
            )
            for neighbour in sorted(shifted, key=lambda r: r["priority_order"])
        )
        payload = await _serialize(ctx.session, request.client_id)

    await dispatch(
        coalesce_stock_report_events(events, initial_row_values=initial_row_values)
    )
    return {"stock_report_item": payload}


async def _serialize(session, client_id):
    """Read the row back (and its category **by id**) after the Core statements
    above, which leave any ORM instance stale (§9 rule 3)."""
    row = (
        await session.execute(
            select(StockReportItem)
            .where(StockReportItem.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    category = await session.get(ItemCategory, row.item_category_id)
    return serialize_stock_report_item(row, category=category)
