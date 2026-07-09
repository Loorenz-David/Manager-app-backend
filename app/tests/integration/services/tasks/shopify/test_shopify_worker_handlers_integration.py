from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookIntakeStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.tasks.shopify.handle_shopify_process_webhook import (
    handle_shopify_process_webhook,
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
