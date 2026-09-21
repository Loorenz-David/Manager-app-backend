from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import stock_report
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims

ROUTES = [
    ("GET", "/api/v1/stock-report/consistency"),
    ("POST", "/api/v1/stock-report/repair"),
]

_ASSIGNMENT_ENTRY = {
    "stock_report_item_id": "sri_1",
    "task_id": "tsk_1",
    "item_id": "itm_1",
}
ASSIGNMENT_ROUTES = [
    ("POST", "/api/v1/stock-report/assignments", {"entries": [_ASSIGNMENT_ENTRY]}),
    ("POST", "/api/v1/stock-report/assignments/delete", {"client_ids": ["sta_1"]}),
]


def client(monkeypatch, role, *, fake_outcome=None):
    app = FastAPI()
    app.include_router(stock_report.router, prefix="/api/v1/stock-report")
    calls = []

    async def fake_db():
        yield object()

    async def fake_run(service, context):
        calls.append((service, context))
        if fake_outcome is not None:
            return fake_outcome
        return SimpleNamespace(success=True, data={"ok": True}, error=None)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(stock_report, "run_service", fake_run)
    return TestClient(app), calls


@pytest.mark.parametrize("role", ["worker", "seller"])
@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_stock_report_routes_reject_non_manager_roles(monkeypatch, role, method, path):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path).status_code == 403
    assert calls == []


@pytest.mark.parametrize("role", ["admin", "manager"])
@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_stock_report_routes_reach_service_for_permitted_roles(
    monkeypatch, role, method, path
):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path).status_code == 200
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Plan 8 C8 — assignment role cells (ADMIN, MANAGER, WORKER reach; SELLER refused)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["seller"])
@pytest.mark.parametrize(("method", "path", "body"), ASSIGNMENT_ROUTES)
def test_assignment_routes_reject_seller(monkeypatch, role, method, path, body):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path, json=body).status_code == 403
    assert calls == []


@pytest.mark.parametrize("role", ["admin", "manager", "worker"])
@pytest.mark.parametrize(("method", "path", "body"), ASSIGNMENT_ROUTES)
def test_assignment_routes_reach_service_for_permitted_roles(
    monkeypatch, role, method, path, body
):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path, json=body).status_code == 200
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Plan 8 C8(i)/(j) — the two structured assignment errors render code + details
# ---------------------------------------------------------------------------


def test_stock_assignment_refused_renders_code_and_details(monkeypatch):
    error = StockAssignmentRefused([{"index": 0, "reason": "item_already_assigned"}])
    http, _ = client(
        monkeypatch,
        "manager",
        fake_outcome=SimpleNamespace(success=False, data=None, error=error),
    )
    response = http.post(
        "/api/v1/stock-report/assignments", json={"entries": [_ASSIGNMENT_ENTRY]}
    )
    assert response.status_code == 422
    body = response.json()
    assert body == {
        "error": "Stock assignment refused.",
        "ok": False,
        "code": "stock_assignment_refused",
        "details": [{"index": 0, "reason": "item_already_assigned"}],
    }


def test_stock_assignment_property_mismatch_renders_code_and_details(monkeypatch):
    details = [
        {
            "index": 0,
            "stock_report_item_id": "sri_1",
            "task_id": "tsk_1",
            "item_id": "itm_1",
            "failures": [{"key": "wood_group", "reason": "missing_on_item"}],
        }
    ]
    error = StockAssignmentPropertyMismatch(details)
    http, _ = client(
        monkeypatch,
        "manager",
        fake_outcome=SimpleNamespace(success=False, data=None, error=error),
    )
    response = http.post(
        "/api/v1/stock-report/assignments", json={"entries": [_ASSIGNMENT_ENTRY]}
    )
    assert response.status_code == 409
    body = response.json()
    assert body == {
        "error": "Stock assignment property mismatch.",
        "ok": False,
        "code": "stock_assignment_property_mismatch",
        "details": details,
    }
