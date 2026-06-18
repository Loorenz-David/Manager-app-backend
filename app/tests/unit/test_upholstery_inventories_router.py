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
        "favorite": True,
        "in_stock": False,
    }
