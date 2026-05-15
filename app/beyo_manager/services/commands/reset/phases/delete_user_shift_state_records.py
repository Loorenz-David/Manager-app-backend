from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord


async def delete_user_shift_state_records(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UserShiftStateRecord rows for workspace."""
    await session.execute(
        delete(UserShiftStateRecord).where(
            UserShiftStateRecord.workspace_id == workspace_id,
        )
    )
