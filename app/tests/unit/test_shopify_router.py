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
    captured: dict = {"calls": 0, "contexts": []}

    async def _fake_get_db():
        yield object()

    async def _fake_run_service(command, ctx):
        captured["calls"] += 1
        captured["contexts"].append(ctx)
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
    assert captured["contexts"][-1].incoming_data["shop_domain"] == "valid-shop"


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


@pytest.mark.unit
@pytest.mark.parametrize(
    "method,path,kwargs,expected_query_params,expected_incoming_data,role_name",
    [
        ("get", "/api/v1/integrations/shopify/shops", {"params": {"limit": "2", "offset": "1"}}, {"limit": "2", "offset": "1"}, {}, "admin"),
        ("get", "/api/v1/integrations/shopify/shops/shpint_1", {}, {}, {"shop_integration_id": "shpint_1"}, "manager"),
        ("get", "/api/v1/integrations/shopify/shops/shpint_1/webhooks/history", {"params": {"limit": "10", "offset": "2"}}, {"limit": "10", "offset": "2"}, {"shop_integration_id": "shpint_1"}, "manager"),
        ("post", "/api/v1/integrations/shopify/shops/shpint_1/reauthorize-url", {"json": {}}, {}, {"shop_integration_id": "shpint_1"}, "manager"),
        ("get", "/api/v1/integrations/shopify/scopes", {"params": {"shop_integration_id": "shpint_1"}}, {"shop_integration_id": "shpint_1"}, {}, "admin"),
        ("post", "/api/v1/integrations/shopify/customers/by-product-identity", {"json": {"sku": "SKU-123", "article_number": "BAR-123"}}, {}, {"sku": "SKU-123", "article_number": "BAR-123"}, "seller"),
        ("post", "/api/v1/integrations/shopify/products/process", {"json": {"items": [{"client_id": "frontend_1", "title": "Chair", "sku": "SKU-123"}]}}, {}, {"items": [{"client_id": "frontend_1", "title": "Chair", "description": None, "status": None, "tags": [], "product_category": None, "price": None, "weight": None, "sku": "SKU-123", "item_article_number": None, "article_number": None, "metafields": {}, "target_shop_integration_ids": None}]}, "manager"),
        ("post", "/api/v1/integrations/shopify/products/process", {"json": {"items": [{"client_id": "frontend_1", "title": "Chair", "sku": "SKU-123"}]}}, {}, {"items": [{"client_id": "frontend_1", "title": "Chair", "description": None, "status": None, "tags": [], "product_category": None, "price": None, "weight": None, "sku": "SKU-123", "item_article_number": None, "article_number": None, "metafields": {}, "target_shop_integration_ids": None}]}, "admin"),
    ],
)
def test_new_shopify_shared_role_routes_call_service_with_expected_context(
    method: str,
    path: str,
    kwargs: dict,
    expected_query_params: dict,
    expected_incoming_data: dict,
    role_name: str,
    monkeypatch,
) -> None:
    client, captured = _build_test_client(
        claims={"role_name": role_name, "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"ok": True}, error=None),
    )

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 200
    assert captured["calls"] == 1
    ctx = captured["contexts"][-1]
    assert ctx.query_params == expected_query_params
    assert ctx.incoming_data == expected_incoming_data
    assert "access_token_encrypted" not in response.text
    assert "raw_payload" not in response.text
    assert "shopify_client_secret" not in response.text


@pytest.mark.unit
def test_shopify_webhook_history_route_is_reachable_at_exact_admin_path(monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "manager", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"webhook_history_records": [], "webhook_history_records_pagination": {"has_more": False, "limit": 10, "offset": 0}}, error=None),
    )

    response = client.get(
        "/api/v1/integrations/shopify/shops/shpint_1/webhooks/history",
        params={"limit": "10", "offset": "0"},
    )

    assert response.status_code == 200
    assert captured["calls"] == 1
    assert client.get("/api/v1/shopify/webhooks/history").status_code == 404


@pytest.mark.unit
@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("delete", "/api/v1/integrations/shopify/shops/shpint_1", {}),
        ("post", "/api/v1/integrations/shopify/shops/shpint_1/webhooks/sync", {}),
        ("post", "/api/v1/integrations/shopify/webhooks/sync", {}),
    ],
)
def test_new_shopify_admin_only_routes_allow_admin_and_reject_manager_before_service_logic(
    method: str,
    path: str,
    kwargs: dict,
    monkeypatch,
) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "admin", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"ok": True}, error=None),
    )

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 200
    assert captured["calls"] == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("delete", "/api/v1/integrations/shopify/shops/shpint_1", {}),
        ("post", "/api/v1/integrations/shopify/shops/shpint_1/webhooks/sync", {}),
        ("post", "/api/v1/integrations/shopify/webhooks/sync", {}),
    ],
)
def test_existing_shopify_admin_only_routes_reject_manager_before_service_logic(
    method: str,
    path: str,
    kwargs: dict,
    monkeypatch,
) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "manager", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"ok": True}, error=None),
    )

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 403
    assert captured["calls"] == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("get", "/api/v1/integrations/shopify/shops", {"params": {"limit": "2"}}),
        ("get", "/api/v1/integrations/shopify/shops/shpint_1", {}),
        ("get", "/api/v1/integrations/shopify/shops/shpint_1/webhooks/history", {"params": {"limit": "10"}}),
        ("post", "/api/v1/integrations/shopify/shops/shpint_1/reauthorize-url", {"json": {}}),
        ("delete", "/api/v1/integrations/shopify/shops/shpint_1", {}),
        ("post", "/api/v1/integrations/shopify/shops/shpint_1/webhooks/sync", {}),
        ("post", "/api/v1/integrations/shopify/webhooks/sync", {}),
        ("get", "/api/v1/integrations/shopify/scopes", {"params": {"shop_integration_id": "shpint_1"}}),
        ("post", "/api/v1/integrations/shopify/products/process", {"json": {"items": [{"client_id": "frontend_1", "title": "Chair", "sku": "SKU-123"}]}}),
    ],
)
@pytest.mark.parametrize("role_name", ["worker", "seller"])
def test_new_shopify_admin_routes_reject_worker_and_seller_before_service_logic(
    method: str,
    path: str,
    kwargs: dict,
    role_name: str,
    monkeypatch,
) -> None:
    client, captured = _build_test_client(
        claims={"role_name": role_name, "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"ok": True}, error=None),
    )

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 403
    assert captured["calls"] == 0


@pytest.mark.unit
def test_customer_lookup_route_rejects_worker_before_service_logic(monkeypatch) -> None:
    client, captured = _build_test_client(
        claims={"role_name": "worker", "workspace_id": "ws_1", "user_id": "usr_1"},
        monkeypatch=monkeypatch,
        run_service_result=SimpleNamespace(success=True, data={"ok": True}, error=None),
    )

    response = client.post(
        "/api/v1/integrations/shopify/customers/by-product-identity",
        json={"sku": "SKU-123"},
    )

    assert response.status_code == 403
    assert captured["calls"] == 0
