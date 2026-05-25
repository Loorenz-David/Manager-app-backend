from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats


async def delete_user_section_daily_work_stats(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UserSectionDailyWorkStats rows for workspace."""
    await session.execute(
        delete(UserSectionDailyWorkStats).where(
            UserSectionDailyWorkStats.workspace_id == workspace_id,
        )
    )
