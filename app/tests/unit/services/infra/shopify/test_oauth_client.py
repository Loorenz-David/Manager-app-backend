from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.shopify.oauth_client import exchange_oauth_code_for_offline_token


def _mock_response(status_code: int, json_body) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exchange_oauth_code_for_offline_token_returns_access_token_and_granted_scopes(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.oauth_client.settings.shopify_client_id", "client-id")
    monkeypatch.setattr("beyo_manager.services.infra.shopify.oauth_client.settings.shopify_client_secret", "client-secret")
    monkeypatch.setattr("beyo_manager.services.infra.shopify.oauth_client.settings.request_timeout_seconds", 5)

    with patch("beyo_manager.services.infra.shopify.oauth_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            return_value=_mock_response(
                200,
                {"access_token": "offline-token", "scope": "read_products,read_orders"},
            )
        )
        mock_client_class.return_value = mock_client

        result = await exchange_oauth_code_for_offline_token(
            shop_domain="valid-shop.myshopify.com",
            code="oauth-code",
        )

    assert result.access_token == "offline-token"
    assert result.granted_scopes == ("read_orders", "read_products")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exchange_oauth_code_for_offline_token_raises_external_service_error_on_timeout(
    monkeypatch,
) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.oauth_client.settings.shopify_client_id", "client-id")
    monkeypatch.setattr("beyo_manager.services.infra.shopify.oauth_client.settings.shopify_client_secret", "client-secret")
    monkeypatch.setattr("beyo_manager.services.infra.shopify.oauth_client.settings.request_timeout_seconds", 5)

    with patch("beyo_manager.services.infra.shopify.oauth_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_class.return_value = mock_client

        with pytest.raises(ExternalServiceError, match="timed out"):
            await exchange_oauth_code_for_offline_token(
                shop_domain="valid-shop.myshopify.com",
                code="oauth-code",
            )
