from dataclasses import dataclass

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import ShopifyWebhookPayloadFormatEnum


SHOPIFY_WEBHOOK_CALLBACK_PATH = "/api/v1/shopify/webhooks"


@dataclass(frozen=True)
class ShopifyWebhookDefinition:
    topic: str
    callback_path: str
    required_scopes: tuple[str, ...]
    payload_format: ShopifyWebhookPayloadFormatEnum
    enabled: bool = True


SHOPIFY_WEBHOOK_REGISTRY: tuple[ShopifyWebhookDefinition, ...] = (
    ShopifyWebhookDefinition(
        topic="app/uninstalled",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=(),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="orders/create",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_orders",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="orders/updated",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_orders",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="orders/paid",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_orders",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="orders/cancelled",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_orders",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="products/create",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_products",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="products/update",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_products",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
    ShopifyWebhookDefinition(
        topic="products/delete",
        callback_path=SHOPIFY_WEBHOOK_CALLBACK_PATH,
        required_scopes=("read_products",),
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    ),
)


def webhook_definition_enabled(definition: ShopifyWebhookDefinition) -> bool:
    """Whether this topic should be subscribed now — the one test every reader uses.

    ``SHOPIFY_WEBHOOKS_ENABLED=false`` disables every entry: the webhook sync then
    removes the owned remote subscriptions (and a reconnect or reauthorisation, which
    only enqueues that sync, registers nothing). Read at call time, not import time.

    Not used by the inbound intake (``get_webhook_definition``): deliveries that arrive
    before the subscriptions are gone are still recorded as a known topic.
    """
    return definition.enabled and bool(settings.shopify_webhooks_enabled)


def get_webhook_definition(topic: str) -> ShopifyWebhookDefinition | None:
    for definition in SHOPIFY_WEBHOOK_REGISTRY:
        if definition.topic == topic:
            return definition
    return None
