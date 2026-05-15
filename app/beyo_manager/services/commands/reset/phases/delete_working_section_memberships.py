from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership


async def delete_working_section_memberships(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkingSectionMembership rows for workspace."""
    await session.execute(
        delete(WorkingSectionMembership).where(
            WorkingSectionMembership.workspace_id == workspace_id,
        )
    )
