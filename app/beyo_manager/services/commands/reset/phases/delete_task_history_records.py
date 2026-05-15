from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_history_record import TaskHistoryRecord


async def delete_task_history_records(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskHistoryRecord rows for workspace."""
    await session.execute(
        delete(TaskHistoryRecord).where(
            TaskHistoryRecord.workspace_id == workspace_id,
        )
    )
