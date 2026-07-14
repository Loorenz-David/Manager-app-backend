from __future__ import annotations

from dataclasses import dataclass

from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql

SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE = "PRODUCT"
SEARCH_RESULTS_LIMIT = 20
SHOPIFY_METAFIELD_DEFINITION_PAGE_SIZE = 100

GET_METAFIELD_DEFINITION_BY_ID_QUERY = """
query GetMetafieldDefinition($id: ID!) {
  node(id: $id) {
    id
    ... on MetafieldDefinition {
      id
      name
      namespace
      key
      description
      ownerType
      type { name }
      validations { name value }
    }
  }
}
"""

GET_METAFIELD_DEFINITIONS_BY_IDS_QUERY = """
query GetMetafieldDefinitions($ids: [ID!]!) {
  nodes(ids: $ids) {
    id
    ... on MetafieldDefinition {
      id
      name
      namespace
      key
      description
      ownerType
      type { name }
      validations { name value }
    }
  }
}
"""

LIST_PRODUCT_METAFIELD_DEFINITIONS_QUERY = """
query ListProductMetafieldDefinitions($ownerType: MetafieldOwnerType!, $first: Int!, $after: String) {
  metafieldDefinitions(ownerType: $ownerType, first: $first, after: $after) {
    nodes {
      id
      name
      namespace
      key
      description
      ownerType
      type { name }
      validations { name value }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


@dataclass(frozen=True)
class ShopifyMetafieldDefinitionPage:
    nodes: list[dict]
    has_next_page: bool
    end_cursor: str | None


@dataclass(frozen=True)
class ShopifyMetafieldDefinitionSearchPage:
    nodes: list[dict]
    offset: int
    limit: int
    has_more: bool


async def fetch_shopify_metafield_definition_by_id(
    *, shop_domain: str, access_token_encrypted: str, definition_id: str
) -> dict | None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=GET_METAFIELD_DEFINITION_BY_ID_QUERY,
        variables={"id": definition_id},
        operation_name="GetMetafieldDefinition",
    )
    node = data.get("node")
    return node if isinstance(node, dict) else None


async def fetch_shopify_metafield_definitions_by_ids(
    *, shop_domain: str, access_token_encrypted: str, definition_ids: list[str]
) -> dict[str, dict | None]:
    result: dict[str, dict | None] = {
        definition_id: None for definition_id in definition_ids
    }
    if not definition_ids:
        return result

    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=GET_METAFIELD_DEFINITIONS_BY_IDS_QUERY,
        variables={"ids": definition_ids},
        operation_name="GetMetafieldDefinitions",
    )
    for node in data.get("nodes") or []:
        if (
            isinstance(node, dict)
            and isinstance(node.get("id"), str)
            and node["id"] in result
        ):
            result[node["id"]] = node
    return result


async def fetch_shopify_product_metafield_definitions_page(
    *, shop_domain: str, access_token_encrypted: str, first: int, after: str | None
) -> ShopifyMetafieldDefinitionPage:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=LIST_PRODUCT_METAFIELD_DEFINITIONS_QUERY,
        variables={
            "ownerType": SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE,
            "first": first,
            "after": after,
        },
        operation_name="ListProductMetafieldDefinitions",
    )
    connection = data.get("metafieldDefinitions") or {}
    page_info = connection.get("pageInfo") or {}
    return ShopifyMetafieldDefinitionPage(
        nodes=[
            node for node in connection.get("nodes") or [] if isinstance(node, dict)
        ],
        has_next_page=bool(page_info.get("hasNextPage")),
        end_cursor=page_info.get("endCursor")
        if isinstance(page_info.get("endCursor"), str)
        else None,
    )


async def search_shopify_metafield_definitions_by_name(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    search_term: str,
    result_limit: int = SEARCH_RESULTS_LIMIT,
) -> list[dict]:
    page = await search_shopify_metafield_definitions_by_name_page(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        search_term=search_term,
        offset=0,
        result_limit=result_limit,
    )
    return page.nodes


async def search_shopify_metafield_definitions_by_name_page(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    search_term: str,
    offset: int = 0,
    result_limit: int = SEARCH_RESULTS_LIMIT,
) -> ShopifyMetafieldDefinitionSearchPage:
    term = search_term.strip().casefold()
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if result_limit <= 0:
        return ShopifyMetafieldDefinitionSearchPage(
            nodes=[], offset=offset, limit=result_limit, has_more=False
        )

    matches: list[dict] = []
    after: str | None = None
    target_count = offset + result_limit
    while len(matches) <= target_count:
        page = await fetch_shopify_product_metafield_definitions_page(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            first=SHOPIFY_METAFIELD_DEFINITION_PAGE_SIZE,
            after=after,
        )
        for node in page.nodes:
            name = node.get("name")
            if isinstance(name, str) and (not term or term in name.casefold()):
                matches.append(node)
                if len(matches) > target_count:
                    break
        if len(matches) > target_count or not page.has_next_page or not page.end_cursor:
            break
        after = page.end_cursor
    return ShopifyMetafieldDefinitionSearchPage(
        nodes=matches[offset : offset + result_limit],
        offset=offset,
        limit=result_limit,
        has_more=len(matches) > target_count,
    )
