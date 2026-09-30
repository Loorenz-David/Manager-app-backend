"""The rate limiter fails closed as a 503 auth_unavailable when Redis is down.

Before: the Redis error escaped the dependency and sign-in answered a bare 500.
Silently allowing the request instead would disable brute-force protection on
sign-in for the length of the outage, so the limiter refuses — retryably.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from beyo_manager.config import settings
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import auth as auth_router
from beyo_manager.routers.utils import rate_limit

pytestmark = pytest.mark.unit


class _Pipeline:
    def __init__(self, store: dict[str, int], *, down: bool) -> None:
        self.store = store
        self.down = down
        self.ops: list[tuple[str, str]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def incr(self, key: str) -> None:
        self.ops.append(("incr", key))

    async def expire(self, key: str, _seconds: int) -> None:
        self.ops.append(("expire", key))

    async def execute(self) -> list:
        if self.down:
            raise ConnectionError("redis unavailable")
        results = []
        for op, key in self.ops:
            if op == "incr":
                self.store[key] = self.store.get(key, 0) + 1
                results.append(self.store[key])
            else:
                results.append(True)
        return results


class _FakeAsyncRedis:
    def __init__(self, *, down: bool) -> None:
        self.down = down
        self.store: dict[str, int] = {}

    def pipeline(self, transaction: bool = True) -> _Pipeline:
        return _Pipeline(self.store, down=self.down)


@pytest.fixture
def enforced(monkeypatch):
    # The limiter is a no-op in development/testing; enforce it here.
    monkeypatch.setattr(settings, "environment", "production")


def _sign_in_client(monkeypatch) -> TestClient:
    async def _no_db():
        yield object()

    async def _service_must_not_run(*_args, **_kwargs):
        raise AssertionError("sign-in must not run when the rate limiter is unavailable")

    monkeypatch.setattr(auth_router, "run_service", _service_must_not_run)
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/v1/auth")
    app.dependency_overrides[get_db] = _no_db
    return TestClient(app)


_SIGN_IN_BODY = {"email": "manager@test.local", "password": "Test1234!"}


def test_sign_in_is_503_auth_unavailable_when_rate_limit_redis_is_down(
    enforced, monkeypatch
) -> None:
    monkeypatch.setattr(rate_limit, "get_async_redis", lambda: _FakeAsyncRedis(down=True))

    response = _sign_in_client(monkeypatch).post("/api/v1/auth/sign-in", json=_SIGN_IN_BODY)

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    detail = response.json()["detail"]
    assert detail["code"] == "auth_unavailable"
    assert detail["ok"] is False
    assert detail["reason"] == "rate_limit_unavailable"


def test_sign_in_is_503_when_the_redis_client_cannot_even_be_built(
    enforced, monkeypatch
) -> None:
    def _broken():
        raise ValueError("bad redis url")

    monkeypatch.setattr(rate_limit, "get_async_redis", _broken)

    response = _sign_in_client(monkeypatch).post("/api/v1/auth/sign-in", json=_SIGN_IN_BODY)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "auth_unavailable"


def test_healthy_rate_limit_still_answers_429_over_the_limit(enforced, monkeypatch) -> None:
    redis = _FakeAsyncRedis(down=False)
    monkeypatch.setattr(rate_limit, "get_async_redis", lambda: redis)
    app = FastAPI()

    @app.post("/limited")
    async def _limited(_rate: None = Depends(rate_limit.ip_rate_limit(2, 60, "t"))):
        return {"ok": True}

    client = TestClient(app)
    assert client.post("/limited").status_code == 200
    assert client.post("/limited").status_code == 200
    over = client.post("/limited")
    assert over.status_code == 429
    assert "Retry-After" not in over.headers
