from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
)
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event

WEBHOOK_SYNC_PENDING_MESSAGE = (
    "Webhook sync pending; will be processed once webhook subscription sync "
    "(phase 3) and the dedicated worker (phase 5) exist."
)


async def record_webhook_sync_pending(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
    shop_integration_id: str,
    shop_domain: str,
) -> None:
    await create_shopify_integration_event(
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
