"""Connection URLs must never reach a log with their password.

Covers `redact_url` itself, the API startup line that logs `DATABASE_URL` and
`REDIS_URL`, and the `create_db` script's parse error. Nothing here touches a
database or Redis.
"""

from __future__ import annotations

import logging

import pytest

import beyo_manager
from beyo_manager.config import settings
from beyo_manager.core.logging.formatter import StructuredJsonFormatter
from beyo_manager.core.logging.redaction import (
    UNPARSEABLE_URL,
    UNSET_URL,
    redact_url,
)
from beyo_manager.models import database as database_module

pytestmark = pytest.mark.unit

_DB_PASSWORD = "Db-Pa55w0rd-that-must-not-leak"
_REDIS_PASSWORD = "Redis-Pa55w0rd-that-must-not-leak"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            f"postgresql+asyncpg://app_user:{_DB_PASSWORD}@db.internal:5432/manager_prod",
            "postgresql+asyncpg://app_user:***@db.internal:5432/manager_prod",
        ),
        (
            f"redis://:{_REDIS_PASSWORD}@cache.internal:6379/0",
            "redis://:***@cache.internal:6379/0",
        ),
        (
            f"rediss://default:{_REDIS_PASSWORD}@cache.internal:6380/2",
            "rediss://default:***@cache.internal:6380/2",
        ),
        (
            "postgresql+asyncpg://postgres@localhost:5433/beyo_manager",
            "postgresql+asyncpg://postgres@localhost:5433/beyo_manager",
        ),
        ("redis://127.0.0.1:6379/0", "redis://127.0.0.1:6379/0"),
        (
            f"postgresql://u:{_DB_PASSWORD}@[::1]:5432/db",
            "postgresql://u:***@[::1]:5432/db",
        ),
    ],
)
def test_redact_url_keeps_location_and_hides_password(url, expected):
    assert redact_url(url) == expected


def test_redact_url_drops_the_query_string_because_it_can_carry_credentials():
    url = f"postgresql+asyncpg://u@h:5432/db?sslmode=require&password={_DB_PASSWORD}"

    redacted = redact_url(url)

    assert _DB_PASSWORD not in redacted
    assert "sslmode" not in redacted
    assert redacted == "postgresql+asyncpg://u@h:5432/db?<query-redacted>"


def test_redact_url_hides_a_password_that_contains_url_delimiters():
    password = "p@ss:w/rd#1"
    redacted = redact_url(f"postgresql://user:{password}@host:5432/db")

    assert password not in redacted
    assert "ss:w" not in redacted


@pytest.mark.parametrize("url", [None, ""])
def test_redact_url_reports_an_unset_url(url):
    assert redact_url(url) == UNSET_URL


@pytest.mark.parametrize(
    "url",
    [
        f"not a url but it holds {_DB_PASSWORD}",
        f"postgresql://user:{_DB_PASSWORD}@host:notaport/db",
        f"{_DB_PASSWORD}",
        f"://user:{_DB_PASSWORD}@host/db",
    ],
)
def test_redact_url_never_falls_back_to_the_raw_input(url):
    assert redact_url(url) == UNPARSEABLE_URL


async def test_startup_log_line_does_not_contain_connection_passwords(
    monkeypatch, caplog
):
    async def _noop():
        return None

    monkeypatch.setattr(database_module, "init_db", _noop)
    monkeypatch.setattr(database_module, "close_db", _noop)
    monkeypatch.setattr(
        settings,
        "database_url",
        f"postgresql+asyncpg://app_user:{_DB_PASSWORD}@db.internal:5432/manager_prod",
    )
    monkeypatch.setattr(
        settings, "redis_url", f"redis://:{_REDIS_PASSWORD}@cache.internal:6379/0"
    )

    with caplog.at_level(logging.INFO, logger="beyo_manager.startup"):
        async with beyo_manager.lifespan(None):
            pass

    startup_records = [r for r in caplog.records if r.name == "beyo_manager.startup"]
    assert startup_records, "the startup line was not emitted"

    formatter = StructuredJsonFormatter()
    emitted = "\n".join(formatter.format(r) for r in startup_records)
    assert _DB_PASSWORD not in emitted
    assert _REDIS_PASSWORD not in emitted
    assert "db.internal:5432/manager_prod" in emitted
    assert "cache.internal:6379/0" in emitted


def test_create_db_parse_error_does_not_echo_the_password():
    from scripts.create_db import _admin_dsn

    with pytest.raises(RuntimeError) as excinfo:
        _admin_dsn(f"postgresql+asyncpg://app_user:{_DB_PASSWORD}@db.internal:5432/")

    assert _DB_PASSWORD not in str(excinfo.value)
