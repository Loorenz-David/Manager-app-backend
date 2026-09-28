from datetime import datetime

from sqlalchemy import DateTime, bindparam, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from beyo_manager.domain.stock_report.enums import StockReportRepairTargetKindEnum
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
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._events import (
    build_stock_report_item_snapshot_updated_event,
)
from beyo_manager.services.commands.stock_report._ordering import close_priority_gap
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.stock_report._repair_records import (
    write_repair_record,
)
from beyo_manager.services.commands.stock_report._task_flag import set_task_stock_flag
from beyo_manager.services.commands.stock_report._predicates import (
    snapshot_is_open,
    version_is_open,
)
from beyo_manager.services.commands.stock_report.create_stock_report_snapshot_version import (
    draft_snapshot_values,
)
from beyo_manager.services.commands.stock_report._version_schedule import (
    cancel_activation_schedulers,
    create_activation_scheduler,
    lock_activation_schedulers,
)
from beyo_manager.services.commands.stock_report._versions import find_version
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
    lock_stock_report_item_snapshots,
    lock_stock_report_items,
    lock_stock_report_history_records,
    lock_stock_task_assignments,
    lock_tasks,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)

_TARGETS = {
    "counter_in_queue": StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
    "counter_in_progress": StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
    "counter_awaiting": StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
    "task_flag": StockReportRepairTargetKindEnum.TASK,
    "goal_total": StockReportRepairTargetKindEnum.HISTORY_RECORD,
    # The ordering repair targets the active item snapshot since 2026-09-26. There
    # is no `priority_order_nullness` any more: the snapshot table's pairing check
    # makes a half-null position unstorable.
    "order_density": StockReportRepairTargetKindEnum.GROUP,
    "missing_over_ceiling": StockReportRepairTargetKindEnum.ITEM_SNAPSHOT,
    "snapshot_version_state_mismatch": StockReportRepairTargetKindEnum.ITEM_SNAPSHOT,
    # Draft membership (plan §4.12) and the schedule's scheduler row (plan §7,
    # R-4) target the **version** (2026-09-28).
    "draft_membership_mismatch": StockReportRepairTargetKindEnum.SNAPSHOT_VERSION,
    "schedule_scheduler_mismatch": StockReportRepairTargetKindEnum.SNAPSHOT_VERSION,
}

# State repair (ii): stamp the version's `active_at` onto a snapshot that lacks
# it. `ck_…_scanner_iff_activated` and `ck_…_missing_set_once_activated` are
# per-statement, so the Scanner column (from the row, when NULL) and the
# missing (0, when NULL) land in the same statement as the stamp.
_STAMP_ACTIVE_AT = text(
    "UPDATE stock_report_item_snapshots AS s "
    "SET active_at = :active_at, "
    "quantity_requested_scanner = COALESCE(s.quantity_requested_scanner, "
    "r.quantity_requested), "
    "quantity_missing = COALESCE(s.quantity_missing, 0), "
    "updated_at = :now, updated_by_id = :actor "
    "FROM stock_report_items AS r "
    "WHERE r.client_id = s.stock_report_item_id "
    "AND s.workspace_id = :ws AND s.client_id = :id"
).bindparams(
    bindparam("active_at", type_=DateTime(timezone=True)),
    bindparam("now", type_=DateTime(timezone=True)),
)


async def _repair_draft_membership(ctx, divergence, changed_snapshot_ids):
    """A missing snapshot is inserted as the webhook inserts it (§4.9's shape, one
    row into one draft); a stray one — it may hold a priority — closes its gap in
    the draft's group and is deleted; the draft's `snapshot_count` is recomputed."""
    version_id = divergence["client_id"]
    if divergence["stored"] is None:
        row = await ctx.session.scalar(
            select(StockReportItem).where(
                StockReportItem.workspace_id == ctx.workspace_id,
                StockReportItem.client_id == divergence["expected"],
            )
        )
        await ctx.session.execute(
            pg_insert(StockReportItemSnapshot).values(
                draft_snapshot_values(
                    workspace_id=ctx.workspace_id,
                    version_id=version_id,
                    row=row,
                    now=ctx.now,
                )
            )
        )
    else:
        stray = await ctx.session.scalar(
            select(StockReportItemSnapshot).where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                StockReportItemSnapshot.version_id == version_id,
                StockReportItemSnapshot.stock_report_item_id == divergence["stored"],
            )
        )
        if stray.priority is not None:
            shifted = await close_priority_gap(
                ctx.session,
                version_id=version_id,
                priority=stray.priority,
                removed_order=stray.priority_order,
            )
            changed_snapshot_ids.update(neighbour["client_id"] for neighbour in shifted)
        await ctx.session.execute(
            delete(StockReportItemSnapshot).where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                StockReportItemSnapshot.client_id == stray.client_id,
            )
        )
    # The draft's `snapshot_count` is its live membership: recomputed, not
    # nudged, so a count left behind by whatever caused the divergence is fixed
    # with it.
    held = (
        select(func.count())
        .select_from(StockReportItemSnapshot)
        .where(StockReportItemSnapshot.version_id == version_id)
        .scalar_subquery()
    )
    result = await ctx.session.execute(
        update(StockReportSnapshotVersion)
        .where(
            StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
            StockReportSnapshotVersion.client_id == version_id,
        )
        .values(snapshot_count=held)
    )
    if result.rowcount != 1:
        raise RuntimeError(
            "draft-membership repair affected an unexpected number of rows"
        )


async def _repair_schedule(ctx, divergence):
    """(a)/(b) a draft's schedule with no `ACTIVE` row due at it: recreate the row,
    stamped with the **repairing** user — the recovery path of a fire that failed
    or errored while due; the late fire then activates (card 3) or skips (card 4).
    (c) an `ACTIVE` row matching no draft's column: cancel it."""
    if divergence["stored"] is not None:
        version = await find_version(
            ctx.session, ctx.workspace_id, divergence["client_id"]
        )
        await create_activation_scheduler(
            ctx.session, version, scheduled_by_user_id=ctx.user_id
        )
        return
    cancelled = await cancel_activation_schedulers(
        ctx.session,
        divergence["client_id"],
        now=ctx.now,
        scheduled_for=datetime.fromisoformat(divergence["expected"]),
    )
    if cancelled < 1:
        raise RuntimeError("schedule repair cancelled no scheduler row")


async def _repair_priority_orders(ctx, repaired, changed_snapshot_ids):
    """Densify each `(version_id, priority)` group of the **open snapshots** — the
    board's and every draft's, each within its own version — and record the net,
    not intermediate, changes. Every prioritised snapshot has an order (the pairing
    check), so densification is the only ordering repair."""
    snapshots = (
        (
            await ctx.session.execute(
                select(StockReportItemSnapshot)
                .where(
                    StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                    snapshot_is_open(),
                )
                .order_by(
                    StockReportItemSnapshot.priority,
                    StockReportItemSnapshot.priority_order,
                    StockReportItemSnapshot.client_id,
                )
            )
        )
        .scalars()
        .all()
    )

    async def _write(snapshot, expected, kind, target_kind):
        stored = snapshot.priority_order
        result = await ctx.session.execute(
            update(StockReportItemSnapshot)
            .where(
                StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                StockReportItemSnapshot.client_id == snapshot.client_id,
            )
            .values(
                priority_order=expected,
                updated_at=ctx.now,
                updated_by_id=ctx.user_id,
            )
        )
        if result.rowcount != 1:
            raise RuntimeError(
                "priority-order repair affected an unexpected number of rows"
            )
        await write_repair_record(
            ctx.session,
            workspace_id=ctx.workspace_id,
            target_kind=target_kind,
            target_client_id=snapshot.client_id,
            field="priority_order",
            stored_value=stored,
            recomputed_value=expected,
            trigger="manual",
            created_by_id=ctx.user_id,
            now=ctx.now,
        )
        repaired.append(
            {
                "kind": kind,
                "client_id": snapshot.client_id,
                "field": "priority_order",
                "stored": stored,
                "expected": expected,
            }
        )
        changed_snapshot_ids.add(snapshot.client_id)

    groups = {}
    for snapshot in snapshots:
        if snapshot.priority is not None:
            groups.setdefault((snapshot.version_id, snapshot.priority), []).append(
                snapshot
            )
    for group_snapshots in groups.values():
        ordered = sorted(
            group_snapshots,
            key=lambda snapshot: (snapshot.priority_order, snapshot.client_id),
        )
        for expected, snapshot in enumerate(ordered, 1):
            if snapshot.priority_order == expected:
                continue
            await _write(
                snapshot,
                expected,
                "order_density",
                StockReportRepairTargetKindEnum.GROUP,
            )


async def repair_stock_report(ctx) -> dict:
    repaired = []
    not_repaired = []
    changed_row_ids = set()
    changed_snapshot_ids = set()
    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)
        divergences = await compute_stock_report_divergences(
            ctx.session, ctx.workspace_id
        )
        await lock_tasks(
            ctx.session,
            ctx.workspace_id,
            [
                entry["client_id"]
                for entry in divergences
                if entry["kind"] == "task_flag"
            ],
        )
        await lock_stock_report_items(
            ctx.session,
            ctx.workspace_id,
            (
                await ctx.session.scalars(
                    select(StockReportItem.client_id).where(
                        StockReportItem.workspace_id == ctx.workspace_id,
                        StockReportItem.is_deleted.is_(False),
                    )
                )
            ).all(),
        )
        await lock_stock_report_item_snapshots(
            ctx.session,
            ctx.workspace_id,
            (
                await ctx.session.scalars(
                    select(StockReportItemSnapshot.client_id).where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        snapshot_is_open(),
                    )
                )
            ).all(),
        )
        # The version rows (drafts', for the membership kind) come after the
        # snapshots, and the scheduler rows of every version come last — the
        # order plan §7 fixes (Q-18).
        await ctx.session.execute(
            select(StockReportSnapshotVersion.client_id)
            .where(
                StockReportSnapshotVersion.workspace_id == ctx.workspace_id,
                version_is_open(),
            )
            .order_by(StockReportSnapshotVersion.client_id)
            .with_for_update()
        )
        await lock_activation_schedulers(
            ctx.session,
            (
                await ctx.session.scalars(
                    select(StockReportSnapshotVersion.client_id).where(
                        StockReportSnapshotVersion.workspace_id == ctx.workspace_id
                    )
                )
            ).all(),
        )
        await lock_stock_task_assignments(
            ctx.session,
            ctx.workspace_id,
            (
                await ctx.session.scalars(
                    select(StockTaskAssignment.client_id).where(
                        StockTaskAssignment.workspace_id == ctx.workspace_id,
                        StockTaskAssignment.is_deleted.is_(False),
                    )
                )
            ).all(),
        )
        await lock_stock_report_history_records(
            ctx.session,
            ctx.workspace_id,
            [
                entry["client_id"]
                for entry in divergences
                if entry["kind"] == "goal_total"
            ],
        )
        # The unlocked read above only determines the task-lock set.  All repair
        # decisions are derived again once the report graph is locked.
        divergences = await compute_stock_report_divergences(
            ctx.session, ctx.workspace_id
        )
        divergences.sort(
            key=lambda item: (
                item["kind"] == "order_density",
                item["kind"],
                item["client_id"],
            )
        )
        if any(divergence["kind"] == "order_density" for divergence in divergences):
            await _repair_priority_orders(ctx, repaired, changed_snapshot_ids)
        for divergence in divergences:
            kind = divergence["kind"]
            if kind == "order_density":
                continue
            if kind == "signature":
                not_repaired.append(divergence)
                continue
            if kind == "task_flag":
                await set_task_stock_flag(
                    ctx.session,
                    ctx.workspace_id,
                    divergence["client_id"],
                    divergence["expected"] == "true",
                    require_update=True,
                )
            elif kind == "draft_membership_mismatch":
                await _repair_draft_membership(ctx, divergence, changed_snapshot_ids)
            elif kind == "schedule_scheduler_mismatch":
                await _repair_schedule(ctx, divergence)
            elif kind == "missing_over_ceiling":
                result = await ctx.session.execute(
                    update(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id == divergence["client_id"],
                    )
                    .values(
                        quantity_missing=divergence["expected"],
                        updated_at=ctx.now,
                        updated_by_id=ctx.user_id,
                    )
                )
                if result.rowcount != 1:
                    raise RuntimeError(
                        "missing-quantity repair affected an unexpected number of rows"
                    )
                changed_snapshot_ids.add(divergence["client_id"])
            elif (
                kind == "snapshot_version_state_mismatch"
                and divergence["field"] == "active_at"
            ):
                # (ii) stamp the version's `active_at` (Scanner column and missing
                # settled in the same statement); (iii) clear a draft snapshot's
                # stamp, and with it the Scanner column the check ties to it.
                if divergence["expected"] is not None:
                    result = await ctx.session.execute(
                        _STAMP_ACTIVE_AT,
                        {
                            "active_at": datetime.fromisoformat(divergence["expected"]),
                            "now": ctx.now,
                            "actor": ctx.user_id,
                            "ws": ctx.workspace_id,
                            "id": divergence["client_id"],
                        },
                    )
                else:
                    result = await ctx.session.execute(
                        update(StockReportItemSnapshot)
                        .where(
                            StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                            StockReportItemSnapshot.client_id
                            == divergence["client_id"],
                        )
                        .values(
                            active_at=None,
                            quantity_requested_scanner=None,
                            updated_at=ctx.now,
                            updated_by_id=ctx.user_id,
                        )
                    )
                if result.rowcount != 1:
                    raise RuntimeError(
                        "snapshot-state repair affected an unexpected number of rows"
                    )
            elif kind == "snapshot_version_state_mismatch":
                # (i) Never reopen: the snapshot follows its version into the past.
                # Its counters are frozen from the row exactly as a version close does.
                row_counters = (
                    await ctx.session.execute(
                        select(
                            StockReportItem.quantity_in_queue,
                            StockReportItem.quantity_in_progress,
                            StockReportItem.quantity_awaiting,
                        )
                        .join(
                            StockReportItemSnapshot,
                            StockReportItemSnapshot.stock_report_item_id
                            == StockReportItem.client_id,
                        )
                        .where(
                            StockReportItemSnapshot.client_id == divergence["client_id"]
                        )
                    )
                ).one()
                result = await ctx.session.execute(
                    update(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id == divergence["client_id"],
                    )
                    .values(
                        closed_at=datetime.fromisoformat(divergence["expected"]),
                        quantity_in_queue=row_counters[0],
                        quantity_in_progress=row_counters[1],
                        quantity_awaiting=row_counters[2],
                        updated_at=ctx.now,
                        updated_by_id=ctx.user_id,
                    )
                )
                if result.rowcount != 1:
                    raise RuntimeError(
                        "snapshot-close repair affected an unexpected number of rows"
                    )
            elif kind == "goal_total":
                result = await ctx.session.execute(
                    update(StockReportHistoryRecord)
                    .where(
                        StockReportHistoryRecord.workspace_id == ctx.workspace_id,
                        StockReportHistoryRecord.client_id == divergence["client_id"],
                    )
                    .values(quantity_awaiting=divergence["expected"])
                )
                if result.rowcount != 1:
                    raise RuntimeError(
                        "goal-total repair affected an unexpected number of rows"
                    )
            else:
                result = await ctx.session.execute(
                    update(StockReportItem)
                    .where(
                        StockReportItem.workspace_id == ctx.workspace_id,
                        StockReportItem.client_id == divergence["client_id"],
                    )
                    .values(
                        {
                            divergence["field"]: divergence["expected"],
                            "updated_at": ctx.now,
                            "updated_by_id": ctx.user_id,
                        }
                    )
                )
                if result.rowcount != 1:
                    raise RuntimeError(
                        "counter repair affected an unexpected number of rows"
                    )
                changed_row_ids.add(divergence["client_id"])
            await write_repair_record(
                ctx.session,
                workspace_id=ctx.workspace_id,
                target_kind=_TARGETS[kind],
                target_client_id=divergence["client_id"],
                field=divergence["field"],
                stored_value=divergence["stored"],
                recomputed_value=divergence["expected"],
                trigger="manual",
                created_by_id=ctx.user_id,
                now=ctx.now,
            )
            repaired.append(divergence)
        remaining = await compute_stock_report_divergences(
            ctx.session, ctx.workspace_id
        )
        unexpected_remaining = [
            divergence for divergence in remaining if divergence["kind"] != "signature"
        ]
        if unexpected_remaining:
            raise RuntimeError(
                f"stock-report repair left divergences: {unexpected_remaining!r}"
            )
    pending = []
    if changed_row_ids:
        rows = (
            (
                await ctx.session.execute(
                    select(StockReportItem)
                    .where(
                        StockReportItem.workspace_id == ctx.workspace_id,
                        StockReportItem.client_id.in_(sorted(changed_row_ids)),
                    )
                    .order_by(StockReportItem.client_id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        pending.extend(
            build_workspace_event(
                row,
                "stock_report_item:updated",
                extra={
                    "quantity_requested": row.quantity_requested,
                    "quantity_in_queue": row.quantity_in_queue,
                    "quantity_in_progress": row.quantity_in_progress,
                    "quantity_awaiting": row.quantity_awaiting,
                },
            )
            for row in rows
        )
    if changed_snapshot_ids:
        snapshots = (
            (
                await ctx.session.execute(
                    select(StockReportItemSnapshot)
                    .where(
                        StockReportItemSnapshot.workspace_id == ctx.workspace_id,
                        StockReportItemSnapshot.client_id.in_(
                            sorted(changed_snapshot_ids)
                        ),
                    )
                    .order_by(StockReportItemSnapshot.client_id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        pending.extend(
            build_stock_report_item_snapshot_updated_event(
                client_id=snapshot.client_id,
                workspace_id=ctx.workspace_id,
                values=snapshot_values(snapshot),
            )
            for snapshot in snapshots
        )
    if pending:
        await dispatch(pending)
    return {"repaired": repaired, "not_repaired": not_repaired}
