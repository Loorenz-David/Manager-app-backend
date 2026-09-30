import json
from types import SimpleNamespace

import jwt
import pytest
from starlette.requests import Request

import beyo_manager.services.commands.auth.refresh_token as refresh_module
from beyo_manager.config import settings
from beyo_manager.errors.availability import AuthUnavailableError
from beyo_manager.errors.permissions import RefreshTokenRejected
from beyo_manager.routers.api_v1 import auth as auth_router
from beyo_manager.services.infra.redis import async_client


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
async def test_floor_sign_in_route_sets_no_refresh_cookie(monkeypatch) -> None:
    async def _fake_run_service(command, ctx):
        return SimpleNamespace(
            success=True,
            data={
                "access_token": "floor-access",
                "user": {
                    "user_id": "usr_1",
                    "workspace_id": "ws_1",
                    "role_name": "manager",
                    "app_scope": "floor",
                },
                "workspace_id": "ws_1",
            },
            error=None,
        )

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    response = await auth_router.sign_in_route(
        body=auth_router.SignInBody(
            email="manager@test.local",
            password="Test1234!",
            app_scope="floor",
        ),
        session=object(),
        _rate=None,
    )
    body = json.loads(response.body)

    assert not any(name == b"set-cookie" for name, _value in response.raw_headers)
    assert body == {
        "ok": True,
        "warnings": [],
        "data": {
            "access_token": "floor-access",
            "user": {
                "user_id": "usr_1",
                "workspace_id": "ws_1",
                "role_name": "manager",
                "app_scope": "floor",
            },
            "workspace_id": "ws_1",
        },
    }


@pytest.mark.unit
async def test_non_floor_sign_in_route_fails_loudly_without_refresh_token(
    monkeypatch,
) -> None:
    async def _fake_run_service(command, ctx):
        return SimpleNamespace(
            success=True,
            data={"access_token": "access"},
            error=None,
        )

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    with pytest.raises(KeyError, match="_refresh_token"):
        await auth_router.sign_in_route(
            body=auth_router.SignInBody(
                email="manager@test.local",
                password="Test1234!",
                app_scope="manager",
            ),
            session=object(),
            _rate=None,
        )


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


@pytest.mark.unit
async def test_refresh_route_rejects_floor_scope_without_cookie_cleanly() -> None:
    response = await auth_router.refresh_route(
        request=_request_with_cookies({}),
        scope="floor",
        session=object(),
    )
    body = json.loads(response.body)

    assert response.status_code == 401
    assert body["ok"] is False
    assert body["code"] == "auth_refresh_rejected"
    assert body["reason"] == "floor_scope_not_refreshable"


@pytest.mark.unit
async def test_refresh_route_rejects_floor_scope_cookie_before_reading_the_blocklist(
    monkeypatch,
) -> None:
    """Named for what it proves: the floor-scope guard rejects first.

    The blocklist stub below never gets called — `floor_scope_not_refreshable` is
    returned before any revocation lookup (phase 5 review finding R3-1). Renamed in
    phase 6; assertions unchanged.
    """
    async def _is_blocklisted(jti: str) -> bool:
        assert jti == "device-jti"
        return True

    monkeypatch.setattr(
        refresh_module,
        "is_token_blocklisted",
        _is_blocklisted,
    )
    floor_access_token = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "floor",
            "jti": "device-jti",
            "token_type": "access",
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    response = await auth_router.refresh_route(
        request=_request_with_cookies(
            {"floor_refresh_token": floor_access_token}
        ),
        scope="floor",
        session=object(),
    )
    body = json.loads(response.body)

    assert response.status_code == 401
    assert body["ok"] is False
    assert body["reason"] == "floor_scope_not_refreshable"
    assert "access_token" not in body


@pytest.mark.unit
async def test_refresh_route_answers_503_auth_unavailable_when_blocklist_is_down(
    monkeypatch,
) -> None:
    """Through the real service and run_service: not a 401, and the body carries the
    top-level code the client detects, plus Retry-After."""

    async def _blocklist_unavailable(_jti: str) -> bool:
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(refresh_module, "is_token_blocklisted", _blocklist_unavailable)
    refresh = jwt.encode(
        {
            "user_id": "usr_manager",
            "workspace_id": "ws_test",
            "app_scope": "manager",
            "jti": "refresh-jti",
            "token_type": "refresh",
            "exp": 4_000_000_000,
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    response = await auth_router.refresh_route(
        request=_request_with_cookies({"manager_refresh_token": refresh}),
        scope="manager",
        session=object(),
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert json.loads(response.body) == {
        "error": "Refresh token verification is temporarily unavailable. Please retry.",
        "ok": False,
        "code": "auth_unavailable",
        "reason": "refresh_blocklist_unavailable",
    }


class _DownRedis:
    async def set(self, *_args, **_kwargs) -> None:
        raise ConnectionError("redis unavailable")


@pytest.mark.unit
async def test_logout_route_answers_503_and_keeps_cookies_when_blocklist_is_down(
    monkeypatch,
) -> None:
    """The tokens were not revoked, so this is not a logout: 503, and the refresh
    cookie is kept so the client can retry (deleting it would hide a still-valid
    refresh token from the only party able to revoke it)."""
    monkeypatch.setattr(async_client, "get_async_redis", lambda: _DownRedis())
    refresh = jwt.encode(
        {"jti": "refresh-jti", "exp": 4_000_000_000},
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    response = await auth_router.logout_route(
        request=_request_with_cookies({"manager_refresh_token": refresh}),
        claims={"app_scope": "manager", "jti": "access-jti", "exp": 4_000_000_000},
        session=object(),
    )

    body = json.loads(response.body)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert body["code"] == "auth_unavailable"
    assert body["ok"] is False
    assert body["reason"] == "logout_blocklist_unavailable"
    assert "data" not in body
    assert not any(name == b"set-cookie" for name, _value in response.raw_headers)


@pytest.mark.unit
async def test_logout_route_still_deletes_cookies_on_other_failures(monkeypatch) -> None:
    async def _fake_run_service(command, ctx):
        return SimpleNamespace(success=False, data=None, error=RefreshTokenRejected("x", reason="y"))

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)

    response = await auth_router.logout_route(
        request=_request_with_cookies({"manager_refresh_token": "refresh-value"}),
        claims={"app_scope": "manager"},
        session=object(),
    )

    set_cookie_headers = [value.decode() for name, value in response.raw_headers if name == b"set-cookie"]
    assert any(header.startswith("manager_refresh_token=") and "Max-Age=0" in header for header in set_cookie_headers)


@pytest.mark.unit
def test_build_err_renders_auth_unavailable_with_code_and_retry_after() -> None:
    from beyo_manager.routers.http.response import build_err

    response = build_err(AuthUnavailableError())

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert json.loads(response.body) == {
        "error": "Authentication is temporarily unavailable. Please retry.",
        "ok": False,
        "code": "auth_unavailable",
    }
