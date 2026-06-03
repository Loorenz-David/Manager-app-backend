from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.items.item_category_issue_type import ItemCategoryIssueType


async def delete_item_category_issue_types(session: AsyncSession, workspace_id: str) -> None:
    await session.execute(
        delete(ItemCategoryIssueType).where(
            ItemCategoryIssueType.workspace_id == workspace_id,
        )
    )
