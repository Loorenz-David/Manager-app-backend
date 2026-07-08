import hashlib
import hmac
from urllib.parse import urlencode

from beyo_manager.services.infra.shopify.hmac_verifier import is_valid_shopify_oauth_callback_hmac


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
