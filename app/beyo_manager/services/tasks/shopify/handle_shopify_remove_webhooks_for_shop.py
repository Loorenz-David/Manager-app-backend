from __future__ import annotations

from beyo_manager.domain.execution.payloads.shopify import ShopifyRemoveWebhooksForShopPayload
from beyo_manager.models.database import get_db_session
from beyo_manager.services.commands.shopify.remove_shopify_webhooks_for_shop import (
    remove_shopify_webhooks_for_shop,
)
from beyo_manager.services.context import ServiceContext


async def handle_shopify_remove_webhooks_for_shop(raw: dict, task_client_id: str) -> None:
    payload = ShopifyRemoveWebhooksForShopPayload(**raw)

    async for session in get_db_session():
        ctx = ServiceContext(
            identity={},
            incoming_data={"shop_integration_id": payload.shop_integration_id},
            session=session,
        )
        await remove_shopify_webhooks_for_shop(ctx)
        return
