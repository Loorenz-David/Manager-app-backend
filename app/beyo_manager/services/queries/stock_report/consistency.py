from __future__ import annotations
from typing import TypedDict

from sqlalchemy import func, select
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import ACTIVE_ASSIGNMENT_STATES
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
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


async def expected_task_flag(session, task_id: str) -> bool:
    result = await session.execute(
        select(StockTaskAssignment.client_id)
        .where(
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
    priority_groups = {}
    for row in rows:
        if row.priority is not None:
            priority_groups.setdefault(row.priority, []).append(row)
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
        if (row.priority is None) != (row.priority_order is None):
            expected = None
            if row.priority is not None:
                assigned_orders = [
                    candidate.priority_order
                    for candidate in priority_groups[row.priority]
                    if candidate.priority_order is not None
                ]
                expected = max(assigned_orders, default=0) + 1
            found.append(
                {
                    "kind": "priority_order_nullness",
                    "client_id": row.client_id,
                    "field": "priority_order",
                    "stored": row.priority_order,
                    "expected": expected,
                }
            )
    for group in priority_groups.values():
        valid = sorted(
            (row for row in group if row.priority_order is not None),
            key=lambda row: (row.priority_order, row.client_id),
        )
        for expected, row in enumerate(valid, 1):
            if row.priority_order != expected:
                found.append(
                    {
                        "kind": "order_density",
                        "client_id": row.client_id,
                        "field": "priority_order",
                        "stored": row.priority_order,
                        "expected": expected,
                    }
                )
    histories = (
        (
            await session.execute(
                select(StockReportHistoryRecord)
                .where(StockReportHistoryRecord.workspace_id == workspace_id)
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
        expected = await expected_task_flag(session, task.client_id)
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
