"""`set_stock_report_item_priority` — MC-7's priority change (master plan §6.5,
phase 12; intention §7A before/after rows 6–9, §6A MC-6, §14B B2, MC-17, MC-19).
"""

from __future__ import annotations

from sqlalchemy import or_, select, update

from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.errors.not_found import NotFound
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
from beyo_manager.services.commands.stock_report._ordering import (
    append_to_priority_group,
    close_priority_gap,
)
from beyo_manager.services.commands.stock_report._row_values import row_values
from beyo_manager.services.commands.stock_report.requests import (
    parse_set_stock_report_item_priority_request,
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
    """The row lookup — the tenancy and visibility boundary of this command (plan 12
    C1(o)). Absent, soft-deleted and foreign are one answer: `NotFound`."""
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


async def _lock_row_and_groups(session, workspace_id, client_id, priorities):
    """One statement, ordered by `client_id`: the target row plus every non-deleted
    row of the source and destination groups (MC-7 "Serialization")."""
    named = [priority for priority in priorities if priority is not None]
    predicate = StockReportItem.client_id == client_id
    if named:
        predicate = or_(predicate, StockReportItem.priority.in_(named))
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


async def set_stock_report_item_priority(ctx: ServiceContext) -> dict:
    request = parse_set_stock_report_item_priority_request(ctx.incoming_data)
    target_priority = request.priority

    async with maybe_begin(ctx.session):
        # Advisory lock first: every ordering operation serializes workspace-wide
        # before it reads any position, which is what removes MC-7's phantom case.
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        # Unlocked discovery — it only decides which ids to lock (§9 rule 4).
        discovered = await _find_row(ctx.session, ctx.workspace_id, request.client_id)
        locked = await _lock_row_and_groups(
            ctx.session,
            ctx.workspace_id,
            request.client_id,
            (discovered.priority, target_priority),
        )
        # Re-read after the lock and decide on that (§9 rule 4).
        row = locked.get(request.client_id)
        if row is None or row.is_deleted:
            raise NotFound("Stock report item not found.")

        source_priority = row.priority
        source_order = row.priority_order
        initial_row_values = {
            client_id: row_values(candidate) for client_id, candidate in locked.items()
        }

        if source_priority == target_priority:
            # §14B B2: no write, no record, no stamp, no event.
            return {
                "stock_report_item": await _serialize(
                    ctx.session, ctx.workspace_id, request.client_id
                )
            }

        shifted = []
        if source_priority is not None:
            shifted = await close_priority_gap(
                ctx.session,
                workspace_id=ctx.workspace_id,
                priority=source_priority,
                removed_order=source_order,
            )

        target_order = None
        if target_priority is not None:
            target_order = await append_to_priority_group(
                ctx.session, workspace_id=ctx.workspace_id, priority=target_priority
            )

        mover = (
            (
                await ctx.session.execute(
                    update(StockReportItem)
                    .where(
                        StockReportItem.workspace_id == ctx.workspace_id,
                        StockReportItem.client_id == request.client_id,
                    )
                    .values(
                        priority=target_priority,
                        priority_order=target_order,
                        updated_by_id=ctx.user_id or None,
                        updated_at=ctx.now,
                    )
                    .returning(*_MOVER_RETURNING)
                )
            )
            .mappings()
            .one()
        )

        # MC-6: exactly one record, inserted **after** all row mutations, so its
        # `priority_order` and live `quantity_awaiting` are the post-move values.
        ctx.session.add(
            StockReportHistoryRecord(
                workspace_id=ctx.workspace_id,
                stock_report_item_id=request.client_id,
                type=StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
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
            # Deterministic order: the shift statement's RETURNING order is not
            # guaranteed, so neighbours follow their new position.
            for neighbour in sorted(shifted, key=lambda r: r["priority_order"])
        )
        payload = await _serialize(ctx.session, ctx.workspace_id, request.client_id)

    await dispatch(
        coalesce_stock_report_events(events, initial_row_values=initial_row_values)
    )
    return {"stock_report_item": payload}


async def _serialize(session, workspace_id, client_id):
    """Read the row back (and its category **by id**, so a soft-deleted category
    still serializes its name — MC-16) after the Core statements above.

    The `workspace_id` term carries no behaviour — the caller has already resolved
    and locked the row by workspace, and `client_id` is a globally unique prefixed
    ULID. It is here for **legibility** (owner card D-9): this module threaded
    `workspace_id` into some of its statements and omitted it from others, so no
    reader could tell which omission was deliberate. Precedent: batch B1 added
    `Task.workspace_id` to `set_task_stock_flag` for the same reason.

    This docstring used to say the Core statements above "leave any ORM instance
    stale (§9 rule 3)". **That is false and was corrected 2026-09-22:** those
    statements are ORM-enabled, `synchronize_session="auto"` resolves to
    `"evaluate"`, and their criteria evaluate identically in Python and in SQL, so
    the identity map is synchronised (master plan L-40 as corrected, L-49).
    `populate_existing=True` stays as defensive code; it is not load-bearing today.
    """
    row = (
        await session.execute(
            select(StockReportItem)
            .where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.client_id == client_id,
            )
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    category = await session.get(ItemCategory, row.item_category_id)
    return serialize_stock_report_item(row, category=category)
