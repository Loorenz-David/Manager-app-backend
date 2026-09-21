"""`DELETE /api/v1/stock-report/items/{client_id}` (master plan §6.5, phase 13;
intention §9, §5A MC-16).

`DELETE` takes **no body** (§9B ruling 1): `client_id` travels in the path and the
router injects it into `incoming_data`, so there is no request model to parse.
"""

from __future__ import annotations

from sqlalchemy import or_, select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report._delete_stock_report_item_cascade import (
    cascade_delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report._events import (
    coalesce_stock_report_events,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
    lock_stock_task_assignments,
    lock_tasks,
)
from beyo_manager.services.commands.stock_report._row_values import row_values
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch


async def _lock_row_and_group(session, workspace_id, client_id, priority):
    """The row **and** its priority group in one statement ordered by `client_id`
    (MC-1 step 4 / MC-7 "Serialization").

    This is also the command's post-lock re-read and its whole visibility boundary:
    `workspace_id` and `is_deleted = false` live here, so an absent, soft-deleted or
    foreign id simply is not in the result and the caller raises `NotFound`.
    """
    predicate = StockReportItem.client_id == client_id
    if priority is not None:
        predicate = or_(predicate, StockReportItem.priority == priority)
    rows = (
        (
            await session.execute(
                select(StockReportItem)
                .where(
                    StockReportItem.workspace_id == workspace_id,
                    StockReportItem.is_deleted.is_(False),
                    predicate,
                )
                .order_by(StockReportItem.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    return {row.client_id: row for row in rows}


async def delete_stock_report_item(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)

        # Unlocked discovery — it decides only which ids to lock (§9 rule 4).
        discovered = await ctx.session.scalar(
            select(StockReportItem).where(
                StockReportItem.workspace_id == ctx.workspace_id,
                StockReportItem.client_id == client_id,
                StockReportItem.is_deleted.is_(False),
            )
        )
        discovered_assignments = (
            await ctx.session.execute(
                select(
                    StockTaskAssignment.client_id, StockTaskAssignment.task_id
                ).where(
                    StockTaskAssignment.workspace_id == ctx.workspace_id,
                    StockTaskAssignment.stock_report_item_id == client_id,
                    StockTaskAssignment.is_deleted.is_(False),
                )
            )
        ).all()

        # MC-1's lock order: advisory -> tasks -> stock_report_items (+ group) ->
        # stock_task_assignments, ascending `client_id` within each class. The task
        # lock is held for lock-order correctness; this command reads no task field.
        await lock_tasks(
            ctx.session,
            ctx.workspace_id,
            {task_id for _assignment_id, task_id in discovered_assignments},
        )
        locked = await _lock_row_and_group(
            ctx.session,
            ctx.workspace_id,
            client_id,
            discovered.priority if discovered is not None else None,
        )
        await lock_stock_task_assignments(
            ctx.session,
            ctx.workspace_id,
            {assignment_id for assignment_id, _task_id in discovered_assignments},
        )

        row = locked.get(client_id)
        if row is None or row.is_deleted:
            raise NotFound("Stock report item not found.")

        initial_row_values = {
            row_id: row_values(candidate) for row_id, candidate in locked.items()
        }
        events = await cascade_delete_stock_report_item(
            ctx.session,
            row,
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            now=ctx.now,
            trigger="delete_stock_report_item",
        )

    await dispatch(
        coalesce_stock_report_events(events, initial_row_values=initial_row_values)
    )
    return {"client_id": client_id}
