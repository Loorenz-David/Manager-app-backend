import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.notifications.pin_conditions import EventFacts
from beyo_manager.domain.notifications.pinned_subscribers import resolve_pinned_subscribers
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.domain.roles.queries import get_manager_user_ids


async def resolve_task_notification_targets(
    session: AsyncSession,
    workspace_id: str,
    task_client_id: str,
    task_created_by_id: str | None,
    actor_id: str,
    event_facts: EventFacts,
) -> set[str]:
    sources = await asyncio.gather(
        get_manager_user_ids(session, workspace_id),
        _get_task_creator(task_created_by_id),
        _get_pinned_subscribers(session, task_client_id, event_facts),
    )
    targets: set[str] = set().union(*sources)
    targets.discard(actor_id)
    return targets


async def _get_task_creator(task_created_by_id: str | None) -> set[str]:
    if task_created_by_id is None:
        return set()
    return {task_created_by_id}


async def _get_pinned_subscribers(
    session: AsyncSession,
    task_client_id: str,
    event_facts: EventFacts,
) -> set[str]:
    return await resolve_pinned_subscribers(
        session=session,
        entity_type=EntityType.TASK.value,
        entity_client_id=task_client_id,
        event_facts=event_facts,
    )
