from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)


async def delete_working_section_supported_issue_types(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkingSectionSupportedIssueType rows for workspace. Phase 3 of reset."""
    await session.execute(
        delete(WorkingSectionSupportedIssueType).where(
            WorkingSectionSupportedIssueType.workspace_id == workspace_id,
        )
    )
