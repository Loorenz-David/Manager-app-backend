from __future__ import annotations

import pytest

from beyo_manager.services.infra.shopify import product_sync_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_shopify_product_uses_product_create_then_bulk_variant_update(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute_shopify_graphql(**kwargs):
        calls.append(kwargs)
        if kwargs["operation_name"] == "create_shopify_product":
            return {
                "productCreate": {
                    "product": {
                        "id": "gid://shopify/Product/1",
                        "variants": {"edges": [{"node": {"id": "gid://shopify/ProductVariant/10"}}]},
                    },
                    "userErrors": [],
                }
            }
        return {
            "productVariantsBulkUpdate": {
                "productVariants": [{"id": "gid://shopify/ProductVariant/10", "barcode": "BAR-1", "inventoryItem": {"sku": "SKU-1"}}],
                "userErrors": [],
            }
        }

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute_shopify_graphql)

    result = await product_sync_client.create_shopify_product(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        normalized_payload={
            "product": {"title": "Chair", "descriptionHtml": "Desc", "status": "DRAFT"},
            "variant": {
                "barcode": "BAR-1",
                "price": "99.00",
                "inventoryItem": {"sku": "SKU-1", "measurement": {"weight": {"value": 1.2, "unit": "KILOGRAMS"}}},
            },
            "metafields": [],
        },
    )

    assert result == {
        "shopify_product_id": "gid://shopify/Product/1",
        "shopify_variant_id": "gid://shopify/ProductVariant/10",
    }
    assert calls[0]["variables"] == {"product": {"title": "Chair", "descriptionHtml": "Desc", "status": "DRAFT"}}
    assert "productCreate(product: $product)" in calls[0]["query"]
    assert "input:" not in calls[0]["query"]
    variant_payload = calls[1]["variables"]["variants"][0]
    assert variant_payload["barcode"] == "BAR-1"
    assert variant_payload["price"] == "99.00"
    assert "sku" not in variant_payload
    assert variant_payload["inventoryItem"]["sku"] == "SKU-1"
    assert variant_payload["inventoryItem"]["measurement"]["weight"] == {"value": 1.2, "unit": "KILOGRAMS"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_shopify_product_uses_product_update_then_bulk_variant_update(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute_shopify_graphql(**kwargs):
        calls.append(kwargs)
        if kwargs["operation_name"] == "update_shopify_product":
            return {"productUpdate": {"product": {"id": "gid://shopify/Product/2"}, "userErrors": []}}
        return {
            "productVariantsBulkUpdate": {
                "productVariants": [{"id": "gid://shopify/ProductVariant/20"}],
                "userErrors": [],
            }
        }

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute_shopify_graphql)

    result = await product_sync_client.update_shopify_product(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        shopify_product_id="gid://shopify/Product/2",
        shopify_variant_id="gid://shopify/ProductVariant/20",
        normalized_payload={
            "product": {"title": "Updated Chair", "status": "ACTIVE"},
            "variant": {
                "barcode": "BAR-2",
                "inventoryItem": {"sku": "SKU-2", "measurement": {"weight": {"value": 4.0, "unit": "POUNDS"}}},
            },
            "metafields": [],
        },
    )

    assert result == {
        "shopify_product_id": "gid://shopify/Product/2",
        "shopify_variant_id": "gid://shopify/ProductVariant/20",
    }
    assert calls[0]["variables"]["product"] == {
        "id": "gid://shopify/Product/2",
        "title": "Updated Chair",
        "status": "ACTIVE",
    }
    variant_payload = calls[1]["variables"]["variants"][0]
    assert variant_payload["id"] == "gid://shopify/ProductVariant/20"
    assert variant_payload["barcode"] == "BAR-2"
    assert variant_payload["inventoryItem"]["sku"] == "SKU-2"
    assert variant_payload["inventoryItem"]["measurement"]["weight"] == {"value": 4.0, "unit": "POUNDS"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_shopify_product_metafields_uses_metafields_set(monkeypatch) -> None:
    captured: dict = {}

    async def _fake_execute_shopify_graphql(**kwargs):
        captured.update(kwargs)
        return {"metafieldsSet": {"metafields": [{"id": "mf_1", "key": "origin", "namespace": "custom"}], "userErrors": []}}

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute_shopify_graphql)

    await product_sync_client.set_shopify_product_metafields(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        shopify_product_id="gid://shopify/Product/1",
        metafields=[{"key": "origin", "type": "single_line_text_field", "value": "warehouse"}],
    )

    assert "metafieldsSet(metafields: $metafields)" in captured["query"]
    assert captured["variables"]["metafields"] == [
        {
            "ownerId": "gid://shopify/Product/1",
            "namespace": "custom",
            "key": "origin",
            "type": "single_line_text_field",
            "value": "warehouse",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_product_variant_by_identity_prefers_exact_sku_then_falls_back_to_barcode(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute_shopify_graphql(**kwargs):
        calls.append(kwargs)
        if kwargs["operation_name"] == "find_product_variants_by_sku":
            return {"productVariants": {"edges": [{"node": {"id": "var_1", "sku": "OTHER", "barcode": "BAR-9", "product": {"id": "prod_1", "status": "ACTIVE"}}}]}}
        return {"productVariants": {"edges": [{"node": {"id": "var_2", "sku": "SKU-9", "barcode": "BAR-9", "product": {"id": "prod_2", "status": "ACTIVE"}}}]}}

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute_shopify_graphql)

    result = await product_sync_client.find_product_variant_by_identity(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        sku="SKU-9",
        barcode="BAR-9",
    )

    assert [call["operation_name"] for call in calls] == [
        "find_product_variants_by_sku",
        "find_product_variants_by_barcode",
    ]
    assert result[0]["id"] == "var_2"
