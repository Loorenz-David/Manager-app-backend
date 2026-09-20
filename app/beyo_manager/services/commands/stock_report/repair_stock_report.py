from sqlalchemy import select, update
from beyo_manager.domain.stock_report.enums import StockReportRepairTargetKindEnum
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._repair_records import (
    write_repair_record,
)
from beyo_manager.services.commands.stock_report._task_flag import set_task_stock_flag
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
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
    "priority_order_nullness": StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
    "order_density": StockReportRepairTargetKindEnum.GROUP,
}


async def _repair_priority_orders(ctx, repaired, changed_row_ids):
    """Densify each priority group and record the net, not intermediate, changes."""
    rows = (
        (
            await ctx.session.execute(
                select(StockReportItem)
                .where(
                    StockReportItem.workspace_id == ctx.workspace_id,
                    StockReportItem.is_deleted.is_(False),
                )
                .order_by(
                    StockReportItem.priority,
                    StockReportItem.priority_order,
                    StockReportItem.client_id,
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        if row.priority is None and row.priority_order is not None:
            stored = row.priority_order
            result = await ctx.session.execute(
                update(StockReportItem)
                .where(
                    StockReportItem.workspace_id == ctx.workspace_id,
                    StockReportItem.client_id == row.client_id,
                )
                .values(
                    priority_order=None,
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
                target_kind=StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM,
                target_client_id=row.client_id,
                field="priority_order",
                stored_value=stored,
                recomputed_value=None,
                trigger="manual",
                created_by_id=ctx.user_id,
                now=ctx.now,
            )
            repaired.append(
                {
                    "kind": "priority_order_nullness",
                    "client_id": row.client_id,
                    "field": "priority_order",
                    "stored": stored,
                    "expected": None,
                }
            )
            changed_row_ids.add(row.client_id)

    groups = {}
    for row in rows:
        if row.priority is not None:
            groups.setdefault(row.priority, []).append(row)
    for group_rows in groups.values():
        ordered = sorted(
            group_rows,
            key=lambda row: (
                row.priority_order is None,
                row.priority_order if row.priority_order is not None else 0,
                row.client_id,
            ),
        )
        for expected, row in enumerate(ordered, 1):
            if row.priority_order == expected:
                continue
            stored = row.priority_order
            result = await ctx.session.execute(
                update(StockReportItem)
                .where(
                    StockReportItem.workspace_id == ctx.workspace_id,
                    StockReportItem.client_id == row.client_id,
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
                target_kind=(
                    StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM
                    if stored is None
                    else StockReportRepairTargetKindEnum.GROUP
                ),
                target_client_id=row.client_id,
                field="priority_order",
                stored_value=stored,
                recomputed_value=expected,
                trigger="manual",
                created_by_id=ctx.user_id,
                now=ctx.now,
            )
            repaired.append(
                {
                    "kind": (
                        "priority_order_nullness" if stored is None else "order_density"
                    ),
                    "client_id": row.client_id,
                    "field": "priority_order",
                    "stored": stored,
                    "expected": expected,
                }
            )
            changed_row_ids.add(row.client_id)


async def repair_stock_report(ctx) -> dict:
    repaired = []
    not_repaired = []
    changed_row_ids = set()
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
        # Nullness changes establish the ordering population before density is recomputed.
        divergences.sort(
            key=lambda item: (
                item["kind"] == "order_density",
                item["kind"],
                item["client_id"],
            )
        )
        if any(
            divergence["kind"] in {"priority_order_nullness", "order_density"}
            for divergence in divergences
        ):
            await _repair_priority_orders(ctx, repaired, changed_row_ids)
        for divergence in divergences:
            kind = divergence["kind"]
            if kind in {"priority_order_nullness", "order_density"}:
                continue
            if kind == "signature":
                not_repaired.append(divergence)
                continue
            if kind == "task_flag":
                await set_task_stock_flag(
                    ctx.session,
                    divergence["client_id"],
                    divergence["expected"] == "true",
                    require_update=True,
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
                )
            )
            .scalars()
            .all()
        )
        await dispatch(
            [
                build_workspace_event(
                    row,
                    "stock_report_item:updated",
                    extra={
                        "quantity_requested": row.quantity_requested,
                        "quantity_in_queue": row.quantity_in_queue,
                        "quantity_in_progress": row.quantity_in_progress,
                        "quantity_awaiting": row.quantity_awaiting,
                        "priority": row.priority.value if row.priority else None,
                        "priority_order": row.priority_order,
                    },
                )
                for row in rows
            ]
        )
    return {"repaired": repaired, "not_repaired": not_repaired}
