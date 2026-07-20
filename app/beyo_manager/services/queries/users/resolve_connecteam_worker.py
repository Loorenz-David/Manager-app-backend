from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile


class AmbiguousConnecteamMappingError(Exception):
    """More than one work profile claims the same external worker ID."""


@dataclass(frozen=True)
class ResolvedConnecteamWorker:
    work_profile_id: str
    user_id: str
    workspace_id: str


async def resolve_connecteam_worker(
    session: AsyncSession,
    *,
    connecteam_user_id: str,
    company_id: str | None = None,
) -> ResolvedConnecteamWorker | None:
    del company_id  # reserved for future company-scoped integration ownership
    value = str(connecteam_user_id).strip()
    if not value:
        return None
    rows = (
        await session.execute(
            select(UserWorkProfile).where(UserWorkProfile.connecteam_user_id == value)
        )
    ).scalars().all()
    if len(rows) > 1:
        raise AmbiguousConnecteamMappingError("Connecteam worker mapping is ambiguous.")
    if not rows:
        return None
    profile = rows[0]
    return ResolvedConnecteamWorker(
        work_profile_id=profile.client_id,
        user_id=profile.user_id,
        workspace_id=profile.workspace_id,
    )

