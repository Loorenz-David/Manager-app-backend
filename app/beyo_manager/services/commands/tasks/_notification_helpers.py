from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def _resolve_task_audience(
    session: AsyncSession,
    workspace_id: str,
    task_client_id: str,
    task_created_by_id: str | None,
    actor_id: str,
) -> list[str]:
    """Return user_ids to notify on task state change.

    Sources (unioned, deduped, actor excluded):
    1. Active manager-role workspace members
    2. task.created_by_id (if set)
    3. NotificationPin holders for entity_type='task', entity_client_id=task_client_id
    """
    managers_result = await session.execute(
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
    pins_result = await session.execute(
        select(NotificationPin.user_id).where(
            NotificationPin.entity_type == "task",
            NotificationPin.entity_client_id == task_client_id,
        )
    )
    candidate_ids: set[str] = set(managers_result.scalars().all())
    candidate_ids |= set(pins_result.scalars().all())
    if task_created_by_id:
        candidate_ids.add(task_created_by_id)
    candidate_ids.discard(actor_id)
    return list(candidate_ids)
