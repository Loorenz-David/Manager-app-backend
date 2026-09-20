from sqlalchemy import update
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.queries.stock_report.consistency import expected_task_flag


async def set_task_stock_flag(session, task_id, value, *, require_update=False):
    result = await session.execute(
        update(Task)
        .where(
            Task.client_id == task_id, Task.is_stock_assignment.is_distinct_from(value)
        )
        .values(is_stock_assignment=value, updated_at=Task.updated_at)
    )
    if result.rowcount not in (0, 1) or (require_update and result.rowcount != 1):
        raise RuntimeError("task flag update affected an unexpected number of rows")


async def recompute_task_stock_flag(session, workspace_id, task_id):
    expected = await expected_task_flag(session, workspace_id, task_id)
    await set_task_stock_flag(session, task_id, expected)
    return expected
