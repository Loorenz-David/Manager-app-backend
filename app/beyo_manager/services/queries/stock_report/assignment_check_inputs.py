from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.stock_report.enums import (
    ACTIVE_ASSIGNMENT_STATES,
    StockTaskAssignmentStateEnum,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task_item import TaskItem


_SCANNER_PROCESSED_STATES = frozenset(
    {
        StockTaskAssignmentStateEnum.RESOLVED,
        StockTaskAssignmentStateEnum.RESOLVED_EARLY,
    }
)


async def fetch_assignment_check_inputs(
    session, *, workspace_id, task_ids, item_ids
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[str]]:
    if task_ids and item_ids:
        primary_rows = await session.execute(
            select(TaskItem.task_id, TaskItem.item_id).where(
                TaskItem.workspace_id == workspace_id,
                TaskItem.task_id.in_(task_ids),
                TaskItem.item_id.in_(item_ids),
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
                TaskItem.removed_at.is_(None),
            )
        )
        primary_pairs = {(task_id, item_id) for task_id, item_id in primary_rows}

        processed_rows = await session.execute(
            select(StockTaskAssignment.task_id, StockTaskAssignment.item_id)
            .where(
                StockTaskAssignment.workspace_id == workspace_id,
                StockTaskAssignment.task_id.in_(task_ids),
                StockTaskAssignment.item_id.in_(item_ids),
                StockTaskAssignment.is_deleted.is_(False),
                StockTaskAssignment.state.in_(_SCANNER_PROCESSED_STATES),
            )
            .distinct()
        )
        processed_pairs = {
            (task_id, item_id) for task_id, item_id in processed_rows
        }
    else:
        primary_pairs = set()
        processed_pairs = set()

    if item_ids:
        active_rows = await session.execute(
            select(StockTaskAssignment.item_id)
            .where(
                StockTaskAssignment.workspace_id == workspace_id,
                StockTaskAssignment.item_id.in_(item_ids),
                StockTaskAssignment.is_deleted.is_(False),
                StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
            )
            .distinct()
        )
        active_item_ids = {item_id for (item_id,) in active_rows}
    else:
        active_item_ids = set()

    return primary_pairs, processed_pairs, active_item_ids
