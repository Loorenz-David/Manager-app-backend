from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum, ShopifyWebhookPayloadFormatEnum, ShopifyWebhookSubscriptionStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_subscription import ShopifyWebhookSubscription
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.shopify.get_shopify_scope_status import get_shopify_scope_status
from beyo_manager.services.queries.shopify.get_shopify_shop_integration import get_shopify_shop_integration
from beyo_manager.services.queries.shopify.list_shopify_shop_integrations import list_shopify_shop_integrations


def unique_shop_domain(prefix: str = "shop") -> str:
    return f"{prefix}-{uuid4().hex}.myshopify.com"


def _ctx(db_session, *, workspace_id: str, incoming_data: dict | None = None, query_params: dict | None = None) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "role_name": "admin", "user_id": "usr_1"},
        incoming_data=incoming_data or {},
        query_params=query_params or {},
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
    user_id: str | None = None,
    status: ShopifyIntegrationStatusEnum,
    created_at: datetime,
    shop_domain: str,
) -> ShopifyShopIntegration:
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=status,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_orders"],
        requested_scopes=["read_orders", "write_products"],
        api_version="2026-01",
        installed_at=created_at - timedelta(hours=1),
        last_connected_at=created_at - timedelta(hours=1),
        created_by_id=user_id,
        updated_by_id=user_id,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


async def _seed_subscription(
    db_session,
    *,
    workspace_id: str,
    shop_integration_id: str,
    topic: str,
    status: ShopifyWebhookSubscriptionStatusEnum,
) -> ShopifyWebhookSubscription:
    row = ShopifyWebhookSubscription(
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        topic=topic,
        callback_url="https://backend.example.com/api/v1/shopify/webhooks",
        remote_subscription_id=f"remote_{topic}",
        payload_format=ShopifyWebhookPayloadFormatEnum.JSON,
        required_scopes=["read_orders"],
        status=status,
        installed_at=datetime.now(timezone.utc),
        last_verified_at=datetime.now(timezone.utc),
        last_install_attempt_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(row)
    await db_session.flush()
    return row


@pytest.mark.integration
async def test_list_shopify_shop_integrations_is_workspace_scoped_and_paginated(db_session) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fourth_shop_domain = unique_shop_domain("fourth")
    first_shop_domain = unique_shop_domain("first")
    second_shop_domain = unique_shop_domain("second")
    third_shop_domain = unique_shop_domain("third")
    other_shop_domain = unique_shop_domain("other")
    await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.DISABLED,
        created_at=base - timedelta(minutes=1),
        shop_domain=fourth_shop_domain,
    )
    first = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.DISABLED,
        created_at=base,
        shop_domain=first_shop_domain,
    )
    second = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.UNINSTALLED,
        created_at=base + timedelta(minutes=1),
        shop_domain=second_shop_domain,
    )
    third = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ERROR,
        created_at=base + timedelta(minutes=2),
        shop_domain=third_shop_domain,
    )
    await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=base + timedelta(minutes=3),
        shop_domain=other_shop_domain,
    )
    await db_session.flush()

    result = await list_shopify_shop_integrations(
        _ctx(db_session, workspace_id=workspace.client_id, query_params={"limit": "2", "offset": "1"})
    )

    assert result["shops_pagination"] == {"limit": 2, "offset": 1, "has_more": True}
    assert [item["client_id"] for item in result["shops"]] == [second.client_id, first.client_id]
    assert all(item["workspace_id"] == workspace.client_id for item in result["shops"])
    assert {item["status"] for item in result["shops"]} == {ShopifyIntegrationStatusEnum.UNINSTALLED.value, ShopifyIntegrationStatusEnum.DISABLED.value}
    assert all(item["created_by"] == {"client_id": user.client_id, "username": user.username, "profile_picture": None} for item in result["shops"])
    assert all(item["updated_by"] == {"client_id": user.client_id, "username": user.username, "profile_picture": None} for item in result["shops"])

    all_result = await list_shopify_shop_integrations(_ctx(db_session, workspace_id=workspace.client_id, query_params={"limit": "10"}))
    assert {item["status"] for item in all_result["shops"]} == {
        ShopifyIntegrationStatusEnum.ERROR.value,
        ShopifyIntegrationStatusEnum.UNINSTALLED.value,
        ShopifyIntegrationStatusEnum.DISABLED.value,
    }
    assert all(item["workspace_id"] == workspace.client_id for item in all_result["shops"])


@pytest.mark.integration
async def test_get_shopify_shop_integration_is_workspace_scoped_and_returns_subscription_summary(db_session) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    detail_shop_domain = unique_shop_domain("detail")
    other_detail_shop_domain = unique_shop_domain("other-detail")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        shop_domain=detail_shop_domain,
    )
    await _seed_subscription(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        topic="orders/create",
        status=ShopifyWebhookSubscriptionStatusEnum.ACTIVE,
    )
    await _seed_subscription(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        topic="products/create",
        status=ShopifyWebhookSubscriptionStatusEnum.FAILED,
    )
    other_integration = await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        shop_domain=other_detail_shop_domain,
    )
    await db_session.flush()

    result = await get_shopify_shop_integration(
        _ctx(db_session, workspace_id=workspace.client_id, incoming_data={"shop_integration_id": integration.client_id})
    )

    assert result["shop_integration"]["client_id"] == integration.client_id
    assert result["shop_integration"]["webhooks_status"] == "has_failures"
    assert result["shop_integration"]["created_by"] == {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": None,
    }
    assert result["shop_integration"]["updated_by"] == {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": None,
    }
    assert result["webhook_subscription_summary"] == {"total": 2, "active": 1, "failed": 1, "pending": 0, "disabled": 0, "removed": 0}
    assert len(result["webhook_subscriptions"]) == 2

    with pytest.raises(NotFound):
        await get_shopify_shop_integration(
            _ctx(db_session, workspace_id=workspace.client_id, incoming_data={"shop_integration_id": other_integration.client_id})
        )


@pytest.mark.integration
async def test_get_shopify_scope_status_supports_single_shop_and_workspace_listing(db_session) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    outdated_shop_domain = unique_shop_domain("outdated")
    current_shop_domain = unique_shop_domain("current")
    outdated = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.SCOPES_OUTDATED,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        shop_domain=outdated_shop_domain,
    )
    current = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        shop_domain=current_shop_domain,
    )
    await db_session.flush()

    single = await get_shopify_scope_status(
        _ctx(db_session, workspace_id=workspace.client_id, query_params={"shop_integration_id": outdated.client_id})
    )
    assert len(single["scope_statuses"]) == 1
    assert single["scope_statuses"][0]["shop_integration_id"] == outdated.client_id
    assert single["scope_statuses"][0]["shop_status"] == "outdated"

    all_result = await get_shopify_scope_status(_ctx(db_session, workspace_id=workspace.client_id))
    assert {item["shop_integration_id"] for item in all_result["scope_statuses"]} == {outdated.client_id, current.client_id}