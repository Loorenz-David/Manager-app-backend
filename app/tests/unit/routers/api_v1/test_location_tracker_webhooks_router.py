"""Plan 7 — C5(c), C1(j): the demand webhook router (master plan §6.6).

Precedent: `tests/unit/test_shopify_webhooks_router.py` (raw-body router shape).
`run_service` is faked so this file never touches a database; it proves the route
forwards raw bytes and headers, and renders `build_ok`/`build_err`.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import location_tracker_webhooks as router_module

pytestmark = pytest.mark.unit


def _build_test_client(monkeypatch, run_service_result):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1/location-tracker")
    captured: dict = {"calls": 0}

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        captured["calls"] += 1
        captured["incoming_data"] = ctx.incoming_data
        captured["identity"] = ctx.identity
        return run_service_result

    app.dependency_overrides[get_db] = _fake_get_db
    monkeypatch.setattr(router_module, "run_service", _fake_run_service)
    return TestClient(app), captured


def test_c5c_route_forwards_raw_bytes_and_headers_and_renders_build_ok(monkeypatch):
    client, captured = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"results": []}, error=None),
    )

    response = client.post(
        "/api/v1/location-tracker/webhooks/stock-demand",
        content=b"[...]",
        headers={"X-API-KEY": "k"},
    )

    assert response.status_code == 200
    assert response.json() == {"data": {"results": []}, "ok": True, "warnings": []}
    assert captured["calls"] == 1
    assert captured["identity"] == {}
    assert captured["incoming_data"]["raw_body"] == b"[...]"
    assert captured["incoming_data"]["headers"]["x-api-key"] == "k"


def test_c1j_header_key_sent_uppercase_is_still_found(monkeypatch):
    # Same call as above: Starlette lower-cases header keys, so `dict(request.headers)`
    # already carries "x-api-key" regardless of how the sender capitalized it.
    client, captured = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"results": []}, error=None),
    )

    response = client.post(
        "/api/v1/location-tracker/webhooks/stock-demand",
        content=b"[]",
        headers={"X-API-KEY": "k"},
    )

    assert response.status_code == 200
    assert "x-api-key" in captured["incoming_data"]["headers"]
    assert "X-API-KEY" not in captured["incoming_data"]["headers"]


def test_c5c_router_renders_build_err_for_a_faked_auth_error(monkeypatch):
    client, captured = _build_test_client(
        monkeypatch,
        SimpleNamespace(
            success=False,
            data=None,
            error=LocationTrackerWebhookAuthError("Unauthorized."),
        ),
    )

    response = client.post(
        "/api/v1/location-tracker/webhooks/stock-demand",
        content=b"[]",
        headers={"x-api-key": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized.", "ok": False}
    assert captured["calls"] == 1
