from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item_category import ItemCategory


async def delete_item_categories(session: AsyncSession, workspace_id: str) -> None:
    """Delete all ItemCategory rows for workspace. Phase 8 of reset."""
    await session.execute(
        delete(ItemCategory).where(
            ItemCategory.workspace_id == workspace_id,
        )
    )
