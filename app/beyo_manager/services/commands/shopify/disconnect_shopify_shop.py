from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifyRemoveWebhooksForShopPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyIntegrationStatusEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def disconnect_shopify_shop(ctx: ServiceContext) -> dict:
    shop_integration_id = str(ctx.incoming_data.get("shop_integration_id") or "").strip()
    if not shop_integration_id:
        raise NotFound("Shopify shop integration not found.")

    async with maybe_begin(ctx.session):
        integration = await ctx.session.get(ShopifyShopIntegration, shop_integration_id)
        if integration is None or integration.workspace_id != ctx.workspace_id or integration.is_deleted:
            raise NotFound("Shopify shop integration not found.")

        previous_status = str(integration.status.value)
        integration.status = ShopifyIntegrationStatusEnum.DISABLED
        integration.uninstalled_at = datetime.now(timezone.utc)
        integration.access_token_encrypted = None

        event = await create_shopify_integration_event(
            ctx.session,
            workspace_id=ctx.workspace_id,
            shop_integration_id=integration.client_id,
            event_type=ShopifyIntegrationEventTypeEnum.DISCONNECT,
            severity=ShopifyIntegrationEventSeverityEnum.INFO,
            message="Shopify shop disconnected.",
            metadata_json={
                "action": "disconnect",
                "shop_domain": integration.shop_domain,
                "previous_status": previous_status,
                "new_status": "disabled",
                "remove_webhooks_task_id": None,
            },
            created_by_id=ctx.user_id or integration.updated_by_id or integration.created_by_id,
        )

        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP,
            payload=asdict(ShopifyRemoveWebhooksForShopPayload(shop_integration_id=integration.client_id)),
            event_client_id=event.client_id,
        )

        event.metadata_json = {
            **(event.metadata_json or {}),
            "remove_webhooks_task_id": task.client_id,
        }

    return {
        "shop_integration_id": integration.client_id,
        "shop_domain": integration.shop_domain,
        "status": integration.status.value,
        "uninstalled_at": integration.uninstalled_at.isoformat() if integration.uninstalled_at else None,
        "remove_webhooks_task_id": task.client_id,
    }