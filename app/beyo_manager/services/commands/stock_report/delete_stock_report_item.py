"""`DELETE /api/v1/stock-report/items/{client_id}` (master plan §6.5, phase 13;
intention §9, §5A MC-16).

`DELETE` takes **no body** (§9B ruling 1): `client_id` travels in the path and the
router injects it into `incoming_data`, so there is no request model to parse.
"""

from __future__ import annotations

from sqlalchemy import or_, select, tuple_

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
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
from beyo_manager.services.commands.stock_report._predicates import snapshot_is_open
from beyo_manager.services.commands.stock_report._row_values import row_values
from beyo_manager.services.commands.stock_report._snapshot_values import (
    snapshot_values,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch


async def _lock_row(session, workspace_id, client_id):
    """The row, locked (MC-1 step 4).

    This is also the command's post-lock re-read and its whole visibility boundary:
    `workspace_id` and `is_deleted = false` live here, so an absent, soft-deleted or
    foreign id simply is not in the result and the caller raises `NotFound`.
    """
    return await session.scalar(
        select(StockReportItem)
        .where(
            StockReportItem.workspace_id == workspace_id,
            StockReportItem.client_id == client_id,
            StockReportItem.is_deleted.is_(False),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def lock_active_snapshots_and_groups(session, workspace_id, row_ids):
    """The rows' **open** snapshots (the active one and every draft's, 2026-09-28)
    **and** every open snapshot of their `(version_id, priority)` groups, in one
    `SELECT … FOR UPDATE ORDER BY client_id` (MC-7 "Serialization", on the snapshot
    table since 2026-09-26). Shared with the Scanner delete webhook.
    """
    row_ids = sorted(set(row_ids))
    if not row_ids:
        return {}
    group_keys = select(
        StockReportItemSnapshot.version_id, StockReportItemSnapshot.priority
    ).where(
        StockReportItemSnapshot.workspace_id == workspace_id,
        StockReportItemSnapshot.stock_report_item_id.in_(row_ids),
        snapshot_is_open(),
        StockReportItemSnapshot.priority.is_not(None),
    )
    snapshots = (
        (
            await session.execute(
                select(StockReportItemSnapshot)
                .where(
                    StockReportItemSnapshot.workspace_id == workspace_id,
                    snapshot_is_open(),
                    or_(
                        StockReportItemSnapshot.stock_report_item_id.in_(row_ids),
                        tuple_(
                            StockReportItemSnapshot.version_id,
                            StockReportItemSnapshot.priority,
                        ).in_(group_keys),
                    ),
                )
                .order_by(StockReportItemSnapshot.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    return {snapshot.client_id: snapshot for snapshot in snapshots}


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

        # MC-1's lock order: advisory -> tasks -> stock_report_items ->
        # stock_report_item_snapshots (the row's active one + its group) ->
        # stock_task_assignments, ascending `client_id` within each class. The task
        # lock is held for lock-order correctness; this command reads no task field.
        await lock_tasks(
            ctx.session,
            ctx.workspace_id,
            {task_id for _assignment_id, task_id in discovered_assignments},
        )
        row = await _lock_row(ctx.session, ctx.workspace_id, client_id)
        locked_snapshots = await lock_active_snapshots_and_groups(
            ctx.session, ctx.workspace_id, [client_id] if discovered else []
        )
        await lock_stock_task_assignments(
            ctx.session,
            ctx.workspace_id,
            {assignment_id for assignment_id, _task_id in discovered_assignments},
        )

        if row is None or row.is_deleted:
            raise NotFound("Stock report item not found.")

        initial_row_values = {client_id: row_values(row)}
        initial_snapshot_values = {
            snapshot_id: snapshot_values(snapshot)
            for snapshot_id, snapshot in locked_snapshots.items()
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
        coalesce_stock_report_events(
            events,
            initial_row_values=initial_row_values,
            initial_snapshot_values=initial_snapshot_values,
        )
    )
    return {"client_id": client_id}
