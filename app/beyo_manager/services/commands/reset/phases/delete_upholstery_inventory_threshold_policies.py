from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.upholstery.upholstery_inventory_threshold_policy import UpholsteryInventoryThresholdPolicy


async def delete_upholstery_inventory_threshold_policies(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UpholsteryInventoryThresholdPolicy rows for workspace."""
    await session.execute(
        delete(UpholsteryInventoryThresholdPolicy).where(
            UpholsteryInventoryThresholdPolicy.workspace_id == workspace_id,
        )
    )
