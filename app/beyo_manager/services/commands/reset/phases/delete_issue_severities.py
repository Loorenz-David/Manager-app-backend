from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.issue_types.issue_severity import IssueSeverity


async def delete_issue_severities(session: AsyncSession, workspace_id: str) -> None:
    """Delete all IssueSeverity rows for workspace. Phase 6 of reset."""
    await session.execute(
        delete(IssueSeverity).where(
            IssueSeverity.workspace_id == workspace_id,
        )
    )
