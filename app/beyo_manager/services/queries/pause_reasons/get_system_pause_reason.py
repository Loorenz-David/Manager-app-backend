from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason


async def get_system_pause_reason_id(session: AsyncSession, workspace_id: str, slug: str) -> str:
    client_id = await session.scalar(
        select(PauseReason.client_id).where(
            PauseReason.workspace_id == workspace_id,
            PauseReason.slug == slug,
            PauseReason.is_deleted.is_(False),
            PauseReason.is_system_managed.is_(True),
        )
    )
    if client_id is None:
        raise NotFound(f"System pause reason '{slug}' is not configured.")
    return client_id
