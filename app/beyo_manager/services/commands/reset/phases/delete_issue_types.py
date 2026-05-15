from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_type import IssueType


async def delete_issue_types(session: AsyncSession, workspace_id: str) -> None:
    """Delete all IssueType rows for workspace. Phase 7 of reset."""
    await session.execute(
        delete(IssueType).where(
            IssueType.workspace_id == workspace_id,
        )
    )
