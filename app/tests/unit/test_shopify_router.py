from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import shopify as shopify_router
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims


def _build_test_client(*, claims: dict, monkeypatch, run_service_result: SimpleNamespace) -> tuple[TestClient, dict]:
    app = FastAPI()
    app.include_router(shopify_router.router, prefix="/api/v1/integrations/shopify")
    captured: dict = {"calls": 0}

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        captured["calls"] += 1
        captured["incoming_data"] = ctx.incoming_data
        return run_service_result

    app.dependency_overrides[get_db] = _fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: claims
    monkeypatch.setattr(shopify_router, "run_service", _fake_run_service)
    return TestClient(app), captured


@pytest.mark.unit
@pytest.mark.parametrize("role_name", ["admin", "manager"])
def test_install_url_route_allows_admin_and_manager(role_name: str, monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": role_name},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"install_url": "https://shopify.test"}, error=None),
    )

    response = client.post(
        "/api/v1/integrations/shopify/install-url",
        json={"shop_domain": "valid-shop"},
    )

    assert response.status_code == 200
    assert captured["calls"] == 1
    assert captured["incoming_data"]["shop_domain"] == "valid-shop"


@pytest.mark.unit
@pytest.mark.parametrize("role_name", ["worker", "seller"])
def test_install_url_route_rejects_worker_and_seller_before_command_logic(role_name: str, monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": role_name},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"install_url": "https://shopify.test"}, error=None),
    )

    response = client.post(
        "/api/v1/integrations/shopify/install-url",
        json={"shop_domain": "valid-shop"},
    )

    assert response.status_code == 403
    assert captured["calls"] == 0


@pytest.mark.unit
def test_oauth_callback_route_redirects_to_safe_frontend_location(monkeypatch) -> None:
    client, _captured = _build_test_client(
        claims={"role_name": "admin"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(
            success=True,
            data={"redirect_url": "https://frontend.example.com/shopify/result?success=true&shop_domain=valid-shop.myshopify.com"},
            error=None,
        ),
    )

    response = client.get(
        "/api/v1/integrations/shopify/oauth/callback?shop=valid-shop.myshopify.com&state=abc&code=def&hmac=ghi",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://frontend.example.com/shopify/result?success=true&shop_domain=valid-shop.myshopify.com"
