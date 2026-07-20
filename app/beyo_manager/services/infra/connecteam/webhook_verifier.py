from __future__ import annotations

import hmac
from collections.abc import Mapping

from beyo_manager.config import settings
from beyo_manager.errors.base import DomainError


class ConnecteamWebhookAuthError(DomainError):
    http_status = 401


def verify_connecteam_webhook(raw_body: bytes, headers: Mapping[str, str]) -> None:
    """Verify the observed Connecteam static shared-secret header.

    The body is intentionally accepted as an argument so a future verified
    provider contract can switch to a body HMAC without changing the command.
    """
    del raw_body
    secret = settings.connecteam_webhook_secret
    provided = headers.get("x-webhook-secret") or headers.get("X-Webhook-Secret")
    if not secret or not provided or not hmac.compare_digest(str(provided), secret):
        raise ConnecteamWebhookAuthError("Invalid Connecteam webhook authentication.")

