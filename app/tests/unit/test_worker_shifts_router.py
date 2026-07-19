from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import worker_shifts as worker_shifts_router
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


def _build_client(*, role_name: str, monkeypatch) -> tuple[TestClient, dict]:
    app = FastAPI()
    app.include_router(worker_shifts_router.router, prefix="/api/v1/worker-shifts")
    captured = {"calls": []}

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        captured["calls"].append((command, ctx))
        return SimpleNamespace(success=True, data={"action": "ok"}, error=None)

    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role_name,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(worker_shifts_router, "run_service", _fake_run_service)
    return TestClient(app), captured


@pytest.mark.parametrize("role_name", ["worker", "manager", "admin"])
def test_clock_route_role_matrix_allows_shift_roles(role_name: str, monkeypatch) -> None:
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)

    response = client.post(
        "/api/v1/worker-shifts/clock",
        json={"user_id": "usr_worker" if role_name != "worker" else None},
    )

    assert response.status_code == 200
    assert len(captured["calls"]) == 1
    assert captured["calls"][0][1].incoming_data == {
        "user_id": "usr_worker" if role_name != "worker" else None
    }


def test_clock_route_rejects_unrelated_role(monkeypatch) -> None:
    client, captured = _build_client(role_name="seller", monkeypatch=monkeypatch)

    response = client.post("/api/v1/worker-shifts/clock", json={})

    assert response.status_code == 403
    assert captured["calls"] == []


@pytest.mark.parametrize(
    ("path", "json"),
    [
        ("/api/v1/worker-shifts/pause", {"reason": "Lunch"}),
        ("/api/v1/worker-shifts/resume", None),
    ],
)
def test_pause_and_resume_are_worker_self_service(path: str, json, monkeypatch) -> None:
    worker_client, worker_calls = _build_client(role_name="worker", monkeypatch=monkeypatch)
    kwargs = {"json": json} if json is not None else {}
    worker_response = worker_client.post(path, **kwargs)

    assert worker_response.status_code == 200
    assert len(worker_calls["calls"]) == 1

    manager_client, manager_calls = _build_client(role_name="manager", monkeypatch=monkeypatch)
    manager_response = manager_client.post(path, **kwargs)

    assert manager_response.status_code == 403
    assert manager_calls["calls"] == []
