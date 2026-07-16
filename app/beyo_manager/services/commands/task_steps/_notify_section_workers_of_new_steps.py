from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def enqueue_section_workers_new_steps_notification(
    session: AsyncSession,
    *,
    workspace_id: str,
    task: Task,
    members_by_section: dict[str, list[str]],
    working_section_names: dict[str, str],
    actor_id: str,
) -> bool:
    """Enqueue one deduplicated notification for members of newly added sections.

    Takes the already-resolved ``members_by_section`` (see
    ``resolve_section_worker_ids``) so the audience is queried once per
    ``add_task_steps`` call and shared with the acknowledgment obligations —
    never re-resolved here.

    This helper intentionally does not own a transaction or dispatch events. The
    caller keeps the notification task atomic with the step creation and task
    state transition.
    """
    worker_ids = {
        user_id
        for member_ids in members_by_section.values()
        for user_id in member_ids
    }
    worker_ids.discard(actor_id)
    if not worker_ids:
        return False

    section_names = sorted(
        {
            working_section_names[section_id]
            for section_id in members_by_section
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
