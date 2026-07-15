from __future__ import annotations

import logging

from beyo_manager.errors.external_service import ShopifyGraphQLNonRetryableError
from beyo_manager.services.infra.shopify.graphql_client import execute_shopify_graphql

logger = logging.getLogger(__name__)

_LOCATIONS_PAGE_SIZE = 250
_MAX_LOCATION_PAGES = 10


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
"""

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
"""

ENABLE_INVENTORY_TRACKING_MUTATION = """
mutation EnableInventoryTracking($inventoryItemId: ID!, $input: InventoryItemInput!) {
  inventoryItemUpdate(id: $inventoryItemId, input: $input) {
    inventoryItem {
      id
      tracked
    }
    userErrors {
      field
      message
    }
  }
}
"""

ACTIVATE_INVENTORY_MUTATION = """
mutation ActivateInventory(
  $inventoryItemId: ID!,
  $locationId: ID!,
  $available: Int!
) {
  inventoryActivate(
    inventoryItemId: $inventoryItemId,
    locationId: $locationId,
    available: $available
  ) {
    inventoryLevel {
      id
      quantities(names: ["available"]) {
        name
        quantity
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

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
"""


async def fetch_shop_locations(
    *,
    shop_domain: str,
    access_token_encrypted: str,
) -> list[dict]:
    locations: list[dict] = []
    cursor: str | None = None
    for _ in range(_MAX_LOCATION_PAGES):
        data = await execute_shopify_graphql(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            query=GET_SHOP_LOCATIONS_QUERY,
            variables={
                "first": _LOCATIONS_PAGE_SIZE,
                "after": cursor,
                "includeInactive": True,
            },
            operation_name="fetch_shop_locations",
        )
        connection = data.get("locations") or {}
        for edge in connection.get("edges") or []:
            node = (edge or {}).get("node") or {}
            location_id = node.get("id")
            if not isinstance(location_id, str) or not location_id:
                continue
            locations.append(
                {
                    "location_id": location_id,
                    "name": str(node.get("name") or ""),
                    "is_active": bool(node.get("isActive")),
                }
            )
        page_info = connection.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            return locations
        cursor = page_info.get("endCursor")
        if not isinstance(cursor, str) or not cursor:
            return locations
    raise ShopifyGraphQLNonRetryableError(
        "Shopify returned too many locations to process safely.",
        error_code="shopify_locations_pagination_limit",
    )


async def resolve_inventory_item_state(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    inventory_item_id: str,
    location_id: str,
) -> dict:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=RESOLVE_INVENTORY_ITEM_STATE_QUERY,
        variables={"inventoryItemId": inventory_item_id, "locationId": location_id},
        operation_name="resolve_inventory_item_state",
    )
    item = data.get("inventoryItem")
    if not isinstance(item, dict):
        raise ShopifyGraphQLNonRetryableError(
            "Shopify inventory item could not be resolved.",
            error_code="inventory_item_unresolved",
        )
    level = item.get("inventoryLevel")
    quantities_by_name: dict[str, int] = {}
    for quantity in (level or {}).get("quantities") or []:
        name = (quantity or {}).get("name")
        if isinstance(name, str):
            quantities_by_name[name] = int((quantity or {}).get("quantity") or 0)
    available = quantities_by_name.get("available", 0)
    on_hand = quantities_by_name.get("on_hand", 0)
    state = {
        "tracked": bool(item.get("tracked")),
        "level_exists": level is not None,
        "available": available,
        "on_hand": on_hand,
    }
    logger.info(
        "shopify_inventory_diag | resolved_state | inventory_item_id=%s location_id=%s "
        "tracked=%s level_present=%s available=%s on_hand=%s",
        inventory_item_id,
        location_id,
        state["tracked"],
        level is not None,
        available,
        on_hand,
    )
    return state


async def enable_inventory_tracking(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    inventory_item_id: str,
) -> None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=ENABLE_INVENTORY_TRACKING_MUTATION,
        variables={"inventoryItemId": inventory_item_id, "input": {"tracked": True}},
        operation_name="enable_inventory_tracking",
    )
    response = data.get("inventoryItemUpdate") or {}
    returned_tracked = ((response.get("inventoryItem") or {}).get("tracked"))
    logger.info(
        "shopify_inventory_diag | enable_tracking_response | inventory_item_id=%s returned_tracked=%s user_error_count=%s",
        inventory_item_id,
        returned_tracked,
        len(response.get("userErrors") or []),
    )
    _raise_inventory_user_errors(response.get("userErrors"), "enable_inventory_tracking")
    if returned_tracked is not True:
        logger.warning(
            "shopify_inventory_diag | enable_tracking_not_confirmed | inventory_item_id=%s returned_tracked=%s "
            "(Shopify accepted the mutation but did not report tracked=true)",
            inventory_item_id,
            returned_tracked,
        )


async def activate_inventory_at_location(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    inventory_item_id: str,
    location_id: str,
    idempotency_key: str,
) -> None:
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=ACTIVATE_INVENTORY_MUTATION,
        variables={
            "inventoryItemId": inventory_item_id,
            "locationId": location_id,
            "available": 0,
        },
        operation_name="activate_inventory_at_location",
    )
    response = data.get("inventoryActivate") or {}
    logger.info(
        "shopify_inventory_diag | activate_response | inventory_item_id=%s location_id=%s "
        "level_present=%s user_error_count=%s",
        inventory_item_id,
        location_id,
        response.get("inventoryLevel") is not None,
        len(response.get("userErrors") or []),
    )
    _raise_inventory_user_errors(response.get("userErrors"), "activate_inventory_at_location")


async def adjust_inventory_quantities(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    changes: list[dict],
    reference_document_uri: str,
    idempotency_key: str,
) -> None:
    adjust_quantity_name = "available"
    logger.info(
        "shopify_inventory_diag | adjust_request | quantity_name=%s change_count=%s changes=%s",
        adjust_quantity_name,
        len(changes),
        [
            {
                "delta": change["quantity_to_add"],
                "location_id": change["location_id"],
            }
            for change in changes
        ],
    )
    data = await execute_shopify_graphql(
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
        query=ADJUST_INVENTORY_MUTATION,
        variables={
            "input": {
                "reason": "correction",
                "name": adjust_quantity_name,
                "referenceDocumentUri": reference_document_uri,
                "changes": [
                    {
                        "delta": change["quantity_to_add"],
                        "inventoryItemId": change["inventory_item_id"],
                        "locationId": change["location_id"],
                    }
                    for change in changes
                ],
            },
        },
        operation_name="adjust_inventory_quantities",
    )
    response = data.get("inventoryAdjustQuantities") or {}
    logger.info(
        "shopify_inventory_diag | adjust_response | quantity_name=%s reference_uri=%s "
        "adjustment_group_present=%s user_error_count=%s",
        adjust_quantity_name,
        reference_document_uri,
        response.get("inventoryAdjustmentGroup") is not None,
        len(response.get("userErrors") or []),
    )
    _raise_inventory_user_errors(response.get("userErrors"), "adjust_inventory_quantities")


def _raise_inventory_user_errors(user_errors: list[dict] | None, operation_name: str) -> None:
    if not user_errors:
        return
    first_error = user_errors[0] or {}
    code = str(first_error.get("code") or "graphql_user_errors").lower()
    logger.warning(
        "shopify_inventory | user_error | operation=%s error_code=%s error_count=%s errors=%s",
        operation_name,
        code,
        len(user_errors),
        [
            {
                "field": (error or {}).get("field"),
                "message": str((error or {}).get("message") or "")[:300],
                "code": (error or {}).get("code"),
            }
            for error in user_errors
            if isinstance(error, dict)
        ],
    )
    raise ShopifyGraphQLNonRetryableError(
        "Shopify inventory operation returned a user error.",
        error_code=code,
    )
