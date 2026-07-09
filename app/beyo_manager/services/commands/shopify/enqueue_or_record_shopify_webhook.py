from __future__ import annotations

import json
import logging
from dataclasses import asdict

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessWebhookPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
    ShopifyWebhookIntakeStatusEnum,
)
from beyo_manager.domain.shopify.shop_domains import normalize_shop_domain
from beyo_manager.domain.shopify.webhook_registry import get_webhook_definition
from beyo_manager.errors.base import DomainError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.shopify.hmac_verifier import is_valid_shopify_webhook_hmac

logger = logging.getLogger(__name__)

_INACTIVE_INTEGRATION_STATUSES = {
    ShopifyIntegrationStatusEnum.DISABLED,
    ShopifyIntegrationStatusEnum.UNINSTALLED,
}


class InvalidShopifyWebhookRequest(DomainError):
    http_status = 400


class EnqueueOrRecordShopifyWebhookRequest(BaseModel):
    raw_body: bytes
    hmac_header: str | None = None
    topic: str | None = None
    shop_domain: str | None = None
    webhook_id: str | None = None

    @field_validator("raw_body")
    @classmethod
    def _raw_body_is_required(cls, value: bytes) -> bytes:
        if value is None:
            raise ValueError("raw_body is required.")
        return value


def parse_enqueue_or_record_shopify_webhook_request(data: dict) -> EnqueueOrRecordShopifyWebhookRequest:
    try:
        return EnqueueOrRecordShopifyWebhookRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise InvalidShopifyWebhookRequest(f"{field}: {first_error['msg']}") from exc


def _parse_payload_for_storage(raw_body: bytes) -> dict | list | None:
    if not raw_body:
        return None
    try:
        parsed = json.loads(raw_body)
    except (TypeError, ValueError):
        return None
    if isinstance(parsed, (dict, list)):
        return parsed
    return {"value": parsed}


def _safe_log_debug(message: str, **kwargs) -> None:
    if settings.shopify_integration_debug_logs:
        logger.debug(message, extra=kwargs)


async def enqueue_or_record_shopify_webhook(ctx: ServiceContext) -> dict:
    request = parse_enqueue_or_record_shopify_webhook_request(ctx.incoming_data)
    if not is_valid_shopify_webhook_hmac(request.raw_body, request.hmac_header):
        raise InvalidShopifyWebhookRequest("Invalid Shopify webhook signature.")

    webhook_id = (request.webhook_id or "").strip()
    if not webhook_id:
        raise InvalidShopifyWebhookRequest("X-Shopify-Webhook-Id is required.")

    try:
        normalized_shop_domain = normalize_shop_domain(request.shop_domain or "")
    except ValidationError as exc:
        raise InvalidShopifyWebhookRequest(str(exc)) from exc

    topic = (request.topic or "").strip()
    raw_payload = _parse_payload_for_storage(request.raw_body)

    async with maybe_begin(ctx.session):
        integration = (
            await ctx.session.execute(
                select(ShopifyShopIntegration)
                .where(
                    ShopifyShopIntegration.shop_domain == normalized_shop_domain,
                    ShopifyShopIntegration.is_deleted.is_(False),
                )
                .order_by(ShopifyShopIntegration.created_at.desc())
            )
        ).scalars().first()

        if integration is None:
            _safe_log_debug(
                "Shopify webhook ignored because no shop integration exists.",
                shop_domain=normalized_shop_domain,
                topic=topic,
                webhook_id=webhook_id,
                outcome="unknown_shop",
            )
            return {
                "outcome": "unknown_shop",
                "shop_domain": normalized_shop_domain,
                "topic": topic,
                "webhook_id": webhook_id,
            }

        dedupe_key = f"{integration.client_id}:{topic}:{webhook_id}"
        existing_intake_id = await ctx.session.scalar(
            select(ShopifyWebhookIntake.client_id).where(ShopifyWebhookIntake.dedupe_key == dedupe_key)
        )
        if existing_intake_id is not None:
            _safe_log_debug(
                "Shopify webhook duplicate delivery ignored.",
                shop_domain=normalized_shop_domain,
                topic=topic,
                webhook_id=webhook_id,
                outcome="duplicate",
            )
            return {
                "outcome": "duplicate",
                "shop_domain": normalized_shop_domain,
                "topic": topic,
                "webhook_id": webhook_id,
            }

        event_severity = ShopifyIntegrationEventSeverityEnum.INFO
        intake_status = ShopifyWebhookIntakeStatusEnum.RECEIVED
        retryable = True
        reason: str | None = None
        message = "Shopify webhook received and recorded for later processing."

        if integration.status in _INACTIVE_INTEGRATION_STATUSES:
            intake_status = ShopifyWebhookIntakeStatusEnum.IGNORED
            retryable = False
            event_severity = ShopifyIntegrationEventSeverityEnum.WARNING
            reason = "inactive_shop_integration"
            message = "Ignored Shopify webhook for inactive shop integration."
        elif get_webhook_definition(topic) is None:
            intake_status = ShopifyWebhookIntakeStatusEnum.IGNORED
            retryable = False
            event_severity = ShopifyIntegrationEventSeverityEnum.WARNING
            reason = "unsupported_topic"
            message = "Ignored unsupported Shopify webhook topic."

        intake_values = {
            "client_id": generate_id(ShopifyWebhookIntake.CLIENT_ID_PREFIX),
            "workspace_id": integration.workspace_id,
            "shop_integration_id": integration.client_id,
            "shop_domain": normalized_shop_domain,
            "topic": topic,
            "webhook_id": webhook_id,
            "dedupe_key": dedupe_key,
            "raw_payload": raw_payload,
            "status": intake_status,
            "retryable": retryable,
        }
        insert_result = await ctx.session.execute(
            insert(ShopifyWebhookIntake)
            .values(**intake_values)
            .on_conflict_do_nothing(index_elements=["dedupe_key"])
            .returning(ShopifyWebhookIntake.client_id)
        )
        intake_id = insert_result.scalar_one_or_none()
        if intake_id is None:
            _safe_log_debug(
                "Shopify webhook duplicate delivery ignored after dedupe race.",
                shop_domain=normalized_shop_domain,
                topic=topic,
                webhook_id=webhook_id,
                outcome="duplicate",
            )
            return {
                "outcome": "duplicate",
                "shop_domain": normalized_shop_domain,
                "topic": topic,
                "webhook_id": webhook_id,
            }

        metadata_json: dict[str, object] = {
            "shop_domain": normalized_shop_domain,
            "topic": topic,
            "webhook_id": webhook_id,
            "intake_status": intake_status.value,
        }
        if reason is not None:
            metadata_json["reason"] = reason
        if reason == "inactive_shop_integration":
            metadata_json["integration_status"] = integration.status.value
        if intake_status == ShopifyWebhookIntakeStatusEnum.RECEIVED:
            metadata_json["processing_status"] = "pending"

        event = await create_shopify_integration_event(
            ctx.session,
            workspace_id=integration.workspace_id,
            shop_integration_id=integration.client_id,
            event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_RECEIVED,
            severity=event_severity,
            message=message,
            metadata_json=metadata_json,
            created_by_id=None,
        )
        if intake_status == ShopifyWebhookIntakeStatusEnum.RECEIVED:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.SHOPIFY_PROCESS_WEBHOOK,
                payload=asdict(
                    ShopifyProcessWebhookPayload(webhook_intake_id=intake_id)
                ),
                event_client_id=event.client_id,
            )

    return {
        "outcome": intake_status.value,
        "shop_domain": normalized_shop_domain,
        "topic": topic,
        "webhook_id": webhook_id,
    }
