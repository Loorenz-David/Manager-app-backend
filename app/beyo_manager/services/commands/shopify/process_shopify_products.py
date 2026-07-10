from __future__ import annotations

from dataclasses import asdict

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.shopify import ShopifyProcessProductsPayload
from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventSeverityEnum,
    ShopifyIntegrationEventTypeEnum,
    ShopifyProductSyncItemStatusEnum,
)
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.services.commands.shopify._events import create_shopify_integration_event
from beyo_manager.services.commands.shopify._product_sync_normalizer import resolve_and_normalize_sync_targets
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
    parse_process_shopify_products_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task


async def process_shopify_products(ctx: ServiceContext) -> dict:
    request = parse_process_shopify_products_request(ctx.incoming_data)

    async with ctx.session.begin():
        targets = await resolve_and_normalize_sync_targets(
            ctx.session,
            workspace_id=ctx.workspace_id,
            request=request,
        )

        sync_items = [
            ShopifyProductSyncItem(
                workspace_id=ctx.workspace_id,
                shop_integration_id=shop.client_id,
                frontend_client_id=item.client_id,
                status=ShopifyProductSyncItemStatusEnum.PENDING,
                normalized_payload_json=normalized_payload,
                created_by_id=ctx.user_id,
            )
            for shop, item, normalized_payload in targets
        ]
        ctx.session.add_all(sync_items)
        await ctx.session.flush()

        distinct_shops: dict[str, object] = {}
        for shop, _item, _payload in targets:
            distinct_shops.setdefault(shop.client_id, shop)

        events = []
        for shop in distinct_shops.values():
            events.append(
                await create_shopify_integration_event(
                    ctx.session,
                    workspace_id=ctx.workspace_id,
                    shop_integration_id=shop.client_id,
                    event_type=ShopifyIntegrationEventTypeEnum.PRODUCT_SYNC,
                    severity=ShopifyIntegrationEventSeverityEnum.INFO,
                    message=f"Product sync batch enqueued for {len(sync_items)} (item, shop) operations.",
                    metadata_json={
                        "item_count": len(request.items),
                        "target_count": len(sync_items),
                    },
                    created_by_id=ctx.user_id,
                )
            )

        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.SHOPIFY_PROCESS_PRODUCTS,
            payload=asdict(
                ShopifyProcessProductsPayload(
                    workspace_id=ctx.workspace_id,
                    requested_by_user_id=ctx.user_id,
                    sync_item_client_ids=[row.client_id for row in sync_items],
                )
            ),
            event_client_id=events[0].client_id if events else None,
        )

        for event in events:
            event.metadata_json = {
                **(event.metadata_json or {}),
                "shopify_process_products_task_id": task.client_id,
            }

    return {
        "queued": True,
        "task_id": task.client_id,
        "sync_item_client_ids": [row.client_id for row in sync_items],
        "target_count": len(sync_items),
    }
