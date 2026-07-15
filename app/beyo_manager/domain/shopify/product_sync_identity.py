from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from beyo_manager.errors.external_service import ShopifyProductLookupAmbiguousError

IdentityType = Literal["sku", "barcode"]


@dataclass(frozen=True)
class ProductSyncMatchResult:
    found: bool
    shopify_product_id: str | None = None
    shopify_variant_id: str | None = None
    shopify_inventory_item_id: str | None = None


def select_exact_variant_match(
    variant_nodes: list[dict],
    *,
    identity_type: IdentityType,
    identity_value: str,
) -> ProductSyncMatchResult:
    expected = _clean_str(identity_value)
    if expected is None:
        return ProductSyncMatchResult(found=False)

    exact_matches = []
    for variant_node in variant_nodes:
        if _clean_str(variant_node.get(identity_type)) != expected:
            continue
        product = variant_node.get("product") or {}
        product_id = _clean_str(product.get("id"))
        variant_id = _clean_str(variant_node.get("id"))
        if product_id is None or variant_id is None:
            continue
        inventory_item = variant_node.get("inventoryItem") or {}
        exact_matches.append((product_id, variant_id, _clean_str(inventory_item.get("id"))))

    if not exact_matches:
        return ProductSyncMatchResult(found=False)

    product_ids = {product_id for product_id, _variant_id, _inventory_item_id in exact_matches}
    if len(product_ids) > 1:
        raise ShopifyProductLookupAmbiguousError()

    product_id, variant_id, inventory_item_id = exact_matches[0]
    return ProductSyncMatchResult(
        found=True,
        shopify_product_id=product_id,
        shopify_variant_id=variant_id,
        shopify_inventory_item_id=inventory_item_id,
    )


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
