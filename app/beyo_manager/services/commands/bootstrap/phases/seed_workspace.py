from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.domain.workspaces.enums import WorkspaceRoleNameEnum
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace import Workspace

_DISPLAY_NAMES: dict[str, str] = {
    "admin": "Admin",
    "worker": "Worker",
    "manager": "Manager",
    "seller": "Seller",
    "wood_worker": "Wood Worker",
    "upholstery_worker": "Upholstery Worker",
    "quality_control": "Quality Control",
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
    workspace_role_rows = existing_roles.scalars().all()
    workspace_roles_by_role_id = {row.role_id: row for row in workspace_role_rows if row.is_system}
    workspace_roles_by_name = {row.name: row for row in workspace_role_rows if row.name is not None}

    for role_name_value, role_client_id in role_ids.items():
        workspace_role = workspace_roles_by_role_id.get(role_client_id)
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=workspace_id,
                role_id=role_client_id,
                name=None,
                description=_DISPLAY_NAMES[role_name_value],
                is_system=True,
            )
            session.add(workspace_role)
            await session.flush()
            workspace_roles_by_role_id[role_client_id] = workspace_role
        result[role_name_value] = workspace_role.client_id

    wood_worker_role = workspace_roles_by_name.get(WorkspaceRoleNameEnum.WOOD_WORKER)
    if wood_worker_role is None:
        wood_worker_role = WorkspaceRole(
            workspace_id=workspace_id,
            role_id=role_ids["worker"],
            name=WorkspaceRoleNameEnum.WOOD_WORKER,
            description=_DISPLAY_NAMES[WorkspaceRoleNameEnum.WOOD_WORKER.value],
            is_system=False,
        )
        session.add(wood_worker_role)
        await session.flush()
    result[WorkspaceRoleNameEnum.WOOD_WORKER.value] = wood_worker_role.client_id

    upholstery_worker_role = workspace_roles_by_name.get(WorkspaceRoleNameEnum.UPHOLSTERY_WORKER)
    if upholstery_worker_role is None:
        upholstery_worker_role = WorkspaceRole(
            workspace_id=workspace_id,
            role_id=role_ids["worker"],
            name=WorkspaceRoleNameEnum.UPHOLSTERY_WORKER,
            description=_DISPLAY_NAMES[WorkspaceRoleNameEnum.UPHOLSTERY_WORKER.value],
            is_system=False,
        )
        session.add(upholstery_worker_role)
        await session.flush()
    result[WorkspaceRoleNameEnum.UPHOLSTERY_WORKER.value] = upholstery_worker_role.client_id

    quality_control_role = workspace_roles_by_name.get(WorkspaceRoleNameEnum.QUALITY_CONTROL)
    if quality_control_role is None:
        quality_control_role = WorkspaceRole(
            workspace_id=workspace_id,
            role_id=role_ids["worker"],
            name=WorkspaceRoleNameEnum.QUALITY_CONTROL,
            description=_DISPLAY_NAMES[WorkspaceRoleNameEnum.QUALITY_CONTROL.value],
            is_system=False,
        )
        session.add(quality_control_role)
        await session.flush()
    result[WorkspaceRoleNameEnum.QUALITY_CONTROL.value] = quality_control_role.client_id

    return result
