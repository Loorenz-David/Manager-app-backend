import logging

from beyo_manager.models.tables.notifications.notification import Notification
from beyo_manager.models.database import get_db_session
from beyo_manager.services.infra.events.build_event import build_user_event
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.presence import get_viewers

logger = logging.getLogger(__name__)


async def handle_create_notifications(payload: dict, task_id: str) -> None:
    notification_type = payload["notification_type"]
    user_ids          = list(payload.get("user_ids", []))
    title             = payload["title"]
    body              = payload["body"]
    entity_type       = payload.get("entity_type")
    entity_client_id  = payload.get("entity_client_id")
    task_client_id    = payload.get("task_client_id")
    exclude_viewing   = payload.get("exclude_viewing", [])

    # Exclude users currently viewing the entity contexts
    viewing_ids: set[str] = set()
    for ctx in exclude_viewing:
        viewing_ids |= get_viewers(ctx["entity_type"], ctx["entity_client_id"])
    if viewing_ids:
        user_ids = [uid for uid in user_ids if uid not in viewing_ids]
    if not user_ids:
        return

    pending_events = []
    created_notifications: list[Notification] = []

    async for session in get_db_session():
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                entity_type=entity_type,
                entity_client_id=entity_client_id,
            )
            session.add(notification)
            created_notifications.append(notification)

        await session.flush()

        # After flush, notifications are persistent (not in session.new),
        # so we iterate over the tracked objects to emit events + push tasks.
        for obj in created_notifications:
            pending_events.append(
                build_user_event(
                    user_id=obj.user_id,
                    event_name="notification:new",
                    client_id=obj.client_id,
                )
            )
            # Enqueue SEND_PUSH_NOTIFICATION task within same transaction
            from beyo_manager.domain.execution.enums import TaskType
            from beyo_manager.services.infra.execution.task_factory import create_instant_task
            await create_instant_task(
                session=session,
                task_type=TaskType.SEND_PUSH_NOTIFICATION,
                payload={
                    "user_id":                obj.user_id,
                    "notification_client_id": obj.client_id,
                    "title":                  title,
                    "body":                   body,
                    "entity_type":            entity_type,
                    "entity_client_id":       entity_client_id,
                    "task_client_id":         task_client_id,
                },
            )

        await session.commit()

    await dispatch(pending_events)
