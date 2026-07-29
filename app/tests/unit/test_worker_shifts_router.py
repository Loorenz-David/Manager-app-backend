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


@pytest.mark.parametrize("role_name", ["worker", "manager", "admin"])
@pytest.mark.parametrize(
    ("path", "payload", "expected_command"),
    [
        (
            "/api/v1/worker-shifts/declared-states",
            {
                "user_id": "usr_worker",
                "pause_reason_id": "par_cleaning",
                "description": "Cleaning section B",
            },
            worker_shifts_router.declare_worker_state,
        ),
        (
            "/api/v1/worker-shifts/declared-states/close",
            {"user_id": "usr_worker"},
            worker_shifts_router.close_declared_worker_state,
        ),
    ],
)
def test_declared_state_routes_allow_all_shift_roles(
    role_name: str,
    path: str,
    payload: dict,
    expected_command,
    monkeypatch,
) -> None:
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)
    expected = dict(payload)
    if role_name == "worker":
        expected["user_id"] = None

    response = client.post(path, json=expected)

    assert response.status_code == 200
    assert len(captured["calls"]) == 1
    assert captured["calls"][0][0] is expected_command
    assert captured["calls"][0][1].incoming_data == expected


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/worker-shifts/pause",
        "/api/v1/worker-shifts/resume",
    ],
)
def test_retired_manual_pause_routes_are_not_registered(path: str, monkeypatch) -> None:
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)

    response = client.post(path, json={})

    assert response.status_code == 404
    assert captured["calls"] == []
