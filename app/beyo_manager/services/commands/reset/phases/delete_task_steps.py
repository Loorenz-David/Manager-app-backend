from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_step import TaskStep


async def delete_task_steps(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskStep rows for workspace."""
    await session.execute(
        delete(TaskStep).where(
            TaskStep.workspace_id == workspace_id,
        )
    )
