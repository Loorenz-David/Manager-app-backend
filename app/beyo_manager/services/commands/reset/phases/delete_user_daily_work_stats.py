from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats


async def delete_user_daily_work_stats(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UserDailyWorkStats rows for workspace."""
    await session.execute(
        delete(UserDailyWorkStats).where(
            UserDailyWorkStats.workspace_id == workspace_id,
        )
    )
