"""Bootstrap, wipe-db and reset are development tools, never production capabilities.

Production must refuse all three even with DESTRUCTIVE_ENDPOINTS_ENABLED=true and the
correct secret. Outside production they need an explicitly set non-production
ENVIRONMENT, the flag, and the right secret. Every refusal must happen before a
database session opens and before any bootstrap or deletion logic runs.

Each test builds a fresh `Settings` from a controlled environment, so a missing or
malformed ENVIRONMENT is exercised for real. The session opener and the services are
replaced with recorders; nothing here touches a database.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.config import Settings
from beyo_manager.routers.api_v1 import bootstrap as bootstrap_module
from beyo_manager.routers.api_v1 import reset as reset_module
from beyo_manager.routers.utils import destructive_guard

pytestmark = pytest.mark.unit

_BOOTSTRAP_SECRET = "fixture-bootstrap-secret"
_RESET_SECRET = "fixture-reset-secret"

_BASE_ENV = {
    "SECRET_KEY": "fixture-secret-key",
    "JWT_SECRET_KEY": "fixture-jwt-secret",
    "DATABASE_URL": "postgresql+asyncpg://fixture@127.0.0.1:1/fixture",
    "REDIS_URL": "redis://127.0.0.1:1/0",
    "CONNECTEAM_WEBHOOK_ENABLED": "false",
    "BOOTSTRAP_SECRET": _BOOTSTRAP_SECRET,
    "RESET_SECRET": _RESET_SECRET,
}

_ALL_ROUTES = [
    ("POST", "/api/v1/bootstrap", {"X-Bootstrap-Secret": _BOOTSTRAP_SECRET}),
    ("DELETE", "/api/v1/bootstrap/wipe-db", {"X-Bootstrap-Secret": _BOOTSTRAP_SECRET}),
    (
        "DELETE",
        "/api/v1/reset?workspace_id=ws_fixture",
        {"X-Reset-Secret": _RESET_SECRET},
    ),
]


class _Recorder:
    def __init__(self):
        self.sessions_opened = 0
        self.services_run = []


def _client(monkeypatch, *, environment, flag):
    """App with the three routes, settings built from a controlled environment."""
    for key in [*_BASE_ENV, "ENVIRONMENT", "DESTRUCTIVE_ENDPOINTS_ENABLED"]:
        monkeypatch.delenv(key, raising=False)
    for key, value in _BASE_ENV.items():
        monkeypatch.setenv(key, value)
    if environment is not None:
        monkeypatch.setenv("ENVIRONMENT", environment)
    if flag is not None:
        monkeypatch.setenv("DESTRUCTIVE_ENDPOINTS_ENABLED", flag)

    fresh = Settings(_env_file=None)
    for module in (destructive_guard, bootstrap_module, reset_module):
        monkeypatch.setattr(module, "settings", fresh)

    recorder = _Recorder()

    class _FakeSession:
        async def execute(self, *args, **kwargs):
            recorder.services_run.append("wipe-db")
            return []

        async def commit(self):
            return None

    async def _fake_get_db_session():
        recorder.sessions_opened += 1
        yield _FakeSession()

    async def _fake_run_service(command, ctx):
        recorder.services_run.append(command.__name__)
        return SimpleNamespace(success=True, data={"ran": command.__name__}, error=None)

    for module in (bootstrap_module, reset_module):
        monkeypatch.setattr(module, "get_db_session", _fake_get_db_session)
        monkeypatch.setattr(module, "run_service", _fake_run_service)

    app = FastAPI()
    app.include_router(bootstrap_module.router, prefix="/api/v1/bootstrap")
    app.include_router(reset_module.router, prefix="/api/v1/reset")
    return TestClient(app), recorder


def _assert_refused_before_any_work(response, recorder, status=403):
    assert response.status_code == status, response.text
    assert recorder.sessions_opened == 0
    assert recorder.services_run == []


@pytest.mark.parametrize(("method", "path", "headers"), _ALL_ROUTES)
@pytest.mark.parametrize("environment", ["production", "Production", "  PRODUCTION  "])
def test_production_rejects_even_with_flag_and_correct_secret(
    monkeypatch, method, path, headers, environment
):
    client, recorder = _client(monkeypatch, environment=environment, flag="true")

    response = client.request(method, path, headers=headers)

    _assert_refused_before_any_work(response, recorder)
    assert "production" in response.json()["detail"]


@pytest.mark.parametrize(("method", "path", "headers"), _ALL_ROUTES)
def test_production_rejects_even_when_reset_secret_is_unset(
    monkeypatch, method, path, headers
):
    """The environment boundary runs before the reset route's own 501 check."""
    client, recorder = _client(monkeypatch, environment="production", flag="true")
    monkeypatch.setattr(reset_module.settings, "reset_secret", "")

    response = client.request(method, path, headers=headers)

    _assert_refused_before_any_work(response, recorder)


@pytest.mark.parametrize(("method", "path", "headers"), _ALL_ROUTES)
@pytest.mark.parametrize(
    "environment", [None, "", "prod", "prd", "live", "development-ish"]
)
def test_missing_or_unrecognised_environment_fails_closed(
    monkeypatch, method, path, headers, environment
):
    client, recorder = _client(monkeypatch, environment=environment, flag="true")

    response = client.request(method, path, headers=headers)

    _assert_refused_before_any_work(response, recorder)


@pytest.mark.parametrize(("method", "path", "headers"), _ALL_ROUTES)
@pytest.mark.parametrize("flag", [None, "false", "0"])
def test_non_production_requires_the_flag(monkeypatch, method, path, headers, flag):
    client, recorder = _client(monkeypatch, environment="development", flag=flag)

    response = client.request(method, path, headers=headers)

    _assert_refused_before_any_work(response, recorder)
    assert "DESTRUCTIVE_ENDPOINTS_ENABLED" in response.json()["detail"]


@pytest.mark.parametrize(
    ("method", "path", "header_name"),
    [
        ("POST", "/api/v1/bootstrap", "X-Bootstrap-Secret"),
        ("DELETE", "/api/v1/bootstrap/wipe-db", "X-Bootstrap-Secret"),
        ("DELETE", "/api/v1/reset?workspace_id=ws_fixture", "X-Reset-Secret"),
    ],
)
@pytest.mark.parametrize(
    "supplied", [None, "", "wrong-secret", _BOOTSTRAP_SECRET + "x"]
)
def test_non_production_with_flag_still_requires_the_right_secret(
    monkeypatch, method, path, header_name, supplied
):
    client, recorder = _client(monkeypatch, environment="development", flag="true")
    headers = {} if supplied is None else {header_name: supplied}

    response = client.request(method, path, headers=headers)

    _assert_refused_before_any_work(response, recorder)


def test_reset_keeps_its_501_when_reset_secret_is_unset(monkeypatch):
    client, recorder = _client(monkeypatch, environment="development", flag="true")
    monkeypatch.setattr(reset_module.settings, "reset_secret", "")

    response = client.delete(
        "/api/v1/reset?workspace_id=ws_fixture", headers={"X-Reset-Secret": "anything"}
    )

    _assert_refused_before_any_work(response, recorder, status=501)


@pytest.mark.parametrize(
    "environment", ["development", "testing", "validation", "staging", " Development "]
)
@pytest.mark.parametrize(
    ("method", "path", "headers", "expected_work"),
    [
        (
            "POST",
            "/api/v1/bootstrap",
            {"X-Bootstrap-Secret": _BOOTSTRAP_SECRET},
            "bootstrap_app",
        ),
        (
            "DELETE",
            "/api/v1/bootstrap/wipe-db",
            {"X-Bootstrap-Secret": _BOOTSTRAP_SECRET},
            "wipe-db",
        ),
        (
            "DELETE",
            "/api/v1/reset?workspace_id=ws_fixture",
            {"X-Reset-Secret": _RESET_SECRET},
            "reset_app",
        ),
    ],
)
def test_non_production_with_flag_and_secret_is_allowed(
    monkeypatch, environment, method, path, headers, expected_work
):
    client, recorder = _client(monkeypatch, environment=environment, flag="true")

    response = client.request(method, path, headers=headers)

    assert response.status_code == 200, response.text
    assert recorder.sessions_opened == 1
    assert recorder.services_run == [expected_work]


@pytest.mark.parametrize(
    ("provided", "expected", "matches"),
    [
        ("abc", "abc", True),
        ("abc", "abd", False),
        ("abc", "abcd", False),
        ("", "abc", False),
        (None, "abc", False),
        ("abc", "", False),
        ("abc", None, False),
        (None, None, False),
        ("", "", False),
    ],
)
def test_secret_matches(provided, expected, matches):
    assert destructive_guard.secret_matches(provided, expected) is matches
