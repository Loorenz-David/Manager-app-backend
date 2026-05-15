from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_event import TaskEvent


async def delete_task_events(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskEvent rows for workspace."""
    await session.execute(
        delete(TaskEvent).where(
            TaskEvent.workspace_id == workspace_id,
        )
    )
