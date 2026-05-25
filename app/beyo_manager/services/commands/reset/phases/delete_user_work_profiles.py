from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile


async def delete_user_work_profiles(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UserWorkProfile rows for workspace."""
    await session.execute(
        delete(UserWorkProfile).where(
            UserWorkProfile.workspace_id == workspace_id,
        )
    )
