from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import item_economics
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


def _client(monkeypatch, role_name: str = "manager", invoke_service: bool = False):
    app = FastAPI()
    app.include_router(item_economics.router, prefix="/api/v1/item-economics")
    calls = []

    async def fake_get_db():
        yield _EmptySession() if invoke_service else object()

    async def fake_run_service(function, context):
        calls.append((function, context))
        if invoke_service:
            try:
                data = await function(context)
            except Exception as error:
                return SimpleNamespace(success=False, data=None, error=error)
        else:
            data = {"budget_signals": []}
        return SimpleNamespace(success=True, data=data, error=None)

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role_name,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(item_economics, "run_service", fake_run_service)
    return TestClient(app), calls


class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []

    def __iter__(self):
        return iter(())


class _EmptySession:
    async def execute(self, statement):
        return _EmptyResult()


def _query(count: int) -> str:
    return "&".join(f"task_ids=tsk_{index}" for index in range(count))


@pytest.mark.unit
def test_budget_signals_dispatches_batch_ids_and_uses_the_signal_service(monkeypatch):
    client, calls = _client(monkeypatch)

    response = client.get(
        "/api/v1/item-economics/tasks/budget-signals?task_ids=tsk_1&task_ids=tsk_2"
    )

    assert response.status_code == 200
    assert calls[0][0] is item_economics.get_task_budget_signals
    assert calls[0][1].query_params == {"task_ids": ["tsk_1", "tsk_2"]}


@pytest.mark.unit
def test_budget_signals_fixed_route_precedes_parameterized_task_routes():
    paths = [route.path for route in item_economics.router.routes]
    signal_index = paths.index("/tasks/budget-signals")
    allocation_index = paths.index("/tasks/budget-allocations")
    parameterized_indices = [
        index for index, path in enumerate(paths) if path.startswith("/tasks/{")
    ]

    assert signal_index == allocation_index + 1
    assert signal_index < min(parameterized_indices)
    assert allocation_index < min(parameterized_indices)


@pytest.mark.unit
def test_budget_signals_rejects_more_than_fifty_ids_with_registered_identity(monkeypatch):
    client, calls = _client(monkeypatch, invoke_service=True)
    response = client.get(
        f"/api/v1/item-economics/tasks/budget-signals?{_query(51)}"
    )

    assert response.status_code == 422
    payload = response.json()
    assert set(payload) == {"error", "ok"}
    assert payload["error"].startswith(
        "BUDGET_SIGNALS_TOO_MANY_TASK_IDS:"
    )
    assert payload["ok"] is False
    assert len(calls) == 1


@pytest.mark.unit
def test_budget_signals_at_fifty_enters_the_service_once(monkeypatch):
    client, calls = _client(monkeypatch, invoke_service=True)
    response = client.get(
        f"/api/v1/item-economics/tasks/budget-signals?{_query(50)}"
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0][0] is item_economics.get_task_budget_signals


@pytest.mark.unit
def test_budget_signals_missing_ids_uses_fastapi_validation_envelope(monkeypatch):
    client, calls = _client(monkeypatch, invoke_service=True)

    response = client.get("/api/v1/item-economics/tasks/budget-signals")

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert "error" not in response.json()
    assert calls == []


@pytest.mark.unit
def test_budget_signals_readme_detail_documents_the_ten_field_contract():
    from pathlib import Path

    readme = Path(__file__).resolve().parents[4] / "beyo_manager" / "routers" / "README.md"
    text = readme.read_text()
    heading = "### GET /api/v1/item-economics/tasks/budget-signals"
    assert text.count(heading) == 1
    section = text.split(heading, 1)[1].split("\n### ", 1)[0]
    string_fields = (
        "task_id",
        "budget_state",
        "currency",
    )
    numeric_fields = (
        "over_seconds",
        "over_cost_minor",
        "projected_over_seconds",
        "projected_over_cost_minor",
        "allowed_seconds",
        "actual_worked_seconds",
        "cost_per_worker_minute_ten_thousandths",
    )
    for field in string_fields:
        cell = f"| data.budget_signals[].{field} | string | Yes |"
        assert section.count(cell) == 1
    for field in numeric_fields:
        cell = f"| data.budget_signals[].{field} | integer | Yes |"
        assert section.count(cell) == 1
