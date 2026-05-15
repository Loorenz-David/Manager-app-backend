from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole


async def delete_orphan_bootstrap_roles(session: AsyncSession) -> int:
    """
    Delete bootstrap global roles only when no workspace_role references them.
    """
    has_workspace_role = exists(
        select(WorkspaceRole.client_id).where(WorkspaceRole.role_id == Role.client_id)
    )

    result = await session.execute(
        delete(Role).where(
            Role.name.in_(
                [
                    RoleNameEnum.ADMIN,
                    RoleNameEnum.WORKER,
                    RoleNameEnum.MANAGER,
                    RoleNameEnum.SELLER,
                ]
            ),
            ~has_workspace_role,
        )
    )
    return result.rowcount or 0
