import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import case_types as case_types_router


@pytest.mark.unit
async def test_route_create_case_type_dispatches_command_with_body(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"case_type": {"client_id": "cty_1"}}, error=None)

    monkeypatch.setattr(case_types_router, "run_service", _fake_run_service)

    result = await case_types_router.route_create_case_type(
        body=case_types_router._CreateCaseTypeBody(
            client_id="cty_1",
            name="Repair",
            image_url=None,
            description="Repair requests",
            entity_type="item",
        ),
        claims={"user_id": "usr_1", "role": "admin"},
        session=object(),
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is case_types_router.create_case_type
    assert captured["ctx"].incoming_data["name"] == "Repair"
    assert captured["ctx"].incoming_data["entity_type"] == "item"


@pytest.mark.unit
async def test_route_list_case_types_forwards_query_params(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"case_types": []}, error=None)

    monkeypatch.setattr(case_types_router, "run_service", _fake_run_service)

    result = await case_types_router.route_list_case_types(
        claims={"user_id": "usr_2", "role": "manager"},
        session=object(),
        limit=25,
        offset=10,
        q="rep",
        entity_type="item,task",
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is case_types_router.list_case_types
    assert captured["ctx"].query_params == {
        "limit": 25,
        "offset": 10,
        "q": "rep",
        "entity_type": "item,task",
    }


@pytest.mark.unit
async def test_route_get_case_type_forwards_client_id(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"case_type": {"client_id": "cty_9"}}, error=None)

    monkeypatch.setattr(case_types_router, "run_service", _fake_run_service)

    result = await case_types_router.route_get_case_type(
        client_id="cty_9",
        claims={"user_id": "usr_3", "role": "worker"},
        session=object(),
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is case_types_router.get_case_type
    assert captured["ctx"].incoming_data == {"client_id": "cty_9"}
