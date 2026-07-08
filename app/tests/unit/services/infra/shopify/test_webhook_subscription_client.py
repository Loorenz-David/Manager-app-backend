from __future__ import annotations

import pytest

from beyo_manager.domain.shopify.enums import ShopifyWebhookPayloadFormatEnum
from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError
from beyo_manager.services.infra.shopify.webhook_subscription_client import (
    create_remote_webhook_subscription,
    delete_remote_webhook_subscription,
    list_remote_webhook_subscriptions,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_remote_webhook_subscriptions_maps_graphql_payload(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return {
            "webhookSubscriptions": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/WebhookSubscription/1",
                            "topic": "ORDERS_CREATE",
                            "format": "JSON",
                            "endpoint": {
                                "__typename": "WebhookHttpEndpoint",
                                "callbackUrl": "https://backend.example.com/api/v1/shopify/webhooks",
                            },
                        }
                    }
                ]
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.webhook_subscription_client.execute_shopify_graphql",
        _fake_execute,
    )

    subscriptions = await list_remote_webhook_subscriptions(
        shop_domain="valid-shop.myshopify.com",
        access_token_encrypted="encrypted-token",
    )

    assert len(subscriptions) == 1
    assert subscriptions[0].topic == "orders/create"
    assert subscriptions[0].callback_url == "https://backend.example.com/api/v1/shopify/webhooks"
    assert subscriptions[0].payload_format == ShopifyWebhookPayloadFormatEnum.JSON


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_remote_webhook_subscription_maps_graphql_payload(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return {
            "webhookSubscriptionCreate": {
                "userErrors": [],
                "webhookSubscription": {
                    "id": "gid://shopify/WebhookSubscription/2",
                    "topic": "PRODUCTS_UPDATE",
                    "format": "JSON",
                    "endpoint": {
                        "__typename": "WebhookHttpEndpoint",
                        "callbackUrl": "https://backend.example.com/api/v1/shopify/webhooks",
                    },
                },
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.webhook_subscription_client.execute_shopify_graphql",
        _fake_execute,
    )

    subscription = await create_remote_webhook_subscription(
        shop_domain="valid-shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        topic="products/update",
        callback_url="https://backend.example.com/api/v1/shopify/webhooks",
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    )

    assert subscription.topic == "products/update"
    assert subscription.id == "gid://shopify/WebhookSubscription/2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_remote_webhook_subscription_raises_non_retryable_on_user_errors(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return {
            "webhookSubscriptionCreate": {
                "userErrors": [{"field": ["topic"], "message": "Invalid topic"}],
                "webhookSubscription": None,
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.webhook_subscription_client.execute_shopify_graphql",
        _fake_execute,
    )

    with pytest.raises(ShopifyGraphQLNonRetryableError) as exc_info:
        await create_remote_webhook_subscription(
            shop_domain="valid-shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            topic="products/update",
            callback_url="https://backend.example.com/api/v1/shopify/webhooks",
            payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
        )

    assert exc_info.value.error_code == "graphql_user_errors"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_remote_webhook_subscription_treats_missing_remote_as_success(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return {
            "webhookSubscriptionDelete": {
                "deletedWebhookSubscriptionId": None,
                "userErrors": [{"field": ["id"], "message": "Webhook subscription not found"}],
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.webhook_subscription_client.execute_shopify_graphql",
        _fake_execute,
    )

    await delete_remote_webhook_subscription(
        shop_domain="valid-shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        remote_subscription_id="gid://shopify/WebhookSubscription/999",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_remote_webhook_subscription_raises_on_other_user_errors(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return {
            "webhookSubscriptionDelete": {
                "deletedWebhookSubscriptionId": None,
                "userErrors": [{"field": ["id"], "message": "Invalid id"}],
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.webhook_subscription_client.execute_shopify_graphql",
        _fake_execute,
    )

    with pytest.raises(ShopifyGraphQLNonRetryableError) as exc_info:
        await delete_remote_webhook_subscription(
            shop_domain="valid-shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            remote_subscription_id="gid://shopify/WebhookSubscription/999",
        )

    assert exc_info.value.error_code == "graphql_user_errors"
