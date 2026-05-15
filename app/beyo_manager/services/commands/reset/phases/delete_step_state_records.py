from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord


async def delete_step_state_records(session: AsyncSession, workspace_id: str) -> None:
    """Delete all StepStateRecord rows for workspace."""
    await session.execute(
        delete(StepStateRecord).where(
            StepStateRecord.workspace_id == workspace_id,
        )
    )
