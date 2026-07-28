from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.shopify.enums import (
    ShopifyIntegrationEventTypeEnum,
    ShopifyInventoryModeEnum,
)
from beyo_manager.domain.shopify.preorder_policy import (
    PREORDER_PRODUCT_STATUS,
    PREORDER_QUANTITY_METAFIELD_KEY,
    build_preorder_quantity_metafield,
)
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_integration_event import ShopifyIntegrationEvent
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.services.commands.shopify.process_shopify_products import (
    process_shopify_products,
)
from beyo_manager.services.commands.tasks.requests import ShopifyPreorderSectionInput
from beyo_manager.services.context import ServiceContext


async def _create_preorder_sync_item_in_session(
    ctx: ServiceContext,
    *,
    task_id: str,
    preorder: ShopifyPreorderSectionInput,
    item_category_id: str | None = None,
) -> dict:
    product = preorder.product.model_dump(exclude_none=True)
    # Shopify's productType defaults to the task item's category name, so a seller who has already
    # categorised the item does not have to restate it. An explicit `product_category` on the
    # pre-order section wins — unlike the quantity metafield, this is a product attribute a seller
    # may legitimately want to differ from the internal category.
    if not product.get("product_category") and item_category_id:
        category_name = (
            await ctx.session.execute(
                select(ItemCategory.name).where(
                    ItemCategory.client_id == item_category_id,
                    ItemCategory.workspace_id == ctx.workspace_id,
                    ItemCategory.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if category_name:
            product["product_category"] = category_name
    # `custom.quantity` is derived from the inventory the seller selected, summed across every
    # location, so one entered number drives both the till stock and the product's quantity field.
    # Authoritative: anything the caller sent under this key is replaced, keeping a single source
    # of truth rather than two numbers that can silently diverge.
    metafields = {**(product.pop("metafields", None) or {})}
    metafields[PREORDER_QUANTITY_METAFIELD_KEY] = build_preorder_quantity_metafield(
        entry.quantity for entry in preorder.inventory
    )
    product_sync_ctx = ServiceContext(
        incoming_data={
            "items": [
                {
                    "client_id": task_id,
                    "target_shop_integration_ids": [preorder.shop_integration_id],
                    "status": PREORDER_PRODUCT_STATUS,
                    **product,
                    "metafields": metafields,
                }
            ]
        },
        identity=ctx.identity,
        session=ctx.session,
    )
    queued = await process_shopify_products(product_sync_ctx)
    sync_item = (
        await ctx.session.execute(
            select(ShopifyProductSyncItem).where(
                ShopifyProductSyncItem.client_id
                == queued["sync_item_client_ids"][0],
                ShopifyProductSyncItem.workspace_id == ctx.workspace_id,
            )
        )
    ).scalar_one()
    sync_item.inventory_mode = ShopifyInventoryModeEnum.SET
    # Ordinary product sync and pre-orders both carry absolute per-location targets
    # under `quantities`, consumed by inventorySetQuantities.
    sync_item.normalized_payload_json = {
        **sync_item.normalized_payload_json,
        "inventory": {
            "quantities": [
                {
                    "location_id": entry.location_id,
                    "quantity": entry.quantity,
                }
                for entry in preorder.inventory
            ]
        },
    }

    event = await ctx.session.get(
        ShopifyIntegrationEvent, queued["event_client_ids"][0]
    )
    event.event_type = ShopifyIntegrationEventTypeEnum.PREORDER
    event.message = "Shopify pre-order product provisioning enqueued."
    event.metadata_json = {
        **(event.metadata_json or {}),
        "task_id": task_id,
        "preorder_operation_id": sync_item.client_id,
    }

    return {
        "queued": True,
        "preorder_operation_id": sync_item.client_id,
        "task_id": task_id,
        "shop_integration_id": preorder.shop_integration_id,
        "shopify_task_id": queued["task_id"],
        "inventory": [
            {
                "location_id": entry.location_id,
                "quantity": entry.quantity,
            }
            for entry in preorder.inventory
        ],
    }
