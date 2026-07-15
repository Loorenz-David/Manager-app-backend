from enum import StrEnum


class ShopifyIntegrationStatusEnum(StrEnum):
    PENDING_INSTALL = "pending_install"
    ACTIVE = "active"
    NEEDS_REAUTH = "needs_reauth"
    SCOPES_OUTDATED = "scopes_outdated"
    WEBHOOKS_OUTDATED = "webhooks_outdated"
    DISABLED = "disabled"
    UNINSTALLED = "uninstalled"
    ERROR = "error"


class ShopifyOAuthStateStatusEnum(StrEnum):
    PENDING = "pending"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class ShopifyWebhookSubscriptionStatusEnum(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    DISABLED = "disabled"
    REMOVED = "removed"


class ShopifyWebhookIntakeStatusEnum(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class ShopifyProductSyncOperationEnum(StrEnum):
    CREATE = "create"
    UPDATE = "update"


class ShopifyProductSyncItemStatusEnum(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ShopifyInventoryAdjustmentStatusEnum(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"


class ShopifyIntegrationEventTypeEnum(StrEnum):
    INSTALL = "install"
    REAUTHORIZE = "reauthorize"
    WEBHOOK_SYNC = "webhook_sync"
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_PROCESSED = "webhook_processed"
    HEALTH_CHECK = "health_check"
    PRODUCT_SYNC = "product_sync"
    ERROR = "error"
    DISCONNECT = "disconnect"


class ShopifyIntegrationEventSeverityEnum(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ShopifyWebhookPayloadFormatEnum(StrEnum):
    JSON = "json"
