import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.notifications.pin_conditions import EventFacts
from beyo_manager.domain.notifications.pinned_subscribers import resolve_pinned_subscribers
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.roles.queries import is_active_user_with_role


async def resolve_task_notification_targets(
    session: AsyncSession,
    workspace_id: str,
    task_client_id: str,
    task_created_by_id: str | None,
    actor_id: str,
    event_facts: EventFacts,
) -> set[str]:
    sources = await asyncio.gather(
        _get_seller_task_creator(session, workspace_id, task_created_by_id),
        _get_pinned_subscribers(session, task_client_id, event_facts),
    )
    seller_creator_ids, pinned_ids = sources
    targets: set[str] = set().union(seller_creator_ids, pinned_ids)
    targets.discard(actor_id)
    return targets


async def _get_seller_task_creator(
    session: AsyncSession,
    workspace_id: str,
    task_created_by_id: str | None,
) -> set[str]:
    if task_created_by_id is None:
        return set()
    if await is_active_user_with_role(
        session,
        workspace_id,
        task_created_by_id,
        RoleNameEnum.SELLER,
    ):
        return {task_created_by_id}
    return set()


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
