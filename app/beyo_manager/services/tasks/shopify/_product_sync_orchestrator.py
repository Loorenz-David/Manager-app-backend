from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import (
    ShopifyProductSyncItemStatusEnum,
    ShopifyProductSyncOperationEnum,
)
from beyo_manager.domain.shopify.product_sync_identity import select_exact_variant_match
from beyo_manager.errors.external_service import ShopifyGraphQLError, ShopifyProductLookupAmbiguousError
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.infra.shopify.product_sync_client import (
    create_shopify_product,
    find_product_variant_by_identity,
    set_shopify_product_metafields,
    update_shopify_product,
)


async def sync_one_product_sync_item(
    session: AsyncSession,
    *,
    sync_item: ShopifyProductSyncItem,
    shop: ShopifyShopIntegration,
) -> None:
    payload = sync_item.normalized_payload_json or {}
    variant_payload = payload.get("variant") or {}
    inventory_item = variant_payload.get("inventoryItem") or {}
    sku = _clean_str(inventory_item.get("sku"))
    barcode = _clean_str(variant_payload.get("barcode"))

    sync_item.status = ShopifyProductSyncItemStatusEnum.PROCESSING
    sync_item.error_code = None
    sync_item.error_message = None
    await session.commit()

    try:
        match = None
        if sku is not None:
            sku_nodes = await find_product_variant_by_identity(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                sku=sku,
                barcode=None,
            )
            match = select_exact_variant_match(
                sku_nodes,
                identity_type="sku",
                identity_value=sku,
            )

        if match is not None and match.found and barcode is not None:
            # sku already resolved a product — still verify the item's own barcode
            # doesn't belong to a *different* existing product before writing to it,
            # since Shopify does not enforce barcode uniqueness and would otherwise
            # silently move another product's barcode onto this one.
            barcode_nodes = await find_product_variant_by_identity(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                sku=None,
                barcode=barcode,
            )
            barcode_match = select_exact_variant_match(
                barcode_nodes,
                identity_type="barcode",
                identity_value=barcode,
            )
            if barcode_match.found and barcode_match.shopify_product_id != match.shopify_product_id:
                raise ShopifyProductLookupAmbiguousError(
                    "sku and barcode identities resolved to different existing Shopify products.",
                    error_code="conflicting_identity_match",
                )
        elif (match is None or not match.found) and barcode is not None:
            barcode_nodes = await find_product_variant_by_identity(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                sku=None,
                barcode=barcode,
            )
            match = select_exact_variant_match(
                barcode_nodes,
                identity_type="barcode",
                identity_value=barcode,
            )

        if match is not None and match.found:
            sync_item.requested_operation = ShopifyProductSyncOperationEnum.UPDATE
            result = await update_shopify_product(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                shopify_product_id=match.shopify_product_id or "",
                shopify_variant_id=match.shopify_variant_id or "",
                normalized_payload=payload,
            )
        else:
            sync_item.requested_operation = ShopifyProductSyncOperationEnum.CREATE
            result = await create_shopify_product(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                normalized_payload=payload,
            )

        # Persist the Shopify IDs as soon as create/update succeeds — before the
        # metafields call — so a metafields-only failure still records that the
        # product was created/updated, instead of leaving a FAILED row with no
        # shopify_product_id and risking a duplicate create on a future retry.
        sync_item.shopify_product_id = result["shopify_product_id"]
        sync_item.shopify_variant_id = result["shopify_variant_id"]

        if payload.get("metafields"):
            await set_shopify_product_metafields(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                shopify_product_id=result["shopify_product_id"],
                metafields=payload["metafields"],
            )

        sync_item.status = ShopifyProductSyncItemStatusEnum.SUCCEEDED
        sync_item.error_code = None
        sync_item.error_message = None
        await session.commit()
    except (ShopifyGraphQLError, ShopifyProductLookupAmbiguousError) as exc:
        sync_item.status = ShopifyProductSyncItemStatusEnum.FAILED
        sync_item.error_code = exc.error_code
        sync_item.error_message = str(exc)[:1024]
        await session.commit()


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
