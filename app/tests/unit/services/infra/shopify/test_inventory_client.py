from __future__ import annotations

import pytest

from beyo_manager.services.infra.shopify import inventory_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_shop_locations_paginates_and_includes_inactive(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_execute(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {
                "locations": {
                    "edges": [{"node": {"id": "gid://shopify/Location/1", "name": "A", "isActive": True}}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                }
            }
        return {
            "locations": {
                "edges": [{"node": {"id": "gid://shopify/Location/2", "name": "B", "isActive": False}}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

    monkeypatch.setattr(inventory_client, "execute_shopify_graphql", fake_execute)

    result = await inventory_client.fetch_shop_locations(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
    )

    assert result == [
        {"location_id": "gid://shopify/Location/1", "name": "A", "is_active": True},
        {"location_id": "gid://shopify/Location/2", "name": "B", "is_active": False},
    ]
    assert calls[0]["variables"]["includeInactive"] is True
    assert calls[1]["variables"]["after"] == "cursor-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inventory_mutations_keep_activation_at_zero_and_batch_positive_deltas(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_execute(**kwargs):
        calls.append(kwargs)
        if kwargs["operation_name"] == "activate_inventory_at_location":
            return {"inventoryActivate": {"userErrors": []}}
        return {"inventoryAdjustQuantities": {"userErrors": []}}

    monkeypatch.setattr(inventory_client, "execute_shopify_graphql", fake_execute)

    await inventory_client.activate_inventory_at_location(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        inventory_item_id="gid://shopify/InventoryItem/1",
        location_id="gid://shopify/Location/1",
        idempotency_key="shpia_1",
    )
    await inventory_client.adjust_inventory_quantities(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        changes=[
            {
                "inventory_item_id": "gid://shopify/InventoryItem/1",
                "location_id": "gid://shopify/Location/1",
                "quantity_to_add": 3,
            },
            {
                "inventory_item_id": "gid://shopify/InventoryItem/1",
                "location_id": "gid://shopify/Location/2",
                "quantity_to_add": 2,
            },
        ],
        reference_document_uri="managerbeyo://inventory-adjustment/shpia_1/1",
        idempotency_key="shpia_1:shpia_2",
    )

    assert calls[0]["variables"]["available"] == 0
    assert calls[1]["variables"]["input"]["changes"] == [
        {
            "delta": 3,
            "inventoryItemId": "gid://shopify/InventoryItem/1",
            "locationId": "gid://shopify/Location/1",
        },
        {
            "delta": 2,
            "inventoryItemId": "gid://shopify/InventoryItem/1",
            "locationId": "gid://shopify/Location/2",
        },
    ]
