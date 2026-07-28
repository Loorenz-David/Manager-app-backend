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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_product_by_operation_tag_rejects_multiple_products(
    monkeypatch,
) -> None:
    async def _fake_execute_shopify_graphql(**kwargs):
        assert kwargs["variables"] == {
            "searchQuery": 'tag:"managerbeyo-sync-shpsi_1"',
            "first": 2,
        }
        return {
            "products": {
                "nodes": [
                    {"id": "gid://shopify/Product/1"},
                    {"id": "gid://shopify/Product/2"},
                ]
            }
        }

    monkeypatch.setattr(
        product_sync_client,
        "execute_shopify_graphql",
        _fake_execute_shopify_graphql,
    )

    with pytest.raises(
        product_sync_client.ShopifyProductLookupAmbiguousError
    ) as exc_info:
        await product_sync_client.find_product_by_operation_tag(
            shop_domain="shop.myshopify.com",
            access_token_encrypted="encrypted-token",
            operation_tag="managerbeyo-sync-shpsi_1",
        )

    assert exc_info.value.error_code == "ambiguous_operation_tag"
