from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats


async def delete_working_section_daily_work_stats(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkingSectionDailyWorkStats rows for workspace."""
    await session.execute(
        delete(WorkingSectionDailyWorkStats).where(
            WorkingSectionDailyWorkStats.workspace_id == workspace_id,
        )
    )
