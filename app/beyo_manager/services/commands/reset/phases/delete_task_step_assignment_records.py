from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_step_assignment_record import TaskStepAssignmentRecord


async def delete_task_step_assignment_records(session: AsyncSession, workspace_id: str) -> None:
    """Delete all TaskStepAssignmentRecord rows for workspace."""
    await session.execute(
        delete(TaskStepAssignmentRecord).where(
            TaskStepAssignmentRecord.workspace_id == workspace_id,
        )
    )
