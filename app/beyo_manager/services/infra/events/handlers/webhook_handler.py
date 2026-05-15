import logging

from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

logger = logging.getLogger(__name__)

# Populate with webhook-eligible event names in local extensions.
# e.g. _WEBHOOK_EVENTS = {"invoice:updated", "case:state-changed"}
_WEBHOOK_EVENTS: set[str] = set()


async def handle(event) -> None:
    """Enqueue a durable webhook delivery task — never calls external APIs inline."""
    if not _WEBHOOK_EVENTS:
        return
    if not isinstance(event, WorkspaceEvent):
        return
    if event.event_name not in _WEBHOOK_EVENTS:
        return

    try:
        from beyo_manager.domain.execution.enums import EventTaskOriginSourceEnum, TaskType
        from beyo_manager.models.database import get_db_session
        from beyo_manager.services.infra.execution.task_factory import create_execution_task

        async for session in get_db_session():
            await create_execution_task(
                session=session,
                task_type=TaskType.DELIVER_WEBHOOK,
                payload={
                    "event_name":   event.event_name,
                    "client_id":    event.client_id,
                    "workspace_id": event.workspace_id,
                    "extra":        event.extra,
                },
                origin_source=EventTaskOriginSourceEnum.INSTANT,
            )
            await session.commit()
    except Exception:
        logger.exception(
            "webhook_handler: failed to enqueue | event=%s workspace=%s",
            event.event_name,
            event.workspace_id,
        )
