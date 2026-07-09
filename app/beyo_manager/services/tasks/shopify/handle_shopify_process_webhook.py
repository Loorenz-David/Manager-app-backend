from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessWebhookPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyWebhookIntakeStatusEnum,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.shopify.shopify_webhook_intake import ShopifyWebhookIntake
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event

logger = logging.getLogger(__name__)

_NON_PROCESSABLE_STATUSES = {
    ShopifyWebhookIntakeStatusEnum.PROCESSING,
    ShopifyWebhookIntakeStatusEnum.PROCESSED,
    ShopifyWebhookIntakeStatusEnum.FAILED,
    ShopifyWebhookIntakeStatusEnum.IGNORED,
}


async def handle_shopify_process_webhook(raw: dict, task_client_id: str) -> None:
    payload = ShopifyProcessWebhookPayload(**raw)

    async for session in get_db_session():
        async with session.begin():
            intake = (
                await session.execute(
                    select(ShopifyWebhookIntake)
                    .where(ShopifyWebhookIntake.client_id == payload.webhook_intake_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()

            if intake is None:
                logger.warning(
                    "shopify_process_webhook | intake_not_found | task_id=%s intake_id=%s",
                    task_client_id,
                    payload.webhook_intake_id,
                )
                return

            if intake.status in _NON_PROCESSABLE_STATUSES:
                logger.info(
                    "shopify_process_webhook | skipped | task_id=%s intake_id=%s status=%s",
                    task_client_id,
                    intake.client_id,
                    intake.status.value,
                )
                return

            now = datetime.now(timezone.utc)
            intake.status = ShopifyWebhookIntakeStatusEnum.PROCESSING
            intake.processing_started_at = now
            intake.attempts += 1
            await session.flush()

            intake.status = ShopifyWebhookIntakeStatusEnum.PROCESSED
            intake.processed_at = now
            intake.last_error = None
            await create_shopify_integration_event(
                session,
                workspace_id=intake.workspace_id,
                shop_integration_id=intake.shop_integration_id,
                event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_PROCESSED,
                severity=ShopifyIntegrationEventSeverityEnum.INFO,
                message="Shopify webhook marked processed by Shopify worker.",
                metadata_json={
                    "shop_domain": intake.shop_domain,
                    "topic": intake.topic,
                    "webhook_id": intake.webhook_id,
                    "webhook_intake_id": intake.client_id,
                    "processing_mode": "no_business_processor_yet",
                },
                created_by_id=None,
            )

            logger.info(
                "shopify_process_webhook | completed | task_id=%s intake_id=%s shop_domain=%s topic=%s mode=no_business_processor_yet",
                task_client_id,
                intake.client_id,
                intake.shop_domain,
                intake.topic,
            )
        return
