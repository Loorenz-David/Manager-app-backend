import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.routers.api_v1 import tasks as tasks_router


@pytest.mark.unit
async def test_route_update_task_ready_by_at_forwards_payload(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"client_id": "tsk_1"}, error=None)

    monkeypatch.setattr(tasks_router, "run_service", _fake_run_service)

    result = await tasks_router.route_update_task_ready_by_at(
        task_id="tsk_1",
        body=tasks_router._UpdateReadyByAtBody(ready_by_at="2026-06-25T12:30:00Z"),
        claims={"user_id": "usr_1", "role_name": "manager"},
        session=object(),
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert captured["command"] is tasks_router.update_task_ready_by_at
    assert captured["ctx"].incoming_data == {
        "client_id": "tsk_1",
        "ready_by_at": datetime(2026, 6, 25, 12, 30, tzinfo=timezone.utc),
    }


@pytest.mark.unit
async def test_route_update_task_schedule_forwards_payload(monkeypatch):
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["command"] = command
        captured["ctx"] = ctx
        return SimpleNamespace(success=True, data={"client_id": "tsk_1"}, error=None)

    monkeypatch.setattr(tasks_router, "run_service", _fake_run_service)

    result = await tasks_router.route_update_task_schedule(
        task_id="tsk_1",
        body=tasks_router._UpdateScheduleBody(
            scheduled_start_at="2026-06-25T09:00:00Z",
            scheduled_end_at="2026-06-25T10:00:00Z",
        ),
        claims={"user_id": "usr_1", "role_name": "manager"},
        session=object(),
    )

    payload = json.loads(result.body)

    assert result.status_code == 200
    assert payload["ok"] is True
    assert captured["command"] is tasks_router.update_task_schedule
    assert captured["ctx"].incoming_data == {
        "client_id": "tsk_1",
        "scheduled_start_at": datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc),
        "scheduled_end_at": datetime(2026, 6, 25, 10, 0, tzinfo=timezone.utc),
    }
