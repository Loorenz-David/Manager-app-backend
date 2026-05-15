from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace import Workspace

_DISPLAY_NAMES: dict[str, str] = {
    "admin": "Admin",
    "worker": "Worker",
    "manager": "Manager",
    "seller": "Seller",
}


async def seed_workspace(
    session: AsyncSession,
    settings: Settings,
    role_ids: dict[str, str],
) -> dict[str, str]:
    existing_workspace = await session.scalar(select(Workspace).limit(1))
    if existing_workspace is None:
        workspace = Workspace(
            name=settings.bootstrap_workspace_name,
            time_zone=settings.bootstrap_workspace_timezone,
        )
        session.add(workspace)
        await session.flush()
        workspace_id = workspace.client_id
    else:
        workspace_id = existing_workspace.client_id

    result: dict[str, str] = {"workspace_id": workspace_id}

    existing_roles = await session.execute(
        select(WorkspaceRole).where(WorkspaceRole.workspace_id == workspace_id)
    )
    workspace_roles = {row.name: row for row in existing_roles.scalars().all()}

    for role_name_value, role_client_id in role_ids.items():
        workspace_role = workspace_roles.get(role_name_value)
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=workspace_id,
                role_id=role_client_id,
                name=role_name_value,
                description=_DISPLAY_NAMES[role_name_value],
                is_system=True,
            )
            session.add(workspace_role)
            await session.flush()
        result[role_name_value] = workspace_role.client_id

    return result
