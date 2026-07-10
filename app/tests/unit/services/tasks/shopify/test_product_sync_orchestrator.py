from __future__ import annotations

from types import SimpleNamespace

import pytest

from beyo_manager.domain.shopify.enums import ShopifyProductSyncItemStatusEnum
from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError
from beyo_manager.services.tasks.shopify import _product_sync_orchestrator as module


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _sync_item(**overrides) -> SimpleNamespace:
    base = dict(
        client_id="shpsi_1",
        normalized_payload_json={
            "product": {"title": "Chair"},
            "variant": {"barcode": "BAR-1", "inventoryItem": {"sku": "SKU-1"}},
            "metafields": [{"key": "origin", "type": "single_line_text_field", "value": "warehouse"}],
        },
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        error_code=None,
        error_message=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _shop() -> SimpleNamespace:
    return SimpleNamespace(shop_domain="shop.myshopify.com", access_token_encrypted="encrypted-token")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_one_product_sync_item_keeps_shopify_ids_when_metafields_call_fails(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _fake_find(**_kwargs):
        return []  # no existing match -> create path

    async def _fake_create(**_kwargs):
        return {
            "shopify_product_id": "gid://shopify/Product/1",
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
        }

    async def _fake_set_metafields(**_kwargs):
        raise ShopifyGraphQLNonRetryableError("Shopify rejected a metafield.", error_code="graphql_user_errors")

    monkeypatch.setattr(module, "find_product_variant_by_identity", _fake_find)
    monkeypatch.setattr(module, "create_shopify_product", _fake_create)
    monkeypatch.setattr(module, "set_shopify_product_metafields", _fake_set_metafields)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.FAILED
    assert sync_item.error_code == "graphql_user_errors"
    # The product was actually created in Shopify before the metafields call failed —
    # its id must still be recorded on the row, otherwise a future resubmission of
    # this item risks creating a second, orphaned duplicate product.
    assert sync_item.shopify_product_id == "gid://shopify/Product/1"
    assert sync_item.shopify_variant_id == "gid://shopify/ProductVariant/1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_one_product_sync_item_fails_when_sku_and_barcode_match_different_products(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _fake_find(*, sku, barcode, **_kwargs):
        if sku is not None:
            return [{"id": "var_1", "sku": "SKU-1", "barcode": None, "product": {"id": "gid://shopify/Product/X"}}]
        return [{"id": "var_2", "sku": None, "barcode": "BAR-1", "product": {"id": "gid://shopify/Product/Y"}}]

    async def _unexpected_write(**_kwargs):
        raise AssertionError("create/update must not be called when identities conflict")

    monkeypatch.setattr(module, "find_product_variant_by_identity", _fake_find)
    monkeypatch.setattr(module, "create_shopify_product", _unexpected_write)
    monkeypatch.setattr(module, "update_shopify_product", _unexpected_write)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.FAILED
    assert sync_item.error_code == "conflicting_identity_match"
    assert sync_item.shopify_product_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_one_product_sync_item_updates_when_sku_and_barcode_agree_on_same_product(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _fake_find(*, sku, barcode, **_kwargs):
        if sku is not None:
            return [{"id": "var_1", "sku": "SKU-1", "barcode": None, "product": {"id": "gid://shopify/Product/X"}}]
        return [{"id": "var_1", "sku": None, "barcode": "BAR-1", "product": {"id": "gid://shopify/Product/X"}}]

    async def _fake_update(**_kwargs):
        return {
            "shopify_product_id": "gid://shopify/Product/X",
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
        }

    async def _fake_set_metafields(**_kwargs):
        return None

    monkeypatch.setattr(module, "find_product_variant_by_identity", _fake_find)
    monkeypatch.setattr(module, "update_shopify_product", _fake_update)
    monkeypatch.setattr(module, "set_shopify_product_metafields", _fake_set_metafields)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.shopify_product_id == "gid://shopify/Product/X"
