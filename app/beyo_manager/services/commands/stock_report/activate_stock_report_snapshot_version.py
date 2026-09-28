"""`activate_stock_report_snapshot_version` —
`POST /api/v1/stock-report/snapshots/versions/{client_id}/activate` (draft versions,
2026-09-28; plan §4.2, O-1/O-9). Also the delayed scheduler's entry point (§5.3):
the handler calls this command directly with `expected_scheduled_activation_at` in
the body, which is what makes an activation "scheduled" (R-6).

A draft goes live: the running board is closed exactly as a direct create closes it
(`close_active_version`), the draft's row set is reconciled with the live rows (the
safety net for §4.1's window), and then **one statement** freezes each row's live
Scanner value into `quantity_requested_scanner`, settles `quantity_missing` and
stamps `active_at` on every snapshot — the two per-statement checks
(`scanner_iff_activated`, `missing_set_once_activated`) forbid doing any of the
three first (Q-1). The manual overrides survive (O-4). The missing rule (O-9): a row
the draft typed a value for keeps it; for the rest the flag decides — `true` carries
the closing board's value for the same row, `false` (the default) starts at 0. A
manual activation reads the flag from its body; a scheduled fire reads the draft's
stored `scheduled_activation_keeps_active_missing` at fire time (P-5). The settled
missing is then clamped to the live ceiling in one bulk statement.

The version row is stamped in **one** UPDATE — `active_at` set (the fire time, never
the scheduled time, R-15) and `scheduled_activation_at` cleared together, because
`ck_…_schedule_only_on_draft` is checked per statement (R-2); `snapshot_count` is
recomputed from the reconciled set. History: one `priority_change` record per
snapshot whose priority is set, carrying the effective requested quantity and its
source (Q-10). Events: `:closed` for the previous version and one `:activated`; **no
per-snapshot event** — clients refetch on `:activated` (P-16).

Refusals, all raised (nothing written): 404 absent/foreign; 422
`STOCK_REPORT_VERSION_NOT_DRAFT` unless a draft. The supersede rules of a scheduled
fire (§4.2 step 2 — moved, hand-published, later plan due), which **return**
`{"skipped": …}` and commit, and the scheduler row's `CANCELED`, land with plan §5.

Locks, in MC-1 order: advisory -> every live row FOR UPDATE (sorted) -> every
**open** snapshot FOR UPDATE (the board's and every draft's) -> the version FOR
UPDATE. Holding the rows makes a concurrent demand webhook wait up to its
`lock_timeout`; Scanner retries.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    bindparam,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.domain.stock_report.enums import StockReportHistoryRecordTypeEnum
from beyo_manager.domain.stock_report.snapshot_rules import (
    is_version_draft,
    snapshot_history_quantities,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_open
from beyo_manager.services.commands.stock_report._snapshot_missing import (
    clamp_version_missing_quantities,
)
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_NOT_DRAFT_MESSAGE,
    close_active_version,
    closed_version_event,
    find_version,
)
from beyo_manager.services.commands.stock_report.create_stock_report_snapshot_version import (
    draft_snapshot_values,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_activate_stock_report_snapshot_version_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

# Plan §4.2 step 5, verbatim: freeze, settle the missing and stamp — one statement.
# `:previous` is the version just closed (NULL → the join is empty, the fallback 0).
# Deleted rows are included: a snapshot of a deleted row is unreachable but the
# checks need values on every row of the version.
_ACTIVATE_SNAPSHOTS_STATEMENT = text(
    "UPDATE stock_report_item_snapshots AS s "
    "SET quantity_requested_scanner = r.quantity_requested, "
    "quantity_missing = COALESCE(s.quantity_missing, "
    "CASE WHEN :keep THEN a.quantity_missing END, 0), "
    "active_at = :now, "
    "quantity_in_queue = r.quantity_in_queue, "
    "quantity_in_progress = r.quantity_in_progress, "
    "quantity_awaiting = r.quantity_awaiting, "
    "updated_at = :now, updated_by_id = :actor "
    "FROM stock_report_items AS r "
    "LEFT JOIN stock_report_item_snapshots AS a "
    "ON a.stock_report_item_id = r.client_id AND a.version_id = :previous "
    "WHERE s.workspace_id = :ws AND s.version_id = :v "
    "AND r.client_id = s.stock_report_item_id"
).bindparams(
    bindparam("keep", type_=Boolean),
    bindparam("now", type_=DateTime(timezone=True)),
    # Typed so a NULL (no previous version) reaches asyncpg with a known type.
    bindparam("previous", type_=String),
)


async def _lock_live_rows(session, workspace_id):
    return (
        (
            await session.execute(
                select(StockReportItem)
                .where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                )
                .order_by(StockReportItem.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )


async def _lock_open_snapshots(session, workspace_id):
    return (
        await session.execute(
            select(
                StockReportItemSnapshot.version_id,
                StockReportItemSnapshot.stock_report_item_id,
            )
            .where(
                StockReportItemSnapshot.workspace_id == workspace_id,
                snapshot_is_open(),
            )
            .order_by(StockReportItemSnapshot.client_id)
            .with_for_update()
        )
    ).all()


async def _reconcile_membership(session, *, workspace_id, version_id, rows, held, now):
    """Insert a draft snapshot for every live row the draft has none for (§4.2
    step 4); expected to add nothing under live membership (O-3)."""
    missing = [row for row in rows if row.client_id not in held]
    if missing:
        await session.execute(
            pg_insert(StockReportItemSnapshot).on_conflict_do_nothing(
                constraint="uq_stock_report_item_snapshots_version_row"
            ),
            [
                draft_snapshot_values(
                    workspace_id=workspace_id,
                    version_id=version_id,
                    row=row,
                    now=now,
                )
                for row in missing
            ],
        )


async def _write_activation_history(session, *, workspace_id, version_id, actor, now):
    """One `priority_change` per prioritised snapshot, with the effective requested
    quantity and its source read **after** the freeze (§4.2 step 7)."""
    prioritised = (
        (
            await session.execute(
                select(StockReportItemSnapshot)
                .where(
                    StockReportItemSnapshot.workspace_id == workspace_id,
                    StockReportItemSnapshot.version_id == version_id,
                    StockReportItemSnapshot.priority.is_not(None),
                )
                .order_by(StockReportItemSnapshot.client_id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    if not prioritised:
        return
    rows_by_id = {
        row.client_id: row
        for row in (
            await session.execute(
                select(StockReportItem).where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.client_id.in_(
                        sorted({s.stock_report_item_id for s in prioritised})
                    ),
                )
            )
        )
        .scalars()
        .all()
    }
    session.add_all(
        [
            StockReportHistoryRecord(
                workspace_id=workspace_id,
                stock_report_item_id=snapshot.stock_report_item_id,
                type=StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
                **snapshot_history_quantities(
                    snapshot, row=rows_by_id[snapshot.stock_report_item_id]
                ),
                quantity_awaiting=rows_by_id[
                    snapshot.stock_report_item_id
                ].quantity_awaiting,
                priority=snapshot.priority,
                priority_order=snapshot.priority_order,
                created_by_id=actor or None,
                created_at=now,
            )
            for snapshot in prioritised
        ]
    )
    await session.flush()


async def activate_stock_report_snapshot_version(ctx: ServiceContext) -> dict:
    request = parse_activate_stock_report_snapshot_version_request(ctx.incoming_data)
    events = []

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)
        rows = await _lock_live_rows(ctx.session, ctx.workspace_id)
        open_snapshots = await _lock_open_snapshots(ctx.session, ctx.workspace_id)
        version = await find_version(
            ctx.session, ctx.workspace_id, request.client_id, for_update=True
        )
        if not is_version_draft(version):
            raise ValidationError(VERSION_NOT_DRAFT_MESSAGE)

        # The flag: the body's on a manual activation, the stored one on a
        # scheduled fire (R-6, P-5).
        keep_active_missing = (
            version.scheduled_activation_keeps_active_missing
            if request.scheduled
            else request.keep_active_missing
        )

        # Step 3 — close the running board before any partial unique index can see
        # a second active version or a second active snapshot per row (R-2).
        previous = await close_active_version(
            ctx.session,
            workspace_id=ctx.workspace_id,
            now=ctx.now,
            actor_user_id=ctx.user_id,
        )
        if previous is not None:
            events.append(closed_version_event(previous))

        # Step 4 — the row set.
        await _reconcile_membership(
            ctx.session,
            workspace_id=ctx.workspace_id,
            version_id=version.client_id,
            rows=rows,
            held={
                row_id
                for version_id, row_id in open_snapshots
                if version_id == version.client_id
            },
            now=ctx.now,
        )

        # Step 5 — freeze, settle, stamp: one statement.
        await ctx.session.execute(
            _ACTIVATE_SNAPSHOTS_STATEMENT,
            {
                "keep": keep_active_missing,
                "now": ctx.now,
                "actor": ctx.user_id or None,
                "previous": previous.client_id if previous is not None else None,
                "ws": ctx.workspace_id,
                "v": version.client_id,
            },
        )

        # Step 6 — the version row in one UPDATE; then the bulk clamp, whose
        # per-snapshot events are not emitted at activation (P-16).
        await ctx.session.execute(
            update(StockReportSnapshotVersion)
            .where(StockReportSnapshotVersion.client_id == version.client_id)
            .values(
                active_at=ctx.now,
                scheduled_activation_at=None,
                snapshot_count=(
                    select(func.count())
                    .select_from(StockReportItemSnapshot)
                    .where(StockReportItemSnapshot.version_id == version.client_id)
                    .scalar_subquery()
                ),
            )
            .execution_options(synchronize_session=False)
        )
        await clamp_version_missing_quantities(
            ctx.session,
            version_id=version.client_id,
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            now=ctx.now,
        )

        # Step 7 — history.
        await _write_activation_history(
            ctx.session,
            workspace_id=ctx.workspace_id,
            version_id=version.client_id,
            actor=ctx.user_id,
            now=ctx.now,
        )

        version = await find_version(ctx.session, ctx.workspace_id, version.client_id)
        events.append(
            WorkspaceEvent(
                event_name="stock_report_snapshot_version:activated",
                client_id=version.client_id,
                workspace_id=ctx.workspace_id,
                extra={
                    "snapshot_count": version.snapshot_count,
                    "title": version.title,
                    "scheduled": request.scheduled,
                    "keep_active_missing": keep_active_missing,
                },
            )
        )
        payload = serialize_stock_report_snapshot_version(version)

    await dispatch(events)
    return {"stock_report_snapshot_version": payload}
