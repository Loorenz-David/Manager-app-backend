from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from beyo_manager.errors.external_service import (
    ShopifyGraphQLNonRetryableError,
    ShopifyGraphQLRetryableError,
)
from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql


def _mock_response(status_code: int, json_body) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_shopify_graphql_returns_data_and_never_logs_token(monkeypatch, caplog) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.graphql_client.settings.request_timeout_seconds", 5)
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.decrypt_field",
        lambda ciphertext: "secret-token-value",
    )

    with patch("beyo_manager.services.infra.shopify.graphql_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            return_value=_mock_response(
                200,
                {"data": {"shop": {"id": "gid://shopify/Shop/1"}}},
            )
        )
        mock_client_class.return_value = mock_client

        data = await execute_shopify_graphql(
            shop_domain="valid-shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            query="query { shop { id } }",
            variables={"unsafe": "raw-body-secret"},
            operation_name="shop_lookup",
        )

    assert data == {"shop": {"id": "gid://shopify/Shop/1"}}
    assert "secret-token-value" not in caplog.text
    assert "raw-body-secret" not in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_shopify_graphql_classifies_timeout_as_retryable(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.graphql_client.settings.request_timeout_seconds", 5)
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.decrypt_field",
        lambda ciphertext: "secret-token-value",
    )

    with patch("beyo_manager.services.infra.shopify.graphql_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_class.return_value = mock_client

        with pytest.raises(ShopifyGraphQLRetryableError) as exc_info:
            await execute_shopify_graphql(
                shop_domain="valid-shop.myshopify.com",
                access_token_encrypted="encrypted-token",
                query="query { shop { id } }",
                variables={},
                operation_name="shop_lookup",
            )

    assert exc_info.value.retryable is True
    assert exc_info.value.error_code == "timeout"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_shopify_graphql_classifies_connection_failure_as_retryable(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.graphql_client.settings.request_timeout_seconds", 5)
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.decrypt_field",
        lambda ciphertext: "secret-token-value",
    )

    with patch("beyo_manager.services.infra.shopify.graphql_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("cannot connect"))
        mock_client_class.return_value = mock_client

        with pytest.raises(ShopifyGraphQLRetryableError) as exc_info:
            await execute_shopify_graphql(
                shop_domain="valid-shop.myshopify.com",
                access_token_encrypted="encrypted-token",
                query="query { shop { id } }",
                variables={},
                operation_name="shop_lookup",
            )

    assert exc_info.value.retryable is True
    assert exc_info.value.error_code == "connection_error"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_error_code"),
    [
        (500, "server_error"),
        (429, "rate_limited"),
    ],
)
async def test_execute_shopify_graphql_classifies_retryable_http_failures(
    monkeypatch,
    status_code: int,
    expected_error_code: str,
) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.graphql_client.settings.request_timeout_seconds", 5)
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.decrypt_field",
        lambda ciphertext: "secret-token-value",
    )

    with patch("beyo_manager.services.infra.shopify.graphql_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_mock_response(status_code, {"errors": [{"message": "raw"}]}))
        mock_client_class.return_value = mock_client

        with pytest.raises(ShopifyGraphQLRetryableError) as exc_info:
            await execute_shopify_graphql(
                shop_domain="valid-shop.myshopify.com",
                access_token_encrypted="encrypted-token",
                query="query { shop { id } }",
                variables={},
                operation_name="shop_lookup",
            )

    assert exc_info.value.retryable is True
    assert exc_info.value.error_code == expected_error_code


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "body", "expected_error_code"),
    [
        (401, {"errors": [{"message": "auth failed"}]}, "auth_error"),
        (422, {"errors": [{"message": "invalid input"}]}, "validation_error"),
        (200, {"errors": [{"message": "graphql broke"}]}, "graphql_errors"),
    ],
)
async def test_execute_shopify_graphql_classifies_non_retryable_failures(
    monkeypatch,
    status_code: int,
    body: dict,
    expected_error_code: str,
) -> None:
    monkeypatch.setattr("beyo_manager.services.infra.shopify.graphql_client.settings.request_timeout_seconds", 5)
    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.decrypt_field",
        lambda ciphertext: "secret-token-value",
    )

    with patch("beyo_manager.services.infra.shopify.graphql_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_mock_response(status_code, body))
        mock_client_class.return_value = mock_client

        with pytest.raises(ShopifyGraphQLNonRetryableError) as exc_info:
            await execute_shopify_graphql(
                shop_domain="valid-shop.myshopify.com",
                access_token_encrypted="encrypted-token",
                query="query { shop { id } }",
                variables={},
                operation_name="shop_lookup",
            )

    assert exc_info.value.retryable is False
    assert exc_info.value.error_code == expected_error_code
