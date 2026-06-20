import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.notifications.pin_conditions import EventFacts
from beyo_manager.domain.notifications.pinned_subscribers import resolve_pinned_subscribers
from beyo_manager.domain.presence.enums import EntityType


async def resolve_task_step_notification_targets(
    session: AsyncSession,
    step_client_id: str,
    actor_id: str,
    event_facts: EventFacts,
) -> set[str]:
    sources = await asyncio.gather(
        _get_pinned_subscribers(session, step_client_id, event_facts),
    )
    targets: set[str] = set().union(*sources)
    targets.discard(actor_id)
    return targets


async def _get_pinned_subscribers(
    session: AsyncSession,
    step_client_id: str,
    event_facts: EventFacts,
) -> set[str]:
    return await resolve_pinned_subscribers(
        session=session,
        entity_type=EntityType.TASK_STEP.value,
        entity_client_id=step_client_id,
        event_facts=event_facts,
    )
