from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats


async def delete_user_lifetime_stats(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UserLifetimeStats rows for workspace."""
    await session.execute(
        delete(UserLifetimeStats).where(
            UserLifetimeStats.workspace_id == workspace_id,
        )
    )
