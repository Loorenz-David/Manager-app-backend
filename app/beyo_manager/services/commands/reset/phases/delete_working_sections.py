from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section import WorkingSection


async def delete_working_sections(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkingSection rows for workspace. Phase 5 of reset."""
    await session.execute(
        delete(WorkingSection).where(
            WorkingSection.workspace_id == workspace_id,
        )
    )
