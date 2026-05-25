from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery


async def delete_item_upholsteries(session: AsyncSession, workspace_id: str) -> None:
    """Delete all ItemUpholstery rows for workspace."""
    await session.execute(
        delete(ItemUpholstery).where(
            ItemUpholstery.workspace_id == workspace_id,
        )
    )
