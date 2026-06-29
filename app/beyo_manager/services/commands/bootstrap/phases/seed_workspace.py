from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import Settings
from beyo_manager.domain.workspaces.enums import WorkspaceSpecializationEnum
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

_SPECIALIZATION_DISPLAY_NAMES: dict[WorkspaceSpecializationEnum, str] = {
    WorkspaceSpecializationEnum.WOOD_WORKER: _DISPLAY_NAMES["wood_worker"],
    WorkspaceSpecializationEnum.UPHOLSTERY_WORKER: _DISPLAY_NAMES["upholstery_worker"],
    WorkspaceSpecializationEnum.QUALITY_CONTROL: _DISPLAY_NAMES["quality_control"],
}


def _workspace_role_variant_key(role_key: str, specialization: WorkspaceSpecializationEnum | None = None) -> str:
    if specialization is None:
        return role_key
    return f"{role_key}:{specialization.value}"


def _workspace_role_description(role_key: str, specialization: WorkspaceSpecializationEnum | None = None) -> str:
    if specialization is None:
        return _DISPLAY_NAMES[role_key]
    if role_key == "worker":
        return _SPECIALIZATION_DISPLAY_NAMES[specialization]
    return f"{_DISPLAY_NAMES[role_key]} - {_SPECIALIZATION_DISPLAY_NAMES[specialization]}"


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
    workspace_roles_by_signature = {
        (row.role_id, row.specialization): row
        for row in workspace_role_rows
    }

    for role_name_value, role_client_id in role_ids.items():
        workspace_role = workspace_roles_by_signature.get((role_client_id, None))
        if workspace_role is None:
            workspace_role = WorkspaceRole(
                workspace_id=workspace_id,
                role_id=role_client_id,
                specialization=None,
                description=_workspace_role_description(role_name_value),
                is_system=True,
            )
            session.add(workspace_role)
            await session.flush()
            workspace_roles_by_signature[(role_client_id, None)] = workspace_role
        result[_workspace_role_variant_key(role_name_value)] = workspace_role.client_id

    for role_key in ("worker", "manager"):
        for specialization in WorkspaceSpecializationEnum:
            signature = (role_ids[role_key], specialization)
            workspace_role = workspace_roles_by_signature.get(signature)
            if workspace_role is None:
                workspace_role = WorkspaceRole(
                    workspace_id=workspace_id,
                    role_id=role_ids[role_key],
                    specialization=specialization,
                    description=_workspace_role_description(role_key, specialization),
                    is_system=False,
                )
                session.add(workspace_role)
                await session.flush()
                workspace_roles_by_signature[signature] = workspace_role
            result[_workspace_role_variant_key(role_key, specialization)] = workspace_role.client_id

    return result
