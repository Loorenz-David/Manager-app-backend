from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookIntakeStatusEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.shopify.get_shopify_webhook_history_records import (
    get_shopify_webhook_history_records,
)


def unique_shop_domain(prefix: str = "shop") -> str:
    return f"{prefix}-{uuid4().hex}.myshopify.com"


def _ctx(
    db_session,
    *,
    workspace_id: str,
    shop_integration_id: str,
    query_params: dict | None = None,
) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "role_name": "admin", "user_id": "usr_1"},
        incoming_data={"shop_integration_id": shop_integration_id},
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
    user_id: str,
    shop_domain: str,
    is_deleted: bool = False,
) -> ShopifyShopIntegration:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=ShopifyIntegrationStatusEnum.ACTIVE,
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
        is_deleted=is_deleted,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


async def _seed_intake(
    db_session,
    *,
    workspace_id: str,
    shop_integration_id: str,
    shop_domain: str,
    topic: str,
    status: ShopifyWebhookIntakeStatusEnum,
    webhook_id: str,
    received_at: datetime,
    client_suffix: str,
) -> ShopifyWebhookIntake:
    intake = ShopifyWebhookIntake(
        client_id=f"shpwhi_{client_suffix}",
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        shop_domain=shop_domain,
        topic=topic,
        webhook_id=webhook_id,
        dedupe_key=f"dedupe_{client_suffix}",
        raw_payload={"private": True},
        status=status,
        attempts=1,
        retryable=True,
        received_at=received_at,
        processing_started_at=received_at + timedelta(seconds=1),
        processed_at=received_at + timedelta(seconds=2),
        last_error=None,
        created_at=received_at,
        updated_at=received_at + timedelta(seconds=3),
    )
    db_session.add(intake)
    await db_session.flush()
    return intake


async def _seed_event(
    db_session,
    *,
    workspace_id: str,
    shop_integration_id: str,
    user_id: str,
    event_type: ShopifyIntegrationEventTypeEnum,
    created_at: datetime,
    client_suffix: str,
    metadata_json: dict | None = None,
) -> ShopifyIntegrationEvent:
    event = ShopifyIntegrationEvent(
        client_id=f"shpevt_{client_suffix}",
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        event_type=event_type,
        severity=ShopifyIntegrationEventSeverityEnum.INFO,
        message=f"{event_type.value} happened",
        metadata_json=metadata_json,
        created_by_id=user_id,
        created_at=created_at,
    )
    db_session.add(event)
    await db_session.flush()
    return event


@pytest.mark.integration
async def test_webhook_history_query_returns_merged_records_newest_first_and_filters_oauth_events(db_session) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    history_shop_domain = unique_shop_domain("history-shop")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=history_shop_domain,
    )
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    newest_intake = await _seed_intake(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        shop_domain=integration.shop_domain,
        topic="orders/create",
        status=ShopifyWebhookIntakeStatusEnum.PROCESSED,
        webhook_id="wh_new",
        received_at=base + timedelta(minutes=3),
        client_suffix="003",
    )
    tied_event = await _seed_event(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        user_id=user.client_id,
        event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_PROCESSED,
        created_at=base + timedelta(minutes=2),
        client_suffix="999",
        metadata_json={"shop_domain": integration.shop_domain, "oauth_code": "hidden", "sync_status": "done"},
    )
    tied_intake = await _seed_intake(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        shop_domain=integration.shop_domain,
        topic="orders/updated",
        status=ShopifyWebhookIntakeStatusEnum.RECEIVED,
        webhook_id="wh_tie",
        received_at=base + timedelta(minutes=2),
        client_suffix="001",
    )
    older_event = await _seed_event(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        user_id=user.client_id,
        event_type=ShopifyIntegrationEventTypeEnum.DISCONNECT,
        created_at=base + timedelta(minutes=1),
        client_suffix="002",
        metadata_json={"action": "disconnect", "remove_webhooks_task_id": "task_1"},
    )
    await _seed_event(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        user_id=user.client_id,
        event_type=ShopifyIntegrationEventTypeEnum.INSTALL,
        created_at=base,
        client_suffix="000",
        metadata_json={"shop_domain": integration.shop_domain},
    )
    await db_session.flush()

    result = await get_shopify_webhook_history_records(
        _ctx(db_session, workspace_id=workspace.client_id, shop_integration_id=integration.client_id)
    )

    records = result["webhook_history_records"]
    assert [record["client_id"] for record in records] == [
        newest_intake.client_id,
        tied_intake.client_id,
        tied_event.client_id,
        older_event.client_id,
    ]
    assert records[0]["record_type"] == "webhook_intake"
    assert records[1]["record_type"] == "webhook_intake"
    assert records[2]["record_type"] == "integration_event"
    assert records[2]["created_by"] == {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": None,
    }
    assert records[2]["metadata_json"] == {"shop_domain": integration.shop_domain, "sync_status": "done"}
    assert all(record.get("event_type") != ShopifyIntegrationEventTypeEnum.INSTALL.value for record in records)
    assert all("raw_payload" not in record for record in records)


@pytest.mark.integration
async def test_webhook_history_query_applies_offset_pagination_and_has_more(db_session) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    paged_shop_domain = unique_shop_domain("paged-shop")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=paged_shop_domain,
    )
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    for index in range(4):
        await _seed_event(
            db_session,
            workspace_id=workspace.client_id,
            shop_integration_id=integration.client_id,
            user_id=user.client_id,
            event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_RECEIVED,
            created_at=base + timedelta(minutes=index),
            client_suffix=f"00{index}",
            metadata_json={"topic": f"orders/{index}"},
        )
    await db_session.flush()

    result = await get_shopify_webhook_history_records(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            shop_integration_id=integration.client_id,
            query_params={"limit": "2", "offset": "1"},
        )
    )

    assert result["webhook_history_records_pagination"] == {"has_more": True, "limit": 2, "offset": 1}
    assert len(result["webhook_history_records"]) == 2


@pytest.mark.integration
async def test_webhook_history_query_returns_empty_history_shape(db_session) -> None:
    workspace, _other_workspace, user = await _seed_workspace_and_user(db_session)
    empty_shop_domain = unique_shop_domain("empty-shop")
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=empty_shop_domain,
    )
    await db_session.flush()

    result = await get_shopify_webhook_history_records(
        _ctx(db_session, workspace_id=workspace.client_id, shop_integration_id=integration.client_id)
    )

    assert result == {
        "webhook_history_records": [],
        "webhook_history_records_pagination": {"has_more": False, "limit": 10, "offset": 0},
    }


@pytest.mark.integration
async def test_webhook_history_query_is_workspace_scoped_and_rejects_soft_deleted_shops(db_session) -> None:
    workspace, other_workspace, user = await _seed_workspace_and_user(db_session)
    valid_shop_domain = unique_shop_domain("valid-shop")
    foreign_shop_domain = unique_shop_domain("foreign-shop")
    deleted_shop_domain = unique_shop_domain("deleted-shop")
    valid = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=valid_shop_domain,
    )
    foreign = await _seed_integration(
        db_session,
        workspace_id=other_workspace.client_id,
        user_id=user.client_id,
        shop_domain=foreign_shop_domain,
    )
    deleted = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=deleted_shop_domain,
        is_deleted=True,
    )
    await db_session.flush()

    ok = await get_shopify_webhook_history_records(
        _ctx(db_session, workspace_id=workspace.client_id, shop_integration_id=valid.client_id)
    )
    assert ok["webhook_history_records"] == []

    with pytest.raises(NotFound, match="Shopify shop integration not found."):
        await get_shopify_webhook_history_records(
            _ctx(db_session, workspace_id=workspace.client_id, shop_integration_id=foreign.client_id)
        )

    with pytest.raises(NotFound, match="Shopify shop integration not found."):
        await get_shopify_webhook_history_records(
            _ctx(db_session, workspace_id=workspace.client_id, shop_integration_id=deleted.client_id)
        )