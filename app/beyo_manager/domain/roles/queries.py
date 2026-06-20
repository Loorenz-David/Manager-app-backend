from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def get_manager_user_ids(session: AsyncSession, workspace_id: str) -> set[str]:
    rows = await session.execute(
        select(WorkspaceMembership.user_id)
        .join(WorkspaceRole, WorkspaceMembership.workspace_role_id == WorkspaceRole.client_id)
        .join(Role, WorkspaceRole.role_id == Role.client_id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
            Role.name == RoleNameEnum.MANAGER,
        )
        .distinct()
    )
    return set(rows.scalars().all())
