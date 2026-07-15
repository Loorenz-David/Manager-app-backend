from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopifyWebhookSubscriptionResult:
    client_id: str
    workspace_id: str
    shop_integration_id: str
    topic: str
    callback_url: str
    remote_subscription_id: str | None
    payload_format: str
    required_scopes: list[str] | None
    status: str
    installed_at: str | None
    last_verified_at: str | None
    last_install_attempt_at: str | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: str
    updated_at: str | None


@dataclass(frozen=True)
class ShopifyScopeStatusResult:
    shop_integration_id: str
    shop_domain: str
    requested_scopes: list[str]
    granted_scopes: list[str]
    missing_scopes: list[str]
    has_all_required_scopes: bool
    shop_status: str


@dataclass(frozen=True)
class ShopifyShopIntegrationResult:
    client_id: str
    workspace_id: str
    shop_domain: str
    shop_name: str | None
    provider: str
    status: str
    access_token_expires_at: str | None
    granted_scopes: list[str] | None
    requested_scopes: list[str] | None
    api_version: str
    installed_at: str | None
    uninstalled_at: str | None
    last_connected_at: str | None
    last_health_check_at: str | None
    last_health_check_status: str | None
    last_error_code: str | None
    last_error_message: str | None
    scopes_status: str
    webhooks_status: str
    created_by: dict | None
    updated_by: dict | None
    created_at: str
    updated_at: str
    is_deleted: bool


@dataclass(frozen=True)
class ShopifyCustomerLookupCoordinatesResult:
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class ShopifyCustomerLookupAddressResult:
    street_address: str | None
    post_code: str | None
    coordinates: ShopifyCustomerLookupCoordinatesResult
    city: str | None
    district: str | None


@dataclass(frozen=True)
class ShopifyCustomerLookupResult:
    shop_integration_id: str
    shop_domain: str
    match_type: str
    matched_value: str
    order_id: str | None
    order_name: str | None
    customer_id: str | None
    display_name: str | None
    primary_phone_number: str | None
    primary_email: str | None
    address: ShopifyCustomerLookupAddressResult


@dataclass(frozen=True)
class ShopifyWebhookIntakeHistoryRecordResult:
    record_type: str
    client_id: str
    shop_integration_id: str
    shop_domain: str
    topic: str
    webhook_id: str | None
    status: str
    retryable: bool
    attempts: int
    received_at: str
    processing_started_at: str | None
    processed_at: str | None
    last_error: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ShopifyIntegrationEventHistoryRecordResult:
    record_type: str
    client_id: str
    shop_integration_id: str
    event_type: str
    severity: str
    message: str
    metadata_json: dict | None
    created_by: dict | None
    created_at: str


@dataclass(frozen=True)
class ShopifyMetafieldPreferenceResult:
    client_id: str
    item_category_id: str
    shop_integration_id: str
    shopify_metafield_definition_id: str
    name: str | None
    namespace: str | None
    key: str | None
    description: str | None
    type: str | None
    validations: list[dict] | None
    reference_options: dict | None
    sequence_order: int
    is_enabled: bool
    created_at: str
    updated_at: str | None
    created_by: dict | None


@dataclass(frozen=True)
class ShopifyMetafieldDefinitionResult:
    shopify_metafield_definition_id: str
    name: str | None
    namespace: str | None
    key: str | None
    description: str | None
    type: str | None
    validations: list[dict] | None
    reference_options: dict | None


@dataclass(frozen=True)
class ShopifyLocationResult:
    location_id: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class ShopifyLocationsShopResult:
    shop_integration_id: str
    shop_domain: str
    status: str
    locations: list[ShopifyLocationResult]
