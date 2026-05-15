import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.notifications.notification_pin import NotificationPin


async def resolve_case_notification_targets(
    session: AsyncSession,
    case,
    *,
    exclude_user_id: str | None = None,
) -> set[str]:
    """Return all user client_ids that should receive notifications for this case.
    Sources run concurrently. Add new sources without touching any command.
    """
    sources = await asyncio.gather(
        _get_participants(session, case),
        _get_pinned_subscribers(session, case),
    )
    target_ids: set[str] = set().union(*sources)
    if exclude_user_id:
        target_ids.discard(exclude_user_id)
    return target_ids


async def _get_participants(session: AsyncSession, case) -> set[str]:
    try:
        from beyo_manager.models.tables.cases.case_participant import CaseParticipant
        rows = await session.execute(
            select(CaseParticipant.user_id).where(CaseParticipant.case_id == case.client_id)
        )
        return {row[0] for row in rows}
    except Exception:
        return set()


async def _get_pinned_subscribers(session: AsyncSession, case) -> set[str]:
    rows = await session.execute(
        select(NotificationPin.user_id).where(
            NotificationPin.entity_type      == "case",
            NotificationPin.entity_client_id == case.client_id,
        )
    )
    return {row[0] for row in rows}
