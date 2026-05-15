from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.upholstery.upholstery_inventory import UpholsteryInventory


async def delete_upholstery_inventories(session: AsyncSession, workspace_id: str) -> None:
    """Delete all UpholsteryInventory rows for workspace."""
    await session.execute(
        delete(UpholsteryInventory).where(
            UpholsteryInventory.workspace_id == workspace_id,
        )
    )
