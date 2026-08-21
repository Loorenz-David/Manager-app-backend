from __future__ import annotations

from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql

GET_SHOP_QUERY = """
query GetShop {
  shop {
    name
  }
}
"""

GET_SHOP_CURRENCY_QUERY = """
query GetShopCurrency {
  shop {
    currencyCode
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


async def fetch_shopify_shop_currency(
    *,
    shop_domain: str,
    access_token_encrypted: str,
) -> str | None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=GET_SHOP_CURRENCY_QUERY,
        variables={},
        operation_name="get_shop_currency",
    )
    shop = data.get("shop") or {}
    currency_code = shop.get("currencyCode")
    if not isinstance(currency_code, str) or not currency_code.strip():
        return None
    return currency_code.strip().upper()
