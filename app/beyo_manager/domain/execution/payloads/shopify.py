from dataclasses import dataclass


@dataclass(frozen=True)
class ShopifyProcessWebhookPayload:
    webhook_intake_id: str


@dataclass(frozen=True)
class ShopifySyncWebhooksForShopPayload:
    shop_integration_id: str


@dataclass(frozen=True)
class ShopifyRemoveWebhooksForShopPayload:
    shop_integration_id: str


@dataclass(frozen=True)
class ShopifyReconcileShopPayload:
    shop_integration_id: str


@dataclass(frozen=True)
class ShopifyProcessProductsPayload:
    workspace_id: str
    requested_by_user_id: str
    sync_item_client_ids: list[str]
