from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyProductSyncItemStatusEnum,
    ShopifyWebhookIntakeStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.tasks.shopify.handle_shopify_process_webhook import (
    handle_shopify_process_webhook,
)
from beyo_manager.services.tasks.shopify.handle_shopify_process_products import (
    handle_shopify_process_products,
)


_HANDLER_LOGGER_NAME = "beyo_manager.services.tasks.shopify.handle_shopify_process_webhook"


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
) -> ShopifyShopIntegration:
    now = datetime.now(timezone.utc) - timedelta(days=1)
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
    status: ShopifyWebhookIntakeStatusEnum,
    topic: str = "orders/create",
    raw_payload: dict | None = None,
) -> ShopifyWebhookIntake:
    intake = ShopifyWebhookIntake(
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        shop_domain=shop_domain,
        topic=topic,
        webhook_id=f"wh_{uuid4().hex[:8]}",
        dedupe_key=f"{shop_integration_id}:{topic}:{uuid4().hex[:8]}",
        raw_payload=raw_payload,
        status=status,
        retryable=status == ShopifyWebhookIntakeStatusEnum.RECEIVED,
    )
    if status == ShopifyWebhookIntakeStatusEnum.PROCESSING:
        intake.processing_started_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    if status == ShopifyWebhookIntakeStatusEnum.PROCESSED:
        intake.processed_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.add(intake)
    await db_session.flush()
    return intake


async def _fetch_processed_events(db_session, shop_integration_id: str) -> list[ShopifyIntegrationEvent]:
    return (
        await db_session.execute(
            select(ShopifyIntegrationEvent)
            .where(
                ShopifyIntegrationEvent.shop_integration_id == shop_integration_id,
                ShopifyIntegrationEvent.event_type == ShopifyIntegrationEventTypeEnum.WEBHOOK_PROCESSED,
            )
            .order_by(ShopifyIntegrationEvent.created_at.asc())
        )
    ).scalars().all()


@pytest.mark.integration
async def test_handle_shopify_process_webhook_marks_received_intake_processed_and_is_idempotent(
    db_session,
    caplog,
) -> None:
    workspace, user = await _seed_workspace_and_user(db_session)
    shop_domain = f"handler-shop-{uuid4().hex[:8]}.myshopify.com"
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
    )
    intake = await _seed_intake(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        shop_domain=shop_domain,
        status=ShopifyWebhookIntakeStatusEnum.RECEIVED,
        raw_payload={"id": 123, "title": "Secret order"},
    )
    await db_session.commit()

    with caplog.at_level(logging.INFO, logger=_HANDLER_LOGGER_NAME):
        await handle_shopify_process_webhook({"webhook_intake_id": intake.client_id}, "task_shopify_1")
        await handle_shopify_process_webhook({"webhook_intake_id": intake.client_id}, "task_shopify_2")

    await db_session.refresh(intake)
    refreshed = intake
    events = await _fetch_processed_events(db_session, integration.client_id)

    assert refreshed is not None
    assert refreshed.status == ShopifyWebhookIntakeStatusEnum.PROCESSED
    assert refreshed.processing_started_at is not None
    assert refreshed.processed_at is not None
    assert refreshed.attempts == 1
    assert len(events) == 1
    assert events[0].metadata_json["processing_mode"] == "no_business_processor_yet"
    handler_log_text = "\n".join(record.getMessage() for record in caplog.records if record.name == _HANDLER_LOGGER_NAME)
    assert "Secret order" not in handler_log_text
    assert "encrypted-token" not in handler_log_text


@pytest.mark.integration
@pytest.mark.parametrize(
    "status",
    [
        ShopifyWebhookIntakeStatusEnum.IGNORED,
        ShopifyWebhookIntakeStatusEnum.FAILED,
        ShopifyWebhookIntakeStatusEnum.PROCESSING,
        ShopifyWebhookIntakeStatusEnum.PROCESSED,
    ],
)
async def test_handle_shopify_process_webhook_skips_non_processable_statuses(db_session, status) -> None:
    workspace, user = await _seed_workspace_and_user(db_session)
    shop_domain = f"handler-skip-{uuid4().hex[:8]}.myshopify.com"
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
    )
    intake = await _seed_intake(
        db_session,
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        shop_domain=shop_domain,
        status=status,
    )
    starting_attempts = intake.attempts
    starting_started_at = intake.processing_started_at
    starting_processed_at = intake.processed_at
    await db_session.commit()

    await handle_shopify_process_webhook({"webhook_intake_id": intake.client_id}, "task_shopify_skip")

    refreshed = await db_session.get(ShopifyWebhookIntake, intake.client_id)
    events = await _fetch_processed_events(db_session, integration.client_id)

    assert refreshed is not None
    assert refreshed.status == status
    assert refreshed.attempts == starting_attempts
    assert refreshed.processing_started_at == starting_started_at
    assert refreshed.processed_at == starting_processed_at
    assert events == []


@pytest.mark.integration
async def test_handle_shopify_process_products_transitions_rows_to_succeeded_and_failed(db_session, monkeypatch) -> None:
    workspace, user = await _seed_workspace_and_user(db_session)
    shop_domain = f"product-sync-{uuid4().hex[:8]}.myshopify.com"
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
    )
    success_row = ShopifyProductSyncItem(
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        frontend_client_id="frontend_success",
        normalized_payload_json={
            "product": {"title": "Chair", "status": "DRAFT"},
            "variant": {"barcode": "BAR-SUCCESS"},
            "metafields": [],
        },
        created_by_id=user.client_id,
    )
    failed_row = ShopifyProductSyncItem(
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        frontend_client_id="frontend_failed",
        normalized_payload_json={
            "product": {"title": "Table", "status": "DRAFT"},
            "variant": {"barcode": "BAR-FAILED"},
            "metafields": [],
        },
        created_by_id=user.client_id,
    )
    db_session.add_all([success_row, failed_row])
    await db_session.commit()

    emitted: dict = {}

    async def _fake_find_product_variant_by_identity(**kwargs):
        if kwargs["barcode"] == "BAR-SUCCESS":
            return []
        return [
            {"id": "gid://shopify/ProductVariant/1", "barcode": "BAR-FAILED", "sku": None, "product": {"id": "gid://shopify/Product/1"}},
            {"id": "gid://shopify/ProductVariant/2", "barcode": "BAR-FAILED", "sku": None, "product": {"id": "gid://shopify/Product/2"}},
        ]

    async def _fake_create_shopify_product(**_kwargs):
        # db_session has expire_on_commit=False, so success_row's cached identity-map
        # entry never sees the handler's own (separate-session) commit without an
        # explicit refresh — session.get() alone would just return the stale object.
        await db_session.refresh(success_row)
        assert success_row.status == ShopifyProductSyncItemStatusEnum.PROCESSING
        return {
            "shopify_product_id": "gid://shopify/Product/created",
            "shopify_variant_id": "gid://shopify/ProductVariant/created",
        }

    async def _fake_update_shopify_product(**_kwargs):
        raise AssertionError("Update path should not be reached in this test")

    async def _fake_set_shopify_product_metafields(**_kwargs):
        return None

    async def _fake_emit_to_workspace_room(**kwargs):
        emitted.update(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.tasks.shopify._product_sync_orchestrator.find_product_variant_by_identity",
        _fake_find_product_variant_by_identity,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.shopify._product_sync_orchestrator.create_shopify_product",
        _fake_create_shopify_product,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.shopify._product_sync_orchestrator.update_shopify_product",
        _fake_update_shopify_product,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.shopify._product_sync_orchestrator.set_shopify_product_metafields",
        _fake_set_shopify_product_metafields,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.shopify.handle_shopify_process_products.emit_to_workspace_room",
        _fake_emit_to_workspace_room,
    )

    await handle_shopify_process_products(
        {
            "workspace_id": workspace.client_id,
            "requested_by_user_id": user.client_id,
            "sync_item_client_ids": [success_row.client_id, failed_row.client_id],
        },
        "task_shopify_products_1",
    )

    await db_session.refresh(success_row)
    await db_session.refresh(failed_row)

    assert success_row.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert success_row.shopify_product_id == "gid://shopify/Product/created"
    assert success_row.shopify_variant_id == "gid://shopify/ProductVariant/created"
    assert failed_row.status == ShopifyProductSyncItemStatusEnum.FAILED
    assert failed_row.error_code == "ambiguous_product_match"
    assert emitted["payload"]["task_id"] == "task_shopify_products_1"
    assert emitted["payload"]["succeeded"][0]["frontend_client_id"] == "frontend_success"
    assert emitted["payload"]["failed"][0]["frontend_client_id"] == "frontend_failed"


@pytest.mark.integration
async def test_handle_shopify_process_products_skips_rows_for_disabled_shop_integration(db_session, monkeypatch) -> None:
    workspace, user = await _seed_workspace_and_user(db_session)
    shop_domain = f"product-sync-disabled-{uuid4().hex[:8]}.myshopify.com"
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
    )
    # Simulate the shop being disabled after the sync item was enqueued but
    # before the worker picked up the task.
    integration.status = ShopifyIntegrationStatusEnum.DISABLED
    await db_session.commit()

    row = ShopifyProductSyncItem(
        workspace_id=workspace.client_id,
        shop_integration_id=integration.client_id,
        frontend_client_id="frontend_disabled",
        normalized_payload_json={
            "product": {"title": "Chair", "status": "DRAFT"},
            "variant": {"barcode": "BAR-DISABLED"},
            "metafields": [],
        },
        created_by_id=user.client_id,
    )
    db_session.add(row)
    await db_session.commit()

    emitted: dict = {}

    async def _unexpected_graphql_call(**_kwargs):
        raise AssertionError("Shopify GraphQL must not be called for a disabled shop integration")

    async def _fake_emit_to_workspace_room(**kwargs):
        emitted.update(kwargs)

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.graphql_client.execute_shopify_graphql",
        _unexpected_graphql_call,
    )
    monkeypatch.setattr(
        "beyo_manager.services.tasks.shopify.handle_shopify_process_products.emit_to_workspace_room",
        _fake_emit_to_workspace_room,
    )

    await handle_shopify_process_products(
        {
            "workspace_id": workspace.client_id,
            "requested_by_user_id": user.client_id,
            "sync_item_client_ids": [row.client_id],
        },
        "task_shopify_products_disabled",
    )

    await db_session.refresh(row)

    assert row.status == ShopifyProductSyncItemStatusEnum.FAILED
    assert row.error_code == "missing_shop_integration"
    assert emitted["payload"]["failed"][0]["error_code"] == "missing_shop_integration"
