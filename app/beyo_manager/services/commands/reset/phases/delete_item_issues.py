from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item_issue import ItemIssue


async def delete_item_issues(session: AsyncSession, workspace_id: str) -> None:
    """Delete all ItemIssue rows for workspace."""
    await session.execute(
        delete(ItemIssue).where(
            ItemIssue.workspace_id == workspace_id,
        )
    )
