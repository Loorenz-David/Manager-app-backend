"""`GET /api/v1/pricing/item-costs` router: forwarding, 401 shape, 422."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.config import settings
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import pricing_api as router_module

pytestmark = pytest.mark.unit


def _client(monkeypatch, run_service_result=None):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1/pricing")
    captured: dict = {}

    async def _fake_get_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_get_db
    if run_service_result is not None:
        async def _fake_run_service(command, ctx):
            captured["incoming_data"] = ctx.incoming_data
            captured["identity"] = ctx.identity
            return run_service_result

        monkeypatch.setattr(router_module, "run_service", _fake_run_service)
    return TestClient(app), captured


def test_forwards_sku_and_headers_and_renders_the_house_envelope(monkeypatch):
    data = {"sku": "ABC-1", "currency": "SEK"}
    client, captured = _client(monkeypatch, SimpleNamespace(success=True, data=data, error=None))

    response = client.get("/api/v1/pricing/item-costs", params={"sku": "ABC-1"}, headers={"X-API-KEY": "k"})

    assert response.status_code == 200
    assert response.json() == {"data": data, "ok": True, "warnings": []}
    assert captured["identity"] == {}
    assert captured["incoming_data"]["sku"] == "ABC-1"
    assert captured["incoming_data"]["headers"]["x-api-key"] == "k"


def test_every_401_cause_renders_the_same_body(monkeypatch):
    # Real run_service: the key check refuses before any database access.
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", "k")
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", "ws_configured")
    client, _ = _client(monkeypatch)

    missing = client.get("/api/v1/pricing/item-costs", params={"sku": "ABC-1"})
    wrong = client.get("/api/v1/pricing/item-costs", params={"sku": "ABC-1"}, headers={"X-API-KEY": "nope"})

    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json() == {"error": "Unauthorized.", "ok": False}


@pytest.mark.parametrize("params", [{}, {"sku": ""}], ids=["absent", "empty"])
def test_missing_sku_is_a_422(monkeypatch, params):
    client, _ = _client(monkeypatch, SimpleNamespace(success=True, data={}, error=None))

    response = client.get("/api/v1/pricing/item-costs", params=params, headers={"X-API-KEY": "k"})

    assert response.status_code == 422
