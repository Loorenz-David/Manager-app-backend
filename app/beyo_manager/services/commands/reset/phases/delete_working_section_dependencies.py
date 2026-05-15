from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency


async def delete_working_section_dependencies(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkingSectionDependency rows for workspace. Phase 4 of reset."""
    await session.execute(
        delete(WorkingSectionDependency).where(
            WorkingSectionDependency.workspace_id == workspace_id,
        )
    )
