from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.files.pending_upload import PendingUpload


async def delete_pending_uploads(session: AsyncSession, workspace_id: str) -> None:
    """Delete all PendingUpload rows for workspace."""
    await session.execute(
        delete(PendingUpload).where(
            PendingUpload.workspace_id == workspace_id,
        )
    )
