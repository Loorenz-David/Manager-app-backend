from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime, timezone

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookPayloadFormatEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.domain.shopify.results import (
    ShopifyIntegrationEventHistoryRecordResult,
    ShopifyScopeStatusResult,
    ShopifyShopIntegrationResult,
    ShopifyWebhookIntakeHistoryRecordResult,
    ShopifyWebhookSubscriptionResult,
)
from beyo_manager.domain.shopify.serializers import (
    _filter_safe_metadata,
    serialize_shopify_integration_event_history_record,
    serialize_shopify_scope_status,
    serialize_shopify_shop_integration,
    serialize_shopify_webhook_intake_history_record,
    serialize_shopify_webhook_subscription,
)
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.models.tables.users.user import User


def test_shopify_serializer_result_fields_do_not_expose_secrets() -> None:
    forbidden_fragments = [
        "access_token_encrypted",
        "state",
        "raw_payload",
        "hmac",
        "client_secret",
        "webhook_secret",
        "created_by_id",
        "updated_by_id",
    ]

    for result_type in [
        ShopifyShopIntegrationResult,
        ShopifyWebhookSubscriptionResult,
        ShopifyScopeStatusResult,
        ShopifyWebhookIntakeHistoryRecordResult,
        ShopifyIntegrationEventHistoryRecordResult,
    ]:
        field_names = [field.name for field in fields(result_type)]
        combined = " ".join(field_names).lower()
        for fragment in forbidden_fragments:
            assert fragment not in combined


def test_serialize_shopify_shop_integration_derives_statuses_without_leaking_tokens() -> None:
    actor = User(
        client_id="usr_1",
        username="actor",
        email="actor@example.com",
        password="secret",
    )
    integration = ShopifyShopIntegration(
        workspace_id="ws_1",
        shop_domain="demo-shop.myshopify.com",
        shop_name="Demo Shop",
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        access_token_expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        granted_scopes=["read_orders"],
        requested_scopes=["read_orders", "write_products"],
        api_version="2026-01",
        installed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_connected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_health_check_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        last_health_check_status="ok",
        last_error_code=None,
        last_error_message=None,
        created_by_id="usr_1",
        updated_by_id="usr_1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        is_deleted=False,
    )
    integration.created_by = actor
    integration.updated_by = actor
    failed_subscription = ShopifyWebhookSubscription(
        workspace_id="ws_1",
        shop_integration_id=integration.client_id,
        topic="orders/create",
        callback_url="https://backend.example.com/api/v1/shopify/webhooks",
        remote_subscription_id="remote_1",
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
        required_scopes=["read_orders"],
        status=ShopifyWebhookSubscriptionStatusEnum.FAILED,
        installed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_verified_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        last_install_attempt_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        last_error_code="missing_scope",
        last_error_message="missing scope",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    result = serialize_shopify_shop_integration(integration, [failed_subscription])
    serialized = asdict(result)

    assert serialized["status"] == "active"
    assert serialized["scopes_status"] == "up_to_date"
    assert serialized["webhooks_status"] == "has_failures"
    assert serialized["created_by"] == {
        "client_id": "usr_1",
        "username": "actor",
        "profile_picture": None,
    }
    assert serialized["updated_by"] == {
        "client_id": "usr_1",
        "username": "actor",
        "profile_picture": None,
    }
    assert "access_token_encrypted" not in serialized
    assert "encrypted-token" not in str(serialized)


def test_serialize_shopify_scope_status_reports_missing_scopes() -> None:
    integration = ShopifyShopIntegration(
        workspace_id="ws_1",
        shop_domain="demo-shop.myshopify.com",
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.SCOPES_OUTDATED,
        granted_scopes=["read_orders"],
        requested_scopes=["read_orders", "write_products"],
        api_version="2026-01",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        is_deleted=False,
    )

    result = serialize_shopify_scope_status(integration)

    assert result.has_all_required_scopes is False
    assert result.missing_scopes == ["write_products"]
    assert result.shop_status == "outdated"


def test_filter_safe_metadata_removes_blocked_keys_case_insensitively() -> None:
    filtered = _filter_safe_metadata(
        {
            "shop_domain": "demo-shop.myshopify.com",
            "sync_status": "pending",
            "tokenValue": "secret",
            "client_secret": "nope",
            "error_code": "hidden-because-code-is-blocked",
            "payload": {"nested": True},
            "remove_webhooks_task_id": "task_1",
            "Provider_Response": {"foo": "bar"},
        }
    )

    assert filtered == {
        "shop_domain": "demo-shop.myshopify.com",
        "sync_status": "pending",
        "remove_webhooks_task_id": "task_1",
    }


def test_serialize_shopify_webhook_intake_history_record_excludes_raw_payload() -> None:
    intake = ShopifyWebhookIntake(
        workspace_id="ws_1",
        shop_integration_id="shpint_1",
        shop_domain="demo-shop.myshopify.com",
        topic="orders/create",
        webhook_id="wh_1",
        dedupe_key="dedupe_1",
        raw_payload={"secret": True},
        attempts=2,
        retryable=True,
        received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        processing_started_at=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
        processed_at=datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc),
        last_error=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, 0, 3, tzinfo=timezone.utc),
    )

    serialized = asdict(serialize_shopify_webhook_intake_history_record(intake))

    assert serialized["record_type"] == "webhook_intake"
    assert serialized["topic"] == "orders/create"
    assert "raw_payload" not in serialized
    assert "secret" not in str(serialized)


def test_serialize_shopify_integration_event_history_record_filters_metadata() -> None:
    actor = User(
        client_id="usr_1",
        username="actor",
        email="actor@example.com",
        password="secret",
    )
    event = ShopifyIntegrationEvent(
        workspace_id="ws_1",
        shop_integration_id="shpint_1",
        event_type="webhook_processed",
        severity="info",
        message="Processed.",
        metadata_json={
            "shop_domain": "demo-shop.myshopify.com",
            "topic": "orders/create",
            "webhook_id": "wh_1",
            "processing_status": "done",
            "oauth_code": "drop-me",
            "raw_payload": {"secret": True},
        },
        created_by_id="usr_1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    event.created_by = actor

    serialized = asdict(serialize_shopify_integration_event_history_record(event))

    assert serialized["record_type"] == "integration_event"
    assert serialized["event_type"] == "webhook_processed"
    assert serialized["created_by"] == {
        "client_id": "usr_1",
        "username": "actor",
        "profile_picture": None,
    }
    assert serialized["metadata_json"] == {
        "shop_domain": "demo-shop.myshopify.com",
        "topic": "orders/create",
        "webhook_id": "wh_1",
        "processing_status": "done",
    }