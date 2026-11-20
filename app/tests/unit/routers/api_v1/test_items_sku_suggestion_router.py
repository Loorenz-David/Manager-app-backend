import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import items as items_router


@pytest.mark.unit
async def test_sku_suggestion_route_forwards_query_params(monkeypatch):
    captured = {}

    async def fake_run_service(query, ctx):
        captured["query"] = query
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"sku": "T3-201126"}, error=None)

    monkeypatch.setattr(items_router, "run_service", fake_run_service)
    result = await items_router.route_suggest_item_sku(
        claims={"user_id": "usr_1", "workspace_id": "ws_1"},
        session=object(),
        item_category_id="itc_1",
        date_code="201126",
    )

    assert json.loads(result.body)["data"] == {"sku": "T3-201126"}
    assert captured["query"] is items_router.suggest_item_sku
    assert captured["ctx"].query_params == {"item_category_id": "itc_1", "date_code": "201126"}


@pytest.mark.unit
def test_sku_suggestion_is_registered_before_item_detail_route():
    paths = [route.path for route in items_router.router.routes]
    assert paths.index("/sku-suggestion") < paths.index("/{client_id}")
