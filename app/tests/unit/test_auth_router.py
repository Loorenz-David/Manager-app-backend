import json
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from beyo_manager.errors.permissions import RefreshTokenRejected
from beyo_manager.routers.api_v1 import auth as auth_router


def _request_with_cookies(cookies: dict[str, str]) -> Request:
    cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items()).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/test",
        "headers": [(b"cookie", cookie_header)] if cookie_header else [],
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.unit
async def test_sign_in_route_sets_scope_cookie_and_deletes_legacy_cookie(monkeypatch) -> None:
    async def _fake_run_service(command, ctx):
        return SimpleNamespace(success=True, data={"access_token": "access", "_refresh_token": "refresh"}, error=None)

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    response = await auth_router.sign_in_route(
        body=auth_router.SignInBody(email="user@test.local", password="Test1234!", app_scope="manager"),
        session=object(),
        _rate=None,
    )

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    assert any(header.startswith("manager_refresh_token=refresh;") for header in set_cookie_headers)
    assert any(header.startswith("refresh_token=") and "Max-Age=0" in header for header in set_cookie_headers)


@pytest.mark.unit
async def test_logout_route_reads_scope_cookie_and_deletes_scope_and_legacy(monkeypatch) -> None:
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["incoming_data"] = ctx.incoming_data
        return SimpleNamespace(success=True, data={"logged_out": True}, error=None)

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    response = await auth_router.logout_route(
        request=_request_with_cookies({"manager_refresh_token": "refresh-value"}),
        claims={"app_scope": "manager"},
        session=object(),
    )

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]

    assert captured["incoming_data"] == {"refresh_token": "refresh-value"}
    assert any(header.startswith("manager_refresh_token=") and "Max-Age=0" in header for header in set_cookie_headers)
    assert any(header.startswith("refresh_token=") and "Max-Age=0" in header for header in set_cookie_headers)


@pytest.mark.unit
async def test_refresh_route_reads_scope_cookie_and_passes_scope(monkeypatch) -> None:
    captured = {}

    async def _fake_run_service(command, ctx):
        captured["incoming_data"] = ctx.incoming_data
        return SimpleNamespace(success=True, data={"access_token": "access"}, error=None)

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    response = await auth_router.refresh_route(
        request=_request_with_cookies({"manager_refresh_token": "refresh-value"}),
        scope="manager",
        session=object(),
    )
    body = json.loads(response.body)

    assert body["ok"] is True
    assert captured["incoming_data"] == {"scope": "manager", "refresh_token": "refresh-value"}


@pytest.mark.unit
async def test_refresh_route_returns_custom_payload_for_rejected_refresh(monkeypatch) -> None:
    async def _fake_run_service(command, ctx):
        return SimpleNamespace(
            success=False,
            data=None,
            error=RefreshTokenRejected("Refresh token missing.", reason="refresh_cookie_missing"),
        )

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    response = await auth_router.refresh_route(
        request=_request_with_cookies({}),
        scope="manager",
        session=object(),
    )
    body = json.loads(response.body)

    assert response.status_code == 401
    assert body["code"] == "auth_refresh_rejected"
    assert body["reason"] == "refresh_cookie_missing"
