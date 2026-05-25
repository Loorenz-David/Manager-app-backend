from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_note import TaskNote


async def delete_task_notes(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskNote rows for workspace."""
    await session.execute(
        delete(TaskNote).where(
            TaskNote.workspace_id == workspace_id,
        )
    )
