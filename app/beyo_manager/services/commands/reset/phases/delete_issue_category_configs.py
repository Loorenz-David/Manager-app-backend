from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig


async def delete_issue_category_configs(session: AsyncSession, workspace_id: str) -> None:
    """Delete all IssueCategoryConfig rows for workspace. Phase 1 of reset."""
    await session.execute(
        delete(IssueCategoryConfig).where(
            IssueCategoryConfig.workspace_id == workspace_id,
        )
    )
