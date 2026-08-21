from __future__ import annotations

import pytest

from beyo_manager.errors.external_service import (
    ShopifyGraphQLNonRetryableError,
    ShopifyGraphQLRetryableError,
)
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
    variant_result = await product_sync_client.configure_shopify_product_variant(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        shopify_product_id=result["shopify_product_id"],
        shopify_variant_id=result["shopify_variant_id"],
        normalized_payload={
            "variant": {
                "barcode": "BAR-1",
                "price": "99.00",
                "inventoryItem": {"sku": "SKU-1", "measurement": {"weight": {"value": 1.2, "unit": "KILOGRAMS"}}},
            },
        },
        operation_name="create_shopify_product_variant_update",
    )

    assert result == {
        "shopify_product_id": "gid://shopify/Product/1",
        "shopify_variant_id": "gid://shopify/ProductVariant/10",
    }
    assert variant_result["shopify_variant_id"] == "gid://shopify/ProductVariant/10"
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

    payload = {
        "product": {"title": "Updated Chair", "status": "ACTIVE"},
        "variant": {
            "barcode": "BAR-2",
            "inventoryItem": {"sku": "SKU-2", "measurement": {"weight": {"value": 4.0, "unit": "POUNDS"}}},
        },
        "metafields": [],
    }
    result = await product_sync_client.update_shopify_product(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        shopify_product_id="gid://shopify/Product/2",
        shopify_variant_id="gid://shopify/ProductVariant/20",
        normalized_payload=payload,
    )
    variant_result = await product_sync_client.configure_shopify_product_variant(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        shopify_product_id=result["shopify_product_id"],
        shopify_variant_id=result["shopify_variant_id"],
        normalized_payload=payload,
        operation_name="update_shopify_product_variant_update",
    )

    assert result == {
        "shopify_product_id": "gid://shopify/Product/2",
        "shopify_variant_id": "gid://shopify/ProductVariant/20",
    }
    assert variant_result["shopify_variant_id"] == "gid://shopify/ProductVariant/20"
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
@pytest.mark.parametrize("operation", ["create", "update"])
async def test_product_write_includes_media_only_when_supplied(
    monkeypatch,
    operation: str,
) -> None:
    calls: list[dict] = []

    async def _fake_execute_shopify_graphql(**kwargs):
        calls.append(kwargs)
        if kwargs["operation_name"] == "create_shopify_product":
            return {
                "productCreate": {
                    "product": {
                        "id": "gid://shopify/Product/1",
                        "media": {
                            "nodes": [
                                {
                                    "id": "gid://shopify/MediaImage/3",
                                    "status": "PROCESSING",
                                }
                            ]
                        },
                        "variants": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "gid://shopify/ProductVariant/2"
                                    }
                                }
                            ]
                        },
                    },
                    "userErrors": [],
                }
            }
        if kwargs["operation_name"] == "update_shopify_product":
            return {
                "productUpdate": {
                    "product": {
                        "id": "gid://shopify/Product/1",
                        "media": {
                            "nodes": [
                                {
                                    "id": "gid://shopify/MediaImage/3",
                                    "status": "PROCESSING",
                                }
                            ]
                        },
                    },
                    "userErrors": [],
                }
            }
        return {
            "productVariantsBulkUpdate": {
                "productVariants": [
                    {"id": "gid://shopify/ProductVariant/2"}
                ],
                "userErrors": [],
            }
        }

    monkeypatch.setattr(
        product_sync_client,
        "execute_shopify_graphql",
        _fake_execute_shopify_graphql,
    )
    payload = {
        "product": {"title": "Chair", "status": "UNLISTED"},
        "variant": {"price": "5200.00", "inventoryItem": {"sku": "SKU-1"}},
        "metafields": [],
    }
    media = [
        {
            "originalSource": "https://cdn.example.com/chair.webp",
            "mediaContentType": "IMAGE",
        }
    ]
    if operation == "create":
        result = await product_sync_client.create_shopify_product(
            shop_domain="shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            normalized_payload=payload,
            media=media,
        )
    else:
        result = await product_sync_client.update_shopify_product(
            shop_domain="shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            shopify_product_id="gid://shopify/Product/1",
            shopify_variant_id="gid://shopify/ProductVariant/2",
            normalized_payload=payload,
            media=media,
        )

    assert calls[0]["variables"]["media"] == media
    assert "$media: [CreateMediaInput!]" in calls[0]["query"]
    assert "media: $media" in calls[0]["query"]
    assert result["shopify_media_id"] == "gid://shopify/MediaImage/3"
    assert result["media_status"] == "PROCESSING"


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


def _variant(variant_id: str, barcode: str, price: str = "100.00") -> dict:
    return {
        "id": variant_id,
        "sku": None,
        "barcode": barcode,
        "price": price,
        "product": {"id": f"prod_{variant_id}", "title": "T", "status": "ACTIVE"},
    }


def _page(nodes: list[dict], *, has_next: bool = False, cursor: str | None = None) -> dict:
    return {
        "productVariants": {
            "edges": [{"node": node} for node in nodes],
            "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
        }
    }


@pytest.mark.unit
def test_group_variants_by_barcode_buckets_exact_matches_only() -> None:
    grouped = product_sync_client.group_variants_by_barcode(
        [_variant("v1", "A-1"), _variant("v2", "A-10"), _variant("v3", "B-2"), _variant("v4", "A-1")],
        ["A-1", "B-2", "C-3"],
    )

    assert [node["id"] for node in grouped["A-1"]] == ["v1", "v4"]  # ambiguous stays ambiguous
    assert [node["id"] for node in grouped["B-2"]] == ["v3"]
    assert grouped["C-3"] == []  # requested but unmatched -> explicit "not found"
    assert "A-10" not in grouped  # fuzzy near-miss never leaks into a bucket


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batched_lookup_uses_one_request_for_many_barcodes(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_execute(**kwargs):
        calls.append(kwargs)
        return _page([_variant("v1", "A-1"), _variant("v2", "B-2")])

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute)

    grouped = await product_sync_client.find_product_variant_pricing_by_barcodes(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        barcodes=["A-1", "B-2", "A-1", "  "],
    )

    assert len(calls) == 1
    assert calls[0]["variables"]["searchQuery"] == 'barcode:"A-1" OR barcode:"B-2"'
    assert set(grouped) == {"A-1", "B-2"}
    assert grouped["A-1"][0]["price"] == "100.00"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batched_lookup_paginates_until_exhausted(monkeypatch) -> None:
    pages = [
        _page([_variant("v1", "A-1")], has_next=True, cursor="cur1"),
        _page([_variant("v2", "B-2")], has_next=False),
    ]
    seen_cursors: list[object] = []

    async def _fake_execute(**kwargs):
        seen_cursors.append(kwargs["variables"]["after"])
        return pages[len(seen_cursors) - 1]

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute)

    grouped = await product_sync_client.find_product_variant_pricing_by_barcodes(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        barcodes=["A-1", "B-2"],
    )

    assert seen_cursors == [None, "cur1"]
    assert [node["id"] for node in grouped["B-2"]] == ["v2"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batched_lookup_retries_retryable_errors(monkeypatch) -> None:
    attempts = {"count": 0}

    async def _fake_execute(**kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ShopifyGraphQLRetryableError("throttled", error_code="throttled")
        return _page([_variant("v1", "A-1")])

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute)
    monkeypatch.setattr(product_sync_client.asyncio, "sleep", _no_sleep)

    grouped = await product_sync_client.find_product_variant_pricing_by_barcodes(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        barcodes=["A-1"],
    )

    assert attempts["count"] == 3
    assert [node["id"] for node in grouped["A-1"]] == ["v1"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batched_lookup_raises_rather_than_truncating_endless_pagination(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return _page([_variant("v1", "A-1")], has_next=True, cursor="cur")

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute)

    with pytest.raises(ShopifyGraphQLNonRetryableError):
        await product_sync_client.find_product_variant_pricing_by_barcodes(
            shop_domain="shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            barcodes=["A-1"],
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_single_barcode_lookup_delegates_to_the_batched_path(monkeypatch) -> None:
    async def _fake_execute(**kwargs):
        return _page([_variant("v1", "A-1"), _variant("v2", "OTHER")])

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _fake_execute)

    result = await product_sync_client.find_product_variant_pricing_by_barcode(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        barcode="A-1",
    )

    assert [node["id"] for node in result] == ["v1"]
