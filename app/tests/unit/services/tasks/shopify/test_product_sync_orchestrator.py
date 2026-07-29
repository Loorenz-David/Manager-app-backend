from __future__ import annotations

from types import SimpleNamespace

import pytest

from beyo_manager.domain.shopify.enums import (
    ShopifyProductSyncItemStatusEnum,
    ShopifyProductSyncOperationEnum,
    ShopifyProductSyncStageEnum,
)
from beyo_manager.errors.external_service import (
    ShopifyGraphQLNonRetryableError,
    ShopifyGraphQLRetryableError,
)
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
        shopify_inventory_item_id=None,
        shopify_media_id=None,
        media_status=None,
        inventory_result_json=None,
        stage=ShopifyProductSyncStageEnum.QUEUED,
        error_code=None,
        error_message=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _shop() -> SimpleNamespace:
    return SimpleNamespace(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        granted_scopes=["read_locations", "write_inventory"],
    )


@pytest.mark.unit
def test_legacy_persisted_adjustments_are_converted_to_absolute_quantities(
    caplog,
) -> None:
    quantities, converted = module._resolve_absolute_inventory_entries(
        {
            "adjustments": [
                {
                    "location_id": "gid://shopify/Location/1",
                    "quantity_to_add": 0,
                },
                {
                    "location_id": "gid://shopify/Location/2",
                    "quantity_to_add": 2,
                },
            ]
        },
        sync_item_id="shpsi_legacy",
    )

    assert converted is True
    assert quantities == [
        {"location_id": "gid://shopify/Location/1", "quantity": 0},
        {"location_id": "gid://shopify/Location/2", "quantity": 2},
    ]
    assert "legacy_persisted_inventory_converted" in caplog.text


@pytest.fixture(autouse=True)
def _default_stage_dependencies(monkeypatch):
    async def _configure_variant(**kwargs):
        return {
            "shopify_variant_id": kwargs["shopify_variant_id"],
            "shopify_inventory_item_id": "gid://shopify/InventoryItem/1",
        }

    monkeypatch.setattr(
        module,
        "configure_shopify_product_variant",
        _configure_variant,
    )


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
async def test_sku_only_sync_creates_without_identity_lookup(monkeypatch) -> None:
    sync_item = _sync_item(normalized_payload_json={
        "product": {"title": "Chair"},
        "variant": {"inventoryItem": {"sku": "SKU-1"}},
        "metafields": [],
    })
    session = _FakeSession()

    async def _unexpected_find(**_kwargs):
        raise AssertionError("SKU-only sync must not perform an identity lookup")

    async def _create(**_kwargs):
        return {
            "shopify_product_id": "gid://shopify/Product/created",
            "shopify_variant_id": "gid://shopify/ProductVariant/created",
        }

    monkeypatch.setattr(module, "find_product_variant_by_identity", _unexpected_find)
    monkeypatch.setattr(module, "create_shopify_product", _create)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.requested_operation == ShopifyProductSyncOperationEnum.CREATE
    assert sync_item.shopify_product_id == "gid://shopify/Product/created"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_existing_sku_with_new_barcode_creates(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _find(*, sku, barcode, **_kwargs):
        assert sku is None
        assert barcode == "BAR-1"
        return []

    async def _create(**_kwargs):
        return {
            "shopify_product_id": "gid://shopify/Product/created",
            "shopify_variant_id": "gid://shopify/ProductVariant/created",
        }

    async def _set_metafields(**_kwargs):
        return None

    monkeypatch.setattr(module, "find_product_variant_by_identity", _find)
    monkeypatch.setattr(module, "create_shopify_product", _create)
    monkeypatch.setattr(
        module,
        "set_shopify_product_metafields",
        _set_metafields,
    )

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.requested_operation == ShopifyProductSyncOperationEnum.CREATE
    assert sync_item.shopify_product_id == "gid://shopify/Product/created"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_barcode_match_updates_regardless_of_sku(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _find(*, sku, barcode, **_kwargs):
        assert sku is None
        assert barcode == "BAR-1"
        return [
            {
                "id": "gid://shopify/ProductVariant/1",
                "sku": "DUPLICATE-SKU",
                "barcode": "BAR-1",
                "product": {"id": "gid://shopify/Product/X"},
            }
        ]

    async def _fake_update(**_kwargs):
        return {
            "shopify_product_id": "gid://shopify/Product/X",
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
        }

    async def _fake_set_metafields(**_kwargs):
        return None

    monkeypatch.setattr(module, "find_product_variant_by_identity", _find)
    monkeypatch.setattr(module, "update_shopify_product", _fake_update)
    monkeypatch.setattr(module, "set_shopify_product_metafields", _fake_set_metafields)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.requested_operation == ShopifyProductSyncOperationEnum.UPDATE
    assert sync_item.shopify_product_id == "gid://shopify/Product/X"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_duplicate_barcode_variants_fail_without_shopify_write(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _find(**_kwargs):
        return [
            {
                "id": "gid://shopify/ProductVariant/1",
                "barcode": "BAR-1",
                "product": {"id": "gid://shopify/Product/X"},
            },
            {
                "id": "gid://shopify/ProductVariant/2",
                "barcode": "BAR-1",
                "product": {"id": "gid://shopify/Product/X"},
            },
        ]

    async def _unexpected_write(**_kwargs):
        raise AssertionError("ambiguous barcode must not write to Shopify")

    monkeypatch.setattr(module, "find_product_variant_by_identity", _find)
    monkeypatch.setattr(module, "create_shopify_product", _unexpected_write)
    monkeypatch.setattr(module, "update_shopify_product", _unexpected_write)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.FAILED
    assert sync_item.error_code == "ambiguous_product_match"
    assert sync_item.shopify_product_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_id_and_stage_are_committed_before_variant_mutation(
    monkeypatch,
) -> None:
    sync_item = _sync_item(
        normalized_payload_json={
            "product": {"title": "Chair"},
            "variant": {"inventoryItem": {"sku": "SKU-1"}},
            "metafields": [],
        }
    )
    session = _FakeSession()

    async def _find(**_kwargs):
        return []

    async def _create(**_kwargs):
        return {
            "shopify_product_id": "gid://shopify/Product/1",
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
        }

    async def _configure(**kwargs):
        assert session.commits == 2
        assert sync_item.shopify_product_id == "gid://shopify/Product/1"
        assert sync_item.stage == ShopifyProductSyncStageEnum.PRODUCT_CREATED
        return {
            "shopify_variant_id": kwargs["shopify_variant_id"],
            "shopify_inventory_item_id": "gid://shopify/InventoryItem/1",
        }

    monkeypatch.setattr(module, "find_product_variant_by_identity", _find)
    monkeypatch.setattr(module, "create_shopify_product", _create)
    monkeypatch.setattr(module, "configure_shopify_product_variant", _configure)

    await module.sync_one_product_sync_item(session, sync_item=sync_item, shop=_shop())

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.stage == ShopifyProductSyncStageEnum.INVENTORY_SET


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("starting_stage", "expected_calls"),
    [
        (
            ShopifyProductSyncStageEnum.QUEUED,
            ["create", "variant", "metafields"],
        ),
        (
            ShopifyProductSyncStageEnum.PRODUCT_CREATED,
            ["variant", "metafields"],
        ),
        (
            ShopifyProductSyncStageEnum.VARIANT_CONFIGURED,
            ["metafields"],
        ),
        (
            ShopifyProductSyncStageEnum.INVENTORY_SET,
            ["metafields"],
        ),
    ],
)
async def test_resume_from_each_stage_runs_only_remaining_calls(
    monkeypatch,
    starting_stage: ShopifyProductSyncStageEnum,
    expected_calls: list[str],
) -> None:
    sync_item = _sync_item(
        stage=starting_stage,
        requested_operation=ShopifyProductSyncOperationEnum.CREATE,
        shopify_product_id=(
            None
            if starting_stage == ShopifyProductSyncStageEnum.QUEUED
            else "gid://shopify/Product/1"
        ),
        shopify_variant_id=(
            None
            if starting_stage == ShopifyProductSyncStageEnum.QUEUED
            else "gid://shopify/ProductVariant/1"
        ),
        shopify_inventory_item_id=(
            None
            if starting_stage
            in {
                ShopifyProductSyncStageEnum.QUEUED,
                ShopifyProductSyncStageEnum.PRODUCT_CREATED,
            }
            else "gid://shopify/InventoryItem/1"
        ),
        normalized_payload_json={
            "product": {"title": "Chair"},
            "variant": {"inventoryItem": {"sku": "SKU-1"}},
            "metafields": [
                {
                    "key": "origin",
                    "type": "single_line_text_field",
                    "value": "warehouse",
                }
            ],
        },
    )
    calls: list[str] = []

    async def _identity(**_kwargs):
        calls.append("identity")
        return []

    async def _create(**_kwargs):
        calls.append("create")
        return {
            "shopify_product_id": "gid://shopify/Product/1",
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
        }

    async def _variant(**kwargs):
        calls.append("variant")
        return {
            "shopify_variant_id": kwargs["shopify_variant_id"],
            "shopify_inventory_item_id": "gid://shopify/InventoryItem/1",
        }

    async def _metafields(**_kwargs):
        calls.append("metafields")

    monkeypatch.setattr(module, "find_product_variant_by_identity", _identity)
    monkeypatch.setattr(module, "create_shopify_product", _create)
    monkeypatch.setattr(module, "configure_shopify_product_variant", _variant)
    monkeypatch.setattr(module, "set_shopify_product_metafields", _metafields)

    await module.sync_one_product_sync_item(
        _FakeSession(),
        sync_item=sync_item,
        shop=_shop(),
    )

    assert calls == expected_calls
    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.stage == ShopifyProductSyncStageEnum.INVENTORY_SET


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retryable_shopify_error_propagates(monkeypatch) -> None:
    sync_item = _sync_item()
    session = _FakeSession()

    async def _retryable(**_kwargs):
        raise ShopifyGraphQLRetryableError(
            "Shopify timed out.",
            error_code="shopify_timeout",
        )

    monkeypatch.setattr(module, "find_product_variant_by_identity", _retryable)

    with pytest.raises(ShopifyGraphQLRetryableError):
        await module.sync_one_product_sync_item(
            session,
            sync_item=sync_item,
            shop=_shop(),
        )

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.PROCESSING
    assert session.commits == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_preorder_keeps_metafield_quantity_separate_from_absolute_inventory(
    monkeypatch,
) -> None:
    sync_item = _sync_item(
        normalized_payload_json={
            "product": {"title": "Chair", "status": "UNLISTED"},
            "variant": {
                "price": "5200.00",
                "inventoryItem": {"sku": "SKU-1"},
            },
            "metafields": [
                {
                    "key": "quantity",
                    "type": "single_line_text_field",
                    "value": "6",
                }
            ],
            "inventory": {
                "quantities": [
                    {
                        "location_id": "gid://shopify/Location/1",
                        "quantity": 2,
                    }
                ]
            },
        },
    )
    session = _FakeSession()
    captured: dict = {}

    async def _fake_find(**_kwargs):
        return []

    async def _fake_create(**kwargs):
        captured["price"] = kwargs["normalized_payload"]["variant"]["price"]
        return {
            "shopify_product_id": "gid://shopify/Product/1",
            "shopify_variant_id": "gid://shopify/ProductVariant/1",
            "shopify_inventory_item_id": "gid://shopify/InventoryItem/1",
        }

    async def _fake_locations(**_kwargs):
        return [
            {
                "location_id": "gid://shopify/Location/1",
                "name": "Warehouse",
                "is_active": True,
                "is_fulfillment_service": False,
            }
        ]

    async def _fake_state(**_kwargs):
        return {
            "tracked": True,
            "level_exists": True,
            "available": 5,
            "on_hand": 5,
        }

    async def _fake_set(**kwargs):
        captured["set"] = kwargs
        return {}

    async def _fake_metafields(**kwargs):
        captured["metafields"] = kwargs["metafields"]

    monkeypatch.setattr(module, "find_product_variant_by_identity", _fake_find)
    monkeypatch.setattr(module, "create_shopify_product", _fake_create)
    monkeypatch.setattr(module, "fetch_inventory_set_locations", _fake_locations)
    monkeypatch.setattr(module, "resolve_inventory_item_state", _fake_state)
    monkeypatch.setattr(module, "set_inventory_quantities", _fake_set)
    monkeypatch.setattr(module, "set_shopify_product_metafields", _fake_metafields)

    await module.sync_one_product_sync_item(
        session,
        sync_item=sync_item,
        shop=_shop(),
    )

    assert captured["price"] == "5200.00"
    assert captured["metafields"][0]["value"] == "6"
    assert captured["set"]["quantities"][0]["quantity"] == 2
    assert captured["set"]["idempotency_key"] == "shopify-inventory-set:shpsi_1"
    assert sync_item.inventory_result_json == {
        "quantities": [
            {
                "location_id": "gid://shopify/Location/1",
                "quantity": 2,
                "before_available": 5,
                "compare_protection": "explicitly_bypassed",
                "outcome": "applied",
                "available": 2,
            }
        ]
    }
