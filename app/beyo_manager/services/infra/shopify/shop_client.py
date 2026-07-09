from __future__ import annotations

from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql

GET_SHOP_QUERY = """
query GetShop {
  shop {
    name
  }
}
"""


async def fetch_shopify_shop_name(
    *,
    shop_domain: str,
    access_token_encrypted: str,
) -> str | None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=GET_SHOP_QUERY,
        variables={},
        operation_name="get_shop",
    )
    shop = data.get("shop") or {}
    name = shop.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return name.strip()
