from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookIntakeStatusEnum,
)
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.shopify.enqueue_or_record_shopify_webhook import (
    InvalidShopifyWebhookRequest,
    enqueue_or_record_shopify_webhook,
)
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, incoming_data: dict) -> ServiceContext:
    return ServiceContext(identity={}, incoming_data=incoming_data, session=db_session)


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
    status: ShopifyIntegrationStatusEnum,
) -> ShopifyShopIntegration:
    now = datetime.now(timezone.utc) - timedelta(days=1)
    integration = ShopifyShopIntegration(
        workspace_id=workspace_id,
        shop_domain=shop_domain,
        provider="shopify",
        status=status,
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_orders", "read_products"],
        requested_scopes=["read_orders", "read_products"],
        api_version="2026-01",
        installed_at=now,
        last_connected_at=now,
        created_by_id=user_id,
        updated_by_id=user_id,
    )
    db_session.add(integration)
    await db_session.flush()
    return integration


def _signed_webhook(secret: str, raw_body: bytes) -> str:
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _configure_settings(monkeypatch) -> None:
    monkeypatch.setattr("beyo_manager.config.settings.shopify_webhook_secret", "webhook-secret")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_client_secret", "client-secret")
    monkeypatch.setattr("beyo_manager.config.settings.shopify_integration_debug_logs", False)


def _incoming_data(
    *,
    raw_body: bytes,
    signature: str,
    topic: str = "orders/create",
    shop_domain: str = "valid-shop.myshopify.com",
    webhook_id: str | None = "wh_1",
) -> dict:
    return {
        "raw_body": raw_body,
        "hmac_header": signature,
        "topic": topic,
        "shop_domain": shop_domain,
        "webhook_id": webhook_id,
    }


def _unique_shop_domain(label: str) -> str:
    return f"{label}-{uuid4().hex[:8]}.myshopify.com"


async def _fetch_intakes_for_integration(db_session, shop_integration_id: str) -> list[ShopifyWebhookIntake]:
    return (
        await db_session.execute(
            select(ShopifyWebhookIntake)
            .where(ShopifyWebhookIntake.shop_integration_id == shop_integration_id)
            .order_by(ShopifyWebhookIntake.created_at.asc())
        )
    ).scalars().all()


async def _fetch_events_for_integration(db_session, shop_integration_id: str) -> list[ShopifyIntegrationEvent]:
    return (
        await db_session.execute(
            select(ShopifyIntegrationEvent)
            .where(ShopifyIntegrationEvent.shop_integration_id == shop_integration_id)
            .order_by(ShopifyIntegrationEvent.created_at.asc())
        )
    ).scalars().all()


async def _fetch_shopify_process_tasks(db_session, webhook_intake_id: str) -> list[tuple[ExecutionTask, ExecutionPayload]]:
    rows = (
        await db_session.execute(
            select(ExecutionTask, ExecutionPayload)
            .join(ExecutionPayload, ExecutionPayload.execution_task_id == ExecutionTask.client_id)
            .where(
                ExecutionTask.task_type == TaskType.SHOPIFY_PROCESS_WEBHOOK,
                ExecutionPayload.payload["webhook_intake_id"].as_string() == webhook_intake_id,
            )
            .order_by(ExecutionTask.created_at.asc())
        )
    ).all()
    return list(rows)


async def _count_intakes_for_webhook(db_session, webhook_id: str) -> int:
    rows = (
        await db_session.execute(
            select(ShopifyWebhookIntake.client_id).where(ShopifyWebhookIntake.webhook_id == webhook_id)
        )
    ).scalars().all()
    return len(rows)


async def _count_events_for_shop_domain(db_session, shop_domain: str) -> int:
    rows = (
        await db_session.execute(
            select(ShopifyIntegrationEvent.client_id).where(
                ShopifyIntegrationEvent.metadata_json["shop_domain"].astext == shop_domain
            )
        )
    ).scalars().all()
    return len(rows)


@pytest.mark.integration
async def test_valid_supported_webhook_creates_received_intake_and_info_event(db_session, monkeypatch, caplog) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("valid-shop")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    raw_body = b'{"id":123,"title":"Test order"}'
    with caplog.at_level(logging.DEBUG, logger="beyo_manager"):
        result = await enqueue_or_record_shopify_webhook(
            _ctx(
                db_session,
                _incoming_data(
                    raw_body=raw_body,
                    signature=_signed_webhook("webhook-secret", raw_body),
                    shop_domain=shop_domain,
                    webhook_id="wh_valid",
                ),
            )
        )

    intakes = await _fetch_intakes_for_integration(db_session, integration.client_id)
    events = await _fetch_events_for_integration(db_session, integration.client_id)

    assert result["outcome"] == ShopifyWebhookIntakeStatusEnum.RECEIVED.value
    assert len(intakes) == 1
    assert intakes[0].shop_integration_id == integration.client_id
    assert intakes[0].status == ShopifyWebhookIntakeStatusEnum.RECEIVED
    assert intakes[0].retryable is True
    assert intakes[0].raw_payload == {"id": 123, "title": "Test order"}
    assert len(events) == 1
    assert events[0].event_type == ShopifyIntegrationEventTypeEnum.WEBHOOK_RECEIVED
    assert events[0].severity == ShopifyIntegrationEventSeverityEnum.INFO
    assert events[0].metadata_json["processing_status"] == "pending"
    tasks = await _fetch_shopify_process_tasks(db_session, intakes[0].client_id)
    assert len(tasks) == 1
    assert tasks[0][1].payload == {"webhook_intake_id": intakes[0].client_id}
    assert raw_body.decode() not in caplog.text
    assert "webhook-secret" not in caplog.text
    assert "client-secret" not in caplog.text


@pytest.mark.integration
async def test_invalid_hmac_returns_bad_request_and_creates_no_rows(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("invalid-hmac")
    workspace, user = await _seed_workspace_and_user(db_session)
    await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    webhook_id = "wh_invalid_hmac"
    with pytest.raises(InvalidShopifyWebhookRequest, match="Invalid Shopify webhook signature"):
        await enqueue_or_record_shopify_webhook(
            _ctx(
                db_session,
                _incoming_data(
                    raw_body=b'{"id":1}',
                    signature="invalid-signature",
                    shop_domain=shop_domain,
                    webhook_id=webhook_id,
                ),
            )
        )

    assert await _count_intakes_for_webhook(db_session, webhook_id) == 0
    assert await _count_events_for_shop_domain(db_session, shop_domain) == 0


@pytest.mark.integration
async def test_hmac_validation_happens_before_trusting_other_headers(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("invalid-order")
    webhook_id = "wh_invalid_order"

    with pytest.raises(InvalidShopifyWebhookRequest, match="Invalid Shopify webhook signature"):
        await enqueue_or_record_shopify_webhook(
            _ctx(
                db_session,
                {
                    "raw_body": b'{"id":2}',
                    "hmac_header": "bad-signature",
                    "topic": "",
                    "shop_domain": shop_domain,
                    "webhook_id": webhook_id,
                },
            )
        )

    assert await _count_intakes_for_webhook(db_session, webhook_id) == 0
    assert await _count_events_for_shop_domain(db_session, shop_domain) == 0


@pytest.mark.integration
async def test_duplicate_delivery_does_not_create_duplicate_shopify_process_task(
    db_session,
    monkeypatch,
) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("duplicate-task")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    raw_body = b'{"id":99}'
    incoming_data = _incoming_data(
        raw_body=raw_body,
        signature=_signed_webhook("webhook-secret", raw_body),
        shop_domain=shop_domain,
        webhook_id="wh_duplicate_task",
    )

    first_result = await enqueue_or_record_shopify_webhook(_ctx(db_session, incoming_data))
    second_result = await enqueue_or_record_shopify_webhook(_ctx(db_session, incoming_data))

    intakes = await _fetch_intakes_for_integration(db_session, integration.client_id)
    tasks = await _fetch_shopify_process_tasks(db_session, intakes[0].client_id)

    assert first_result["outcome"] == ShopifyWebhookIntakeStatusEnum.RECEIVED.value
    assert second_result["outcome"] == "duplicate"
    assert len(intakes) == 1
    assert len(tasks) == 1


@pytest.mark.integration
@pytest.mark.parametrize(
    ("integration_status", "topic", "expected_outcome"),
    [
        (ShopifyIntegrationStatusEnum.DISABLED, "orders/create", ShopifyWebhookIntakeStatusEnum.IGNORED.value),
        (ShopifyIntegrationStatusEnum.UNINSTALLED, "orders/create", ShopifyWebhookIntakeStatusEnum.IGNORED.value),
        (ShopifyIntegrationStatusEnum.ACTIVE, "unsupported/topic", ShopifyWebhookIntakeStatusEnum.IGNORED.value),
    ],
)
async def test_non_received_intake_outcomes_do_not_enqueue_shopify_process_task(
    db_session,
    monkeypatch,
    integration_status,
    topic,
    expected_outcome,
) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("non-received")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=integration_status,
    )
    await db_session.commit()

    raw_body = b'{"id":77}'
    result = await enqueue_or_record_shopify_webhook(
        _ctx(
            db_session,
            _incoming_data(
                raw_body=raw_body,
                signature=_signed_webhook("webhook-secret", raw_body),
                shop_domain=shop_domain,
                webhook_id=f"wh_{integration_status.value}_{topic.replace('/', '_')}",
                topic=topic,
            ),
        )
    )

    intakes = await _fetch_intakes_for_integration(db_session, integration.client_id)

    assert result["outcome"] == expected_outcome
    assert len(intakes) == 1
    assert await _fetch_shopify_process_tasks(db_session, intakes[0].client_id) == []


@pytest.mark.integration
async def test_unknown_shop_does_not_enqueue_shopify_process_task(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    raw_body = b'{"id":55}'
    task_rows_before = (
        await db_session.execute(
            select(ExecutionTask.client_id).where(
                ExecutionTask.task_type == TaskType.SHOPIFY_PROCESS_WEBHOOK
            )
        )
    ).scalars().all()

    result = await enqueue_or_record_shopify_webhook(
        _ctx(
            db_session,
            _incoming_data(
                raw_body=raw_body,
                signature=_signed_webhook("webhook-secret", raw_body),
                shop_domain=_unique_shop_domain("unknown"),
                webhook_id="wh_unknown_shop",
            ),
        )
    )

    task_rows = (
        await db_session.execute(
            select(ExecutionTask.client_id).where(
                ExecutionTask.task_type == TaskType.SHOPIFY_PROCESS_WEBHOOK
            )
        )
    ).scalars().all()

    assert result["outcome"] == "unknown_shop"
    assert task_rows == task_rows_before


@pytest.mark.integration
async def test_missing_webhook_id_returns_bad_request_and_creates_no_rows(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("missing-webhook-id")
    workspace, user = await _seed_workspace_and_user(db_session)
    await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    raw_body = b'{"id":3}'
    with pytest.raises(InvalidShopifyWebhookRequest, match="X-Shopify-Webhook-Id is required"):
        await enqueue_or_record_shopify_webhook(
            _ctx(
                db_session,
                _incoming_data(
                    raw_body=raw_body,
                    signature=_signed_webhook("webhook-secret", raw_body),
                    shop_domain=shop_domain,
                    webhook_id="   ",
                ),
            )
        )

    assert await _count_events_for_shop_domain(db_session, shop_domain) == 0


@pytest.mark.integration
async def test_unsupported_topic_creates_ignored_intake_and_warning_event(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("unsupported-topic")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    raw_body = b'{"id":4}'
    result = await enqueue_or_record_shopify_webhook(
        _ctx(
            db_session,
                _incoming_data(
                    raw_body=raw_body,
                    signature=_signed_webhook("webhook-secret", raw_body),
                    shop_domain=shop_domain,
                    topic="customers/redact",
                    webhook_id="wh_unsupported",
                ),
            )
        )

    intakes = await _fetch_intakes_for_integration(db_session, integration.client_id)
    events = await _fetch_events_for_integration(db_session, integration.client_id)

    assert result["outcome"] == ShopifyWebhookIntakeStatusEnum.IGNORED.value
    assert intakes[0].status == ShopifyWebhookIntakeStatusEnum.IGNORED
    assert intakes[0].retryable is False
    assert events[0].severity == ShopifyIntegrationEventSeverityEnum.WARNING
    assert events[0].metadata_json["reason"] == "unsupported_topic"


@pytest.mark.integration
async def test_unknown_shop_domain_returns_success_without_db_rows(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)

    shop_domain = _unique_shop_domain("unknown-shop")
    webhook_id = "wh_unknown_shop"
    raw_body = b'{"id":5}'
    result = await enqueue_or_record_shopify_webhook(
        _ctx(
            db_session,
            _incoming_data(
                raw_body=raw_body,
                signature=_signed_webhook("webhook-secret", raw_body),
                shop_domain=shop_domain,
                webhook_id=webhook_id,
            ),
        )
    )

    assert result["outcome"] == "unknown_shop"
    assert await _count_intakes_for_webhook(db_session, webhook_id) == 0
    assert await _count_events_for_shop_domain(db_session, shop_domain) == 0


@pytest.mark.integration
@pytest.mark.parametrize("status", [ShopifyIntegrationStatusEnum.DISABLED, ShopifyIntegrationStatusEnum.UNINSTALLED])
async def test_inactive_shop_creates_ignored_non_retryable_intake_and_warning_event(
    db_session,
    monkeypatch,
    status: ShopifyIntegrationStatusEnum,
) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain(f"inactive-{status.value}")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=status,
    )
    await db_session.commit()

    raw_body = b'{"id":6}'
    result = await enqueue_or_record_shopify_webhook(
        _ctx(
            db_session,
                _incoming_data(
                    raw_body=raw_body,
                    signature=_signed_webhook("webhook-secret", raw_body),
                    shop_domain=shop_domain,
                    webhook_id=f"wh_inactive_{status.value}",
                ),
            )
        )

    intakes = await _fetch_intakes_for_integration(db_session, integration.client_id)
    events = await _fetch_events_for_integration(db_session, integration.client_id)

    assert result["outcome"] == ShopifyWebhookIntakeStatusEnum.IGNORED.value
    assert intakes[0].status == ShopifyWebhookIntakeStatusEnum.IGNORED
    assert intakes[0].retryable is False
    assert events[0].severity == ShopifyIntegrationEventSeverityEnum.WARNING
    assert events[0].metadata_json["reason"] == "inactive_shop_integration"
    assert events[0].metadata_json["integration_status"] == status.value


@pytest.mark.integration
async def test_duplicate_delivery_returns_success_without_second_intake_or_event(db_session, monkeypatch) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("duplicate")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    raw_body = b'{"id":7}'
    incoming = _incoming_data(
        raw_body=raw_body,
        signature=_signed_webhook("webhook-secret", raw_body),
        shop_domain=shop_domain,
        webhook_id="wh_duplicate",
    )

    first_result = await enqueue_or_record_shopify_webhook(_ctx(db_session, incoming))
    second_result = await enqueue_or_record_shopify_webhook(_ctx(db_session, incoming))

    assert first_result["outcome"] == ShopifyWebhookIntakeStatusEnum.RECEIVED.value
    assert second_result["outcome"] == "duplicate"
    assert len(await _fetch_intakes_for_integration(db_session, integration.client_id)) == 1
    assert len(await _fetch_events_for_integration(db_session, integration.client_id)) == 1


@pytest.mark.integration
async def test_non_json_payload_still_records_intake_without_logging_raw_body(db_session, monkeypatch, caplog) -> None:
    _configure_settings(monkeypatch)
    shop_domain = _unique_shop_domain("non-json")
    workspace, user = await _seed_workspace_and_user(db_session)
    integration = await _seed_integration(
        db_session,
        workspace_id=workspace.client_id,
        user_id=user.client_id,
        shop_domain=shop_domain,
        status=ShopifyIntegrationStatusEnum.ACTIVE,
    )
    await db_session.commit()

    raw_body = b"not-json"
    with caplog.at_level(logging.DEBUG, logger="beyo_manager"):
        result = await enqueue_or_record_shopify_webhook(
            _ctx(
                db_session,
                _incoming_data(
                    raw_body=raw_body,
                    signature=_signed_webhook("webhook-secret", raw_body),
                    shop_domain=shop_domain,
                    webhook_id="wh_non_json",
                ),
            )
        )

    intakes = await _fetch_intakes_for_integration(db_session, integration.client_id)

    assert result["outcome"] == ShopifyWebhookIntakeStatusEnum.RECEIVED.value
    assert intakes[0].raw_payload is None
    assert raw_body.decode() not in caplog.text
