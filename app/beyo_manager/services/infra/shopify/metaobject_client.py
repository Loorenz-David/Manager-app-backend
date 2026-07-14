from __future__ import annotations

from dataclasses import dataclass

from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql

SHOPIFY_METAOBJECT_PAGE_SIZE = 250
SHOPIFY_METAOBJECT_ENTRY_MAX = 1000

GET_METAOBJECT_DEFINITIONS_BY_IDS_QUERY = """
query GetMetaobjectDefinitions($ids: [ID!]!) {
  nodes(ids: $ids) {
    id
    ... on MetaobjectDefinition {
      id
      name
      type
      displayNameKey
    }
  }
}
"""

LIST_METAOBJECTS_BY_TYPE_QUERY = """
query ListMetaobjectsByType($type: String!, $first: Int!, $after: String) {
  metaobjects(type: $type, first: $first, after: $after) {
    nodes {
      id
      handle
      displayName
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


@dataclass(frozen=True)
class ShopifyMetaobjectEntriesResult:
    options: list[dict]
    has_more: bool
    end_cursor: str | None
    truncated: bool


async def fetch_shopify_metaobject_definitions_by_ids(
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
        query=GET_METAOBJECT_DEFINITIONS_BY_IDS_QUERY,
        variables={"ids": definition_ids},
        operation_name="GetMetaobjectDefinitions",
    )
    for node in data.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        definition_id = node.get("id")
        if (
            isinstance(definition_id, str)
            and definition_id in result
            and isinstance(node.get("type"), str)
        ):
            result[definition_id] = node
    return result


async def fetch_shopify_metaobject_entries_by_type(
    *, shop_domain: str, access_token_encrypted: str, metaobject_type: str
) -> ShopifyMetaobjectEntriesResult:
    options: list[dict] = []
    seen_ids: set[str] = set()
    after: str | None = None
    last_cursor: str | None = None

    while len(options) < SHOPIFY_METAOBJECT_ENTRY_MAX:
        first = min(
            SHOPIFY_METAOBJECT_PAGE_SIZE,
            SHOPIFY_METAOBJECT_ENTRY_MAX - len(options),
        )
        data = await execute_shopify_graphql(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            query=LIST_METAOBJECTS_BY_TYPE_QUERY,
            variables={"type": metaobject_type, "first": first, "after": after},
            operation_name="ListMetaobjectsByType",
        )
        connection = data.get("metaobjects") or {}
        for node in connection.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            entry_id = node.get("id")
            if not isinstance(entry_id, str) or entry_id in seen_ids:
                continue
            seen_ids.add(entry_id)
            option = {
                "id": entry_id,
                "value": entry_id,
                "label": node.get("displayName")
                if isinstance(node.get("displayName"), str)
                else "",
            }
            if isinstance(node.get("handle"), str):
                option["handle"] = node["handle"]
            options.append(option)

        page_info = connection.get("pageInfo") or {}
        has_next_page = bool(page_info.get("hasNextPage"))
        end_cursor = page_info.get("endCursor")
        last_cursor = end_cursor if isinstance(end_cursor, str) else None
        if not has_next_page:
            return ShopifyMetaobjectEntriesResult(
                options=options,
                has_more=False,
                end_cursor=None,
                truncated=False,
            )
        if not last_cursor:
            return ShopifyMetaobjectEntriesResult(
                options=options,
                has_more=True,
                end_cursor=None,
                truncated=True,
            )
        after = last_cursor

    return ShopifyMetaobjectEntriesResult(
        options=options,
        has_more=True,
        end_cursor=last_cursor,
        truncated=True,
    )
