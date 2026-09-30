"""Human activity over HTTP: which requests count, where it is stored, what never breaks.

The recording rule (ActivityMiddleware + get_jwt_claims): one event iff the token
validated (identity stamped), the method is not OPTIONS, the status is not 401, and
X-Beyo-Activity is ``user`` — or absent on a non-GET. Successful refresh records itself.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.requests import Request

from beyo_manager.config import settings
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import auth as auth_router
from beyo_manager.routers.api_v1 import health
from beyo_manager.routers.middleware import activity as activity_middleware
from beyo_manager.routers.middleware.activity import ActivityMiddleware
from beyo_manager.routers.utils import jwt_dep
from beyo_manager.services.commands.auth import refresh_token as refresh_module
from beyo_manager.services.infra.activity import human_activity
from beyo_manager.services.infra.redis import async_client
from tests.helpers.fake_async_redis import FakeAsyncRedis

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    human_activity.reset_for_tests()
    jwt_dep._claim_cache.clear()

    async def _not_blocklisted(_jti: str) -> bool:
        return False

    monkeypatch.setattr(jwt_dep.auth, "is_token_blocklisted", _not_blocklisted)
    monkeypatch.setattr(refresh_module, "is_token_blocklisted", _not_blocklisted)
    # Keep the legacy tracker out of these tests unless one opts in.
    monkeypatch.setattr(settings, "sleep_mode_enabled", False)
    yield
    human_activity.reset_for_tests()
    jwt_dep._claim_cache.clear()


@pytest.fixture
def fake_redis(monkeypatch) -> FakeAsyncRedis:
    redis = FakeAsyncRedis()
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    return redis


def _token(scope: str = "manager", user_id: str = "usr_1", jti: str | None = None) -> str:
    return jwt.encode(
        {"user_id": user_id, "app_scope": scope, "jti": jti or f"jti-{scope}-{user_id}"},
        settings.jwt_secret_key,
        algorithm="HS256",
    )


def _auth(scope: str = "manager", activity: str | None = None, **kw) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_token(scope, **kw)}"}
    if activity is not None:
        headers["X-Beyo-Activity"] = activity
    return headers


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ActivityMiddleware)
    app.include_router(health.router, prefix="/health")
    app.include_router(auth_router.router, prefix="/api/v1/auth")

    async def _no_db():
        yield None

    app.dependency_overrides[get_db] = _no_db

    @app.get("/api/v1/me")
    async def _me_get(claims: dict = Depends(jwt_dep.get_jwt_claims)):
        return {"ok": True}

    @app.post("/api/v1/me")
    async def _me_post(claims: dict = Depends(jwt_dep.get_jwt_claims)):
        return {"ok": True}

    @app.options("/api/v1/me")
    async def _me_options(claims: dict = Depends(jwt_dep.get_jwt_claims)):
        return {"ok": True}

    @app.post("/api/v1/me/unauthorized")
    async def _me_401(claims: dict = Depends(jwt_dep.get_jwt_claims)):
        return JSONResponse({"detail": "no"}, status_code=401)

    @app.post("/api/v1/roles")
    async def _roles(claims: dict = Depends(jwt_dep.require_roles(["admin"]))):
        return {"ok": True}

    @app.post("/api/v1/anonymous")
    async def _anonymous():
        return {"ok": True}

    @app.post("/api/v1/location-tracker/webhooks/stock-demand")
    async def _webhook():
        return {"ok": True}

    return app


def _key() -> str:
    return f"{settings.redis_key_prefix}:activity:human"


# ── the rule table ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("method", "path", "headers", "status", "recorded"),
    [
        # authenticated, by method × marking
        ("GET", "/api/v1/me", _auth(), 200, False),                         # no header GET
        ("GET", "/api/v1/me", _auth(activity="background"), 200, False),
        ("GET", "/api/v1/me", _auth(activity="user"), 200, True),
        ("GET", "/api/v1/me", _auth(activity=" USER "), 200, True),         # case/space
        ("GET", "/api/v1/me", _auth(activity="garbage"), 200, False),
        ("POST", "/api/v1/me", _auth(), 200, True),                         # no header POST
        ("POST", "/api/v1/me", _auth(activity="background"), 200, False),
        ("POST", "/api/v1/me", _auth(activity="user"), 200, True),
        ("POST", "/api/v1/me", _auth(activity=""), 200, False),             # garbage
        # a validated identity refused by role is still a person acting
        ("POST", "/api/v1/roles", _auth(activity="user"), 403, True),
        # excluded
        ("OPTIONS", "/api/v1/me", _auth(activity="user"), 200, False),
        ("POST", "/api/v1/me/unauthorized", _auth(activity="user"), 401, False),
        ("POST", "/api/v1/me", {"Authorization": "Bearer not-a-jwt", "X-Beyo-Activity": "user"}, 401, False),
        ("POST", "/api/v1/me", {"X-Beyo-Activity": "user"}, 403, False),    # no credentials
        ("POST", "/api/v1/anonymous", {"X-Beyo-Activity": "user"}, 200, False),
        ("POST", "/api/v1/anonymous", _auth(activity="user"), 200, False),  # token, no dep
        ("POST", "/api/v1/location-tracker/webhooks/stock-demand", _auth(activity="user"), 200, False),
        ("GET", "/health/live", _auth(activity="user"), 200, False),
    ],
)
def test_recording_rule(fake_redis, method, path, headers, status, recorded):
    response = TestClient(_app()).request(method, path, headers=headers)

    assert response.status_code == status
    assert len(fake_redis.hset_calls) == (1 if recorded else 0)


def test_revoked_token_is_401_and_not_recorded(fake_redis, monkeypatch):
    async def _revoked(_jti: str) -> bool:
        return True

    monkeypatch.setattr(jwt_dep.auth, "is_token_blocklisted", _revoked)

    response = TestClient(_app()).post("/api/v1/me", headers=_auth(activity="user"))

    assert response.status_code == 401
    assert fake_redis.hset_calls == []


def test_storage_format(fake_redis):
    before = time.time()
    TestClient(_app()).post("/api/v1/me", headers=_auth(scope="floor"))
    after = time.time()

    [(key, fields)] = fake_redis.hset_calls
    assert key == _key()
    assert set(fields) == {"last_at", "last_at:floor", "last_source"}
    assert fields["last_source"] == "http"
    assert before <= float(fields["last_at"]) <= after
    assert fields["last_at:floor"] == fields["last_at"]
    assert fake_redis.expirations.get(key) is None  # never given a TTL


def test_same_scope_is_throttled_other_scope_is_not(fake_redis):
    client = TestClient(_app())

    client.post("/api/v1/me", headers=_auth(scope="manager", user_id="usr_a"))
    client.post("/api/v1/me", headers=_auth(scope="manager", user_id="usr_b"))
    client.get("/api/v1/me", headers=_auth(scope="manager", activity="user"))
    assert len(fake_redis.hset_calls) == 1

    client.post("/api/v1/me", headers=_auth(scope="floor"))
    assert [sorted(f) for _, f in fake_redis.hset_calls] == [
        ["last_at", "last_at:manager", "last_source"],
        ["last_at", "last_at:floor", "last_source"],
    ]


def test_throttle_window_reopens_after_30_seconds(fake_redis, monkeypatch):
    clock = [1_000.0]
    monkeypatch.setattr(human_activity, "_monotonic", lambda: clock[0])
    client = TestClient(_app())

    client.post("/api/v1/me", headers=_auth())
    clock[0] += 29.9
    client.post("/api/v1/me", headers=_auth())
    assert len(fake_redis.hset_calls) == 1

    clock[0] += 0.2
    client.post("/api/v1/me", headers=_auth())
    assert len(fake_redis.hset_calls) == 2


def test_redis_down_the_request_still_succeeds(fake_redis, caplog):
    fake_redis.fail = ConnectionError("redis://secret-host unavailable")
    client = TestClient(_app())

    first = client.post("/api/v1/me", headers=_auth(scope="manager"))
    second = client.post("/api/v1/me", headers=_auth(scope="floor"))

    assert first.status_code == 200 and first.json() == {"ok": True}
    assert second.status_code == 200
    failures = [r for r in caplog.records if "human_activity.record_failed" in r.getMessage()]
    assert len(failures) == 1  # rate-limited: two failures, one log line
    assert "secret-host" not in caplog.text


def test_write_runs_after_the_response_body_is_sent(fake_redis):
    """The write is the response's background task, not awaited before the response."""
    order: list[str] = []
    real_hset = fake_redis.hset

    async def _hset(key, *, mapping):
        order.append("write")
        return await real_hset(key, mapping=mapping)

    fake_redis.hset = _hset
    app = _app()

    async def _asgi(scope, receive, send):
        async def _send(message):
            if message["type"] == "http.response.body" and not message.get("more_body"):
                order.append("body-complete")
            await send(message)

        await app(scope, receive, _send)

    TestClient(_asgi).post("/api/v1/me", headers=_auth())

    assert order == ["body-complete", "write"]


# ── get_jwt_claims stamps identity ───────────────────────────────────────────────

def _bare_request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""})


async def test_claim_cache_hit_also_stamps_identity(monkeypatch):
    calls = []

    async def _not_blocklisted(jti: str) -> bool:
        calls.append(jti)
        return False

    monkeypatch.setattr(jwt_dep.auth, "is_token_blocklisted", _not_blocklisted)
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=_token("floor", "usr_9"))

    first = _bare_request()
    await jwt_dep.get_jwt_claims(creds, first)
    second = _bare_request()
    await jwt_dep.get_jwt_claims(creds, second)

    assert len(calls) == 1  # the second call was a cache hit — no I/O
    expected = {"user_id": "usr_9", "app_scope": "floor"}
    assert first.state.beyo_identity == expected
    assert second.state.beyo_identity == expected


async def test_direct_call_without_request_still_works():
    from fastapi.security import HTTPAuthorizationCredentials

    claims = await jwt_dep.get_jwt_claims(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=_token())
    )
    assert claims["user_id"] == "usr_1"


# ── refresh ──────────────────────────────────────────────────────────────────────

def _refresh_cookie(scope: str = "manager") -> dict[str, str]:
    token = jwt.encode(
        {
            "user_id": "usr_1",
            "app_scope": scope,
            "jti": "refresh-jti",
            "token_type": "refresh",
            "exp": int(time.time()) + 3600,
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {f"{scope}_refresh_token": token}


@pytest.mark.parametrize(
    ("activity", "recorded"),
    [(None, True), ("user", True), ("background", False), ("garbage", False)],
)
def test_successful_refresh_records_unless_background(fake_redis, activity, recorded):
    client = TestClient(_app(), cookies=_refresh_cookie("manager"))
    headers = {} if activity is None else {"X-Beyo-Activity": activity}

    response = client.post("/api/v1/auth/refresh?scope=manager", headers=headers)

    assert response.status_code == 200
    if recorded:
        [(_, fields)] = fake_redis.hset_calls
        assert fields["last_source"] == "refresh"
        assert "last_at:manager" in fields
    else:
        assert fake_redis.hset_calls == []


def test_failed_refresh_is_not_recorded(fake_redis):
    client = TestClient(_app())  # no refresh cookie → rejected

    response = client.post("/api/v1/auth/refresh?scope=manager", headers={"X-Beyo-Activity": "user"})

    assert response.status_code == 401
    assert fake_redis.hset_calls == []


def test_sign_in_is_not_recorded(fake_redis, monkeypatch):
    from types import SimpleNamespace

    async def _fake_run_service(command, ctx):
        return SimpleNamespace(
            success=True, data={"access_token": "a", "_refresh_token": "r"}, error=None
        )

    async def _no_rate_limit() -> None:
        return None

    monkeypatch.setattr(auth_router, "run_service", _fake_run_service)
    app = _app()
    for route in app.routes:
        if getattr(route, "path", "") == "/api/v1/auth/sign-in":
            for dep in route.dependant.dependencies:
                if dep.name == "_rate":
                    app.dependency_overrides[dep.call] = _no_rate_limit

    response = TestClient(app).post(
        "/api/v1/auth/sign-in",
        json={"username": "u", "password": "p"},
        headers={"X-Beyo-Activity": "user"},
    )

    assert response.status_code == 200
    assert fake_redis.hset_calls == []


# ── legacy sleep touch ───────────────────────────────────────────────────────────

@pytest.fixture
def touches(monkeypatch):
    calls = []
    monkeypatch.setattr(activity_middleware.ActivityTracker, "touch", lambda: calls.append(1))
    return calls


def test_flag_true_keeps_the_legacy_touch_on_every_non_health_request(fake_redis, touches, monkeypatch):
    monkeypatch.setattr(settings, "sleep_mode_enabled", True)
    client = TestClient(_app())

    client.post("/api/v1/anonymous")                     # anonymous: touched, not recorded
    client.get("/api/v1/me", headers=_auth(activity="background"))
    client.get("/health/live")                           # health: neither

    assert touches == [1, 1]
    assert fake_redis.hset_calls == []


def test_flag_false_never_calls_touch(fake_redis, touches):
    client = TestClient(_app())

    client.post("/api/v1/anonymous")
    client.post("/api/v1/me", headers=_auth())

    assert touches == []
    assert len(fake_redis.hset_calls) == 1


def test_flag_false_the_tracker_opens_no_redis(fake_redis, monkeypatch):
    from beyo_manager.services.infra.sleep import activity_tracker

    def _no_sync_redis(*_args, **_kwargs):
        raise AssertionError("the legacy tracker must not touch Redis when sleep mode is off")

    monkeypatch.setattr(activity_tracker, "get_redis_client", _no_sync_redis)

    response = TestClient(_app()).post("/api/v1/anonymous")

    assert response.status_code == 200


# ── the real app: CORS and exclusions ────────────────────────────────────────────

def test_cors_preflight_allows_the_activity_header(monkeypatch):
    from beyo_manager import create_app

    monkeypatch.setattr(settings, "frontend_origins", ["https://app.example.test"])
    client = TestClient(create_app())

    response = client.options(
        "/api/v1/users",
        headers={
            "Origin": "https://app.example.test",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, x-beyo-activity",
        },
    )

    assert response.status_code == 200
    assert "x-beyo-activity" in response.headers["access-control-allow-headers"].lower()


def _depends_on(dependant, target) -> bool:
    return any(d.call is target or _depends_on(d, target) for d in dependant.dependencies)


def test_excluded_routes_never_depend_on_get_jwt_claims():
    """Webhooks, health, bootstrap and reset cannot stamp an identity, so never record."""
    from beyo_manager import create_app

    excluded_prefixes = (
        "/health",
        "/api/v1/bootstrap",
        "/api/v1/reset",
        "/api/v1/location-tracker/webhooks/",
        "/api/v1/connecteam/webhooks/",
        "/api/v1/shopify/webhooks",
    )
    checked = []
    routes = create_app().routes
    # The walker is not vacuous: an authenticated route is found to depend on it.
    logout = next(r for r in routes if getattr(r, "path", "") == "/api/v1/auth/logout")
    assert _depends_on(logout.dependant, jwt_dep.get_jwt_claims)
    for route in routes:
        path = getattr(route, "path", "")
        if path.startswith(excluded_prefixes) and hasattr(route, "dependant"):
            checked.append(path)
            assert not _depends_on(route.dependant, jwt_dep.get_jwt_claims), path

    # The table names real routes: health ×2, bootstrap ×2, reset, 3 Scanner, Connecteam, Shopify.
    assert len(checked) >= 10, checked
