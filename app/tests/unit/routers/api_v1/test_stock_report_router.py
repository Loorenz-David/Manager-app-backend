from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import stock_report
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims

ROUTES = [
    ("GET", "/api/v1/stock-report/consistency"),
    ("POST", "/api/v1/stock-report/repair"),
]


def client(monkeypatch, role):
    app = FastAPI()
    app.include_router(stock_report.router, prefix="/api/v1/stock-report")
    calls = []

    async def fake_db():
        yield object()

    async def fake_run(service, context):
        calls.append((service, context))
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
