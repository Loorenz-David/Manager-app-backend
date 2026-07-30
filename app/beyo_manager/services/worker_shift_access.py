from sqlalchemy import and_, select

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext


async def resolve_worker_shift_target(
    ctx: ServiceContext,
    requested_user_id: str | None,
) -> str:
    target_user_id = requested_user_id or ctx.user_id
    acting_on_behalf = target_user_id != ctx.user_id

    if acting_on_behalf and ctx.role_name not in {
        RoleNameEnum.ADMIN.value,
        RoleNameEnum.MANAGER.value,
    }:
        raise PermissionDenied("Workers may only manage their own shift.")
    if not acting_on_behalf and ctx.role_name != RoleNameEnum.WORKER.value:
        raise PermissionDenied("Managers and admins must select a worker.")

    worker = (
        await ctx.session.execute(
            select(User.client_id)
            .join(
                WorkspaceMembership,
                and_(
                    WorkspaceMembership.user_id == User.client_id,
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.is_active.is_(True),
                ),
            )
            .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
            .join(Role, Role.client_id == WorkspaceRole.role_id)
            .where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                User.client_id == target_user_id,
                Role.name == RoleNameEnum.WORKER,
            )
        )
    ).scalar_one_or_none()
    if worker is None:
        raise NotFound("Worker not found in this workspace.")
    return worker
