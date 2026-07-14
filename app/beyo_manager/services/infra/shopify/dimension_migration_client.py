"""Shopify GraphQL adapter used only by the dimension migration script."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from beyo_manager.errors.external_service import ShopifyGraphQLRetryableError
from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql
from beyo_manager.services.infra.shopify.metafield_definition_client import (
    fetch_shopify_product_metafield_definitions_page,
)
from beyo_manager.services.infra.shopify.product_sync_client import SET_METAFIELDS_MUTATION

TARGET_TYPES = {
    "height_dimension": "dimension",
    "width_dimension": "dimension",
    "depth_dimension": "dimension",
    "extensions_quantity": "number_integer",
    "extension_dimension": "dimension",
}
MAX_MUTATION_ENTRIES = 25
MAX_ATTEMPTS = 5
RETRY_BASE_SECONDS = 1.0
RETRY_MAX_SECONDS = 30.0

PRODUCT_DIMENSION_PAGE_QUERY = """
query ProductDimensionPage(
  $first: Int!,
  $after: String,
  $sourceNamespace: String!,
  $sourceHeightKey: String!,
  $sourceWidthKey: String!,
  $sourceDepthKey: String!,
  $legacyExtensionQuantityKey: String!,
  $targetNamespace: String!,
  $targetHeightKey: String!,
  $targetWidthKey: String!,
  $targetDepthKey: String!,
  $targetExtensionsQuantityKey: String!,
  $targetExtensionDimensionKey: String!
) {
  products(first: $first, after: $after) {
    edges {
      node {
        id
        title
        handle
        status
        legacyDimensions: metafield(namespace: "custom", key: "dimensionss") { id value type }
        legacyHeight: metafield(namespace: $sourceNamespace, key: $sourceHeightKey) { value }
        legacyWidth: metafield(namespace: $sourceNamespace, key: $sourceWidthKey) { value }
        legacyDepth: metafield(namespace: $sourceNamespace, key: $sourceDepthKey) { value }
        legacyExtensionQuantity: metafield(namespace: $targetNamespace, key: $legacyExtensionQuantityKey) { value }
        existingHeight: metafield(namespace: $targetNamespace, key: $targetHeightKey) { value }
        existingWidth: metafield(namespace: $targetNamespace, key: $targetWidthKey) { value }
        existingDepth: metafield(namespace: $targetNamespace, key: $targetDepthKey) { value }
        existingExtensionsQuantity: metafield(namespace: $targetNamespace, key: $targetExtensionsQuantityKey) { value }
        existingExtensionDimension: metafield(namespace: $targetNamespace, key: $targetExtensionDimensionKey) { value }
        variants(first: 1) {
          edges { node { sku } }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

METAFIELDS_DELETE_MUTATION = """
mutation DeleteStaleDimensionMetafields($metafields: [MetafieldIdentifierInput!]!) {
  metafieldsDelete(metafields: $metafields) {
    deletedMetafields { key namespace ownerId }
    userErrors { field message }
  }
}
"""


@dataclass(frozen=True)
class ShopifyProductDimensionPage:
    products: list[dict]
    has_next_page: bool
    end_cursor: str | None


async def fetch_target_metafield_definitions(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    target_namespace: str,
    target_keys: Sequence[str],
) -> dict[str, dict | None]:
    wanted = set(target_keys)
    result: dict[str, dict | None] = {key: None for key in wanted}
    cursor: str | None = None
    while True:
        page = await _call_with_retry(
            lambda: fetch_shopify_product_metafield_definitions_page(
                shop_domain=shop_domain,
                access_token_encrypted=access_token_encrypted,
                first=100,
                after=cursor,
            ),
            operation_name="list_dimension_metafield_definitions",
        )
        for node in page.nodes:
            if (
                node.get("namespace") == target_namespace
                and node.get("key") in wanted
                and node.get("ownerType") == "PRODUCT"
            ):
                result[node["key"]] = _map_definition(node)
        if not page.has_next_page or not page.end_cursor:
            break
        cursor = page.end_cursor
    return result


def validate_target_metafield_definitions(
    definitions: dict[str, dict | None],
) -> list[str]:
    problems: list[str] = []
    for key, expected_type in TARGET_TYPES.items():
        definition = definitions.get(key)
        if definition is None:
            problems.append(f"missing_definition:{key}")
        elif definition.get("type") != expected_type:
            problems.append(f"wrong_type:{key}:{definition.get('type')}")
    return problems


async def fetch_products_page(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    source_namespace: str,
    source_keys: dict[str, str],
    target_namespace: str,
    target_keys: dict[str, str],
    first: int = 50,
    after: str | None = None,
) -> ShopifyProductDimensionPage:
    variables = {
        "first": first,
        "after": after,
        "sourceNamespace": source_namespace,
        "sourceHeightKey": source_keys["height"],
        "sourceWidthKey": source_keys["width"],
        "sourceDepthKey": source_keys["depth"],
        "legacyExtensionQuantityKey": "extension_quantity",
        "targetNamespace": target_namespace,
        "targetHeightKey": target_keys["height_dimension"],
        "targetWidthKey": target_keys["width_dimension"],
        "targetDepthKey": target_keys["depth_dimension"],
        "targetExtensionsQuantityKey": target_keys["extensions_quantity"],
        "targetExtensionDimensionKey": target_keys["extension_dimension"],
    }
    data = await _call_with_retry(
        lambda: execute_shopify_graphql(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            query=PRODUCT_DIMENSION_PAGE_QUERY,
            variables=variables,
            operation_name="list_shopify_products_for_dimension_migration",
        ),
        operation_name="list_shopify_products_for_dimension_migration",
    )
    connection = data.get("products") or {}
    page_info = connection.get("pageInfo") or {}
    products = [_map_product(edge.get("node")) for edge in connection.get("edges") or [] if isinstance(edge, dict) and isinstance(edge.get("node"), dict)]
    return ShopifyProductDimensionPage(
        products=products,
        has_next_page=bool(page_info.get("hasNextPage")),
        end_cursor=page_info.get("endCursor") if isinstance(page_info.get("endCursor"), str) else None,
    )


async def iter_product_dimensions(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    source_namespace: str,
    source_keys: dict[str, str],
    target_namespace: str,
    target_keys: dict[str, str],
    limit: int | None = None,
    start_after: str | None = None,
    initial_yielded: int = 0,
    on_page_complete: Callable[[str | None, int], Awaitable[None]] | None = None,
) -> AsyncIterator[dict]:
    cursor: str | None = start_after
    page_size = 50
    yielded = initial_yielded
    while limit is None or yielded < limit:
        try:
            page = await fetch_products_page(
                shop_domain=shop_domain,
                access_token_encrypted=access_token_encrypted,
                source_namespace=source_namespace,
                source_keys=source_keys,
                target_namespace=target_namespace,
                target_keys=target_keys,
                first=min(page_size, limit - yielded) if limit is not None else page_size,
                after=cursor,
            )
        except ShopifyGraphQLRetryableError as exc:
            if page_size <= 1 or exc.error_code not in {"max_cost_exceeded", "query_cost_exceeded"}:
                raise
            page_size = max(1, page_size // 2)
            continue
        for product in page.products:
            yield product
            yielded += 1
            if limit is not None and yielded >= limit:
                if on_page_complete is not None:
                    await on_page_complete(page.end_cursor, yielded)
                return
        if on_page_complete is not None:
            await on_page_complete(page.end_cursor, yielded)
        if not page.has_next_page or not page.end_cursor:
            return
        cursor = page.end_cursor


async def set_dimension_metafields_batch(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    target_namespace: str,
    mutations: Sequence[dict],
    start_offset: int = 0,
    on_batch_complete: Callable[[int], Awaitable[None]] | None = None,
) -> list[dict]:
    errors: list[dict] = []
    for offset in range(start_offset, len(mutations), MAX_MUTATION_ENTRIES):
        batch = list(mutations[offset : offset + MAX_MUTATION_ENTRIES])
        payload = [
            {
                "ownerId": mutation["product_gid"],
                "namespace": target_namespace,
                "key": mutation["key"],
                "type": mutation.get("type") or TARGET_TYPES[mutation["key"]],
                "value": mutation["value"],
            }
            for mutation in batch
        ]
        data = await _call_with_retry(
            lambda payload=payload: execute_shopify_graphql(
                shop_domain=shop_domain,
                access_token_encrypted=access_token_encrypted,
                query=SET_METAFIELDS_MUTATION,
                variables={"metafields": payload},
                operation_name="set_shopify_dimension_metafields",
            ),
            operation_name="set_shopify_dimension_metafields",
        )
        user_errors = ((data.get("metafieldsSet") or {}).get("userErrors") or [])
        errors.extend(_map_user_errors(user_errors, batch))
        if on_batch_complete is not None:
            await on_batch_complete(offset + len(batch))
    return errors


async def delete_stale_extension_dimension_batch(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    target_namespace: str,
    mutations: Sequence[dict],
    start_offset: int = 0,
    on_batch_complete: Callable[[int], Awaitable[None]] | None = None,
) -> list[dict]:
    errors: list[dict] = []
    for offset in range(start_offset, len(mutations), MAX_MUTATION_ENTRIES):
        batch = list(mutations[offset : offset + MAX_MUTATION_ENTRIES])
        identifiers = [
            {
                "ownerId": mutation["product_gid"],
                "namespace": target_namespace,
                "key": "extension_dimension",
            }
            for mutation in batch
        ]
        data = await _call_with_retry(
            lambda identifiers=identifiers: execute_shopify_graphql(
                shop_domain=shop_domain,
                access_token_encrypted=access_token_encrypted,
                query=METAFIELDS_DELETE_MUTATION,
                variables={"metafields": identifiers},
                operation_name="delete_stale_shopify_extension_dimensions",
            ),
            operation_name="delete_stale_shopify_extension_dimensions",
        )
        user_errors = ((data.get("metafieldsDelete") or {}).get("userErrors") or [])
        errors.extend(_map_user_errors(user_errors, batch))
        if on_batch_complete is not None:
            await on_batch_complete(offset + len(batch))
    return errors


async def _call_with_retry(
    operation: Callable[[], Awaitable[Any]],
    *,
    operation_name: str,
) -> Any:
    del operation_name  # kept in the helper contract for call-site observability/debugging
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await operation()
        except ShopifyGraphQLRetryableError:
            if attempt == MAX_ATTEMPTS:
                raise
            await asyncio.sleep(min(RETRY_BASE_SECONDS * (2 ** (attempt - 1)), RETRY_MAX_SECONDS))


def _map_definition(node: dict) -> dict:
    validations: dict[str, Decimal | None] = {"min": None, "max": None}
    for validation in node.get("validations") or []:
        if not isinstance(validation, dict):
            continue
        name = str(validation.get("name") or "").lower()
        if name not in validations:
            continue
        validations[name] = _to_decimal(validation.get("value"))
    return {
        "id": node.get("id"),
        "namespace": node.get("namespace"),
        "key": node.get("key"),
        "owner_type": node.get("ownerType"),
        "type": ((node.get("type") or {}).get("name") if isinstance(node.get("type"), dict) else node.get("type")),
        "validations": validations,
    }


def _map_product(node: dict) -> dict:
    variants = ((node.get("variants") or {}).get("edges") or [])
    first_variant = variants[0].get("node") if variants and isinstance(variants[0], dict) else {}
    return {
        "gid": node.get("id"),
        "title": node.get("title") or "",
        "handle": node.get("handle") or "",
        "status": node.get("status") or "",
        "sku": (first_variant or {}).get("sku"),
        "legacy": {
            "dimensions": _metafield_value(node.get("legacyDimensions")),
            "height": _metafield_value(node.get("legacyHeight")),
            "width": _metafield_value(node.get("legacyWidth")),
            "depth": _metafield_value(node.get("legacyDepth")),
            "extension_quantity": _metafield_value(node.get("legacyExtensionQuantity")),
        },
        "existing": {
            "height_dimension": _metafield_value(node.get("existingHeight")),
            "width_dimension": _metafield_value(node.get("existingWidth")),
            "depth_dimension": _metafield_value(node.get("existingDepth")),
            "extensions_quantity": _metafield_value(node.get("existingExtensionsQuantity")),
            "extension_dimension": _metafield_value(node.get("existingExtensionDimension")),
        },
    }


def _metafield_value(value: Any) -> str | None:
    if isinstance(value, dict) and isinstance(value.get("value"), str):
        return value["value"]
    return None


def _map_user_errors(user_errors: Sequence[dict], batch: Sequence[dict]) -> list[dict]:
    mapped: list[dict] = []
    for error in user_errors:
        if not isinstance(error, dict):
            continue
        index = _field_index(error.get("field"))
        source = batch[index] if index is not None and index < len(batch) else {}
        mapped.append(
            {
                "product_gid": source.get("product_gid"),
                "key": source.get("key", "extension_dimension"),
                "message": str(error.get("message") or "Shopify rejected the mutation."),
                "field": error.get("field"),
            }
        )
    return mapped


def _field_index(field: Any) -> int | None:
    values = field if isinstance(field, list) else []
    for value in values:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
