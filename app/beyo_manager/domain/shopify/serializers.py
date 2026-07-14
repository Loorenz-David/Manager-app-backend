from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.domain.shopify.results import (
    ShopifyIntegrationEventHistoryRecordResult,
    ShopifyMetafieldDefinitionResult,
    ShopifyMetafieldPreferenceResult,
    ShopifyScopeStatusResult,
    ShopifyShopIntegrationResult,
    ShopifyWebhookIntakeHistoryRecordResult,
    ShopifyWebhookSubscriptionResult,
)
from beyo_manager.domain.shopify.scopes import (
    compare_requested_and_granted_scopes,
    has_all_required_scopes,
)
from beyo_manager.domain.shopify.webhook_registry import SHOPIFY_WEBHOOK_REGISTRY
from beyo_manager.domain.users.serializers import serialize_user_working_section_member

if TYPE_CHECKING:
    from beyo_manager.models.tables.shopify.shopify_integration_event import (
        ShopifyIntegrationEvent,
    )
    from beyo_manager.models.tables.shopify.shopify_shop_integration import (
        ShopifyShopIntegration,
    )
    from beyo_manager.models.tables.shopify.shopify_webhook_intake import (
        ShopifyWebhookIntake,
    )
    from beyo_manager.models.tables.shopify.shopify_webhook_subscription import (
        ShopifyWebhookSubscription,
    )
    from beyo_manager.models.tables.users.user import User


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _normalize_scopes(scopes: Iterable[str] | None) -> list[str]:
    return [str(scope) for scope in (scopes or ()) if str(scope)]


def _serialize_user_reference(user: "User | None") -> dict | None:
    if user is None:
        return None
    return serialize_user_working_section_member(user)


def _filter_safe_metadata(metadata: dict | None) -> dict | None:
    if metadata is None:
        return None

    blocked_substrings = (
        "token",
        "secret",
        "hmac",
        "signature",
        "authorization",
        "code",
        "raw_payload",
        "payload",
        "raw_response",
        "provider_response",
    )
    filtered = {
        key: value
        for key, value in metadata.items()
        if not any(fragment in str(key).lower() for fragment in blocked_substrings)
    }
    return filtered or None


def serialize_shopify_webhook_intake_history_record(
    row: "ShopifyWebhookIntake",
) -> ShopifyWebhookIntakeHistoryRecordResult:
    return ShopifyWebhookIntakeHistoryRecordResult(
        record_type="webhook_intake",
        client_id=row.client_id,
        shop_integration_id=row.shop_integration_id,
        shop_domain=row.shop_domain,
        topic=row.topic,
        webhook_id=row.webhook_id,
        status=_enum_value(row.status),
        retryable=row.retryable,
        attempts=row.attempts,
        received_at=row.received_at.isoformat(),
        processing_started_at=_iso(row.processing_started_at),
        processed_at=_iso(row.processed_at),
        last_error=row.last_error,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def serialize_shopify_integration_event_history_record(
    row: "ShopifyIntegrationEvent",
) -> ShopifyIntegrationEventHistoryRecordResult:
    return ShopifyIntegrationEventHistoryRecordResult(
        record_type="integration_event",
        client_id=row.client_id,
        shop_integration_id=row.shop_integration_id,
        event_type=_enum_value(row.event_type),
        severity=_enum_value(row.severity),
        message=row.message,
        metadata_json=_filter_safe_metadata(row.metadata_json),
        created_by=_serialize_user_reference(row.created_by),
        created_at=row.created_at.isoformat(),
    )


def serialize_shopify_metafield_preference(r: ShopifyMetafieldPreferenceResult) -> dict:
    result = {
        "client_id": r.client_id,
        "item_category_id": r.item_category_id,
        "shop_integration_id": r.shop_integration_id,
        "shopify_metafield_definition_id": r.shopify_metafield_definition_id,
        "name": r.name,
        "namespace": r.namespace,
        "key": r.key,
        "description": r.description,
        "type": r.type,
        "validations": r.validations,
        "sequence_order": r.sequence_order,
        "is_enabled": r.is_enabled,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "created_by": r.created_by,
    }
    if r.reference_options is not None:
        result["reference_options"] = r.reference_options
    return result


def serialize_shopify_metafield_definition(r: ShopifyMetafieldDefinitionResult) -> dict:
    result = {
        "shopify_metafield_definition_id": r.shopify_metafield_definition_id,
        "name": r.name,
        "namespace": r.namespace,
        "key": r.key,
        "description": r.description,
        "type": r.type,
        "validations": r.validations,
    }
    if r.reference_options is not None:
        result["reference_options"] = r.reference_options
    return result


def serialize_shopify_metafield_preferences_response(data: dict) -> dict:
    return {
        "shops": [
            {
                "shop_integration_id": shop["shop_integration_id"],
                "shop_domain": shop["shop_domain"],
                "item_categories": [
                    {
                        "item_category_id": category["item_category_id"],
                        "metafield_preferences": [
                            serialize_shopify_metafield_preference(r)
                            for r in category["metafield_preferences"]
                        ],
                    }
                    for category in shop["item_categories"]
                ],
                "unavailable_definition_ids": shop["unavailable_definition_ids"],
                "search_results": [
                    serialize_shopify_metafield_definition(r)
                    for r in shop["search_results"]
                ],
                "search_pagination": shop["search_pagination"],
            }
            for shop in data["shops"]
        ]
    }


def serialize_shopify_webhook_subscription(
    row: "ShopifyWebhookSubscription",
) -> ShopifyWebhookSubscriptionResult:
    return ShopifyWebhookSubscriptionResult(
        client_id=row.client_id,
        workspace_id=row.workspace_id,
        shop_integration_id=row.shop_integration_id,
        topic=row.topic,
        callback_url=row.callback_url,
        remote_subscription_id=row.remote_subscription_id,
        payload_format=_enum_value(row.payload_format),
        required_scopes=_normalize_scopes(row.required_scopes),
        status=_enum_value(row.status),
        installed_at=_iso(row.installed_at),
        last_verified_at=_iso(row.last_verified_at),
        last_install_attempt_at=_iso(row.last_install_attempt_at),
        last_error_code=row.last_error_code,
        last_error_message=row.last_error_message,
        created_at=row.created_at.isoformat(),
        updated_at=_iso(row.updated_at),
    )


def serialize_shopify_scope_status(
    row: "ShopifyShopIntegration",
) -> ShopifyScopeStatusResult:
    comparison = compare_requested_and_granted_scopes(
        row.requested_scopes or (), row.granted_scopes or ()
    )
    return ShopifyScopeStatusResult(
        shop_integration_id=row.client_id,
        shop_domain=row.shop_domain,
        requested_scopes=list(comparison.requested),
        granted_scopes=list(comparison.granted),
        missing_scopes=list(comparison.missing),
        has_all_required_scopes=has_all_required_scopes(
            row.requested_scopes or (), row.granted_scopes or ()
        ),
        shop_status="outdated"
        if row.status
        in {
            ShopifyIntegrationStatusEnum.SCOPES_OUTDATED,
            ShopifyIntegrationStatusEnum.NEEDS_REAUTH,
        }
        else "up_to_date",
    )


def _derive_webhooks_status(
    integration: "ShopifyShopIntegration",
    webhook_subscriptions: Iterable["ShopifyWebhookSubscription"],
) -> str:
    subscriptions_by_topic = {
        subscription.topic: subscription for subscription in webhook_subscriptions
    }
    if any(
        subscription.status == ShopifyWebhookSubscriptionStatusEnum.FAILED
        for subscription in subscriptions_by_topic.values()
    ):
        return "has_failures"

    for definition in SHOPIFY_WEBHOOK_REGISTRY:
        if not definition.enabled:
            continue
        if not has_all_required_scopes(
            definition.required_scopes, integration.granted_scopes or ()
        ):  # type: ignore[arg-type]
            continue
        subscription = subscriptions_by_topic.get(definition.topic)
        if (
            subscription is None
            or subscription.status != ShopifyWebhookSubscriptionStatusEnum.ACTIVE
        ):
            return "needs_sync"
    return "synced"


def serialize_shopify_shop_integration(
    row: "ShopifyShopIntegration",
    webhook_subscriptions: Iterable["ShopifyWebhookSubscription"] | None = None,
) -> ShopifyShopIntegrationResult:
    subscriptions = list(webhook_subscriptions or ())
    scopes_status = (
        "outdated"
        if row.status
        in {
            ShopifyIntegrationStatusEnum.SCOPES_OUTDATED,
            ShopifyIntegrationStatusEnum.NEEDS_REAUTH,
        }
        else "up_to_date"
    )
    return ShopifyShopIntegrationResult(
        client_id=row.client_id,
        workspace_id=row.workspace_id,
        shop_domain=row.shop_domain,
        shop_name=row.shop_name,
        provider=row.provider,
        status=_enum_value(row.status),
        access_token_expires_at=_iso(row.access_token_expires_at),
        granted_scopes=_normalize_scopes(row.granted_scopes),
        requested_scopes=_normalize_scopes(row.requested_scopes),
        api_version=row.api_version,
        installed_at=_iso(row.installed_at),
        uninstalled_at=_iso(row.uninstalled_at),
        last_connected_at=_iso(row.last_connected_at),
        last_health_check_at=_iso(row.last_health_check_at),
        last_health_check_status=row.last_health_check_status,
        last_error_code=row.last_error_code,
        last_error_message=row.last_error_message,
        scopes_status=scopes_status,
        webhooks_status=_derive_webhooks_status(row, subscriptions),
        created_by=_serialize_user_reference(row.created_by),
        updated_by=_serialize_user_reference(row.updated_by),
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        is_deleted=row.is_deleted,
    )
