from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyProductSyncOriginEnum
from beyo_manager.domain.shopify.preorder_policy import (
    PREORDER_PRODUCT_STATUS,
    PREORDER_QUANTITY_METAFIELD_KEY,
    build_preorder_quantity_metafield,
)
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.shopify.process_shopify_products import (
    enqueue_shopify_product_sync,
)
from beyo_manager.services.commands.shopify.requests.process_shopify_products_request import (
    parse_process_shopify_products_request,
)
from beyo_manager.services.commands.tasks.requests import ShopifyPreorderSectionInput
from beyo_manager.services.context import ServiceContext


async def _create_preorder_sync_item_in_session(
    ctx: ServiceContext,
    *,
    task_id: str,
    preorder: ShopifyPreorderSectionInput,
    item_article_number: str | None = None,
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
    metafields = {
        **(product.pop("metafields", None) or {}),
        **preorder.metafields,
    }
    metafields[PREORDER_QUANTITY_METAFIELD_KEY] = build_preorder_quantity_metafield(
        entry.quantity for entry in preorder.inventory
    )
    product_sync_request_data = {
        "items": [
            {
                "client_id": task_id,
                "target_shop_integration_ids": [preorder.shop_integration_id],
                "status": PREORDER_PRODUCT_STATUS,
                **product,
                **(
                    {"article_number": item_article_number}
                    if item_article_number is not None
                    else {}
                ),
                "metafields": metafields,
                "inventory_quantities": [
                    {
                        "shop_integration_id": preorder.shop_integration_id,
                        "location_id": entry.location_id,
                        "quantity": entry.quantity,
                    }
                    for entry in preorder.inventory
                ],
            }
        ]
    }
    product_sync_ctx = ServiceContext(
        incoming_data=product_sync_request_data,
        identity=ctx.identity,
        session=ctx.session,
    )
    queued = await enqueue_shopify_product_sync(
        product_sync_ctx,
        request=parse_process_shopify_products_request(product_sync_request_data),
        sync_origin=ShopifyProductSyncOriginEnum.PREORDER_TASK,
        source_entity_type="task",
        source_entity_id=task_id,
    )
    preorder_operation_id = queued["sync_item_client_ids"][0]

    return {
        "queued": True,
        "preorder_operation_id": preorder_operation_id,
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
