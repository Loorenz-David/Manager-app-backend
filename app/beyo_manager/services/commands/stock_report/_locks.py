from sqlalchemy import select, text
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task


async def acquire_stock_report_order_lock(session, workspace_id):
    await session.execute(
        text(
            "SELECT pg_advisory_xact_lock(hashtext('stock_report_order:' || :workspace_id))"
        ),
        {"workspace_id": workspace_id},
    )


async def _lock(session, model, workspace_id, client_ids):
    if not client_ids:
        return {}
    rows = (
        (
            await session.execute(
                select(model)
                .where(
                    model.workspace_id == workspace_id,
                    model.client_id.in_(sorted(client_ids)),
                )
                .order_by(model.client_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    return {row.client_id: row for row in rows}


async def lock_stock_report_items(session, workspace_id, client_ids):
    return await _lock(session, StockReportItem, workspace_id, client_ids)


async def lock_stock_task_assignments(session, workspace_id, client_ids):
    return await _lock(session, StockTaskAssignment, workspace_id, client_ids)


async def lock_items(session, workspace_id, client_ids):
    return await _lock(session, Item, workspace_id, client_ids)


async def lock_tasks(session, workspace_id, client_ids):
    return await _lock(session, Task, workspace_id, client_ids)
