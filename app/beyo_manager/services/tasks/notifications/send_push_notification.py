import logging

from pywebpush import WebPushException
from sqlalchemy import delete, select

from beyo_manager.models.tables.notifications.push_subscription import PushSubscription
from beyo_manager.models.database import get_db_session
from beyo_manager.services.infra.push.vapid import send_web_push

logger = logging.getLogger(__name__)


async def handle_send_push_notification(payload: dict, task_id: str) -> None:
    user_id = payload["user_id"]

    async for session in get_db_session():
        result        = await session.execute(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
        subscriptions = result.scalars().all()
        if not subscriptions:
            return

        push_payload = {
            "title": payload["title"],
            "body":  payload["body"],
            "data": {
                "notification_client_id": payload.get("notification_client_id"),
                "entity_type":            payload.get("entity_type"),
                "entity_client_id":       payload.get("entity_client_id"),
                "task_client_id":         payload.get("task_client_id"),
            },
        }

        stale_ids = []
        for sub in subscriptions:
            try:
                send_web_push(sub.endpoint, sub.p256dh, sub.auth, push_payload)
            except WebPushException as exc:
                if exc.response and exc.response.status_code == 410:
                    stale_ids.append(sub.client_id)
                else:
                    logger.warning(
                        "push failed | sub=%s status=%s",
                        sub.client_id,
                        exc.response.status_code if exc.response else "no response",
                    )

        if stale_ids:
            await session.execute(
                delete(PushSubscription).where(PushSubscription.client_id.in_(stale_ids))
            )
            await session.commit()
