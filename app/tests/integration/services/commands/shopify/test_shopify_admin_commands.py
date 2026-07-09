from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.create_shopify_reauthorize_url import create_shopify_reauthorize_url
from beyo_manager.services.commands.shopify.disconnect_shopify_shop import disconnect_shopify_shop
from beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_for_shop import enqueue_shopify_webhook_sync_for_shop
from beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_for_workspace import enqueue_shopify_webhook_sync_for_workspace
from beyo_manager.services.context import ServiceContext


def unique_shop_domain(prefix: str = "shop") -> str:
    return f"{prefix}-{uuid4().hex}.myshopify.com"


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": "admin", "username": "tester"},
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_workspace_and_user(db_session) -> tuple[Workspace, Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    other_workspace = Workspace(client_id=f"ws_other_{suffix}", name=f"Other {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, other_workspace, user])
    await db_session.flush()
    return workspace, other_workspace, user


async def _seed_integration(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    status: ShopifyIntegrationStatusEnum,
    shop_domain: str,
) -> ShopifyShopIntegration:
    now = datetime.now(timezone.utc) - timezone.utc.utcoffset(datetime.now(timezone.utc))
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=status,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_orders"],
        requested_scopes=["read_orders"],
        api_version="2026-01",
        installed_at=now,
        last_connected_at=now,
        created_by_id=user_id,
        updated_by_id=user_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


@pytest.mark.integration
async def test_create_shopify_reauthorize_url_uses_stored_shop_domain(db_session, monkeypatch) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    stored_shop_domain = unique_shop_domain("stored-shop")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        shop_domain=stored_shop_domain,
    )
    await db_session.flush()

    async def _fake_install_url(ctx: ServiceContext) -> dict:
        assert ctx.incoming_data["shop_domain"] == integration.shop_domain
        assert ctx.incoming_data["redirect_after_success"] == "default"
        return {"install_url": "https://shopify.test/install", "shop_domain": ctx.incoming_data["shop_domain"], "expires_at": "2026-01-01T00:00:00+00:00"}

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.create_shopify_reauthorize_url.create_shopify_install_url",
        _fake_install_url,
    )

    result = await create_shopify_reauthorize_url(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"shop_integration_id": integration.client_id, "shop_domain": "malicious.example.com"},
        )
    )

    assert result == {
        "install_url": "https://shopify.test/install",
        "shop_domain": integration.shop_domain,
        "expires_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.mark.integration
async def test_disconnect_shopify_shop_soft_deletes_nothing_and_enqueues_remove_task(db_session, monkeypatch) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    disconnect_shop_domain = unique_shop_domain("disconnect-shop")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        shop_domain=disconnect_shop_domain,
    )
    await db_session.flush()

    captured: dict = {}

    async def _fake_create_instant_task(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(client_id="task_disconnect_1")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.disconnect_shopify_shop.create_instant_task",
        _fake_create_instant_task,
    )

    result = await disconnect_shopify_shop(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, incoming_data={"shop_integration_id": integration.client_id})
    )

    refreshed = await db_session.get(ShopifyShopIntegration, integration.client_id)
    events = (
        await db_session.execute(
            select(ShopifyIntegrationEvent).where(ShopifyIntegrationEvent.shop_integration_id == integration.client_id)
        )
    ).scalars().all()

    assert result["status"] == ShopifyIntegrationStatusEnum.DISABLED.value
    assert refreshed is not None
    assert refreshed.status == ShopifyIntegrationStatusEnum.DISABLED
    assert refreshed.uninstalled_at is not None
    assert refreshed.access_token_encrypted is None
    assert refreshed.is_deleted is False
    assert len(events) == 1
    assert events[0].event_type == ShopifyIntegrationEventTypeEnum.DISCONNECT
    assert events[0].severity == ShopifyIntegrationEventSeverityEnum.INFO
    assert events[0].metadata_json["action"] == "disconnect"
    assert events[0].metadata_json["previous_status"] == ShopifyIntegrationStatusEnum.ACTIVE.value
    assert events[0].metadata_json["new_status"] == "disabled"
    assert events[0].metadata_json["remove_webhooks_task_id"] == "task_disconnect_1"
    assert captured["task_type"] == TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP
    assert captured["payload"] == {"shop_integration_id": integration.client_id}
    assert captured["event_client_id"] == events[0].client_id


@pytest.mark.integration
async def test_enqueue_shopify_webhook_sync_for_shop_records_event_and_task(db_session, monkeypatch) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    sync_shop_domain = unique_shop_domain("sync-shop")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        shop_domain=sync_shop_domain,
    )
    await db_session.flush()

    captured: dict = {}

    async def _fake_create_instant_task(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(client_id="task_sync_1")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_for_shop.create_instant_task",
        _fake_create_instant_task,
    )

    result = await enqueue_shopify_webhook_sync_for_shop(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, incoming_data={"shop_integration_id": integration.client_id})
    )

    events = (
        await db_session.execute(
            select(ShopifyIntegrationEvent).where(ShopifyIntegrationEvent.shop_integration_id == integration.client_id)
        )
    ).scalars().all()

    assert result == {
        "shop_integration_id": integration.client_id,
        "shop_domain": integration.shop_domain,
        "sync_status": "pending",
        "sync_webhooks_task_id": "task_sync_1",
    }
    assert len(events) == 1
    assert events[0].event_type == ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC
    assert captured["task_type"] == TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP
    assert captured["payload"] == {"shop_integration_id": integration.client_id}
    assert captured["event_client_id"] == events[0].client_id


@pytest.mark.integration
async def test_enqueue_shopify_webhook_sync_for_workspace_only_includes_active_like_non_deleted_shops(db_session, monkeypatch) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    active_shop_domain = unique_shop_domain("active")
    error_shop_domain = unique_shop_domain("error")
    disabled_shop_domain = unique_shop_domain("disabled")
    other_shop_domain = unique_shop_domain("other")
    active = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        shop_domain=active_shop_domain,
    )
    error = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ERROR,
        shop_domain=error_shop_domain,
    )
    await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.DISABLED,
        shop_domain=disabled_shop_domain,
    )
    await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        shop_domain=other_shop_domain,
    )
    await db_session.flush()

    captured: list[dict] = []

    async def _fake_create_instant_task(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(client_id=f"task_{len(captured)}")

    monkeypatch.setattr(
        "beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_for_workspace.create_instant_task",
        _fake_create_instant_task,
    )

    result = await enqueue_shopify_webhook_sync_for_workspace(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, incoming_data={})
    )

    assert result["enqueued_count"] == 2
    assert {shop["shop_integration_id"] for shop in result["shops"]} == {active.client_id, error.client_id}
    assert len(captured) == 2
    assert all(call["task_type"] == TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP for call in captured)
    assert {call["payload"]["shop_integration_id"] for call in captured} == {active.client_id, error.client_id}
    assert {call["event_client_id"] for call in captured}