from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
)
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent


async def create_shopify_integration_event(
    session: AsyncSession,
    *,
    workspace_id: str,
    shop_integration_id: str,
    event_type: ShopifyIntegrationEventTypeEnum,
    severity: ShopifyIntegrationEventSeverityEnum,
    message: str,
    metadata_json: dict | None,
    created_by_id: str | None,
) -> ShopifyIntegrationEvent:
    event = ShopifyIntegrationEvent(
        workspace_id=workspace_id,
        shop_integration_id=shop_integration_id,
        event_type=event_type,
        severity=severity,
        message=message,
        metadata_json=metadata_json,
        created_by_id=created_by_id,
    )
    session.add(event)
    await session.flush()
    return event
