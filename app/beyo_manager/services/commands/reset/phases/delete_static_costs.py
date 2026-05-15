from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.static_costs.static_cost import StaticCost


async def delete_static_costs(session: AsyncSession, workspace_id: str) -> None:
    """Delete all StaticCost rows for workspace."""
    await session.execute(
        delete(StaticCost).where(
            StaticCost.workspace_id == workspace_id,
        )
    )
