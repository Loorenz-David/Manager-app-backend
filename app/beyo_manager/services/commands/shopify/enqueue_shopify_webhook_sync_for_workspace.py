from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifySyncWebhooksForShopPayload
from beyo_manager.domain.shopify.enums import ShopifyIntegrationEventSeverityEnum, ShopifyIntegrationEventTypeEnum
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop import _SYNCABLE_INTEGRATION_STATUSES
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def enqueue_shopify_webhook_sync_for_workspace(ctx: ServiceContext) -> dict:
    result = await ctx.session.execute(
        select(ShopifyShopIntegration)
        .where(
            ShopifyShopIntegration.workspace_id == ctx.workspace_id,
            ShopifyShopIntegration.is_deleted.is_(False),
            ShopifyShopIntegration.status.in_(_SYNCABLE_INTEGRATION_STATUSES),
        )
        .order_by(ShopifyShopIntegration.created_at.desc())
    )
    integrations = result.scalars().all()

    enqueued_tasks: list[dict] = []
    async with maybe_begin(ctx.session):
        for integration in integrations:
            event = await create_shopify_integration_event(
                ctx.session,
                workspace_id=ctx.workspace_id,
                shop_integration_id=integration.client_id,
                event_type=ShopifyIntegrationEventTypeEnum.WEBHOOK_SYNC,
                severity=ShopifyIntegrationEventSeverityEnum.INFO,
                message="Manual Shopify webhook sync requested for workspace shop.",
                metadata_json={
                    "action": "manual_sync",
                    "shop_domain": integration.shop_domain,
                    "shop_integration_id": integration.client_id,
                },
                created_by_id=ctx.user_id or integration.updated_by_id or integration.created_by_id,
            )
            task = await create_instant_task(
                session=ctx.session,
                task_type=TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
                payload=asdict(ShopifySyncWebhooksForShopPayload(shop_integration_id=integration.client_id)),
                event_client_id=event.client_id,
            )
            event.metadata_json = {
                **(event.metadata_json or {}),
                "sync_webhooks_task_id": task.client_id,
            }
            enqueued_tasks.append(
                {
                    "shop_integration_id": integration.client_id,
                    "shop_domain": integration.shop_domain,
                    "sync_webhooks_task_id": task.client_id,
                }
            )

    return {
        "enqueued_count": len(enqueued_tasks),
        "shops": enqueued_tasks,
    }