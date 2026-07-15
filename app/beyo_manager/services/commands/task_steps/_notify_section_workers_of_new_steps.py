from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def enqueue_section_workers_new_steps_notification(
    session: AsyncSession,
    *,
    workspace_id: str,
    task: Task,
    working_section_ids: set[str],
    working_section_names: dict[str, str],
    actor_id: str,
) -> bool:
    """Enqueue one deduplicated notification for workers of newly added sections.

    This helper intentionally does not own a transaction or dispatch events. The
    caller keeps the notification task atomic with the step creation and task
    state transition.
    """
    if not working_section_ids:
        return False

    result = await session.execute(
        select(WorkingSectionMembership.user_id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.user_id == WorkingSectionMembership.user_id,
        )
        .join(
            WorkspaceRole,
            WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id,
        )
        .join(Role, Role.client_id == WorkspaceRole.role_id)
        .where(
            WorkingSectionMembership.workspace_id == workspace_id,
            WorkingSectionMembership.working_section_id.in_(working_section_ids),
            WorkingSectionMembership.removed_at.is_(None),
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
            WorkspaceRole.workspace_id == workspace_id,
            Role.name == RoleNameEnum.WORKER,
        )
        .distinct()
    )
    worker_ids = set(result.scalars().all())
    worker_ids.discard(actor_id)
    if not worker_ids:
        return False

    section_names = sorted(
        {
            working_section_names[section_id]
            for section_id in working_section_ids
            if section_id in working_section_names
        }
    )
    section_label = ", ".join(f'"{name}"' for name in section_names)
    location_suffix = f" in {section_label}" if section_label else ""

    await create_instant_task(
        session=session,
        task_type=TaskType.CREATE_NOTIFICATIONS,
        payload=asdict(
            NotificationPayload(
                notification_type="task_steps_reopened",
                user_ids=sorted(worker_ids),
                title="New work available",
                body=f"Task #{task.task_scalar_id} has new work available{location_suffix}.",
                entity_type="task",
                entity_client_id=task.client_id,
                task_client_id=task.client_id,
                exclude_viewing=[
                    {
                        "entity_type": "task",
                        "entity_client_id": task.client_id,
                    }
                ],
            )
        ),
    )
    return True
