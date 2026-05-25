from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item import Item


async def delete_items(session: AsyncSession, workspace_id: str) -> None:
    """Delete all Item rows for workspace."""
    await session.execute(
        delete(Item).where(
            Item.workspace_id == workspace_id,
        )
    )
