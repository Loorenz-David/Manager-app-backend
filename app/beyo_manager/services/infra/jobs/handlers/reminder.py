import logging

from beyo_manager.domain.execution.payloads.reminder import ReminderPayload

logger = logging.getLogger(__name__)


async def handle_reminder(raw: dict, task_id: str) -> None:
    """Deserialise payload and send reminder. Implement per-app."""
    payload = ReminderPayload(**raw)
    logger.info(
        "reminder | user_id=%s entity=%s",
        payload.user_id,
        payload.entity_client_id,
    )
