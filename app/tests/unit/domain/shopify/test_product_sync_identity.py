import pytest

from beyo_manager.domain.shopify.product_sync_identity import select_exact_variant_match
from beyo_manager.errors.external_service import ShopifyProductLookupAmbiguousError


@pytest.mark.unit
def test_select_exact_variant_match_returns_not_found_when_no_exact_match() -> None:
    result = select_exact_variant_match(
        [{"id": "gid://shopify/ProductVariant/1", "sku": "OTHER", "barcode": "OTHER", "product": {"id": "gid://shopify/Product/1"}}],
        identity_type="sku",
        identity_value="SKU-1",
    )

    assert result.found is False
    assert result.shopify_product_id is None
    assert result.shopify_variant_id is None


@pytest.mark.unit
def test_select_exact_variant_match_returns_single_match() -> None:
    result = select_exact_variant_match(
        [{"id": "gid://shopify/ProductVariant/1", "sku": "SKU-1", "barcode": "BAR-1", "product": {"id": "gid://shopify/Product/1"}}],
        identity_type="sku",
        identity_value="SKU-1",
    )

    assert result.found is True
    assert result.shopify_product_id == "gid://shopify/Product/1"
    assert result.shopify_variant_id == "gid://shopify/ProductVariant/1"


@pytest.mark.unit
def test_select_exact_variant_match_raises_for_ambiguous_parent_products() -> None:
    with pytest.raises(ShopifyProductLookupAmbiguousError, match="Multiple Shopify products matched"):
        select_exact_variant_match(
            [
                {"id": "gid://shopify/ProductVariant/1", "sku": "SKU-1", "barcode": "BAR-1", "product": {"id": "gid://shopify/Product/1"}},
                {"id": "gid://shopify/ProductVariant/2", "sku": "SKU-1", "barcode": "BAR-1", "product": {"id": "gid://shopify/Product/2"}},
            ],
            identity_type="sku",
            identity_value="SKU-1",
        )
