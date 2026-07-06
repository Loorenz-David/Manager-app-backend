from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def resolve_live_role_name(
    session: AsyncSession,
    *,
    user_id: str,
    workspace_id: str,
) -> str:
    membership_result = await session.execute(
        select(WorkspaceMembership)
        .options(selectinload(WorkspaceMembership.workspace_role).selectinload(WorkspaceRole.role))
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    membership = membership_result.scalar_one_or_none()
    if membership is None:
        raise PermissionDenied("You no longer have access to this workspace.")

    return membership.workspace_role.role.name.value
