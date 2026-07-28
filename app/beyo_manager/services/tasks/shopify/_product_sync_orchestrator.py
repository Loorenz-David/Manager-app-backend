from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.shopify.enums import (
    ShopifyInventoryModeEnum,
    ShopifyProductSyncItemStatusEnum,
    ShopifyProductSyncOperationEnum,
    ShopifyProductSyncStageEnum,
)
from beyo_manager.domain.shopify.product_sync_identity import (
    ProductSyncMatchResult,
    select_exact_variant_match,
)
from beyo_manager.domain.shopify.product_sync_stages import should_run_stage
from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.errors.external_service import (
    ShopifyGraphQLError,
    ShopifyGraphQLNonRetryableError,
    ShopifyProductLookupAmbiguousError,
)
from beyo_manager.models.tables.shopify.shopify_product_sync_item import ShopifyProductSyncItem
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.services.infra.shopify.product_sync_client import (
    configure_shopify_product_variant,
    create_shopify_product,
    find_product_by_operation_tag,
    find_product_variant_by_identity,
    set_shopify_product_metafields,
    update_shopify_product,
)
from beyo_manager.services.infra.shopify.inventory_client import (
    activate_inventory_at_location,
    enable_inventory_tracking,
    fetch_inventory_set_locations,
    resolve_inventory_item_state,
    set_inventory_quantities,
)
from beyo_manager.services.tasks.shopify._inventory_sync import sync_inventory_adjustments
from beyo_manager.services.tasks.shopify._product_media_resolver import resolve_product_media


_REQUIRED_INVENTORY_SCOPES = ("read_locations", "write_inventory")


async def sync_one_product_sync_item(
    session: AsyncSession,
    *,
    sync_item: ShopifyProductSyncItem,
    shop: ShopifyShopIntegration,
) -> None:
    payload = sync_item.normalized_payload_json or {}
    variant_payload = payload.get("variant") or {}
    inventory_item = variant_payload.get("inventoryItem") or {}
    inventory_payload = payload.get("inventory") or {}
    inventory_mode = sync_item.inventory_mode
    # The two modes carry different contracts under `inventory`, under distinct keys so
    # the shape is self-describing: `adjustments` entries are additive deltas
    # (`quantity_to_add`) consumed by the ledger; `quantities` entries are absolute
    # targets (`quantity`) consumed by inventorySetQuantities.
    if inventory_mode == ShopifyInventoryModeEnum.SET:
        inventory_entries = inventory_payload.get("quantities") or []
    else:
        inventory_entries = inventory_payload.get("adjustments") or []
    sku = _clean_str(inventory_item.get("sku"))
    barcode = _clean_str(variant_payload.get("barcode"))
    operation_tag = f"managerbeyo-sync-{sync_item.client_id}"
    current_stage = ShopifyProductSyncStageEnum(
        sync_item.stage
    )

    sync_item.status = ShopifyProductSyncItemStatusEnum.PROCESSING
    sync_item.error_code = None
    sync_item.error_message = None
    await session.commit()

    try:
        match = None
        if should_run_stage(
            current_stage,
            ShopifyProductSyncStageEnum.PRODUCT_CREATED,
        ):
            media = await resolve_product_media(session, normalized_payload=payload)
            operation_match = await find_product_by_operation_tag(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                operation_tag=operation_tag,
            )
            recovered_by_operation_tag = operation_match is not None
            if operation_match is not None:
                match = ProductSyncMatchResult(
                    found=True,
                    shopify_product_id=operation_match["shopify_product_id"],
                    shopify_variant_id=operation_match["shopify_variant_id"],
                    shopify_inventory_item_id=operation_match.get(
                        "shopify_inventory_item_id"
                    ),
                )
            else:
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
                    if (
                        barcode_match.found
                        and barcode_match.shopify_product_id
                        != match.shopify_product_id
                    ):
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
                sync_item.requested_operation = (
                    ShopifyProductSyncOperationEnum.UPDATE
                )
                result = await update_shopify_product(
                    shop_domain=shop.shop_domain,
                    access_token_encrypted=shop.access_token_encrypted,
                    shopify_product_id=match.shopify_product_id or "",
                    shopify_variant_id=match.shopify_variant_id or "",
                    normalized_payload=payload,
                    fallback_inventory_item_id=_match_inventory_item_id(match),
                    media=media,
                    operation_tag=(
                        operation_tag if recovered_by_operation_tag else None
                    ),
                )
            else:
                sync_item.requested_operation = (
                    ShopifyProductSyncOperationEnum.CREATE
                )
                result = await create_shopify_product(
                    shop_domain=shop.shop_domain,
                    access_token_encrypted=shop.access_token_encrypted,
                    normalized_payload=payload,
                    media=media,
                    operation_tag=operation_tag,
                )

            sync_item.shopify_product_id = result["shopify_product_id"]
            sync_item.shopify_variant_id = result["shopify_variant_id"]
            sync_item.shopify_inventory_item_id = result.get(
                "shopify_inventory_item_id"
            )
            sync_item.shopify_media_id = result.get("shopify_media_id")
            sync_item.media_status = result.get("media_status")
            sync_item.stage = ShopifyProductSyncStageEnum.PRODUCT_CREATED
            current_stage = sync_item.stage
            await session.commit()

        if should_run_stage(
            current_stage,
            ShopifyProductSyncStageEnum.VARIANT_CONFIGURED,
        ):
            operation_name = (
                "create_shopify_product_variant_update"
                if sync_item.requested_operation
                == ShopifyProductSyncOperationEnum.CREATE
                else "update_shopify_product_variant_update"
            )
            variant_result = await configure_shopify_product_variant(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted,
                shopify_product_id=sync_item.shopify_product_id or "",
                shopify_variant_id=sync_item.shopify_variant_id or "",
                normalized_payload=payload,
                operation_name=operation_name,
            )
            sync_item.shopify_variant_id = variant_result["shopify_variant_id"]
            if variant_result.get("shopify_inventory_item_id") is not None:
                sync_item.shopify_inventory_item_id = variant_result[
                    "shopify_inventory_item_id"
                ]
            sync_item.stage = ShopifyProductSyncStageEnum.VARIANT_CONFIGURED
            current_stage = sync_item.stage
            await session.commit()

        run_inventory_stage = should_run_stage(
            current_stage,
            ShopifyProductSyncStageEnum.INVENTORY_SET,
        )
        if not run_inventory_stage:
            inventory_entries = []
        result = {
            "shopify_product_id": sync_item.shopify_product_id,
            "shopify_variant_id": sync_item.shopify_variant_id,
            "shopify_inventory_item_id": sync_item.shopify_inventory_item_id,
        }

        if inventory_entries:
            resolved_inventory_item_id = _clean_str(result.get("shopify_inventory_item_id"))
            if resolved_inventory_item_id is None and match is not None:
                resolved_inventory_item_id = _match_inventory_item_id(match)
            sync_item.shopify_inventory_item_id = resolved_inventory_item_id
            if inventory_mode == ShopifyInventoryModeEnum.SET:
                await _sync_absolute_inventory(
                    session,
                    sync_item=sync_item,
                    shop=shop,
                    inventory_item_id=resolved_inventory_item_id,
                    quantities=inventory_entries,
                )
            else:
                await sync_inventory_adjustments(
                    session,
                    sync_item=sync_item,
                    shop=shop,
                    inventory_item_id=resolved_inventory_item_id,
                    adjustments=inventory_entries,
                )

        if run_inventory_stage:
            sync_item.stage = ShopifyProductSyncStageEnum.INVENTORY_SET
            current_stage = sync_item.stage
            await session.commit()

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
    except (
        ShopifyGraphQLNonRetryableError,
        ShopifyProductLookupAmbiguousError,
    ) as exc:
        sync_item.status = ShopifyProductSyncItemStatusEnum.FAILED
        sync_item.error_code = exc.error_code
        sync_item.error_message = str(exc)[:1024]
        await session.commit()


async def _sync_absolute_inventory(
    session: AsyncSession,
    *,
    sync_item: ShopifyProductSyncItem,
    shop: ShopifyShopIntegration,
    inventory_item_id: str | None,
    quantities: list[dict],
) -> None:
    if not has_all_required_scopes(
        _REQUIRED_INVENTORY_SCOPES,
        getattr(shop, "granted_scopes", None) or (),
    ):
        raise _inventory_error(
            "missing_inventory_scope",
            "Shopify inventory access needs reauthorization before inventory can be updated.",
        )
    if not inventory_item_id:
        raise _inventory_error(
            "inventory_item_unresolved",
            "Shopify inventory item could not be resolved.",
        )

    locations = await fetch_inventory_set_locations(
        shop_domain=shop.shop_domain,
        access_token_encrypted=shop.access_token_encrypted or "",
    )
    locations_by_id = {
        location["location_id"]: location
        for location in locations
    }
    invalid_location_ids = [
        quantity["location_id"]
        for quantity in quantities
        if (
            quantity["location_id"] not in locations_by_id
            or not locations_by_id[quantity["location_id"]]["is_active"]
            or locations_by_id[quantity["location_id"]]["is_fulfillment_service"]
        )
    ]
    if invalid_location_ids:
        raise _inventory_error(
            "preorder_inventory_location_invalid",
            "One or more Shopify locations are unavailable for inventory.",
        )

    previous_entries = {
        entry["location_id"]: entry
        for entry in (sync_item.inventory_result_json or {}).get("quantities", [])
        if isinstance(entry, dict) and isinstance(entry.get("location_id"), str)
    }
    summary_entries: list[dict] = []
    for quantity in quantities:
        state = await resolve_inventory_item_state(
            shop_domain=shop.shop_domain,
            access_token_encrypted=shop.access_token_encrypted or "",
            inventory_item_id=inventory_item_id,
            location_id=quantity["location_id"],
        )
        if not state["tracked"]:
            await enable_inventory_tracking(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted or "",
                inventory_item_id=inventory_item_id,
            )
        if not state["level_exists"]:
            await activate_inventory_at_location(
                shop_domain=shop.shop_domain,
                access_token_encrypted=shop.access_token_encrypted or "",
                inventory_item_id=inventory_item_id,
                location_id=quantity["location_id"],
                idempotency_key=f"{sync_item.client_id}:{quantity['location_id']}",
            )
        previous = previous_entries.get(quantity["location_id"]) or {}
        summary_entries.append(
            {
                "location_id": quantity["location_id"],
                "quantity": quantity["quantity"],
                "before_available": previous.get("before_available", state["available"]),
                "compare_protection": "explicitly_bypassed",
                "outcome": "pending",
            }
        )

    sync_item.inventory_result_json = {"quantities": summary_entries}
    await session.commit()

    await set_inventory_quantities(
        shop_domain=shop.shop_domain,
        access_token_encrypted=shop.access_token_encrypted or "",
        quantities=[
            {
                "inventory_item_id": inventory_item_id,
                "location_id": quantity["location_id"],
                "quantity": quantity["quantity"],
            }
            for quantity in quantities
        ],
        reference_document_uri=f"managerbeyo://preorder/{sync_item.client_id}",
        idempotency_key=f"shopify-preorder:{sync_item.client_id}:inventory-set",
    )
    for entry in summary_entries:
        entry["outcome"] = "applied"
        entry["available"] = entry["quantity"]
    sync_item.inventory_result_json = {"quantities": summary_entries}
    await session.commit()


def _inventory_error(code: str, message: str) -> ShopifyGraphQLError:
    from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError

    return ShopifyGraphQLNonRetryableError(message, error_code=code)


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _match_inventory_item_id(match: object) -> str | None:
    inventory_item = getattr(match, "shopify_inventory_item_id", None)
    if inventory_item is not None:
        return _clean_str(inventory_item)
    if isinstance(match, dict):
        return _clean_str(((match.get("inventoryItem") or {}).get("id")))
    return None
