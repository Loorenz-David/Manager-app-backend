"""`set_stock_report_item_snapshot_requested_quantity` —
`PATCH /api/v1/stock-report/snapshots/versions/{version_id}/items/{client_id}/requested-quantity`
(draft versions, 2026-09-28; plan §4.11, O-2/O-4).

The manual requested quantity of one snapshot, on a draft or on the active version:
a number sets `quantity_requested_manual`, `null` reverts it. A revert is one NULL
write whatever the state — on a draft the effective value falls back to the live
row, on the active version to the frozen Scanner column — the same column, the same
route, no branch. There is no active-version shortcut: the route is new and the
frontend is always inside a version.

**The no-op compares against the stored manual column, never the effective value**
(card 6): typing the number Scanner already shows **pins** it — stored, source
`manual`, and the draft holds it when Scanner moves. The same stored value is a 200
with no write and no event; `null` on a snapshot with no override is the one no-op
among reverts.

On the **active** version only, decided on the post-lock read (P-20): the snapshot's
`quantity_missing` is clamped to the new effective ceiling when it fell (the
single-row clamp statement, keyed by row and the active pair — which is this
snapshot), in the same transaction; and one `quantity_requested_override` history
record is written with the effective value after the change and its source
(`manual` on a set, `scanner` on a revert). On a draft: no clamp (a draft's missing
is a guide, re-clamped at activation) and no history.

Locks: the row `FOR UPDATE` -> the version's snapshot of it `FOR UPDATE` (the
missing command's shape, no advisory) -> the version (plain read, post-lock).
"""

from __future__ import annotations

from sqlalchemy import update

from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.domain.stock_report.snapshot_rules import (
    is_version_active,
    snapshot_history_quantities,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._load_row_with_snapshot import (
    load_version_snapshot,
    serialize_row_with_version_snapshot,
)
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_item_snapshots,
    lock_stock_report_items,
)
from beyo_manager.services.commands.stock_report._snapshot_missing import (
    clamp_snapshot_missing_quantity,
)
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report._target_snapshot import (
    check_locked_target,
    discover_target_snapshot,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_set_stock_report_item_snapshot_requested_quantity_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

_RETURNING = (
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


async def set_stock_report_item_snapshot_requested_quantity(
    ctx: ServiceContext,
) -> dict:
    request = parse_set_stock_report_item_snapshot_requested_quantity_request(
        ctx.incoming_data
    )
    target = request.quantity_requested
    events = []

    async with maybe_begin(ctx.session):
        locked_rows = await lock_stock_report_items(
            ctx.session, ctx.workspace_id, [request.client_id]
        )
        row = locked_rows.get(request.client_id)
        if row is None or row.is_deleted:
            raise NotFound("Stock report item not found.")

        target_snapshot = await discover_target_snapshot(
            ctx.session, ctx.workspace_id, row.client_id, request.version_id
        )
        discovered = target_snapshot.snapshot
        locked = await lock_stock_report_item_snapshots(
            ctx.session, ctx.workspace_id, [discovered.client_id]
        )
        snapshot = locked.get(discovered.client_id)
        version = await check_locked_target(
            ctx.session, ctx.workspace_id, target_snapshot, snapshot
        )
        initial_snapshot_values = {snapshot.client_id: snapshot_values(snapshot)}

        if target == snapshot.quantity_requested_manual:
            # The pin rule: the comparison is against the **stored** manual
            # column. No write, no stamp, no event.
            return {
                "stock_report_item": await serialize_row_with_version_snapshot(
                    ctx.session, ctx.workspace_id, row.client_id, version.client_id
                )
            }

        values = (
            (
                await ctx.session.execute(
                    update(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id == snapshot.client_id,
                    )
                    .values(
                        quantity_requested_manual=target,
                        updated_by_id=ctx.user_id or None,
                        updated_at=ctx.now,
                    )
                    .returning(*_RETURNING)
                )
            )
            .mappings()
            .one()
        )
        events.append(
            build_stock_report_item_snapshot_updated_event(
                client_id=snapshot.client_id,
                workspace_id=ctx.workspace_id,
                values=values,
            )
        )

        if is_version_active(version):
            events.extend(
                await clamp_snapshot_missing_quantity(
                    ctx.session,
                    row_id=row.client_id,
                    workspace_id=ctx.workspace_id,
                    actor_user_id=ctx.user_id,
                    now=ctx.now,
                )
            )
            # The record carries the value now in force and where it comes from:
            # re-read the snapshot the Core statements just wrote.
            written = await load_version_snapshot(
                ctx.session, ctx.workspace_id, row.client_id, version.client_id
            )
            ctx.session.add(
                StockReportHistoryRecord(
                    workspace_id=ctx.workspace_id,
                    stock_report_item_id=row.client_id,
                    type=StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_OVERRIDE,
                    **snapshot_history_quantities(written, row=row),
                    quantity_awaiting=row.quantity_awaiting,
                    priority=written.priority,
                    priority_order=written.priority_order,
                    created_by_id=ctx.user_id or None,
                    created_at=ctx.now,
                )
            )
            await ctx.session.flush()

        payload = await serialize_row_with_version_snapshot(
            ctx.session, ctx.workspace_id, row.client_id, version.client_id
        )

    await dispatch(
        coalesce_stock_report_events(
            events,
            initial_row_values={},
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {"stock_report_item": payload}
