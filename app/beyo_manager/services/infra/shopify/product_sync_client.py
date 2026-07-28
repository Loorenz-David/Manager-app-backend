from __future__ import annotations

from beyo_manager.services.infra.shopify.graphql_client import (
    execute_shopify_graphql,
    quote_shopify_search_term,
    raise_for_graphql_user_errors,
)
from beyo_manager.errors.external_service import ShopifyProductLookupAmbiguousError

IdentityType = str
_VARIANTS_FIRST = 10
_OPERATION_TAG_PRODUCTS_FIRST = 2

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
"""

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
"""

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
"""

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
"""

CREATE_PRODUCT_WITH_MEDIA_MUTATION = """
mutation CreateProduct($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $product, media: $media) {
    product {
      id
      status
      media(first: 1) {
        nodes {
          id
          status
        }
      }
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
"""

UPDATE_PRODUCT_WITH_MEDIA_MUTATION = """
mutation UpdateProduct($product: ProductUpdateInput!, $media: [CreateMediaInput!]) {
  productUpdate(product: $product, media: $media) {
    product {
      id
      status
      media(first: 1) {
        nodes {
          id
          status
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

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
"""

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
"""


async def find_product_variant_by_identity(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    sku: str | None,
    barcode: str | None,
) -> list[dict]:
    """Search by sku, falling back to barcode only if sku finds no exact match.

    Callers in this codebase always pass exactly one of sku/barcode (the other
    None) — _product_sync_orchestrator.py does its own sku-then-barcode
    sequencing at a higher level so it can act between the two lookups (e.g.
    to detect a conflicting identity match). The dual-identity fallback below
    remains a real, independently useful capability of this function — it is
    exercised directly by its own unit test — for any future caller that wants
    a single "resolve by either identity" call.
    """
    if sku is not None:
        sku_nodes = await _search_product_variants_by_identity(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            identity_type="sku",
            identity_value=sku,
        )
        if _has_exact_variant_match(sku_nodes, identity_key="sku", identity_value=sku) or barcode is None:
            return sku_nodes

    if barcode is None:
        return []

    return await _search_product_variants_by_identity(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        identity_type="barcode",
        identity_value=barcode,
    )


async def find_product_by_operation_tag(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    operation_tag: str,
) -> dict | None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=FIND_PRODUCT_BY_OPERATION_TAG_QUERY,
        variables={
            "searchQuery": f"tag:{quote_shopify_search_term(operation_tag)}",
            "first": _OPERATION_TAG_PRODUCTS_FIRST,
        },
        operation_name="find_product_by_operation_tag",
    )
    products = (data.get("products") or {}).get("nodes") or []
    if len(products) > 1:
        raise ShopifyProductLookupAmbiguousError(
            "Multiple Shopify products matched the same product-sync operation tag.",
            error_code="ambiguous_operation_tag",
        )
    if not products:
        return None

    product = products[0] or {}
    variants = (product.get("variants") or {}).get("nodes") or []
    variant = (variants[0] or {}) if variants else {}
    inventory_item = variant.get("inventoryItem") or {}
    return {
        "shopify_product_id": _required_id(
            product.get("id"),
            "Shopify product id missing from operation-tag match.",
        ),
        "shopify_variant_id": _required_id(
            variant.get("id"),
            "Shopify variant id missing from operation-tag match.",
        ),
        "shopify_inventory_item_id": _clean_str(inventory_item.get("id")),
    }


async def create_shopify_product(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    normalized_payload: dict,
    media: list[dict] | None = None,
    operation_tag: str | None = None,
) -> dict:
    variables = {
        "product": _product_input_with_operation_tag(
            normalized_payload["product"],
            operation_tag=operation_tag,
        )
    }
    query = CREATE_PRODUCT_MUTATION
    if media:
        variables["media"] = media
        query = CREATE_PRODUCT_WITH_MEDIA_MUTATION
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=query,
        variables=variables,
        operation_name="create_shopify_product",
    )
    response = data.get("productCreate") or {}
    raise_for_graphql_user_errors(
        user_errors=response.get("userErrors"),
        operation_name="create_shopify_product",
        shop_domain=shop_domain,
    )
    product = response.get("product") or {}
    product_id = _required_id(product.get("id"), "Shopify product id missing after create.")
    default_variant_edges = ((product.get("variants") or {}).get("edges") or [])
    default_variant = ((default_variant_edges[0] or {}).get("node") or {}) if default_variant_edges else {}
    variant_id = _required_id(default_variant.get("id"), "Shopify default variant id missing after create.")

    result = {
        "shopify_product_id": product_id,
        "shopify_variant_id": variant_id,
    }
    result.update(_media_result(product))
    return result


async def update_shopify_product(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    shopify_product_id: str,
    shopify_variant_id: str,
    normalized_payload: dict,
    fallback_inventory_item_id: str | None = None,
    media: list[dict] | None = None,
    operation_tag: str | None = None,
) -> dict:
    variables = {
        "product": {
            "id": shopify_product_id,
            **_product_input_with_operation_tag(
                normalized_payload["product"],
                operation_tag=operation_tag,
            ),
        }
    }
    query = UPDATE_PRODUCT_MUTATION
    if media:
        variables["media"] = media
        query = UPDATE_PRODUCT_WITH_MEDIA_MUTATION
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=query,
        variables=variables,
        operation_name="update_shopify_product",
    )
    response = data.get("productUpdate") or {}
    raise_for_graphql_user_errors(
        user_errors=response.get("userErrors"),
        operation_name="update_shopify_product",
        shop_domain=shop_domain,
    )

    result = {
        "shopify_product_id": shopify_product_id,
        "shopify_variant_id": shopify_variant_id,
    }
    if fallback_inventory_item_id is not None:
        result["shopify_inventory_item_id"] = fallback_inventory_item_id
    result.update(_media_result(response.get("product") or {}))
    return result


async def configure_shopify_product_variant(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    shopify_product_id: str,
    shopify_variant_id: str,
    normalized_payload: dict,
    operation_name: str,
) -> dict:
    updated_variant_id, inventory_item_id = await _bulk_update_variant(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        product_id=shopify_product_id,
        variant_payload={"id": shopify_variant_id, **normalized_payload["variant"]},
        operation_name=operation_name,
    )
    result = {"shopify_variant_id": updated_variant_id}
    if inventory_item_id is not None:
        result["shopify_inventory_item_id"] = inventory_item_id
    return result


async def set_shopify_product_metafields(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    shopify_product_id: str,
    metafields: list[dict],
) -> None:
    if not metafields:
        return

    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=SET_METAFIELDS_MUTATION,
        variables={
            "metafields": [
                {
                    "ownerId": shopify_product_id,
                    "namespace": "custom",
                    "key": metafield["key"],
                    "type": metafield["type"],
                    "value": metafield["value"],
                }
                for metafield in metafields
            ]
        },
        operation_name="set_shopify_product_metafields",
    )
    response = data.get("metafieldsSet") or {}
    raise_for_graphql_user_errors(
        user_errors=response.get("userErrors"),
        operation_name="set_shopify_product_metafields",
        shop_domain=shop_domain,
    )


async def _search_product_variants_by_identity(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    identity_type: IdentityType,
    identity_value: str,
) -> list[dict]:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
        variables={
            "searchQuery": f"{identity_type}:{quote_shopify_search_term(identity_value)}",
            "first": _VARIANTS_FIRST,
        },
        operation_name=f"find_product_variants_by_{identity_type}",
    )
    edges = (data.get("productVariants") or {}).get("edges") or []
    return [((edge or {}).get("node") or {}) for edge in edges]


async def _bulk_update_variant(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    product_id: str,
    variant_payload: dict,
    operation_name: str,
) -> tuple[str, str | None]:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=BULK_UPDATE_VARIANT_MUTATION,
        variables={
            "productId": product_id,
            "variants": [variant_payload],
        },
        operation_name=operation_name,
    )
    response = data.get("productVariantsBulkUpdate") or {}
    raise_for_graphql_user_errors(
        user_errors=response.get("userErrors"),
        operation_name=operation_name,
        shop_domain=shop_domain,
    )
    variants = response.get("productVariants") or []
    variant = (variants[0] or {}) if variants else {}
    updated_variant_id = _clean_str(variant.get("id"))
    inventory_item = variant.get("inventoryItem") or {}
    return (
        updated_variant_id or str(variant_payload["id"]),
        _clean_str(inventory_item.get("id")),
    )


def _has_exact_variant_match(variant_nodes: list[dict], *, identity_key: str, identity_value: str) -> bool:
    expected = _clean_str(identity_value)
    if expected is None:
        return False
    return any(_clean_str(variant.get(identity_key)) == expected for variant in variant_nodes)


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _required_id(value: object, message: str) -> str:
    cleaned = _clean_str(value)
    if cleaned is None:
        raise ValueError(message)
    return cleaned


def _product_input_with_operation_tag(
    product_input: dict,
    *,
    operation_tag: str | None,
) -> dict:
    if operation_tag is None:
        return product_input

    result = dict(product_input)
    raw_tags = product_input.get("tags")
    if isinstance(raw_tags, list):
        tags = list(raw_tags)
    elif isinstance(raw_tags, str) and raw_tags.strip():
        tags = [raw_tags]
    else:
        tags = []
    if operation_tag not in tags:
        tags.append(operation_tag)
    result["tags"] = tags
    return result


def _media_result(product: dict) -> dict:
    nodes = ((product.get("media") or {}).get("nodes") or [])
    media = (nodes[0] or {}) if nodes else {}
    media_id = _clean_str(media.get("id"))
    if media_id is None:
        return {}
    return {
        "shopify_media_id": media_id,
        "media_status": _clean_str(media.get("status")),
    }
