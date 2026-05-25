from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord


async def delete_step_state_records(session: AsyncSession, workspace_id: str) -> None:
    """Delete all StepStateRecord rows for workspace."""
    # Break circular FK: task_steps.latest_state_record_id -> step_state_records.client_id
    await session.execute(
        update(TaskStep)
        .where(TaskStep.workspace_id == workspace_id)
        .values(latest_state_record_id=None)
    )

    await session.execute(
        delete(StepStateRecord).where(
            StepStateRecord.workspace_id == workspace_id,
        )
    )
