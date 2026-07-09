from __future__ import annotations

from typing import Literal

from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql

IdentityType = Literal["sku", "barcode"]

_ORDERS_FIRST = 10
_LINE_ITEMS_FIRST = 20
_VARIANTS_FIRST = 5

FIND_VARIANTS_BY_BARCODE_QUERY = """
query FindVariantsByBarcode($searchQuery: String!, $first: Int!) {
  productVariants(first: $first, query: $searchQuery) {
    edges {
      node {
        id
        sku
        barcode
      }
    }
  }
}
"""

SEARCH_ORDERS_BY_SKU_QUERY = """
query SearchOrdersBySku($searchQuery: String!, $ordersFirst: Int!, $lineItemsFirst: Int!) {
  orders(first: $ordersFirst, query: $searchQuery, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        id
        name
        email
        phone
        customer {
          id
          displayName
          defaultEmailAddress {
            emailAddress
          }
          defaultPhoneNumber {
            phoneNumber
          }
          defaultAddress {
            firstName
            lastName
            address1
            address2
            city
            province
            provinceCode
            zip
            phone
            latitude
            longitude
          }
        }
        shippingAddress {
          firstName
          lastName
          address1
          address2
          city
          province
          provinceCode
          zip
          phone
          latitude
          longitude
        }
        billingAddress {
          firstName
          lastName
          address1
          address2
          city
          province
          provinceCode
          zip
          phone
          latitude
          longitude
        }
        lineItems(first: $lineItemsFirst) {
          edges {
            node {
              sku
              variant {
                id
                sku
                barcode
              }
            }
          }
        }
      }
    }
  }
}
"""


async def fetch_shopify_orders_by_product_identity(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    identity_type: IdentityType,
    identity_value: str,
) -> list[dict]:
    if identity_type == "sku":
        return await _search_orders_by_sku(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            sku=identity_value,
        )

    variants = await _find_variants_by_barcode(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        barcode=identity_value,
    )
    exact_variants = [variant for variant in variants if _clean_str(variant.get("barcode")) == _clean_str(identity_value)]
    variant_skus = []
    for variant in exact_variants:
        sku = _clean_str(variant.get("sku"))
        if sku and sku not in variant_skus:
            variant_skus.append(sku)

    if not variant_skus:
        return []

    order_nodes_by_id: dict[str, dict] = {}
    for sku in variant_skus:
        order_nodes = await _search_orders_by_sku(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            sku=sku,
        )
        for order_node in order_nodes:
            order_id = _clean_str(order_node.get("id"))
            if order_id is None:
                continue
            order_nodes_by_id.setdefault(order_id, order_node)
    return list(order_nodes_by_id.values())


async def _search_orders_by_sku(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    sku: str,
) -> list[dict]:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=SEARCH_ORDERS_BY_SKU_QUERY,
        variables={
            "searchQuery": f"sku:{_quote_shopify_search_term(sku)}",
            "ordersFirst": _ORDERS_FIRST,
            "lineItemsFirst": _LINE_ITEMS_FIRST,
        },
        operation_name="search_orders_by_sku",
    )
    edges = (data.get("orders") or {}).get("edges") or []
    return [((edge or {}).get("node") or {}) for edge in edges]


async def _find_variants_by_barcode(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    barcode: str,
) -> list[dict]:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=FIND_VARIANTS_BY_BARCODE_QUERY,
        variables={
            "searchQuery": f"barcode:{_quote_shopify_search_term(barcode)}",
            "first": _VARIANTS_FIRST,
        },
        operation_name="find_variants_by_barcode",
    )
    edges = (data.get("productVariants") or {}).get("edges") or []
    return [((edge or {}).get("node") or {}) for edge in edges]


def _quote_shopify_search_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
