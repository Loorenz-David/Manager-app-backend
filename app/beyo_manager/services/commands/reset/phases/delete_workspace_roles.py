from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole


async def delete_workspace_roles(session: AsyncSession, workspace_id: str) -> None:
    """Delete all WorkspaceRole rows for workspace. Phase 11 of reset."""
    await session.execute(
        delete(WorkspaceRole).where(
            WorkspaceRole.workspace_id == workspace_id,
        )
    )
