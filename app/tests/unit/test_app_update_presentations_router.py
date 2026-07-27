from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import app_update_presentations as router_module
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


def _build_client(*, role_name: str, monkeypatch, app_scope: str = "manager"):
    app = FastAPI()
    app.include_router(
        router_module.router, prefix="/api/v1/app-update-presentations"
    )
    captured = {"calls": []}

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(fn, ctx):
        captured["calls"].append((fn, ctx))
        return SimpleNamespace(success=True, data={"ok": True}, error=None)

    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role_name,
        "app_scope": app_scope,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(router_module, "run_service", _fake_run_service)
    return TestClient(app), captured


@pytest.mark.unit
@pytest.mark.parametrize("role_name", ["admin", "manager"])
def test_create_allows_admin_roles(role_name, monkeypatch):
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)
    response = client.put(
        "/api/v1/app-update-presentations", json={"title": "Release"}
    )
    assert response.status_code == 200
    assert captured["calls"][0][1].incoming_data == {"title": "Release"}


@pytest.mark.unit
@pytest.mark.parametrize("role_name", ["worker", "seller"])
def test_create_rejects_non_admin_roles(role_name, monkeypatch):
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)
    response = client.put(
        "/api/v1/app-update-presentations", json={"title": "Release"}
    )
    assert response.status_code == 403
    assert captured["calls"] == []


@pytest.mark.unit
@pytest.mark.parametrize("role_name", ["admin", "manager", "worker", "seller"])
def test_active_allows_all_roles(role_name, monkeypatch):
    client, captured = _build_client(role_name=role_name, monkeypatch=monkeypatch)
    response = client.get(
        "/api/v1/app-update-presentations/active", params={"app_key": "manager"}
    )
    assert response.status_code == 200
    assert captured["calls"][0][1].query_params == {"app_key": "manager"}


@pytest.mark.unit
def test_active_requires_app_key(monkeypatch):
    client, _ = _build_client(role_name="worker", monkeypatch=monkeypatch)
    response = client.get("/api/v1/app-update-presentations/active")
    assert response.status_code == 422  # missing required query param


@pytest.mark.unit
def test_view_state_merges_path_param_into_incoming(monkeypatch):
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    response = client.post(
        "/api/v1/app-update-presentations/aup_123/view-state",
        json={"version": 1, "action": "shown"},
    )
    assert response.status_code == 200
    incoming = captured["calls"][0][1].incoming_data
    assert incoming["presentation_id"] == "aup_123"
    assert incoming["action"] == "shown"
    assert incoming["version"] == 1


@pytest.mark.unit
def test_list_rejects_worker(monkeypatch):
    client, captured = _build_client(role_name="worker", monkeypatch=monkeypatch)
    response = client.get("/api/v1/app-update-presentations")
    assert response.status_code == 403
    assert captured["calls"] == []


@pytest.mark.unit
def test_create_slide_forwards_background_color(monkeypatch):
    client, captured = _build_client(role_name="manager", monkeypatch=monkeypatch)
    response = client.post(
        "/api/v1/app-update-presentations/aup_123/slides",
        json={"background_color": "#FFAA00"},
    )
    assert response.status_code == 200
    assert captured["calls"][0][1].incoming_data == {
        "presentation_id": "aup_123",
        "background_color": "#FFAA00",
    }


@pytest.mark.unit
def test_composition_forwards_explicit_null_background_color(monkeypatch):
    client, captured = _build_client(role_name="manager", monkeypatch=monkeypatch)
    response = client.put(
        "/api/v1/app-update-presentations/aup_123/slides/aups_123/composition",
        json={"playback_mode": "manual", "background_color": None, "elements": []},
    )
    assert response.status_code == 200
    incoming = captured["calls"][0][1].incoming_data
    assert incoming["background_color"] is None
