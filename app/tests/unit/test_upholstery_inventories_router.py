import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from beyo_manager.routers.api_v1 import upholstery_inventories as upholstery_inventories_router


@pytest.mark.unit
async def test_route_set_current_stored_amount_passes_expected_context(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={}, error=None)

    monkeypatch.setattr(upholstery_inventories_router, "run_service", _fake_run_service)

    result = await upholstery_inventories_router.route_set_current_stored_amount(
        client_id="uin_123",
        body=upholstery_inventories_router._SetCurrentStoredAmountBody(
            current_stored_amount_meters=Decimal("4.250")
        ),
        claims={"user_id": "usr_1", "role_name": "manager"},
        session=object(),
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert captured["command"] is upholstery_inventories_router.set_current_stored_amount_inventory
    assert captured["ctx"].incoming_data == {
        "client_id": "uin_123",
        "current_stored_amount_meters": Decimal("4.250"),
    }


@pytest.mark.unit
async def test_route_set_current_stored_amount_rejects_worker_role() -> None:
    route = next(
        route
        for route in upholstery_inventories_router.router.routes
        if getattr(route, "endpoint", None) is upholstery_inventories_router.route_set_current_stored_amount
    )
    dependency = route.dependant.dependencies[0].call

    with pytest.raises(HTTPException, match="Insufficient role permissions."):
        await dependency({"role_name": "worker", "user_id": "usr_1"})


@pytest.mark.unit
async def test_route_list_upholstery_inventories_passes_filter_query_params(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={}, error=None)

    monkeypatch.setattr(upholstery_inventories_router, "run_service", _fake_run_service)

    result = await upholstery_inventories_router.route_list_upholstery_inventories(
        claims={"user_id": "usr_1", "role_name": "manager"},
        session=object(),
        limit=25,
        offset=10,
        q="oak dune",
        favorite=True,
        in_stock=False,
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert captured["command"] is upholstery_inventories_router.list_upholstery_inventories
    assert captured["ctx"].query_params == {
        "limit": 25,
        "offset": 10,
        "q": "oak dune",
        "favorite": True,
        "in_stock": False,
    }


@pytest.mark.unit
async def test_route_get_upholstery_inventory_history_passes_cursor_and_limit(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"records": []}, error=None)

    monkeypatch.setattr(upholstery_inventories_router, "run_service", _fake_run_service)

    result = await upholstery_inventories_router.route_get_upholstery_inventory_history(
        client_id="uin_123",
        claims={"user_id": "usr_1", "role_name": "worker"},
        session=object(),
        limit=5,
        cursor="abc",
    )

    assert result.status_code == 200
    assert json.loads(result.body)["data"] == {"records": []}
    assert captured["command"] is upholstery_inventories_router.get_upholstery_inventory_history
    assert captured["ctx"].incoming_data == {"client_id": "uin_123"}
    assert captured["ctx"].query_params == {"limit": 5, "cursor": "abc"}


@pytest.mark.unit
async def test_route_get_upholstery_inventory_history_allows_same_roles_as_detail() -> None:
    def _dependency(endpoint):
        route = next(
            r for r in upholstery_inventories_router.router.routes if getattr(r, "endpoint", None) is endpoint
        )
        return route.dependant.dependencies[0].call

    history_dep = _dependency(upholstery_inventories_router.route_get_upholstery_inventory_history)
    for role in ("admin", "manager", "worker"):
        assert await history_dep({"role_name": role, "user_id": "usr_1"})
    with pytest.raises(HTTPException):
        await history_dep({"role_name": "seller", "user_id": "usr_1"})
