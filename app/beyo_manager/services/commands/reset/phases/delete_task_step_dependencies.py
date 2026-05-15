from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency


async def delete_task_step_dependencies(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskStepDependency rows for workspace."""
    await session.execute(
        delete(TaskStepDependency).where(
            TaskStepDependency.workspace_id == workspace_id,
        )
    )
