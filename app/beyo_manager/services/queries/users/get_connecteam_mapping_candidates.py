"""Bulk candidate loader for the Connecteam user mapping command."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile


@dataclass(frozen=True)
class InternalConnecteamMappingCandidate:
    user_id: str
    username: str
    user_work_profile_id: str | None
    workspace_id: str | None
    connecteam_user_id: str | None


async def get_connecteam_mapping_candidates(
    session: AsyncSession,
    *,
    workspace_id: str | None = None,
) -> list[InternalConnecteamMappingCandidate]:
    profile_join = UserWorkProfile.user_id == User.client_id
    if workspace_id is not None:
        profile_join = and_(profile_join, UserWorkProfile.workspace_id == workspace_id)

    result = await session.execute(
        select(
            User.client_id,
            User.username,
            UserWorkProfile.client_id,
            UserWorkProfile.workspace_id,
            UserWorkProfile.connecteam_user_id,
        )
        .outerjoin(UserWorkProfile, profile_join)
        .order_by(User.username.asc(), UserWorkProfile.client_id.asc())
    )
    return [
        InternalConnecteamMappingCandidate(
            user_id=user_id,
            username=username,
            user_work_profile_id=profile_id,
            workspace_id=profile_workspace_id,
            connecteam_user_id=connecteam_id,
        )
        for user_id, username, profile_id, profile_workspace_id, connecteam_id in result.all()
    ]
