from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookPayloadFormatEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.domain.shopify.webhook_registry import SHOPIFY_WEBHOOK_REGISTRY
from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.remove_shopify_webhooks_for_shop import (
    remove_shopify_webhooks_for_shop,
)
from beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop import (
    MISSING_REQUIRED_SCOPE_ERROR_CODE,
    sync_shopify_webhook_subscriptions_for_shop,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.webhook_subscription_client import RemoteWebhookSubscription


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_workspace_and_user(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _seed_integration(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    shop_domain: str,
    granted_scopes: list[str],
) -> ShopifyShopIntegration:
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        granted_scopes=granted_scopes,
        requested_scopes=granted_scopes,
        api_version="2026-01",
        installed_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_connected_at=datetime.now(timezone.utc) - timedelta(days=1),
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


async def _fetch_subscription_rows(db_session, shop_integration_id: str) -> dict[str, ShopifyWebhookSubscription]:
    rows = (
        await db_session.execute(
            select(ShopifyWebhookSubscription).where(
                ShopifyWebhookSubscription.shop_integration_id == shop_integration_id
            )
        )
    ).scalars().all()
    return {row.topic: row for row in rows}


async def _fetch_events(db_session, shop_integration_id: str) -> list[ShopifyIntegrationEvent]:
    return (
        await db_session.execute(
            select(ShopifyIntegrationEvent)
            .where(ShopifyIntegrationEvent.shop_integration_id == shop_integration_id)
            .order_by(ShopifyIntegrationEvent.created_at.asc())
        )
    ).scalars().all()


def _configure_settings(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.config.settings.shopify_webhook_base_url", "https://backend.example.com")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_integration_debug_logs", False)


def _remote_subscription(topic: str, callback_url: str, suffix: str = "1") -> RemoteWebhookSubscription:
    return RemoteWebhookSubscription(
        id=f"gid://shopify/WebhookSubscription/{topic.replace('/', '-')}-{suffix}",
        topic=topic,
        callback_url=callback_url,
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    )


@pytest.mark.integration
async def test_sync_creates_missing_subscriptions_and_records_event(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"create-shop-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders", "read_products"],
    )
    await db_session.commit()

    created_calls: list[tuple[str, str]] = []

    async def _fake_list_remote(**kwargs):
        return []

    async def _fake_create_remote(**kwargs):
        created_calls.append((kwargs["topic"], kwargs["callback_url"]))
        return _remote_subscription(kwargs["topic"], kwargs["callback_url"], suffix="created")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.create_remote_webhook_subscription",
        _fake_create_remote,
    )

    result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    rows = await _fetch_subscription_rows(db_session, integration.client_id)
    events = await _fetch_events(db_session, integration.client_id)

    assert sorted(result["created_topics"]) == sorted(definition.topic for definition in SHOPIFY_WEBHOOK_REGISTRY)
    assert len(created_calls) == len(SHOPIFY_WEBHOOK_REGISTRY)
    assert all(callback_url == "https://backend.example.com/api/v1/shopify/webhooks" for _, callback_url in created_calls)
    assert all(row.status == ShopifyWebhookSubscriptionStatusEnum.ACTIVE for row in rows.values())
    assert events[-1].event_type == ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC
    assert events[-1].metadata_json["created_topics"] == result["created_topics"]


@pytest.mark.integration
async def test_sync_is_idempotent_when_remote_state_matches_desired(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"idempotent-shop-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders", "read_products"],
    )
    await db_session.commit()

    callback_url = "https://backend.example.com/api/v1/shopify/webhooks"
    remote_state = [_remote_subscription(definition.topic, callback_url, suffix="stable") for definition in SHOPIFY_WEBHOOK_REGISTRY]
    create_calls: list[str] = []
    delete_calls: list[str] = []

    async def _fake_list_remote(**kwargs):
        return remote_state

    async def _fake_create_remote(**kwargs):
        create_calls.append(kwargs["topic"])
        return _remote_subscription(kwargs["topic"], kwargs["callback_url"], suffix="created")

    async def _fake_delete_remote(**kwargs):
        delete_calls.append(kwargs["remote_subscription_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.create_remote_webhook_subscription",
        _fake_create_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.delete_remote_webhook_subscription",
        _fake_delete_remote,
    )

    first_result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )
    second_result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    assert create_calls == []
    assert delete_calls == []
    assert sorted(first_result["verified_topics"]) == sorted(definition.topic for definition in SHOPIFY_WEBHOOK_REGISTRY)
    assert sorted(second_result["verified_topics"]) == sorted(definition.topic for definition in SHOPIFY_WEBHOOK_REGISTRY)


@pytest.mark.integration
async def test_sync_skips_missing_scope_topics_and_marks_local_rows_failed(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"scope-shop-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders"],
    )
    await db_session.commit()

    create_calls: list[str] = []

    async def _fake_list_remote(**kwargs):
        return []

    async def _fake_create_remote(**kwargs):
        create_calls.append(kwargs["topic"])
        return _remote_subscription(kwargs["topic"], kwargs["callback_url"], suffix="created")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.create_remote_webhook_subscription",
        _fake_create_remote,
    )

    result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    rows = await _fetch_subscription_rows(db_session, integration.client_id)

    assert "products/create" in result["missing_scope_topics"]
    assert "products/update" in result["missing_scope_topics"]
    assert "products/delete" in result["missing_scope_topics"]
    assert "products/create" not in create_calls
    assert rows["products/create"].status == ShopifyWebhookSubscriptionStatusEnum.FAILED
    assert rows["products/create"].last_error_code == MISSING_REQUIRED_SCOPE_ERROR_CODE


@pytest.mark.integration
async def test_sync_does_not_delete_remote_subscription_only_because_scope_is_missing(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"missing-scope-existing-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders"],
    )
    await db_session.commit()

    callback_url = "https://backend.example.com/api/v1/shopify/webhooks"
    delete_calls: list[str] = []

    async def _fake_list_remote(**kwargs):
        return [_remote_subscription("products/create", callback_url, suffix="existing")]

    async def _fake_create_remote(**kwargs):
        return _remote_subscription(kwargs["topic"], kwargs["callback_url"], suffix="created")

    async def _fake_delete_remote(**kwargs):
        delete_calls.append(kwargs["remote_subscription_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.create_remote_webhook_subscription",
        _fake_create_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.delete_remote_webhook_subscription",
        _fake_delete_remote,
    )

    result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    rows = await _fetch_subscription_rows(db_session, integration.client_id)

    assert "products/create" in result["missing_scope_topics"]
    assert delete_calls == []
    assert rows["products/create"].status == ShopifyWebhookSubscriptionStatusEnum.FAILED
    assert rows["products/create"].remote_subscription_id.endswith("existing")


@pytest.mark.integration
async def test_sync_removes_absent_registry_topic_only_when_callback_matches_backend(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"remove-old-topic-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders", "read_products"],
    )
    old_row = ShopifyWebhookSubscription(
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        topic="orders/legacy",
        callback_url="https://backend.example.com/api/v1/shopify/webhooks",
        remote_subscription_id="gid://shopify/WebhookSubscription/orders-legacy-local",
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
        required_scopes=["read_orders"],
        status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
        installed_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(old_row)
    await db_session.commit()

    callback_url = "https://backend.example.com/api/v1/shopify/webhooks"
    delete_calls: list[str] = []

    async def _fake_list_remote(**kwargs):
        return [
            _remote_subscription("orders/legacy", callback_url, suffix="owned"),
            _remote_subscription("orders/legacy", "https://other-backend.example.com/api/v1/shopify/webhooks", suffix="foreign"),
            _remote_subscription("orders/create", callback_url, suffix="desired"),
        ]

    async def _fake_create_remote(**kwargs):
        return _remote_subscription(kwargs["topic"], kwargs["callback_url"], suffix="created")

    async def _fake_delete_remote(**kwargs):
        delete_calls.append(kwargs["remote_subscription_id"])

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.create_remote_webhook_subscription",
        _fake_create_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.delete_remote_webhook_subscription",
        _fake_delete_remote,
    )

    result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    row = (await _fetch_subscription_rows(db_session, integration.client_id))["orders/legacy"]

    assert delete_calls == ["gid://shopify/WebhookSubscription/orders-legacy-owned"]
    assert "orders/legacy" in result["removed_topics"]
    assert row.status == ShopifyWebhookSubscriptionStatusEnum.REMOVED


@pytest.mark.integration
async def test_sync_continues_when_one_topic_create_fails(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"partial-failure-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders", "read_products"],
    )
    await db_session.commit()

    async def _fake_list_remote(**kwargs):
        return []

    async def _fake_create_remote(**kwargs):
        if kwargs["topic"] == "orders/updated":
            raise ShopifyGraphQLRetryableError(
                "Shopify create failed temporarily.",
                error_code="server_error",
            )
        return _remote_subscription(kwargs["topic"], kwargs["callback_url"], suffix="created")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop.create_remote_webhook_subscription",
        _fake_create_remote,
    )

    result = await sync_shopify_webhook_subscriptions_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    rows = await _fetch_subscription_rows(db_session, integration.client_id)

    assert "orders/updated" in result["failed_topics"]
    assert rows["orders/updated"].status == ShopifyWebhookSubscriptionStatusEnum.FAILED
    assert rows["orders/create"].status == ShopifyWebhookSubscriptionStatusEnum.ACTIVE


@pytest.mark.integration
async def test_remove_shopify_webhooks_marks_local_rows_removed_and_is_idempotent(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=f"remove-shop-{uuid4().hex[:8]}.myshopify.com",
        granted_scopes=["read_orders", "read_products"],
    )
    callback_url = "https://backend.example.com/api/v1/shopify/webhooks"
    for topic in ("orders/create", "products/create"):
        db_session.add(
            ShopifyWebhookSubscription(
                workspace_id=workspace.client_id,
                shop_integration_id=integration.client_id,
                topic=topic,
                callback_url=callback_url,
                remote_subscription_id=f"gid://shopify/WebhookSubscription/{topic}",
                payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
                required_scopes=["read_orders"] if topic.startswith("orders/") else ["read_products"],
                status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
                installed_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
    await db_session.commit()

    delete_calls: list[str] = []
    current_remote = [
        _remote_subscription("orders/create", callback_url, suffix="owned"),
        _remote_subscription("products/create", callback_url, suffix="owned"),
    ]

    async def _fake_list_remote(**kwargs):
        return list(current_remote)

    async def _fake_delete_remote(**kwargs):
        delete_calls.append(kwargs["remote_subscription_id"])
        current_remote[:] = [
            remote_subscription
            for remote_subscription in current_remote
            if remote_subscription.id != kwargs["remote_subscription_id"]
        ]

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.remove_shopify_webhooks_for_shop.list_remote_webhook_subscriptions",
        _fake_list_remote,
    )
    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.remove_shopify_webhooks_for_shop.delete_remote_webhook_subscription",
        _fake_delete_remote,
    )

    first_result = await remove_shopify_webhooks_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )
    second_result = await remove_shopify_webhooks_for_shop(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id},
        )
    )

    rows = await _fetch_subscription_rows(db_session, integration.client_id)
    events = await _fetch_events(db_session, integration.client_id)

    assert len(delete_calls) == 2
    assert sorted(first_result["removed_topics"]) == ["orders/create", "products/create"]
    assert sorted(second_result["removed_topics"]) == ["orders/create", "products/create"]
    assert all(row.status == ShopifyWebhookSubscriptionStatusEnum.REMOVED for row in rows.values())
    assert events[-1].event_type == ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC
