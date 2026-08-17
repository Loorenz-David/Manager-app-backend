from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import item_economics, working_sections
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


def _client(monkeypatch, role_name: str, data=None):
    app = FastAPI()
    app.include_router(item_economics.router, prefix="/api/v1/item-economics")
    app.include_router(working_sections.router, prefix="/api/v1/working-sections")
    calls = []

    async def fake_db():
        yield object()

    async def fake_run_service(command, context):
        calls.append((command, context))
        return SimpleNamespace(success=True, data=data or {"typical_times": []}, error=None)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role_name,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(item_economics, "run_service", fake_run_service)
    monkeypatch.setattr(working_sections, "run_service", fake_run_service)
    return TestClient(app), calls


@pytest.mark.parametrize("role_name", ["admin", "manager", "worker", "seller"])
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/working-sections/typical-times",
        "/api/v1/item-economics/tasks/budget-allocations?task_ids=tsk_1",
    ],
)
def test_both_surfaces_admit_every_role_and_use_the_standard_envelope(path, role_name, monkeypatch):
    client, calls = _client(monkeypatch, role_name)
    response = client.get(path)
    assert response.status_code == 200
    assert set(response.json()) == {"data", "ok", "warnings"}
    assert len(calls) == 1
    if path == "/api/v1/working-sections/typical-times":
        assert calls[0][0] is working_sections.get_working_section_typical_times


def test_budget_allocations_rejects_more_than_fifty_ids_with_registered_identity(monkeypatch):
    app = FastAPI()
    app.include_router(item_economics.router, prefix="/api/v1/item-economics")

    async def fake_db():
        yield object()

    async def fake_run_service(command, context):
        try:
            await command(context)
        except Exception as error:
            return SimpleNamespace(success=False, data=None, error=error)
        return SimpleNamespace(success=True, data={"budget_allocations": []}, error=None)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_jwt_claims] = lambda: {"role_name": "worker", "workspace_id": "ws", "user_id": "usr"}
    monkeypatch.setattr(item_economics, "run_service", fake_run_service)
    client = TestClient(app)
    query = "&".join(f"task_ids=tsk_{index}" for index in range(51))
    response = client.get(f"/api/v1/item-economics/tasks/budget-allocations?{query}")
    assert response.status_code == 422
    assert response.json()["error"].startswith("BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS:")


def test_budget_allocations_at_fifty_calls_the_service(monkeypatch):
    app = FastAPI()
    app.include_router(item_economics.router, prefix="/api/v1/item-economics")

    class EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

        def __iter__(self):
            return iter(())

    class EmptySession:
        async def execute(self, statement):
            return EmptyResult()

    async def fake_db():
        yield EmptySession()

    async def fake_run_service(command, context):
        try:
            data = await command(context)
        except Exception as error:
            return SimpleNamespace(success=False, data=None, error=error)
        return SimpleNamespace(success=True, data=data, error=None)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_jwt_claims] = lambda: {"role_name": "worker", "workspace_id": "ws", "user_id": "usr"}
    monkeypatch.setattr(item_economics, "run_service", fake_run_service)
    client = TestClient(app)
    query = "&".join(f"task_ids=tsk_{index}" for index in range(50))
    response = client.get(f"/api/v1/item-economics/tasks/budget-allocations?{query}")
    assert response.status_code == 200
    assert response.json()["data"] == {"budget_allocations": []}


def test_time_payload_serializers_have_exact_money_free_key_sets():
    typical = {
        "working_section_id": "wsec_1",
        "section_name": "Upholstery",
        "typical_worker_seconds": 3600,
        "sample_count": 5,
        "method": "median_completed_section_totals",
        "window_days": 90,
        "min_sample_size": 5,
    }
    task = {
        "task_id": "tsk_1",
        "status": "ok",
        "allowed_worker_minutes": "195.00",
        "actual_worker_seconds": 9600,
        "remaining_worker_minutes": "35.00",
        "allocation_method": "static_proportional_v1",
        "steps": [
            {
                "step_id": "tsp_1",
                "working_section_id": "wsec_1",
                "section_name_snapshot": "Upholstery",
                "typical_worker_seconds": 3600,
                "allowance_seconds": 3600,
                "worked_seconds": 1500,
                "left_seconds": 2100,
                "share_state": "on_track",
            }
        ],
    }
    from beyo_manager.domain.item_economics.division_serializers import (
        serialize_budget_allocation,
        serialize_budget_step,
        serialize_typical_time,
    )

    assert set(serialize_typical_time(typical)) == {
        "working_section_id", "section_name", "typical_worker_seconds", "sample_count", "method", "window_days", "min_sample_size"
    }
    assert set(serialize_budget_allocation(task)) == {
        "task_id", "status", "allowed_worker_minutes", "actual_worker_seconds", "remaining_worker_minutes", "allocation_method", "steps"
    }
    assert set(serialize_budget_step(task["steps"][0])) == {
        "step_id", "working_section_id", "section_name_snapshot", "typical_worker_seconds",
        "allowance_seconds", "worked_seconds", "left_seconds", "share_state",
    }
    payload = serialize_budget_allocation(task)
    assert not any("money" in key or "minor" in key for key in payload)
    assert not any(
        "money" in key or "minor" in key
        for step_payload in payload["steps"]
        for key in step_payload
    )
