from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.upholstery.upholstery import Upholstery


async def delete_upholsteries(session: AsyncSession, workspace_id: str) -> None:
    """Delete all Upholstery rows for workspace."""
    await session.execute(
        delete(Upholstery).where(
            Upholstery.workspace_id == workspace_id,
        )
    )
