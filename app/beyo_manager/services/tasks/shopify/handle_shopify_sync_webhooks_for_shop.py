from __future__ import annotations

from beyo_manager.domain.execution.payloads.shopify import ShopifySyncWebhooksForShopPayload
from beyo_manager.models.database import get_db_session
from beyo_manager.services.commands.shopify.sync_shopify_webhook_subscriptions_for_shop import (
    sync_shopify_webhook_subscriptions_for_shop,
)
from beyo_manager.services.context import ServiceContext


async def handle_shopify_sync_webhooks_for_shop(raw: dict, task_client_id: str) -> None:
    payload = ShopifySyncWebhooksForShopPayload(**raw)

    async for session in get_db_session():
        ctx = ServiceContext(
            identity={},
            incoming_data={"shop_integration_id": payload.shop_integration_id},
            session=session,
        )
        await sync_shopify_webhook_subscriptions_for_shop(ctx)
        return
