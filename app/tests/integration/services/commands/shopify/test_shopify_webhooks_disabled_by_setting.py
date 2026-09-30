"""SHOPIFY_WEBHOOKS_ENABLED=false (B-11): the webhook sync removes what this backend owns.

With the setting false every registry entry counts as disabled, so the existing sync
deletes the owned remote subscriptions, marks them REMOVED, and creates nothing — on a
plain sync, a reconcile, or the sync a (re)authorisation enqueues. The integration stays
ACTIVE with its token (outbound pushes continue). With the setting true, unchanged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookPayloadFormatEnum,
    ShopifyWebhookSubscriptionStatusEnum,
)
from beyo_manager.domain.shopify.serializers import _derive_webhooks_status
from beyo_manager.domain.shopify.webhook_registry import (
    SHOPIFY_WEBHOOK_REGISTRY,
    webhook_definition_enabled,
)
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify import sync_shopify_webhook_subscriptions_for_shop as sync_module
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.webhook_subscription_client import RemoteWebhookSubscription

pytestmark = pytest.mark.integration

CALLBACK_URL = "https://backend.example.com/api/v1/shopify/webhooks"
FOREIGN_CALLBACK_URL = "https://someone-else.example.com/hooks"
ALL_TOPICS = sorted(definition.topic for definition in SHOPIFY_WEBHOOK_REGISTRY)


def _remote(topic: str, callback_url: str = CALLBACK_URL, suffix: str = "owned") -> RemoteWebhookSubscription:
    return RemoteWebhookSubscription(
        id=f"gid://shopify/WebhookSubscription/{topic.replace('/', '-')}-{suffix}",
        topic=topic,
        callback_url=callback_url,
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
    )


@pytest.fixture
def shopify_client(monkeypatch):
    """The Shopify Admin client, faked: `remote` is the shop's subscription list."""
    state: dict = {"remote": [], "created": [], "deleted": []}

    async def _list(**kwargs):
        return list(state["remote"])

    async def _create(**kwargs):
        state["created"].append(kwargs["topic"])
        return _remote(kwargs["topic"], kwargs["callback_url"], suffix="created")

    async def _delete(**kwargs):
        state["deleted"].append(kwargs["remote_subscription_id"])

    monkeypatch.setattr(sync_module, "list_remote_webhook_subscriptions", _list)
    monkeypatch.setattr(sync_module, "create_remote_webhook_subscription", _create)
    monkeypatch.setattr(sync_module, "delete_remote_webhook_subscription", _delete)
    monkeypatch.setattr(settings, "shopify_webhook_base_url", "https://backend.example.com")
    monkeypatch.setattr(settings, "shopify_integration_debug_logs", False)
    return state


async def _seed(db_session, *, with_active_rows: bool) -> tuple[ServiceContext, ShopifyShopIntegration]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(client_id=f"usr_{suffix}", username=f"user_{suffix}", email=f"{suffix}@example.com", password="secret")
    db_session.add_all([workspace, user])
    await db_session.flush()
    integration = ShopifyShopIntegration(
        workspace_id=workspace.client_id,
        shop_domain=f"webhooks-off-{suffix}.myshopify.com",
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_orders", "read_products"],
        requested_scopes=["read_orders", "read_products"],
        api_version="2026-01",
        installed_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_connected_at=datetime.now(timezone.utc) - timedelta(days=1),
        created_by_id=user.client_id,
        updated_by_id=user.client_id,
    )
    db_session.add(integration)
    await db_session.flush()
    if with_active_rows:
        for topic in ALL_TOPICS:
            db_session.add(ShopifyWebhookSubscription(
                workspace_id=workspace.client_id,
                shop_integration_id=integration.client_id,
                topic=topic,
                callback_url=CALLBACK_URL,
                remote_subscription_id=_remote(topic).id,
                payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
                required_scopes=[],
                status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
                installed_at=datetime.now(timezone.utc) - timedelta(days=1),
            ))
    await db_session.commit()
    ctx = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": user.client_id, "role_name": "manager", "username": "t"},
        incoming_data={"shop_integration_id": integration.client_id},
        session=db_session,
    )
    return ctx, integration


async def _rows(db_session, integration_id: str) -> dict[str, ShopifyWebhookSubscription]:
    rows = (await db_session.execute(
        select(ShopifyWebhookSubscription).where(ShopifyWebhookSubscription.shop_integration_id == integration_id)
    )).scalars().all()
    return {row.topic: row for row in rows}


async def test_flag_off_sync_removes_owned_subscriptions_and_keeps_the_integration(
    db_session, monkeypatch, shopify_client
):
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", False)
    ctx, integration = await _seed(db_session, with_active_rows=True)
    foreign = _remote("orders/create", FOREIGN_CALLBACK_URL, suffix="foreign")
    shopify_client["remote"] = [_remote(topic) for topic in ALL_TOPICS] + [foreign]

    result = await sync_module.sync_shopify_webhook_subscriptions_for_shop(ctx)

    assert sorted(result["removed_topics"]) == ALL_TOPICS
    assert result["created_topics"] == [] and result["verified_topics"] == []
    assert shopify_client["created"] == []
    assert sorted(shopify_client["deleted"]) == sorted(_remote(topic).id for topic in ALL_TOPICS)
    assert foreign.id not in shopify_client["deleted"]  # not ours: left alone

    rows = await _rows(db_session, integration.client_id)
    assert set(rows) == set(ALL_TOPICS)
    assert all(row.status == ShopifyWebhookSubscriptionStatusEnum.REMOVED for row in rows.values())
    assert all(row.remote_subscription_id is None for row in rows.values())

    await db_session.refresh(integration)
    assert integration.status == ShopifyIntegrationStatusEnum.ACTIVE
    assert integration.access_token_encrypted == "encrypted-token"
    assert integration.is_deleted is False
    assert _derive_webhooks_status(integration, rows.values()) == "synced"


async def test_flag_off_second_sync_is_a_no_op(db_session, monkeypatch, shopify_client):
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", False)
    ctx, _integration = await _seed(db_session, with_active_rows=True)
    shopify_client["remote"] = [_remote(topic) for topic in ALL_TOPICS]
    await sync_module.sync_shopify_webhook_subscriptions_for_shop(ctx)
    shopify_client["remote"] = []
    shopify_client["deleted"].clear()

    result = await sync_module.sync_shopify_webhook_subscriptions_for_shop(ctx)

    assert result["removed_topics"] == [] and result["created_topics"] == []
    assert shopify_client["deleted"] == [] and shopify_client["created"] == []


async def test_flag_off_reauthorisation_sync_registers_nothing(db_session, monkeypatch, shopify_client):
    """A connect or reauthorisation only enqueues this sync; with the flag off it adds nothing."""
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", False)
    ctx, integration = await _seed(db_session, with_active_rows=False)
    shopify_client["remote"] = []

    result = await sync_module.sync_shopify_webhook_subscriptions_for_shop(ctx)

    assert shopify_client["created"] == []
    assert result["created_topics"] == [] and result["removed_topics"] == []
    assert await _rows(db_session, integration.client_id) == {}
    assert _derive_webhooks_status(integration, []) == "synced"


async def test_flag_on_is_unchanged(db_session, monkeypatch, shopify_client):
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", True)
    ctx, integration = await _seed(db_session, with_active_rows=True)
    shopify_client["remote"] = [_remote(topic) for topic in ALL_TOPICS]

    result = await sync_module.sync_shopify_webhook_subscriptions_for_shop(ctx)

    assert sorted(result["verified_topics"]) == ALL_TOPICS
    assert result["removed_topics"] == [] and shopify_client["deleted"] == []
    rows = await _rows(db_session, integration.client_id)
    assert all(row.status == ShopifyWebhookSubscriptionStatusEnum.ACTIVE for row in rows.values())
    assert _derive_webhooks_status(integration, rows.values()) == "synced"


async def test_flag_on_registers_missing_topics(db_session, monkeypatch, shopify_client):
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", True)
    ctx, integration = await _seed(db_session, with_active_rows=False)

    result = await sync_module.sync_shopify_webhook_subscriptions_for_shop(ctx)

    assert sorted(result["created_topics"]) == ALL_TOPICS
    assert sorted(shopify_client["created"]) == ALL_TOPICS
    assert _derive_webhooks_status(integration, []) == "needs_sync"


def test_gate_is_read_at_call_time(monkeypatch):
    definition = SHOPIFY_WEBHOOK_REGISTRY[0]
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", True)
    assert webhook_definition_enabled(definition) is True
    monkeypatch.setattr(settings, "shopify_webhooks_enabled", False)
    assert webhook_definition_enabled(definition) is False
