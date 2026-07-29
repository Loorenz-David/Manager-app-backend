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
async def test_inventory_activation_starts_a_missing_level_at_zero(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_execute(**kwargs):
        calls.append(kwargs)
        return {"inventoryActivate": {"userErrors": []}}

    monkeypatch.setattr(inventory_client, "execute_shopify_graphql", fake_execute)

    await inventory_client.activate_inventory_at_location(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        inventory_item_id="gid://shopify/InventoryItem/1",
        location_id="gid://shopify/Location/1",
        idempotency_key="shpia_1",
    )
    assert calls[0]["variables"]["available"] == 0
    assert calls[0]["variables"]["idempotencyKey"] == "shpia_1"
    assert "@idempotent(key: $idempotencyKey)" in calls[0]["query"]
    assert not hasattr(inventory_client, "adjust_inventory_quantities")
    assert "inventoryAdjustQuantities" not in inventory_client.SET_INVENTORY_MUTATION


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_inventory_quantities_uses_idempotent_absolute_available_contract(
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_execute(**kwargs):
        captured.update(kwargs)
        return {"inventorySetQuantities": {"userErrors": []}}

    monkeypatch.setattr(inventory_client, "execute_shopify_graphql", fake_execute)

    await inventory_client.set_inventory_quantities(
        shop_domain="shop.myshopify.com",
        access_token_encrypted="encrypted-token",
        quantities=[
            {
                "inventory_item_id": "gid://shopify/InventoryItem/1",
                "location_id": "gid://shopify/Location/1",
                "quantity": 2,
            },
            {
                "inventory_item_id": "gid://shopify/InventoryItem/1",
                "location_id": "gid://shopify/Location/2",
                "quantity": 0,
            },
        ],
        reference_document_uri="managerbeyo://inventory-set/shpsi_1",
        idempotency_key="shopify-inventory-set:shpsi_1",
    )

    assert "@idempotent(key: $idempotencyKey)" in captured["query"]
    assert "ignoreCompareQuantity" not in captured["query"]
    assert "compareQuantity" not in captured["query"]
    assert captured["variables"]["idempotencyKey"] == "shopify-inventory-set:shpsi_1"
    assert captured["variables"]["input"]["name"] == "available"
    assert captured["variables"]["input"]["quantities"] == [
        {
            "inventoryItemId": "gid://shopify/InventoryItem/1",
            "locationId": "gid://shopify/Location/1",
            "quantity": 2,
            "changeFromQuantity": None,
        },
        {
            "inventoryItemId": "gid://shopify/InventoryItem/1",
            "locationId": "gid://shopify/Location/2",
            "quantity": 0,
            "changeFromQuantity": None,
        },
    ]
