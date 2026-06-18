import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import item_upholsteries as item_upholsteries_router


@pytest.mark.unit
async def test_route_update_item_upholstery_excludes_unset_optional_fields(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={}, error=None)

    monkeypatch.setattr(item_upholsteries_router, "run_service", _fake_run_service)

    result = await item_upholsteries_router.route_update_item_upholstery(
        client_id="iup_123",
        body=item_upholsteries_router._UpdateBody(upholstery_id="uph_123"),
        claims={"user_id": "usr_1", "role": "manager"},
        session=object(),
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert captured["command"] is item_upholsteries_router.update_item_upholstery
    assert captured["ctx"].incoming_data == {
        "client_id": "iup_123",
        "upholstery_id": "uph_123",
    }
