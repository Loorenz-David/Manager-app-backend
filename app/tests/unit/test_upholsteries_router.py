import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import upholsteries as upholsteries_router


@pytest.mark.unit
async def test_route_list_external_upholsteries_forwards_provider_filters(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"upholsteries": []}, error=None)

    monkeypatch.setattr(upholsteries_router, "run_service", _fake_run_service)

    result = await upholsteries_router.route_list_external_upholsteries(
        session=object(),
        q="Afrodite",
        limit=5,
        providers="nevotex,fargotex",
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is upholsteries_router.list_external_upholsteries
    assert captured["ctx"].query_params == {
        "q": "Afrodite",
        "limit": 5,
        "providers": "nevotex,fargotex",
    }


@pytest.mark.unit
async def test_route_list_nevotex_upholsteries_forwards_query(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"upholsteries": []}, error=None)

    monkeypatch.setattr(upholsteries_router, "run_service", _fake_run_service)

    result = await upholsteries_router.route_list_nevotex_upholsteries(
        session=object(),
        q="Nevotex",
        limit=7,
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is upholsteries_router.list_nevotex_upholsteries
    assert captured["ctx"].query_params == {"q": "Nevotex", "limit": 7}
