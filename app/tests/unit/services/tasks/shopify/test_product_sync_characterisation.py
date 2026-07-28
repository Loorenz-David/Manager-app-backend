"""Lock the exact GraphQL emitted by the existing Shopify product sync.

This is a characterization net for production behavior, not a statement of the
desired future API. Do not edit it to match new behavior without explicit human
approval.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from beyo_manager.domain.shopify.enums import (
    ShopifyInventoryAdjustmentStatusEnum,
    ShopifyInventoryModeEnum,
    ShopifyProductSyncItemStatusEnum,
    ShopifyProductSyncOperationEnum,
    ShopifyProductSyncStageEnum,
)
from beyo_manager.services.infra.shopify import inventory_client, product_sync_client
from beyo_manager.services.tasks.shopify import _inventory_sync
from beyo_manager.services.tasks.shopify import _product_sync_orchestrator as orchestrator


FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY = """
query FindProductVariantsByIdentity($searchQuery: String!, $first: Int!) {
  productVariants(first: $first, query: $searchQuery) {
    edges {
      node {
        id
        sku
        barcode
        product {
          id
          status
        }
        inventoryItem {
          id
        }
      }
    }
  }
}
""".rstrip()

FIND_PRODUCT_BY_OPERATION_TAG_QUERY = """
query FindProductByOperationTag($searchQuery: String!, $first: Int!) {
  products(first: $first, query: $searchQuery) {
    nodes {
      id
      variants(first: 1) {
        nodes {
          id
          inventoryItem {
            id
          }
        }
      }
    }
  }
}
""".rstrip()

CREATE_PRODUCT_MUTATION = """
mutation CreateProduct($product: ProductCreateInput!) {
  productCreate(product: $product) {
    product {
      id
      status
      variants(first: 1) {
        edges {
          node {
            id
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
""".rstrip()

UPDATE_PRODUCT_MUTATION = """
mutation UpdateProduct($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
""".rstrip()

BULK_UPDATE_VARIANT_MUTATION = """
mutation BulkUpdateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants {
      id
      barcode
      inventoryItem {
        id
        sku
      }
    }
    userErrors {
      field
      message
    }
  }
}
""".rstrip()

SET_METAFIELDS_MUTATION = """
mutation SetMetafields($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      key
      namespace
    }
    userErrors {
      field
      message
    }
  }
}
""".rstrip()

GET_SHOP_LOCATIONS_QUERY = """
query GetShopLocations($first: Int!, $after: String, $includeInactive: Boolean!) {
  locations(first: $first, after: $after, includeInactive: $includeInactive) {
    edges {
      node {
        id
        name
        isActive
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".rstrip()

RESOLVE_INVENTORY_ITEM_STATE_QUERY = """
query ResolveInventoryItemState($inventoryItemId: ID!, $locationId: ID!) {
  inventoryItem(id: $inventoryItemId) {
    id
    tracked
    inventoryLevel(locationId: $locationId) {
      id
      quantities(names: ["available", "on_hand"]) {
        name
        quantity
      }
    }
  }
}
""".rstrip()

ADJUST_INVENTORY_MUTATION = """
mutation AdjustInventoryQuantities(
  $input: InventoryAdjustQuantitiesInput!
) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      referenceDocumentUri
    }
    userErrors {
      field
      message
      code
    }
  }
}
""".rstrip()


GraphQLCall = tuple[str, str, dict]


@dataclass(frozen=True)
class CharacterisationCase:
    payload: dict
    expected_operation: ShopifyProductSyncOperationEnum
    expected_calls: list[GraphQLCall]


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


@pytest.fixture
def create_path_case() -> CharacterisationCase:
    product = {
        "title": "Create Chair",
        "descriptionHtml": "Create description",
        "status": "UNLISTED",
        "tags": ["characterisation", "create"],
        "productType": "Chair",
    }
    variant = {
        "price": "99.00",
        "inventoryItem": {
            "sku": "SKU-CREATE",
            "measurement": {
                "weight": {
                    "value": 1.2,
                    "unit": "KILOGRAMS",
                }
            },
        },
    }
    return CharacterisationCase(
        payload={"product": product, "variant": variant, "metafields": []},
        expected_operation=ShopifyProductSyncOperationEnum.CREATE,
        expected_calls=[
            (
                "find_product_by_operation_tag",
                FIND_PRODUCT_BY_OPERATION_TAG_QUERY,
                {
                    "searchQuery": (
                        'tag:"managerbeyo-sync-shpsi_characterisation"'
                    ),
                    "first": 2,
                },
            ),
            (
                "find_product_variants_by_sku",
                FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
                {"searchQuery": 'sku:"SKU-CREATE"', "first": 10},
            ),
            (
                "create_shopify_product",
                CREATE_PRODUCT_MUTATION,
                {
                    "product": {
                        **product,
                        "tags": [
                            *product["tags"],
                            "managerbeyo-sync-shpsi_characterisation",
                        ],
                    }
                },
            ),
            (
                "create_shopify_product_variant_update",
                BULK_UPDATE_VARIANT_MUTATION,
                {
                    "productId": "gid://shopify/Product/100",
                    "variants": [
                        {
                            "id": "gid://shopify/ProductVariant/101",
                            **variant,
                        }
                    ],
                },
            ),
        ],
    )


@pytest.fixture
def update_path_case() -> CharacterisationCase:
    product = {
        "title": "Update Chair",
        "status": "UNLISTED",
        "tags": ["characterisation", "update"],
    }
    variant = {
        "price": "149.00",
        "inventoryItem": {"sku": "SKU-UPDATE"},
    }
    return CharacterisationCase(
        payload={"product": product, "variant": variant, "metafields": []},
        expected_operation=ShopifyProductSyncOperationEnum.UPDATE,
        expected_calls=[
            (
                "find_product_by_operation_tag",
                FIND_PRODUCT_BY_OPERATION_TAG_QUERY,
                {
                    "searchQuery": (
                        'tag:"managerbeyo-sync-shpsi_characterisation"'
                    ),
                    "first": 2,
                },
            ),
            (
                "find_product_variants_by_sku",
                FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
                {"searchQuery": 'sku:"SKU-UPDATE"', "first": 10},
            ),
            (
                "update_shopify_product",
                UPDATE_PRODUCT_MUTATION,
                {
                    "product": {
                        "id": "gid://shopify/Product/200",
                        **product,
                    }
                },
            ),
            (
                "update_shopify_product_variant_update",
                BULK_UPDATE_VARIANT_MUTATION,
                {
                    "productId": "gid://shopify/Product/200",
                    "variants": [
                        {
                            "id": "gid://shopify/ProductVariant/201",
                            **variant,
                        }
                    ],
                },
            ),
        ],
    )


@pytest.fixture
def metafields_case() -> CharacterisationCase:
    product = {
        "title": "Metafield Chair",
        "status": "UNLISTED",
    }
    variant = {
        "price": "199.00",
        "inventoryItem": {"sku": "SKU-METAFIELDS"},
    }
    metafields = [
        {
            "key": "quantity",
            "type": "number_integer",
            "value": "6",
        },
        {
            "key": "collection",
            "type": "single_line_text_field",
            "value": "dining",
        },
    ]
    return CharacterisationCase(
        payload={
            "product": product,
            "variant": variant,
            "metafields": metafields,
        },
        expected_operation=ShopifyProductSyncOperationEnum.CREATE,
        expected_calls=[
            (
                "find_product_by_operation_tag",
                FIND_PRODUCT_BY_OPERATION_TAG_QUERY,
                {
                    "searchQuery": (
                        'tag:"managerbeyo-sync-shpsi_characterisation"'
                    ),
                    "first": 2,
                },
            ),
            (
                "find_product_variants_by_sku",
                FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
                {"searchQuery": 'sku:"SKU-METAFIELDS"', "first": 10},
            ),
            (
                "create_shopify_product",
                CREATE_PRODUCT_MUTATION,
                {
                    "product": {
                        **product,
                        "tags": [
                            "managerbeyo-sync-shpsi_characterisation",
                        ],
                    }
                },
            ),
            (
                "create_shopify_product_variant_update",
                BULK_UPDATE_VARIANT_MUTATION,
                {
                    "productId": "gid://shopify/Product/300",
                    "variants": [
                        {
                            "id": "gid://shopify/ProductVariant/301",
                            **variant,
                        }
                    ],
                },
            ),
            (
                "set_shopify_product_metafields",
                SET_METAFIELDS_MUTATION,
                {
                    "metafields": [
                        {
                            "ownerId": "gid://shopify/Product/300",
                            "namespace": "custom",
                            **metafield,
                        }
                        for metafield in metafields
                    ]
                },
            ),
        ],
    )


@pytest.fixture
def multi_location_additive_inventory_case() -> CharacterisationCase:
    product = {
        "title": "Inventory Chair",
        "status": "UNLISTED",
    }
    variant = {
        "price": "249.00",
        "inventoryItem": {"sku": "SKU-INVENTORY"},
    }
    location_1 = "gid://shopify/Location/501"
    location_2 = "gid://shopify/Location/502"
    inventory_item_id = "gid://shopify/InventoryItem/402"
    return CharacterisationCase(
        payload={
            "product": product,
            "variant": variant,
            "metafields": [],
            "inventory": {
                "adjustments": [
                    {"location_id": location_1, "quantity_to_add": 3},
                    {"location_id": location_2, "quantity_to_add": 2},
                ]
            },
        },
        expected_operation=ShopifyProductSyncOperationEnum.CREATE,
        expected_calls=[
            (
                "find_product_by_operation_tag",
                FIND_PRODUCT_BY_OPERATION_TAG_QUERY,
                {
                    "searchQuery": (
                        'tag:"managerbeyo-sync-shpsi_characterisation"'
                    ),
                    "first": 2,
                },
            ),
            (
                "find_product_variants_by_sku",
                FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
                {"searchQuery": 'sku:"SKU-INVENTORY"', "first": 10},
            ),
            (
                "create_shopify_product",
                CREATE_PRODUCT_MUTATION,
                {
                    "product": {
                        **product,
                        "tags": [
                            "managerbeyo-sync-shpsi_characterisation",
                        ],
                    }
                },
            ),
            (
                "create_shopify_product_variant_update",
                BULK_UPDATE_VARIANT_MUTATION,
                {
                    "productId": "gid://shopify/Product/400",
                    "variants": [
                        {
                            "id": "gid://shopify/ProductVariant/401",
                            **variant,
                        }
                    ],
                },
            ),
            (
                "fetch_shop_locations",
                GET_SHOP_LOCATIONS_QUERY,
                {
                    "first": 250,
                    "after": None,
                    "includeInactive": True,
                },
            ),
            (
                "resolve_inventory_item_state",
                RESOLVE_INVENTORY_ITEM_STATE_QUERY,
                {
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_1,
                },
            ),
            (
                "resolve_inventory_item_state",
                RESOLVE_INVENTORY_ITEM_STATE_QUERY,
                {
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_2,
                },
            ),
            (
                "adjust_inventory_quantities",
                ADJUST_INVENTORY_MUTATION,
                {
                    "input": {
                        "reason": "correction",
                        "name": "available",
                        "referenceDocumentUri": (
                            "managerbeyo://inventory-adjustment/"
                            "frontend-characterisation/501"
                        ),
                        "changes": [
                            {
                                "delta": 3,
                                "inventoryItemId": inventory_item_id,
                                "locationId": location_1,
                            },
                            {
                                "delta": 2,
                                "inventoryItemId": inventory_item_id,
                                "locationId": location_2,
                            },
                        ],
                    }
                },
            ),
        ],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_path_emits_exact_graphql(
    monkeypatch,
    create_path_case: CharacterisationCase,
) -> None:
    await _assert_exact_graphql(monkeypatch, create_path_case)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_path_emits_exact_graphql(
    monkeypatch,
    update_path_case: CharacterisationCase,
) -> None:
    await _assert_exact_graphql(monkeypatch, update_path_case)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_two_metafields_emit_exact_graphql(
    monkeypatch,
    metafields_case: CharacterisationCase,
) -> None:
    await _assert_exact_graphql(monkeypatch, metafields_case)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multi_location_additive_inventory_emits_exact_graphql(
    monkeypatch,
    multi_location_additive_inventory_case: CharacterisationCase,
) -> None:
    await _assert_exact_graphql(monkeypatch, multi_location_additive_inventory_case)


async def _assert_exact_graphql(
    monkeypatch,
    case: CharacterisationCase,
) -> None:
    calls: list[GraphQLCall] = []

    async def _record_graphql(
        *,
        query: str,
        variables: dict,
        operation_name: str,
        **_kwargs,
    ) -> dict:
        calls.append((operation_name, query.rstrip(), deepcopy(variables)))
        return _graphql_response(operation_name, variables)

    ledger_number = 0

    async def _claim_ledger_row(*_args, adjustment: dict, **_kwargs) -> SimpleNamespace:
        nonlocal ledger_number
        ledger_number += 1
        location_suffix = adjustment["location_id"].rsplit("/", 1)[-1]
        return SimpleNamespace(
            client_id=f"shpia_{ledger_number}",
            requested_delta=adjustment["quantity_to_add"],
            status=ShopifyInventoryAdjustmentStatusEnum.PENDING,
            baseline_available=None,
            applied_at=None,
            shopify_error_code=None,
            reference_uri=(
                "managerbeyo://inventory-adjustment/"
                f"frontend-characterisation/{location_suffix}"
            ),
        )

    monkeypatch.setattr(product_sync_client, "execute_shopify_graphql", _record_graphql)
    monkeypatch.setattr(inventory_client, "execute_shopify_graphql", _record_graphql)
    monkeypatch.setattr(_inventory_sync, "_claim_ledger_row", _claim_ledger_row)

    sync_item = SimpleNamespace(
        client_id="shpsi_characterisation",
        workspace_id="ws_characterisation",
        shop_integration_id="shsi_characterisation",
        frontend_client_id="frontend-characterisation",
        created_by_id="usr_characterisation",
        normalized_payload_json=deepcopy(case.payload),
        status=ShopifyProductSyncItemStatusEnum.PENDING,
        # Both are NOT NULL with server defaults on the real model, so the stand-in must
        # carry them — the orchestrator reads them directly rather than via getattr.
        inventory_mode=ShopifyInventoryModeEnum.ADD,
        stage=ShopifyProductSyncStageEnum.QUEUED,
        requested_operation=None,
        shopify_product_id=None,
        shopify_variant_id=None,
        shopify_inventory_item_id=None,
        inventory_result_json=None,
        error_code=None,
        error_message=None,
    )
    shop = SimpleNamespace(
        client_id="shsi_characterisation",
        shop_domain="characterisation.myshopify.com",
        access_token_encrypted="encrypted-characterisation-token",
        granted_scopes=("read_locations", "write_inventory"),
    )

    await orchestrator.sync_one_product_sync_item(
        _FakeSession(),
        sync_item=sync_item,
        shop=shop,
    )

    assert sync_item.status == ShopifyProductSyncItemStatusEnum.SUCCEEDED
    assert sync_item.requested_operation == case.expected_operation
    assert calls == case.expected_calls


def _graphql_response(operation_name: str, variables: dict) -> dict:
    if operation_name == "find_product_by_operation_tag":
        return {"products": {"nodes": []}}

    if operation_name == "find_product_variants_by_sku":
        if variables["searchQuery"] == 'sku:"SKU-UPDATE"':
            return {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/201",
                                "sku": "SKU-UPDATE",
                                "barcode": None,
                                "product": {
                                    "id": "gid://shopify/Product/200",
                                    "status": "UNLISTED",
                                },
                                "inventoryItem": {
                                    "id": "gid://shopify/InventoryItem/202",
                                },
                            }
                        }
                    ]
                }
            }
        return {"productVariants": {"edges": []}}

    if operation_name == "create_shopify_product":
        product_ids = {
            "Create Chair": ("100", "101"),
            "Metafield Chair": ("300", "301"),
            "Inventory Chair": ("400", "401"),
        }
        product_id, variant_id = product_ids[variables["product"]["title"]]
        return {
            "productCreate": {
                "product": {
                    "id": f"gid://shopify/Product/{product_id}",
                    "status": "UNLISTED",
                    "variants": {
                        "edges": [
                            {
                                "node": {
                                    "id": (
                                        "gid://shopify/ProductVariant/"
                                        f"{variant_id}"
                                    )
                                }
                            }
                        ]
                    },
                },
                "userErrors": [],
            }
        }

    if operation_name == "update_shopify_product":
        return {
            "productUpdate": {
                "product": {
                    "id": variables["product"]["id"],
                    "status": "UNLISTED",
                },
                "userErrors": [],
            }
        }

    if operation_name.endswith("_product_variant_update"):
        inventory_ids = {
            "gid://shopify/Product/100": "102",
            "gid://shopify/Product/200": "202",
            "gid://shopify/Product/300": "302",
            "gid://shopify/Product/400": "402",
        }
        variant = variables["variants"][0]
        return {
            "productVariantsBulkUpdate": {
                "productVariants": [
                    {
                        "id": variant["id"],
                        "barcode": variant.get("barcode"),
                        "inventoryItem": {
                            "id": (
                                "gid://shopify/InventoryItem/"
                                f"{inventory_ids[variables['productId']]}"
                            ),
                            "sku": (variant.get("inventoryItem") or {}).get("sku"),
                        },
                    }
                ],
                "userErrors": [],
            }
        }

    if operation_name == "set_shopify_product_metafields":
        return {
            "metafieldsSet": {
                "metafields": [
                    {
                        "id": f"gid://shopify/Metafield/{index}",
                        "key": metafield["key"],
                        "namespace": metafield["namespace"],
                    }
                    for index, metafield in enumerate(
                        variables["metafields"],
                        start=1,
                    )
                ],
                "userErrors": [],
            }
        }

    if operation_name == "fetch_shop_locations":
        return {
            "locations": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Location/501",
                            "name": "Stockholm",
                            "isActive": True,
                        }
                    },
                    {
                        "node": {
                            "id": "gid://shopify/Location/502",
                            "name": "Gothenburg",
                            "isActive": True,
                        }
                    },
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
            }
        }

    if operation_name == "resolve_inventory_item_state":
        return {
            "inventoryItem": {
                "id": variables["inventoryItemId"],
                "tracked": True,
                "inventoryLevel": {
                    "id": "gid://shopify/InventoryLevel/1",
                    "quantities": [
                        {"name": "available", "quantity": 5},
                        {"name": "on_hand", "quantity": 5},
                    ],
                },
            }
        }

    if operation_name == "adjust_inventory_quantities":
        return {
            "inventoryAdjustQuantities": {
                "inventoryAdjustmentGroup": {
                    "referenceDocumentUri": variables["input"][
                        "referenceDocumentUri"
                    ],
                },
                "userErrors": [],
            }
        }

    raise AssertionError(f"Unexpected GraphQL operation: {operation_name}")
