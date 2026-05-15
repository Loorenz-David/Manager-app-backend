import logging

from beyo_manager.domain.execution.payloads.notification import NotificationPayload

logger = logging.getLogger(__name__)


async def handle_notification(raw: dict, task_id: str) -> None:
    """Deserialise payload and deliver notification. Implement per-app."""
    payload = NotificationPayload(**raw)
    logger.info(
        "notification | type=%s recipients=%d",
        payload.notification_type,
        len(payload.user_ids),
    )
