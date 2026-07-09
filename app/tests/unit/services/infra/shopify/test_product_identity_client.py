from __future__ import annotations

import pytest

from beyo_manager.services.infra.shopify.product_identity_client import fetch_shopify_orders_by_product_identity


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_shopify_orders_by_product_identity_searches_orders_directly_for_sku(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        return {"orders": {"edges": [{"node": {"id": "gid://shopify/Order/1"}}]}}

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.product_identity_client.execute_shopify_graphql",
        _fake_execute,
    )

    orders = await fetch_shopify_orders_by_product_identity(
        shop_domain="shop-a.myshopify.com",
        access_token_encrypted="encrypted-token",
        identity_type="sku",
        identity_value='SKU "123"',
    )

    assert orders == [{"id": "gid://shopify/Order/1"}]
    assert len(calls) == 1
    assert calls[0]["operation_name"] == "search_orders_by_sku"
    assert calls[0]["variables"]["searchQuery"] == 'sku:"SKU \\"123\\""'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_shopify_orders_by_product_identity_resolves_barcode_to_skus_and_dedupes_orders(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        if kwargs["operation_name"] == "find_variants_by_barcode":
            return {
                "productVariants": {
                    "edges": [
                        {"node": {"id": "v1", "sku": "SKU-1", "barcode": "BAR-1"}},
                        {"node": {"id": "v2", "sku": "SKU-2", "barcode": "BAR-1"}},
                        {"node": {"id": "v3", "sku": "SKU-3", "barcode": "BAR-OTHER"}},
                        {"node": {"id": "v4", "sku": "SKU-1", "barcode": "BAR-1"}},
                    ]
                }
            }
        if kwargs["variables"]["searchQuery"] == 'sku:"SKU-1"':
            return {"orders": {"edges": [{"node": {"id": "gid://shopify/Order/1"}}]}}
        return {
            "orders": {
                "edges": [
                    {"node": {"id": "gid://shopify/Order/1"}},
                    {"node": {"id": "gid://shopify/Order/2"}},
                ]
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.product_identity_client.execute_shopify_graphql",
        _fake_execute,
    )

    orders = await fetch_shopify_orders_by_product_identity(
        shop_domain="shop-a.myshopify.com",
        access_token_encrypted="encrypted-token",
        identity_type="barcode",
        identity_value="BAR-1",
    )

    assert orders == [{"id": "gid://shopify/Order/1"}, {"id": "gid://shopify/Order/2"}]
    assert [call["operation_name"] for call in calls] == [
        "find_variants_by_barcode",
        "search_orders_by_sku",
        "search_orders_by_sku",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_shopify_orders_by_product_identity_returns_empty_when_barcode_has_no_exact_variant_match(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        return {
            "productVariants": {
                "edges": [
                    {"node": {"id": "v1", "sku": "SKU-1", "barcode": "BAR-OTHER"}},
                ]
            }
        }

    monkeypatch.setattr(
        "beyo_manager.services.infra.shopify.product_identity_client.execute_shopify_graphql",
        _fake_execute,
    )

    orders = await fetch_shopify_orders_by_product_identity(
        shop_domain="shop-a.myshopify.com",
        access_token_encrypted="encrypted-token",
        identity_type="barcode",
        identity_value="BAR-1",
    )

    assert orders == []
    assert [call["operation_name"] for call in calls] == ["find_variants_by_barcode"]
