from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.audit.audit_log import AuditLog


async def delete_audit_logs(session: AsyncSession, workspace_id: str) -> None:
    """Delete all AuditLog rows for workspace. Phase 11 of reset."""
    await session.execute(
        delete(AuditLog).where(
            AuditLog.workspace_id == workspace_id,
        )
    )
