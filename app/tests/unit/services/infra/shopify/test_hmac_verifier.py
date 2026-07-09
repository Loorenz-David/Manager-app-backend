import hashlib
import hmac
import base64
from urllib.parse import urlencode

from beyo_manager.services.infra.shopify.hmac_verifier import (
    is_valid_shopify_oauth_callback_hmac,
    is_valid_shopify_webhook_hmac,
)


def _signed_query(secret: str, params: dict[str, str]) -> str:
    message = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return urlencode([*params.items(), ("hmac", digest)])


def test_is_valid_shopify_oauth_callback_hmac_accepts_valid_signature(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.hmac_verifier.settings.shopify_client_secret", "test-secret")
    raw_query = _signed_query(
        "test-secret",
        {"code": "code-1", "shop": "valid-shop.myshopify.com", "state": "state-1", "timestamp": "123"},
    )

    assert is_valid_shopify_oauth_callback_hmac(raw_query) is True


def test_is_valid_shopify_oauth_callback_hmac_rejects_modified_signature(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.hmac_verifier.settings.shopify_client_secret", "test-secret")
    raw_query = _signed_query(
        "wrong-secret",
        {"code": "code-1", "shop": "valid-shop.myshopify.com", "state": "state-1"},
    )

    assert is_valid_shopify_oauth_callback_hmac(raw_query) is False


def test_is_valid_shopify_webhook_hmac_accepts_valid_signature(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.hmac_verifier.settings.shopify_webhook_secret", "webhook-secret")
    raw_body = b'{"id":123,"topic":"orders/create"}'
    digest = hmac.new(b"webhook-secret", raw_body, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()

    assert is_valid_shopify_webhook_hmac(raw_body, signature) is True


def test_is_valid_shopify_webhook_hmac_falls_back_to_client_secret(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.hmac_verifier.settings.shopify_webhook_secret", None)
    monkeypatch.setattr("beyo_manager.services.infra.shopify.hmac_verifier.settings.shopify_client_secret", "client-secret")
    raw_body = b'{"id":456}'
    digest = hmac.new(b"client-secret", raw_body, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()

    assert is_valid_shopify_webhook_hmac(raw_body, signature) is True


def test_is_valid_shopify_webhook_hmac_rejects_blank_signature(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.hmac_verifier.settings.shopify_webhook_secret", "webhook-secret")

    assert is_valid_shopify_webhook_hmac(b'{"id":1}', "   ") is False
