"""`sync_task_stock_assignments` — MC-2's sync (phase 10; master plan §6.5; intention
§5B).

Called once per command, inside the command's own transaction, after the command's
**last** write to `Task.state`, with every task whose state differs from the
captured one. Runs at command level, never inside `transition_step_state`'s
`_task_state_transitions.py` helpers (§5B "why command level"): a helper-level sync
would move an assignment through an intermediate state the transaction never
settles on, un-crediting and re-crediting the goal for no net task change.
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.stock_report.enums import TERMINAL_ASSIGNMENT_STATES
from beyo_manager.domain.stock_report.state_map import ASSIGNMENT_STATE_BY_TASK_STATE
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._events import (
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_items,
    lock_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report._move_assignment import (
    move_assignment,
)


def _row_values(row) -> dict:
    return {
        "quantity_requested": row.quantity_requested,
        "quantity_in_queue": row.quantity_in_queue,
        "quantity_in_progress": row.quantity_in_progress,
        "quantity_awaiting": row.quantity_awaiting,
        "priority": row.priority.value if row.priority is not None else None,
        "priority_order": row.priority_order,
    }


async def sync_task_stock_assignments(
    session, changed, *, workspace_id, actor_user_id, now
):
    # Step 2 (MC-2): first statement, so this transaction holds the task rows'
    # locks (its own UPDATE) before any read here.
    await session.flush()

    events = []
    initial_row_values: dict[str, dict] = {}

    for task, _old_state in sorted(changed, key=lambda pair: pair[0].client_id):
        # Step 3 — the "cheap skip": a fresh query, never the possibly-stale ORM
        # `task.is_stock_assignment` (§4.4/MC-2 step 3).
        assignment = await session.scalar(
            select(StockTaskAssignment).where(
                StockTaskAssignment.workspace_id == workspace_id,
                StockTaskAssignment.task_id == task.client_id,
                StockTaskAssignment.is_deleted.is_(False),
            )
        )
        if assignment is None:
            continue

        target = ASSIGNMENT_STATE_BY_TASK_STATE[task.state]

        # Step 5 — lock the row, then the assignment (MC-1 order), re-read.
        locked_rows = await lock_stock_report_items(
            session, workspace_id, [assignment.stock_report_item_id]
        )
        row = locked_rows[assignment.stock_report_item_id]
        if row.client_id not in initial_row_values:
            initial_row_values[row.client_id] = _row_values(row)
        locked_assignments = await lock_stock_task_assignments(
            session, workspace_id, [assignment.client_id]
        )
        assignment = locked_assignments[assignment.client_id]

        if assignment.is_deleted or assignment.state in TERMINAL_ASSIGNMENT_STATES:
            continue
        if assignment.state == target:
            continue

        events.extend(
            await move_assignment(
                session,
                assignment,
                target,
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                now=now,
                trigger="task_sync",
            )
        )

    return coalesce_stock_report_events(events, initial_row_values=initial_row_values)
