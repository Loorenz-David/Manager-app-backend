from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import worker_shifts as worker_shifts_router
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


def _build_client(*, role_name: str, monkeypatch) -> tuple[TestClient, dict]:
    app = FastAPI()
    app.include_router(worker_shifts_router.router, prefix="/api/v1/worker-shifts")
    captured = {
        "calls": [],
        "response_data": {"action": "ok"},
        "response_error": None,
    }

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        captured["calls"].append((command, ctx))
        error = captured["response_error"]
        return SimpleNamespace(
            success=error is None,
            data=captured["response_data"] if error is None else None,
            error=error,
        )

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
    ("path", "expected_command"),
    [
        ("/api/v1/worker-shifts/clock-in", worker_shifts_router.clock_in_worker_shift),
        ("/api/v1/worker-shifts/clock-out", worker_shifts_router.clock_out_worker_shift),
    ],
)
def test_explicit_clock_routes_allow_shift_roles_and_wire_existing_commands(
    role_name: str,
    path: str,
    expected_command,
    monkeypatch,
) -> None:
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)
    user_id = "usr_worker" if role_name != "worker" else None

    response = client.post(path, json={"user_id": user_id})

    assert response.status_code == 200
    assert len(captured["calls"]) == 1
    assert captured["calls"][0][0] is expected_command
    assert captured["calls"][0][1].incoming_data == {"user_id": user_id}


def test_clock_out_route_does_not_forward_internal_clock_out_at(monkeypatch) -> None:
    client, captured = _build_client(role_name="manager", monkeypatch=monkeypatch)

    response = client.post(
        "/api/v1/worker-shifts/clock-out",
        json={
            "user_id": "usr_worker",
            "clock_out_at": "2026-07-29T06:00:00+00:00",
        },
    )

    assert response.status_code == 200
    assert captured["calls"][0][1].incoming_data == {"user_id": "usr_worker"}


@pytest.mark.parametrize(
    ("path", "error", "expected_status"),
    [
        (
            "/api/v1/worker-shifts/clock-in",
            ConflictError("Worker is already clocked in."),
            409,
        ),
        (
            "/api/v1/worker-shifts/clock-out",
            ConflictError("Worker is not clocked in."),
            409,
        ),
        (
            "/api/v1/worker-shifts/clock-in",
            PermissionDenied("Managers and admins must select a worker."),
            403,
        ),
        (
            "/api/v1/worker-shifts/clock-out",
            PermissionDenied("Managers and admins must select a worker."),
            403,
        ),
    ],
)
def test_explicit_clock_routes_preserve_command_error_statuses(
    path: str,
    error,
    expected_status: int,
    monkeypatch,
) -> None:
    client, captured = _build_client(role_name="manager", monkeypatch=monkeypatch)
    captured["response_error"] = error

    response = client.post(path, json={})

    assert response.status_code == expected_status
    assert response.json() == {"error": error.message, "ok": False}


def test_clock_routes_preserve_analytics_null_contract_by_action(monkeypatch) -> None:
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    captured["response_data"] = {"action": "clock_in", "user_id": "usr_worker"}

    explicit_clock_in = client.post("/api/v1/worker-shifts/clock-in", json={})
    toggle_clock_in = client.post("/api/v1/worker-shifts/clock", json={})

    assert "analytics" not in explicit_clock_in.json()["data"]
    assert "analytics" not in toggle_clock_in.json()["data"]

    captured["response_data"] = {
        "action": "clock_out",
        "user_id": "usr_worker",
        "transitioned_steps": 2,
        "analytics": None,
    }
    explicit_clock_out = client.post("/api/v1/worker-shifts/clock-out", json={})
    toggle_clock_out = client.post("/api/v1/worker-shifts/clock", json={})

    assert explicit_clock_out.json()["data"] == captured["response_data"]
    assert toggle_clock_out.json()["data"] == captured["response_data"]


@pytest.mark.parametrize("path", ["/api/v1/worker-shifts/clock-out", "/api/v1/worker-shifts/clock"])
def test_clock_out_routes_compose_analytics_after_the_command(path: str, monkeypatch) -> None:
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    captured["response_data"] = {
        "action": "clock_out",
        "user_id": "usr_target",
        "transitioned_steps": 2,
        "analytics": None,
        "_clock_out_at": datetime(2026, 7, 30, 12, tzinfo=timezone.utc),
    }
    expected_analytics = {
        "date": "2026-07-30",
        "timeline": {},
        "pause_reasons": {},
        "completed_items": [],
        "completed_items_truncated": False,
        "week": {},
        "rate": {},
    }
    calls = []

    async def _analytics(ctx, user_id, clock_out_at):
        calls.append((ctx, user_id, clock_out_at))
        return expected_analytics

    monkeypatch.setattr(worker_shifts_router, "get_worker_clock_out_analytics", _analytics)

    response = client.post(path, json={})

    assert response.status_code == 200
    assert response.json()["data"]["analytics"] == expected_analytics
    assert "_clock_out_at" not in response.json()["data"]
    assert calls[0][1:] == ("usr_target", datetime(2026, 7, 30, 12, tzinfo=timezone.utc))


@pytest.mark.parametrize("path", ["/api/v1/worker-shifts/clock-out", "/api/v1/worker-shifts/clock"])
def test_clock_out_routes_degrade_to_null_when_analytics_fails(path: str, monkeypatch, caplog) -> None:
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    captured["response_data"] = {
        "action": "clock_out",
        "user_id": "usr_target",
        "transitioned_steps": 0,
        "analytics": None,
    }

    async def _broken_analytics(*_args):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(worker_shifts_router, "get_worker_clock_out_analytics", _broken_analytics)

    response = client.post(path, json={})

    assert response.status_code == 200
    assert response.json()["data"]["analytics"] is None
    assert "worker_shift.clock_out_analytics_failed" in caplog.text


@pytest.mark.parametrize("path", ["/api/v1/worker-shifts/clock-out", "/api/v1/worker-shifts/clock"])
def test_clock_out_routes_degrade_to_null_when_analytics_is_partial(
    path: str,
    monkeypatch,
    caplog,
) -> None:
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    captured["response_data"] = {
        "action": "clock_out",
        "user_id": "usr_target",
        "transitioned_steps": 0,
        "analytics": None,
        "_clock_out_at": datetime(2026, 7, 30, 12, tzinfo=timezone.utc),
    }

    async def _partial_analytics(*_args):
        return {"date": "2026-07-30"}

    monkeypatch.setattr(worker_shifts_router, "get_worker_clock_out_analytics", _partial_analytics)

    response = client.post(path, json={})

    assert response.status_code == 200
    assert response.json()["data"]["analytics"] is None
    assert "worker_shift.clock_out_analytics_failed" in caplog.text


@pytest.mark.parametrize("path", ["/api/v1/worker-shifts/clock-out", "/api/v1/worker-shifts/clock"])
def test_clock_out_routes_degrade_to_null_when_command_omits_clock_out_at(
    path: str,
    monkeypatch,
    caplog,
) -> None:
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    captured["response_data"] = {
        "action": "clock_out",
        "user_id": "usr_target",
        "transitioned_steps": 0,
        "analytics": None,
    }

    composer_calls = []

    async def _analytics(*args):
        composer_calls.append(args)
        return {}

    monkeypatch.setattr(worker_shifts_router, "get_worker_clock_out_analytics", _analytics)

    response = client.post(path, json={})

    assert response.status_code == 200
    assert response.json()["data"]["analytics"] is None
    assert composer_calls == []
    assert "worker_shift.clock_out_analytics_failed" in caplog.text


@pytest.mark.parametrize("role_name", ["worker", "manager", "admin"])
def test_current_route_allows_shift_roles_and_forwards_user_id(
    role_name: str,
    monkeypatch,
) -> None:
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)
    user_id = "usr_worker" if role_name != "worker" else None
    captured["response_data"] = {
        "user_id": user_id or "usr_test",
        "clocked_in": False,
        "shift_started_at": None,
        "state": None,
        "state_entered_at": None,
        "pause_reason": None,
        "declared_state": None,
    }

    response = client.get(
        "/api/v1/worker-shifts/current",
        params={"user_id": user_id} if user_id else None,
    )

    assert response.status_code == 200
    assert captured["calls"][0][0] is worker_shifts_router.get_current_worker_shift_state
    assert captured["calls"][0][1].query_params == {"user_id": user_id}
    assert response.json()["data"] == captured["response_data"]


def test_current_route_preserves_non_member_not_found_status(monkeypatch) -> None:
    client, captured = _build_client(role_name="manager", monkeypatch=monkeypatch)
    captured["response_error"] = NotFound("Worker was not found in this workspace.")

    response = client.get(
        "/api/v1/worker-shifts/current",
        params={"user_id": "usr_non_member"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "Worker was not found in this workspace.",
        "ok": False,
    }


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
