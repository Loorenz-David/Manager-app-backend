from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def delete_workspace_memberships(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkspaceMembership rows for workspace. Phase 9 of reset."""
    await session.execute(
        delete(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
