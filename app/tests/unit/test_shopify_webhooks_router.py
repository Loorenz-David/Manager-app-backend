from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import shopify_webhooks as shopify_webhooks_router


def _build_test_client(monkeypatch, run_service_result: SimpleNamespace) -> tuple[TestClient, dict]:
    app = FastAPI()
    app.include_router(shopify_webhooks_router.router, prefix="/api/v1/shopify")
    captured: dict = {"calls": 0}

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        captured["calls"] += 1
        captured["incoming_data"] = ctx.incoming_data
        return run_service_result

    app.dependency_overrides[get_db] = _fake_get_db
    monkeypatch.setattr(shopify_webhooks_router, "run_service", _fake_run_service)
    return TestClient(app), captured


@pytest.mark.unit
def test_shopify_webhook_route_is_reachable_at_exact_path_and_not_under_integrations_prefix(monkeypatch) -> None:
    client, captured = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"outcome": "received"}, error=None),
    )

    response = client.post(
        "/api/v1/shopify/webhooks",
        content=b'{"id":1}',
        headers={"X-Shopify-Hmac-Sha256": "sig"},
    )

    assert response.status_code == 200
    assert captured["calls"] == 1
    assert client.post("/api/v1/integrations/shopify/webhooks", content=b"{}").status_code == 404


@pytest.mark.unit
def test_shopify_webhook_route_is_not_jwt_or_role_protected(monkeypatch) -> None:
    client, captured = _build_test_client(
        monkeypatch,
        SimpleNamespace(success=True, data={"outcome": "received"}, error=None),
    )

    response = client.post(
        "/api/v1/shopify/webhooks",
        content=b'{"id":2}',
        headers={
            "X-Shopify-Hmac-Sha256": "sig",
            "X-Shopify-Topic": "orders/create",
            "X-Shopify-Shop-Domain": "shop.myshopify.com",
            "X-Shopify-Webhook-Id": "wid-1",
        },
    )

    assert response.status_code == 200
    assert captured["calls"] == 1
    assert captured["incoming_data"]["raw_body"] == b'{"id":2}'
    assert captured["incoming_data"]["topic"] == "orders/create"
    assert captured["incoming_data"]["shop_domain"] == "shop.myshopify.com"
    assert captured["incoming_data"]["webhook_id"] == "wid-1"
