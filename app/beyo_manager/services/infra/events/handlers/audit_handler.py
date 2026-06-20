import logging
from datetime import datetime, timezone

from beyo_manager.services.infra.audit.audited_events import get_audited_events
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent, Event

logger = logging.getLogger(__name__)


async def handle(event: Event | BatchWorkspaceEvent) -> None:
    if isinstance(event, BatchWorkspaceEvent):
        return

    if event.event_name not in get_audited_events():
        return

    workspace_id = getattr(event, "workspace_id", event.extra.get("workspace_id"))
    if not workspace_id:
        logger.warning("audit_handler: no workspace_id on event %s — skipped", event.event_name)
        return

    try:
        from beyo_manager.models.database import get_db_session
        from beyo_manager.services.infra.audit.write_audit import write_audit_from_event

        async for session in get_db_session():
            await write_audit_from_event(
                session=session,
                event_name=event.event_name,
                workspace_id=workspace_id,
                resource_client_id=event.client_id or None,
                detail=event.extra,
                occurred_at=datetime.now(timezone.utc),
            )
            await session.commit()
    except Exception:
        logger.exception(
            "audit_handler: failed to write audit entry | event=%s client_id=%s",
            event.event_name,
            event.client_id,
        )
