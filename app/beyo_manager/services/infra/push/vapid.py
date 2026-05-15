import json
import logging

from pywebpush import WebPushException, webpush

from beyo_manager.config import settings

logger = logging.getLogger(__name__)


def send_web_push(
    endpoint: str,
    p256dh:   str,
    auth:     str,
    payload:  dict,
) -> None:
    """Send a single push notification to one browser subscription.
    Raises WebPushException on failure.
    Caller must handle 410 Gone by deleting the PushSubscription row.
    """
    webpush(
        subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
        data=json.dumps(payload),
        vapid_private_key=settings.vapid_private_key,
        vapid_claims={"sub": f"mailto:{settings.vapid_contact_email}"},
    )
