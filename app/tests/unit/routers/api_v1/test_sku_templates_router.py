import json
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import sku_templates as sku_templates_router


@pytest.mark.unit
async def test_create_sku_template_route_forwards_body(monkeypatch):
    captured = {}

    async def fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"client_id": "skt_1"}, error=None)

    monkeypatch.setattr(sku_templates_router, "run_service", fake_run_service)
    result = await sku_templates_router.route_create_sku_template(
        body=sku_templates_router._CreateBody(task_type="pre_order", prefix="PRE"),
        claims={"user_id": "usr_1", "workspace_id": "ws_1"},
        session=object(),
    )

    assert json.loads(result.body)["ok"] is True
    assert captured["command"] is sku_templates_router.create_sku_template
    assert captured["ctx"].incoming_data["task_type"].value == "pre_order"


@pytest.mark.unit
async def test_reserve_route_forwards_task_type(monkeypatch):
    captured = {}

    async def fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"reserved_scalar": 1}, error=None)

    monkeypatch.setattr(sku_templates_router, "run_service", fake_run_service)
    await sku_templates_router.route_reserve_sku_scalar(
        task_type="pre_order",
        claims={"user_id": "usr_1", "workspace_id": "ws_1"},
        session=object(),
    )

    assert captured["command"] is sku_templates_router.reserve_sku_scalar
    assert captured["ctx"].incoming_data["task_type"] == "pre_order"
