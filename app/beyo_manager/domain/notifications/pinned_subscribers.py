from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.notifications.pin_conditions import EventFacts, pin_conditions_match
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin


async def resolve_pinned_subscribers(
    session: AsyncSession,
    entity_type: str,
    entity_client_id: str,
    event_facts: EventFacts,
) -> set[str]:
    rows = (
        await session.execute(
            select(
                NotificationPin.client_id,
                NotificationPin.user_id,
                NotificationPin.conditions,
                NotificationPin.fire_once,
            ).where(
                NotificationPin.entity_type == entity_type,
                NotificationPin.entity_client_id == entity_client_id,
            )
        )
    ).all()

    matched_user_ids: set[str] = set()
    fire_once_pin_ids: list[str] = []

    for pin_id, user_id, conditions, fire_once in rows:
        if pin_conditions_match(conditions, event_facts):
            matched_user_ids.add(user_id)
            if fire_once:
                fire_once_pin_ids.append(pin_id)

    if fire_once_pin_ids:
        await session.execute(
            delete(NotificationPin).where(NotificationPin.client_id.in_(fire_once_pin_ids))
        )

    return matched_user_ids
