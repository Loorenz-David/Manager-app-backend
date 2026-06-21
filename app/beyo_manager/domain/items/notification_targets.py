import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.notifications.pin_conditions import EventFacts
from beyo_manager.domain.notifications.pinned_subscribers import resolve_pinned_subscribers
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.domain.roles.queries import get_manager_user_ids

_logger = logging.getLogger(__name__)


async def resolve_upholstery_notification_targets(
    session: AsyncSession,
    workspace_id: str,
    item_upholstery_ids: list[str],
    actor_id: str,
    event_facts: EventFacts,
) -> set[str]:
    _logger.info(
        "UPHOLSTERY_NOTIF resolving targets item_upholstery_ids=%s event_facts=%s actor_id=%s",
        item_upholstery_ids, event_facts, actor_id,
    )
    pin_sources = [
        _get_pinned_subscribers(session, item_upholstery_id, event_facts)
        for item_upholstery_id in item_upholstery_ids
    ]
    sources = await asyncio.gather(
        get_manager_user_ids(session, workspace_id),
        *pin_sources,
    )
    manager_ids = sources[0]
    targets: set[str] = set().union(*sources)
    targets.discard(actor_id)
    _logger.info(
        "UPHOLSTERY_NOTIF result manager_ids=%s pin_targets=%s final_targets=%s",
        list(manager_ids), list(set().union(*sources[1:])), list(targets),
    )
    return targets


async def _get_pinned_subscribers(
    session: AsyncSession,
    item_upholstery_id: str,
    event_facts: EventFacts,
) -> set[str]:
    return await resolve_pinned_subscribers(
        session=session,
        entity_type=EntityType.ITEM_UPHOLSTERY.value,
        entity_client_id=item_upholstery_id,
        event_facts=event_facts,
    )
