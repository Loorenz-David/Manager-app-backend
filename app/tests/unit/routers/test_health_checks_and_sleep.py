"""Health checks do not count as activity, and /health reports outages as a 503.

Before: every request, health checks included, touched the sleep tracker in Redis.
A monitor polling /health kept the system awake forever, and with Redis down the
middleware raised first, so /health answered 500 instead of reporting the outage.

ActivityMiddleware replaced SleepMiddleware. The legacy touch survives only with
SLEEP_MODE_ENABLED=true (still every non-health request, anonymous included); human
activity is a separate, authenticated-only signal — see test_activity_middleware.py.
"""

from __future__ import annotations

import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.config import settings
from beyo_manager.routers.api_v1 import health
from beyo_manager.routers.middleware import activity as activity_middleware
from beyo_manager.routers.middleware.activity import ActivityMiddleware

pytestmark = pytest.mark.unit


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ActivityMiddleware)
    app.include_router(health.router, prefix="/health")

    @app.get("/api/v1/anything")
    async def _anything():
        return {"ok": True}

    return app


@pytest.fixture
def touches(monkeypatch):
    calls = []
    monkeypatch.setattr(activity_middleware.ActivityTracker, "touch", lambda: calls.append(1))
    return calls


@pytest.fixture
def records(monkeypatch):
    calls = []

    async def _record(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(activity_middleware, "record_human_activity", _record)
    return calls


@pytest.fixture
def db_ok(monkeypatch):
    async def _ok():
        return None

    monkeypatch.setattr(health, "_check_db", _ok)


def test_health_checks_do_not_count_as_activity(touches, records, db_ok, monkeypatch):
    monkeypatch.setattr(settings, "sleep_mode_enabled", True)
    monkeypatch.setattr(health, "_check_redis", lambda: None)
    client = TestClient(_app())

    assert client.get("/health/live").status_code == 200
    assert client.get("/health").status_code == 200
    assert touches == []

    # Legacy (flag on): an anonymous API request still touches the sleep tracker...
    client.get("/api/v1/anything")
    assert touches == [1]
    # ...but it is not human activity: nothing validated an identity.
    assert records == []


def test_anonymous_requests_neither_touch_nor_record_with_sleep_mode_off(
    touches, records, db_ok, monkeypatch
):
    monkeypatch.setattr(settings, "sleep_mode_enabled", False)
    monkeypatch.setattr(health, "_check_redis", lambda: None)
    client = TestClient(_app())

    client.get("/api/v1/anything", headers={"X-Beyo-Activity": "user"})
    client.get("/health")

    assert touches == []
    assert records == []


def test_liveness_checks_no_dependency(touches, monkeypatch):
    def _must_not_run(*args, **kwargs):
        raise AssertionError("liveness must not check dependencies")

    monkeypatch.setattr(health, "_check_db", _must_not_run)
    monkeypatch.setattr(health, "_check_redis", _must_not_run)

    response = TestClient(_app()).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_redis_down_is_a_503_not_a_500_and_leaks_no_detail(db_ok, monkeypatch):
    # The real middleware and tracker: Redis is unreachable for both.
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")

    response = TestClient(_app(), raise_server_exceptions=False).get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"] == {"db": "ok", "redis": "error: ConnectionError"}
    assert "127.0.0.1" not in response.text


async def test_a_hung_dependency_times_out_instead_of_hanging_the_check(db_ok, monkeypatch):
    # Timed on the handler: TestClient would also wait for the blocked thread when it
    # shuts its event loop down after the request, which a running server never does.
    release = threading.Event()
    monkeypatch.setattr(health, "_CHECK_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(health, "_check_redis", lambda: release.wait(10))

    started = time.monotonic()
    try:
        response = await health.health_check()
    finally:
        release.set()

    assert time.monotonic() - started < 2
    assert response.status_code == 503
    assert b'"redis":"error: TimeoutError"' in response.body
