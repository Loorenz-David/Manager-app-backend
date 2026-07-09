from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifySyncWebhooksForShopPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
)
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.infra.execution.task_factory import create_instant_task

WEBHOOK_SYNC_PENDING_MESSAGE = (
    "Webhook sync pending and enqueued for dedicated Shopify worker processing."
)


async def record_webhook_sync_pending(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
    shop_integration_id: str,
    shop_domain: str,
) -> None:
    event = await create_shopify_integration_event(
        session,
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
        severity=ShopifyIntegrationEventSeverityEnum.INFO,
        message=WEBHOOK_SYNC_PENDING_MESSAGE,
        metadata_json={
            "shop_domain": shop_domain,
            "sync_status": "pending",
        },
        created_by_id=user_id,
    )
    await create_instant_task(
        session=session,
        task_type=TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
        payload=asdict(
            ShopifySyncWebhooksForShopPayload(shop_integration_id=shop_integration_id)
        ),
        event_client_id=event.client_id,
    )
