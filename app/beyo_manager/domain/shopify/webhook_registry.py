from dataclasses import dataclass

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


def get_webhook_definition(topic: str) -> ShopifyWebhookDefinition | None:
    for definition in SHOPIFY_WEBHOOK_REGISTRY:
        if definition.topic == topic:
            return definition
    return None
