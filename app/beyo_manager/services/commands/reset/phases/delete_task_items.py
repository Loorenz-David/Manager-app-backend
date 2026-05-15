from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_item import TaskItem


async def delete_task_items(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskItem rows for workspace."""
    await session.execute(
        delete(TaskItem).where(
            TaskItem.workspace_id == workspace_id,
        )
    )
