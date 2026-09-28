"""`set_stock_report_item_priority` — MC-7's priority change (master plan §6.5,
phase 12; intention §7A before/after rows 6–9, §6A MC-6, §14B B2, MC-17, MC-19),
retargeted on 2026-09-26: the position belongs to the row's **active item snapshot**.

The route and body are unchanged (`PATCH /items/{client_id}/priority`, the row's id
in the path). The row is still the 404 boundary; a row with no active snapshot is a
422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT` — there is no version to order it in.

Locks: advisory -> the target snapshot plus every active snapshot of the source and
destination groups (one statement). No row lock: the row is not written, and every
row-deleting path takes the advisory lock first, so it cannot vanish under us.
"""

from __future__ import annotations

from sqlalchemy import or_, select, update

from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.domain.stock_report.snapshot_rules import is_snapshot_active
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    load_active_snapshot,
    serialize_row_with_active_snapshot,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_open
from beyo_manager.services.commands.stock_report._ordering import (
    append_to_priority_group,
    close_priority_gap,
)
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_set_stock_report_item_priority_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

_MOVER_RETURNING = (
    StockReportItemSnapshot.client_id,
    StockReportItemSnapshot.stock_report_item_id,
    StockReportItemSnapshot.version_id,
    StockReportItemSnapshot.priority,
    StockReportItemSnapshot.priority_order,
    StockReportItemSnapshot.quantity_missing,
    StockReportItemSnapshot.quantity_resolved,
    StockReportItemSnapshot.quantity_requested_scanner,
    StockReportItemSnapshot.quantity_requested_manual,
)

NO_ACTIVE_SNAPSHOT_MESSAGE = (
    "STOCK_REPORT_NO_ACTIVE_SNAPSHOT: this stock report item has no active snapshot; "
    "create a new stock report version first."
)


async def find_row(session, workspace_id, client_id):
    """The row lookup — the tenancy and visibility boundary of the item-scoped
    routes (plan 12 C1(o)). Absent, soft-deleted and foreign are one answer:
    `NotFound`."""
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


async def lock_snapshot_and_groups(
    session, workspace_id, version_id, snapshot_id, priorities
):
    """One statement, ordered by `client_id`: the target snapshot plus every open
    snapshot of the named groups **in that version** (MC-7 "Serialization"; a
    group is `(version_id, priority)` since drafts, 2026-09-28)."""
    named = [priority for priority in priorities if priority is not None]
    predicate = StockReportItemSnapshot.client_id == snapshot_id
    if named:
        predicate = or_(predicate, StockReportItemSnapshot.priority.in_(named))
    snapshots = (
        (
            await session.execute(
                select(StockReportItemSnapshot)
                .where(
                    StockReportItemSnapshot.workspace_id == workspace_id,
                    StockReportItemSnapshot.version_id == version_id,
                    snapshot_is_open(),
                    predicate,
                )
                .order_by(StockReportItemSnapshot.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    return {snapshot.client_id: snapshot for snapshot in snapshots}


async def set_stock_report_item_priority(ctx: ServiceContext) -> dict:
    request = parse_set_stock_report_item_priority_request(ctx.incoming_data)
    target_priority = request.priority

    async with maybe_begin(ctx.session):
        # Advisory lock first: every ordering operation serializes workspace-wide
        # before it reads any position, which is what removes MC-7's phantom case.
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        row = await find_row(ctx.session, ctx.workspace_id, request.client_id)
        # Unlocked discovery — it only decides which ids to lock (§9 rule 4).
        discovered = await load_active_snapshot(
            ctx.session, ctx.workspace_id, row.client_id
        )
        if discovered is None:
            raise ValidationError(NO_ACTIVE_SNAPSHOT_MESSAGE)
        locked = await lock_snapshot_and_groups(
            ctx.session,
            ctx.workspace_id,
            discovered.version_id,
            discovered.client_id,
            (discovered.priority, target_priority),
        )
        # Re-read after the lock and decide on that (§9 rule 4).
        snapshot = locked.get(discovered.client_id)
        if snapshot is None or not is_snapshot_active(snapshot):
            raise ValidationError(NO_ACTIVE_SNAPSHOT_MESSAGE)

        source_priority = snapshot.priority
        source_order = snapshot.priority_order
        initial_snapshot_values = {
            client_id: snapshot_values(candidate)
            for client_id, candidate in locked.items()
        }

        if source_priority == target_priority:
            # §14B B2: no write, no record, no stamp, no event.
            return {
                "stock_report_item": await serialize_row_with_active_snapshot(
                    ctx.session, ctx.workspace_id, row.client_id
                )
            }

        shifted = []
        if source_priority is not None:
            shifted = await close_priority_gap(
                ctx.session,
                version_id=snapshot.version_id,
                priority=source_priority,
                removed_order=source_order,
            )

        target_order = None
        if target_priority is not None:
            target_order = await append_to_priority_group(
                ctx.session, version_id=snapshot.version_id, priority=target_priority
            )

        mover = (
            (
                await ctx.session.execute(
                    update(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id == snapshot.client_id,
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

        # MC-6: exactly one record, per **row**, inserted after all mutations, so its
        # position is the post-move one and its quantities the row's live ones.
        ctx.session.add(
            StockReportHistoryRecord(
                workspace_id=ctx.workspace_id,
                stock_report_item_id=row.client_id,
                type=StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
                quantity_requested=row.quantity_requested,
                quantity_awaiting=row.quantity_awaiting,
                priority=mover["priority"],
                priority_order=mover["priority_order"],
                created_by_id=ctx.user_id or None,
                created_at=ctx.now,
            )
        )
        await ctx.session.flush()

        events = [
            build_stock_report_item_snapshot_updated_event(
                client_id=snapshot.client_id,
                workspace_id=ctx.workspace_id,
                values=mover,
            )
        ]
        events.extend(
            build_stock_report_item_snapshot_updated_event(
                client_id=neighbour["client_id"],
                workspace_id=ctx.workspace_id,
                values=neighbour,
            )
            # Deterministic order: the shift statement's RETURNING order is not
            # guaranteed, so neighbours follow their new position.
            for neighbour in sorted(shifted, key=lambda r: r["priority_order"])
        )
        payload = await serialize_row_with_active_snapshot(
            ctx.session, ctx.workspace_id, row.client_id
        )

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values={},
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {"stock_report_item": payload}
