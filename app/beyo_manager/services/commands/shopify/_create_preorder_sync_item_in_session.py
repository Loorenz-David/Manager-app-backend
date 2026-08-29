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
    item_sku: str | None = None,
) -> dict:
    product = preorder.product.model_dump(exclude_none=True)
    # The Shopify product's sku defaults to the task item's own sku — which may itself have
    # just been auto-assigned from a SKU template — so the local item and the Shopify variant
    # share one sku unless the caller explicitly sets a different `product.sku`.
    if not product.get("sku") and item_sku:
        product["sku"] = item_sku
    # A seller who didn't type a product title still needs *something* Shopify will accept —
    # title is required on the Shopify side regardless of sku. Falls back to the resolved sku
    # (above), not the raw item_sku, so an explicit `product.sku` override is honoured here too.
    # A pre-existing item that was found (not created) may have no sku at all — the sku backfill
    # deliberately never assigns one to a pre-existing item — so fall back further to the item's
    # article_number. If neither resolves, title stays absent and the request-layer validation on
    # ProcessShopifyProductItemRequest.title raises a clear error instead of a downstream one.
    if not product.get("title"):
        fallback_title = product.get("sku") or item_article_number
        if fallback_title:
            product["title"] = fallback_title
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
    # `custom.quantity` is independent of the inventory the seller selected — the merchant's live
    # products carry a `custom.quantity` that legitimately differs from available stock (e.g. a
    # pack size or a display quantity), so the caller's value wins when supplied. When the caller
    # doesn't set it, it defaults to the total inventory this pre-order provisions, summed across
    # every selected location.
    metafields = {
        **(product.pop("metafields", None) or {}),
        **preorder.metafields,
    }
    if PREORDER_QUANTITY_METAFIELD_KEY not in metafields:
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
