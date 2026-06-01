import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import items as items_router


@pytest.mark.unit
async def test_route_list_item_issues_forwards_client_id(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"item_issues": []}, error=None)

    monkeypatch.setattr(items_router, "run_service", _fake_run_service)

    result = await items_router.route_list_item_issues(
        client_id="itm_123",
        claims={"user_id": "usr_1", "role": "worker"},
        session=object(),
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is items_router.list_item_issues_by_item_id
    assert captured["ctx"].incoming_data == {"client_id": "itm_123"}


@pytest.mark.unit
async def test_route_list_item_upholstery_forwards_client_id(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"item_upholstery": [], "requirements": []}, error=None)

    monkeypatch.setattr(items_router, "run_service", _fake_run_service)

    result = await items_router.route_list_item_upholstery(
        client_id="itm_456",
        claims={"user_id": "usr_2", "role": "worker"},
        session=object(),
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is items_router.list_item_upholstery_by_item_id
    assert captured["ctx"].incoming_data == {"client_id": "itm_456"}


@pytest.mark.unit
async def test_route_delete_item_issues_forwards_ids(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={}, error=None)

    monkeypatch.setattr(items_router, "run_service", _fake_run_service)

    result = await items_router.route_delete_item_issues(
        client_id="itm_789",
        body=items_router._DeleteIssuesBody(issue_ids=["iti_1", "iti_2"]),
        claims={"user_id": "usr_3", "role": "manager"},
        session=object(),
    )

    body = json.loads(result.body)

    assert result.status_code == 200
    assert body["ok"] is True
    assert captured["command"] is items_router.delete_item_issues
    assert captured["ctx"].incoming_data == {"item_id": "itm_789", "issue_ids": ["iti_1", "iti_2"]}
