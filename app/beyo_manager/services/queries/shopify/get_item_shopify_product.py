"""Read the Shopify product linked to a ManagerBeyo item, live, per active shop.

Used by the worker product form: when a product already exists the form is
prefilled from Shopify instead of from a browser-stored draft.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.product_sync_identity import select_exact_variant_match
from beyo_manager.errors.external_service import (
    ShopifyGraphQLError,
    ShopifyProductLookupAmbiguousError,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.outbound import require_outbound_integrations
from beyo_manager.services.infra.shopify.product_sync_client import (
    find_product_variant_by_identity,
    get_shopify_product_snapshot,
)
from beyo_manager.services.queries.shopify._resolve_item_shopify_product import (
    find_latest_item_sync_row,
)

logger = logging.getLogger(__name__)


async def get_item_shopify_product(ctx: ServiceContext) -> dict:
    # Calls each shop with its stored access token.
    require_outbound_integrations()
    item_client_id = str(ctx.incoming_data.get("item_client_id") or "").strip()
    if not item_client_id:
        raise ValidationError("item_client_id is required.")

    item = (
        await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == item_client_id,
                Item.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise NotFound("Item not found.")

    shops = (
        await ctx.session.execute(
            select(ShopifyShopIntegration)
            .where(
                ShopifyShopIntegration.workspace_id == ctx.workspace_id,
                ShopifyShopIntegration.is_deleted.is_(False),
                ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
            )
            .order_by(ShopifyShopIntegration.created_at.desc())
        )
    ).scalars().all()

    results = []
    for shop in shops:
        results.append(await _resolve_shop_entry(ctx, item=item, shop=shop))
    return {"item_client_id": item.client_id, "shops": results}


async def _resolve_shop_entry(
    ctx: ServiceContext,
    *,
    item: Item,
    shop: ShopifyShopIntegration,
) -> dict:
    latest_row = await find_latest_item_sync_row(
        ctx.session,
        workspace_id=ctx.workspace_id,
        item_client_id=item.client_id,
        shop_integration_id=shop.client_id,
    )
    entry: dict = {
        "shop_integration_id": shop.client_id,
        "shop_domain": shop.shop_domain,
        "sync": _serialize_sync_row(latest_row),
        "product": None,
        "fetch_error": None,
    }
    if not (shop.access_token_encrypted or "").strip():
        entry["fetch_error"] = "Shopify shop has no access token."
        return entry

    try:
        entry["product"] = await _fetch_item_product_snapshot(ctx, item=item, shop=shop)
    except ShopifyProductLookupAmbiguousError:
        entry["fetch_error"] = "More than one Shopify product matches this item's barcode."
    except ShopifyGraphQLError as exc:
        logger.warning(
            "shopify_item_product | fetch_failed | shop_integration_id=%s item_id=%s error_code=%s",
            shop.client_id,
            item.client_id,
            getattr(exc, "error_code", None),
        )
        entry["fetch_error"] = "Could not read the product from Shopify."
    return entry


async def _fetch_item_product_snapshot(
    ctx: ServiceContext,
    *,
    item: Item,
    shop: ShopifyShopIntegration,
) -> dict | None:
    """Same resolution order as the sync worker: known product id, then barcode."""
    known_row = await find_latest_item_sync_row(
        ctx.session,
        workspace_id=ctx.workspace_id,
        item_client_id=item.client_id,
        shop_integration_id=shop.client_id,
        with_product_id=True,
    )
    if known_row is not None and known_row.shopify_product_id:
        snapshot = await get_shopify_product_snapshot(
            shop_domain=shop.shop_domain,
            access_token_encrypted=shop.access_token_encrypted or "",
            shopify_product_id=known_row.shopify_product_id,
        )
        if snapshot is not None:
            return snapshot

    barcode = (item.article_number or "").strip()
    if not barcode:
        return None
    nodes = await find_product_variant_by_identity(
        shop_domain=shop.shop_domain,
        access_token_encrypted=shop.access_token_encrypted or "",
        sku=None,
        barcode=barcode,
    )
    match = select_exact_variant_match(nodes, identity_type="barcode", identity_value=barcode)
    if not match.found or not match.shopify_product_id:
        return None
    return await get_shopify_product_snapshot(
        shop_domain=shop.shop_domain,
        access_token_encrypted=shop.access_token_encrypted or "",
        shopify_product_id=match.shopify_product_id,
    )


def _serialize_sync_row(row: ShopifyProductSyncItem | None) -> dict | None:
    if row is None:
        return None
    return {
        "sync_item_client_id": row.client_id,
        "status": row.status.value if hasattr(row.status, "value") else str(row.status),
        "error_code": row.error_code,
        "error_message": row.error_message,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
