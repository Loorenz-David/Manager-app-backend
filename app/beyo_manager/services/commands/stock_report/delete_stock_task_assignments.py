"""`delete_stock_task_assignments` — the batch delete (master plan §6.5; intention §9
"assignment deletion"). Discover unlocked, lock tasks -> rows -> assignments (MC-1
order, no Item tier here), re-read, refuse the whole batch on any absent, deleted or
foreign id, then remove each assignment through `remove_assignment`.
"""

from __future__ import annotations

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._events import (
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._locks import (
    lock_stock_report_items,
    lock_stock_task_assignments,
    lock_tasks,
)
from beyo_manager.services.commands.stock_report._remove_assignment import (
    remove_assignment,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_delete_stock_task_assignments_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch


def _row_values(row) -> dict:
    return {
        "quantity_requested": row.quantity_requested,
        "quantity_in_queue": row.quantity_in_queue,
        "quantity_in_progress": row.quantity_in_progress,
        "quantity_awaiting": row.quantity_awaiting,
        "priority": row.priority.value if row.priority is not None else None,
        "priority_order": row.priority_order,
    }


async def delete_stock_task_assignments(ctx: ServiceContext) -> dict:
    request = parse_delete_stock_task_assignments_request(ctx.incoming_data)
    # De-duplicated once, here, so discovery, the missing-check, the removal loop
    # and the response all read the same set (a repeated id must not be removed,
    # and therefore double-subtracted, twice — master plan §6.5, batch C1 review
    # card 2 / B2).
    ids = sorted(set(request.client_ids))

    async with maybe_begin(ctx.session):
        # Discovery, unlocked — decides only which ids exist, are live and are ours.
        # Absent, soft-deleted and foreign ids are all simply missing from this set.
        discovered = (
            (
                await ctx.session.execute(
                    select(StockTaskAssignment).where(
                        StockTaskAssignment.workspace_id == ctx.workspace_id,
                        StockTaskAssignment.client_id.in_(ids),
                        StockTaskAssignment.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        discovered_by_id = {row.client_id: row for row in discovered}
        missing = sorted(set(ids) - set(discovered_by_id))

        row_ids = {row.stock_report_item_id for row in discovered}
        task_ids = {row.task_id for row in discovered}

        # Locks, MC-1 order (no Item tier: delete touches no Item row). The task
        # lock is held for lock-order correctness only — this command reads no
        # task field, so its result is intentionally discarded.
        await lock_tasks(ctx.session, ctx.workspace_id, task_ids)
        locked_rows = await lock_stock_report_items(ctx.session, ctx.workspace_id, row_ids)
        locked_assignments = await lock_stock_task_assignments(
            ctx.session, ctx.workspace_id, set(discovered_by_id)
        )
        initial_row_values = {
            row_id: _row_values(row) for row_id, row in locked_rows.items()
        }

        # Re-read (§9 rule 4): a concurrent delete between discovery and the lock
        # above is caught here, not assumed away.
        missing.extend(
            sorted(
                client_id
                for client_id, assignment in locked_assignments.items()
                if assignment.is_deleted
            )
        )
        missing = sorted(set(missing))
        if missing:
            raise NotFound(
                f"Stock task assignment(s) not found: {', '.join(missing)}"
            )

        events = []
        for client_id in sorted(ids):
            events.extend(
                await remove_assignment(
                    ctx.session,
                    locked_assignments[client_id],
                    workspace_id=ctx.workspace_id,
                    actor_user_id=ctx.user_id,
                    now=ctx.now,
                    trigger="delete_assignments",
                )
            )

    dispatch_events = coalesce_stock_report_events(
        events, initial_row_values=initial_row_values
    )
    await dispatch(dispatch_events)

    return {"deleted_client_ids": sorted(ids)}
