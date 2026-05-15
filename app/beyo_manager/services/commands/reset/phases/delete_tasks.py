from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task import Task


async def delete_tasks(session: AsyncSession, workspace_id: str) -> None:
    """Delete all Task rows for workspace."""
    await session.execute(
        delete(Task).where(
            Task.workspace_id == workspace_id,
        )
    )
