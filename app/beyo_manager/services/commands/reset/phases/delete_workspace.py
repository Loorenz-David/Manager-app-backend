from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.workspaces.workspace import Workspace


async def delete_workspace(session: AsyncSession, workspace_id: str) -> None:
    """Delete the Workspace row itself. Phase 12 of reset (final)."""
    await session.execute(
        delete(Workspace).where(
            Workspace.client_id == workspace_id,
        )
    )
