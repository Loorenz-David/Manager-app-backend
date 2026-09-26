from __future__ import annotations
from typing import TypedDict

from sqlalchemy import func, select
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import (
    ACTIVE_ASSIGNMENT_STATES,
    StockReportHistoryRecordTypeEnum,
)
from beyo_manager.domain.stock_report.snapshot_rules import missing_quantity_ceiling
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
from beyo_manager.models.tables.tasks.task import Task


class Divergence(TypedDict):
    kind: str
    client_id: str
    field: str
    stored: object
    expected: object


async def recompute_row_counters(session, stock_report_item_id: str) -> dict[str, int]:
    result = await session.execute(
        select(
            StockTaskAssignment.state,
            func.coalesce(func.sum(StockTaskAssignment.quantity), 0),
        )
        .where(
            StockTaskAssignment.stock_report_item_id == stock_report_item_id,
            StockTaskAssignment.is_deleted.is_(False),
            StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
        )
        .group_by(StockTaskAssignment.state)
    )
    counters = {
        "quantity_in_queue": 0,
        "quantity_in_progress": 0,
        "quantity_awaiting": 0,
    }
    for state, total in result:
        counters[f"quantity_{state.value}"] = total
    return counters


async def _recompute_row_counters_for_workspace(
    session, workspace_id: str
) -> dict[str, dict[str, int]]:
    rows = await session.execute(
        select(
            StockTaskAssignment.stock_report_item_id,
            StockTaskAssignment.state,
            func.coalesce(func.sum(StockTaskAssignment.quantity), 0),
        )
        .where(
            StockTaskAssignment.workspace_id == workspace_id,
            StockTaskAssignment.is_deleted.is_(False),
            StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
        )
        .group_by(StockTaskAssignment.stock_report_item_id, StockTaskAssignment.state)
    )
    out = {}
    for row_id, state, total in rows:
        out.setdefault(
            row_id,
            {"quantity_in_queue": 0, "quantity_in_progress": 0, "quantity_awaiting": 0},
        )[f"quantity_{state.value}"] = total
    return out


async def recompute_goal_total(session, history_record_id: str) -> int:
    result = await session.scalar(
        select(func.coalesce(func.sum(StockTaskAssignment.quantity), 0)).where(
            StockTaskAssignment.credited_history_record_id == history_record_id
        )
    )
    return result or 0


async def _recompute_goal_totals_for_workspace(
    session, workspace_id: str
) -> dict[str, int]:
    result = await session.execute(
        select(
            StockTaskAssignment.credited_history_record_id,
            func.coalesce(func.sum(StockTaskAssignment.quantity), 0),
        )
        .where(
            StockTaskAssignment.workspace_id == workspace_id,
            StockTaskAssignment.credited_history_record_id.is_not(None),
        )
        .group_by(StockTaskAssignment.credited_history_record_id)
    )
    return dict(result.all())


async def expected_task_flag(session, workspace_id: str, task_id: str) -> bool:
    result = await session.execute(
        select(StockTaskAssignment.client_id)
        .where(
            StockTaskAssignment.workspace_id == workspace_id,
            StockTaskAssignment.task_id == task_id,
            StockTaskAssignment.is_deleted.is_(False),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def compute_stock_report_divergences(
    session, workspace_id: str
) -> list[Divergence]:
    counters = await _recompute_row_counters_for_workspace(session, workspace_id)
    goals = await _recompute_goal_totals_for_workspace(session, workspace_id)
    found: list[Divergence] = []
    rows = (
        (
            await session.execute(
                select(StockReportItem)
                .where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                )
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    rows_by_id = {row.client_id: row for row in rows}
    for row in rows:
        expected = counters.get(
            row.client_id,
            {"quantity_in_queue": 0, "quantity_in_progress": 0, "quantity_awaiting": 0},
        )
        for field in expected:
            stored = getattr(row, field)
            if stored != expected[field]:
                found.append(
                    {
                        "kind": f"counter_{field.removeprefix('quantity_')}",
                        "client_id": row.client_id,
                        "field": field,
                        "stored": stored,
                        "expected": expected[field],
                    }
                )
        signature = compute_stock_criteria_signature(row.properties)
        if row.properties_signature != signature:
            found.append(
                {
                    "kind": "signature",
                    "client_id": row.client_id,
                    "field": "properties_signature",
                    "stored": row.properties_signature,
                    "expected": signature,
                }
            )

    # The snapshot layer (2026-09-26): the ordering checks moved to the **active**
    # snapshots (`client_id` is the snapshot's), plus the missing-quantity ceiling
    # and the one half-applied-close shape a version close could leave behind.
    # There is no `priority_order_nullness` kind any more: the snapshot table's
    # `ck_stock_report_item_snapshots_priority_order_pairing` makes a half-null
    # position unstorable, so the check would be unreachable.
    snapshots = (
        (
            await session.execute(
                select(StockReportItemSnapshot)
                .where(
                    StockReportItemSnapshot.workspace_id == workspace_id,
                    StockReportItemSnapshot.closed_at.is_(None),
                )
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    closed_version_closed_at = {
        version_id: closed_at
        for version_id, closed_at in (
            await session.execute(
                select(
                    StockReportSnapshotVersion.client_id,
                    StockReportSnapshotVersion.closed_at,
                ).where(
                    StockReportSnapshotVersion.workspace_id == workspace_id,
                    StockReportSnapshotVersion.closed_at.is_not(None),
                )
            )
        ).all()
    }
    priority_groups = {}
    for snapshot in snapshots:
        if snapshot.priority is not None:
            priority_groups.setdefault(snapshot.priority, []).append(snapshot)
    for snapshot in snapshots:
        row = rows_by_id.get(snapshot.stock_report_item_id)
        if row is not None:
            ceiling = missing_quantity_ceiling(
                quantity_requested=snapshot.quantity_requested,
                quantity_in_queue=row.quantity_in_queue,
                quantity_in_progress=row.quantity_in_progress,
                quantity_awaiting=row.quantity_awaiting,
                quantity_resolved=snapshot.quantity_resolved,
            )
            if snapshot.quantity_missing > ceiling:
                found.append(
                    {
                        "kind": "missing_over_ceiling",
                        "client_id": snapshot.client_id,
                        "field": "quantity_missing",
                        "stored": snapshot.quantity_missing,
                        "expected": ceiling,
                    }
                )
        if snapshot.version_id in closed_version_closed_at:
            found.append(
                {
                    "kind": "snapshot_version_closed_mismatch",
                    "client_id": snapshot.client_id,
                    "field": "closed_at",
                    "stored": None,
                    "expected": closed_version_closed_at[snapshot.version_id].isoformat(),
                }
            )
    for group in priority_groups.values():
        valid = sorted(
            group, key=lambda snapshot: (snapshot.priority_order, snapshot.client_id)
        )
        for expected, snapshot in enumerate(valid, 1):
            if snapshot.priority_order != expected:
                found.append(
                    {
                        "kind": "order_density",
                        "client_id": snapshot.client_id,
                        "field": "priority_order",
                        "stored": snapshot.priority_order,
                        "expected": expected,
                    }
                )
    histories = (
        (
            await session.execute(
                select(StockReportHistoryRecord)
                .where(
                    StockReportHistoryRecord.workspace_id == workspace_id,
                    StockReportHistoryRecord.type
                    == StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
                )
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    for history in histories:
        expected = goals.get(history.client_id, 0)
        if history.quantity_awaiting != expected:
            found.append(
                {
                    "kind": "goal_total",
                    "client_id": history.client_id,
                    "field": "quantity_awaiting",
                    "stored": history.quantity_awaiting,
                    "expected": expected,
                }
            )
    tasks = (
        (
            await session.execute(
                select(Task)
                .where(Task.workspace_id == workspace_id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    for task in tasks:
        expected = await expected_task_flag(session, workspace_id, task.client_id)
        if task.is_stock_assignment != expected:
            found.append(
                {
                    "kind": "task_flag",
                    "client_id": task.client_id,
                    "field": "is_stock_assignment",
                    "stored": str(task.is_stock_assignment).lower(),
                    "expected": str(expected).lower(),
                }
            )
    return sorted(found, key=lambda d: (d["kind"], d["client_id"], d["field"]))
