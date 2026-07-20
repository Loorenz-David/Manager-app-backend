from __future__ import annotations

import pytest

from beyo_manager.config import settings
from beyo_manager.services.infra.connecteam.webhook_verifier import (
    ConnecteamWebhookAuthError,
    verify_connecteam_webhook,
)


def test_static_secret_header_is_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "connecteam_webhook_secret", "secret")
    verify_connecteam_webhook(b"raw", {"X-Webhook-Secret": "secret"})


def test_invalid_or_missing_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "connecteam_webhook_secret", "secret")
    with pytest.raises(ConnecteamWebhookAuthError):
        verify_connecteam_webhook(b"raw", {})
    with pytest.raises(ConnecteamWebhookAuthError):
        verify_connecteam_webhook(b"raw", {"X-Webhook-Secret": "wrong"})

