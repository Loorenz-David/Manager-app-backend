"""The create-task route must forward the `shopify_preorder` section to the command.

`route_create_task` passes `body.model_dump(exclude_unset=True)` to `create_task`, so any key the
router's `_CreateTaskBody` does not declare is silently dropped by Pydantic — the command never
sees it and the pre-order is never enqueued, while the request still returns 200.

That is exactly what happened on 2026-07-27: the service-layer request model and the command were
both correct, the integration tests passed because they call `create_task` directly, and the
feature was nonetheless unreachable over HTTP. These tests cover the router boundary specifically.
"""

import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import tasks as tasks_router


def _preorder_payload() -> dict:
    return {
        "shop_integration_id": "shpint_1",
        "product": {
            "title": "PRE_ORDER-2",
            "sku": "PRE_ORDER-2",
            "price": "2000.00",
        },
        "inventory": [
            {"location_id": "gid://shopify/Location/90742587722", "quantity": 1},
        ],
    }


async def _call_route(body: tasks_router._CreateTaskBody, monkeypatch) -> dict:
    captured: dict = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"client_id": "tsk_1"}, error=None)

    monkeypatch.setattr(tasks_router, "run_service", _fake_run_service)

    result = await tasks_router.route_create_task(
        body=body,
        claims={"user_id": "usr_1", "role_name": "seller", "workspace_id": "ws_1"},
        session=object(),
    )
    captured["status_code"] = result.status_code
    captured["payload"] = json.loads(result.body)
    return captured


@pytest.mark.unit
async def test_shopify_preorder_section_reaches_the_command(monkeypatch) -> None:
    body = tasks_router._CreateTaskBody(
        task_type="pre_order",
        title="Pre-order chair",
        shopify_preorder=_preorder_payload(),
    )

    captured = await _call_route(body, monkeypatch)

    incoming = captured["ctx"].incoming_data
    assert "shopify_preorder" in incoming, (
        "the section was dropped before reaching create_task — _CreateTaskBody is missing the field"
    )
    assert incoming["shopify_preorder"]["shop_integration_id"] == "shpint_1"


@pytest.mark.unit
async def test_product_and_inventory_survive_the_round_trip(monkeypatch) -> None:
    body = tasks_router._CreateTaskBody(
        task_type="pre_order",
        shopify_preorder=_preorder_payload(),
    )

    captured = await _call_route(body, monkeypatch)
    section = captured["ctx"].incoming_data["shopify_preorder"]

    assert section["product"]["title"] == "PRE_ORDER-2"
    assert section["product"]["sku"] == "PRE_ORDER-2"
    # Price must stay a decimal string — a float here would lose the contract.
    assert section["product"]["price"] == "2000.00"
    assert isinstance(section["product"]["price"], str)
    assert section["inventory"] == [
        {"location_id": "gid://shopify/Location/90742587722", "quantity": 1}
    ]


@pytest.mark.unit
async def test_optional_product_keys_are_forwarded_when_supplied(monkeypatch) -> None:
    payload = _preorder_payload()
    payload["product"].update(
        {
            "description": "Solid oak",
            "product_category": "Chair",
            "tags": ["custom"],
            "metafields": {"notes": "handle with care"},
            "image_id": "img_1",
            "image_alt_text": "Green chair",
        }
    )
    body = tasks_router._CreateTaskBody(task_type="pre_order", shopify_preorder=payload)

    captured = await _call_route(body, monkeypatch)
    product = captured["ctx"].incoming_data["shopify_preorder"]["product"]

    assert product["description"] == "Solid oak"
    assert product["product_category"] == "Chair"
    assert product["tags"] == ["custom"]
    assert product["metafields"] == {"notes": "handle with care"}
    assert product["image_id"] == "img_1"
    assert product["image_alt_text"] == "Green chair"


@pytest.mark.unit
async def test_multiple_inventory_locations_are_forwarded(monkeypatch) -> None:
    payload = _preorder_payload()
    payload["inventory"].append(
        {"location_id": "gid://shopify/Location/11111111", "quantity": 3}
    )
    body = tasks_router._CreateTaskBody(task_type="pre_order", shopify_preorder=payload)

    captured = await _call_route(body, monkeypatch)

    assert len(captured["ctx"].incoming_data["shopify_preorder"]["inventory"]) == 2


@pytest.mark.unit
async def test_omitting_the_section_leaves_it_out_entirely(monkeypatch) -> None:
    # `exclude_unset=True` means an unsent section must not appear as an explicit null, which
    # would be indistinguishable from "sent as null" downstream.
    body = tasks_router._CreateTaskBody(task_type="return", title="Ordinary task")

    captured = await _call_route(body, monkeypatch)

    assert "shopify_preorder" not in captured["ctx"].incoming_data


@pytest.mark.unit
async def test_route_still_targets_create_task(monkeypatch) -> None:
    body = tasks_router._CreateTaskBody(
        task_type="pre_order",
        shopify_preorder=_preorder_payload(),
    )

    captured = await _call_route(body, monkeypatch)

    assert captured["command"] is tasks_router.create_task
    assert captured["status_code"] == 200
    assert captured["payload"]["ok"] is True
