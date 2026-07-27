import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import pause_reasons as pause_reasons_router


@pytest.mark.unit
async def test_create_pause_reason_route_forwards_body(monkeypatch):
    captured = {}

    async def fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"pause_reason": {"client_id": "par_1"}}, error=None)

    monkeypatch.setattr(pause_reasons_router, "run_service", fake_run_service)
    result = await pause_reasons_router.route_create_pause_reason(
        body=pause_reasons_router._CreateBody(name="Lunch", pause_type="personal"),
        claims={"user_id": "usr_1", "workspace_id": "ws_1"},
        session=object(),
    )

    assert json.loads(result.body)["ok"] is True
    assert captured["command"] is pause_reasons_router.create_pause_reason
    assert captured["ctx"].incoming_data["name"] == "Lunch"


@pytest.mark.unit
async def test_list_pause_reasons_route_forwards_offset_filter(monkeypatch):
    captured = {}

    async def fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"pause_reasons": []}, error=None)

    monkeypatch.setattr(pause_reasons_router, "run_service", fake_run_service)
    await pause_reasons_router.route_list_pause_reasons(
        claims={"user_id": "usr_1", "workspace_id": "ws_1"},
        session=object(),
        limit=25,
        offset=10,
        pause_type="blocker",
    )

    assert captured["command"] is pause_reasons_router.list_pause_reasons
    assert captured["ctx"].query_params == {
        "limit": 25,
        "offset": 10,
        "pause_type": "blocker",
    }
