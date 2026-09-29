"""The email IMAP IDLE watcher is off unless EMAIL_IDLE_ENABLED=true.

The feature is not ready for general use, so the default must stay false and a
disabled watcher must return without registering signal handlers, touching the
database, reading the sleep flag, or opening any mailbox.
"""

from __future__ import annotations

import logging

import pytest

from beyo_manager.config import Settings, settings
from beyo_manager.services.infra.email_idle import supervisor

pytestmark = pytest.mark.unit


def test_email_idle_enabled_defaults_to_false(monkeypatch):
    monkeypatch.delenv("EMAIL_IDLE_ENABLED", raising=False)
    monkeypatch.setenv("SECRET_KEY", "fixture")
    monkeypatch.setenv("JWT_SECRET_KEY", "fixture")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://fixture@127.0.0.1:1/fixture"
    )
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("CONNECTEAM_WEBHOOK_ENABLED", "false")

    assert Settings(_env_file=None).email_idle_enabled is False


async def test_disabled_watcher_returns_before_doing_any_work(monkeypatch, caplog):
    monkeypatch.setattr(settings, "email_idle_enabled", False)

    def _must_not_run(*args, **kwargs):
        raise AssertionError("the disabled watcher did work it should have skipped")

    monkeypatch.setattr(supervisor, "_register_shutdown_handler", _must_not_run)
    monkeypatch.setattr(supervisor, "_reconcile", _must_not_run)
    monkeypatch.setattr(supervisor, "get_db_session", _must_not_run)
    monkeypatch.setattr(supervisor, "EmailConnectionWatcher", _must_not_run)
    monkeypatch.setattr(supervisor.ActivityTracker, "is_sleeping", _must_not_run)

    with caplog.at_level(logging.INFO, logger=supervisor.__name__):
        await supervisor.run_email_idle_watcher()

    assert [
        r.getMessage() for r in caplog.records if r.name == supervisor.__name__
    ] == ["email_idle_watcher_disabled"]


async def test_enabled_watcher_stays_off_when_outbound_integrations_are_off(
    monkeypatch, caplog
):
    monkeypatch.setattr(settings, "email_idle_enabled", True)
    monkeypatch.setattr(settings, "outbound_integrations_enabled", False)

    def _must_not_run(*args, **kwargs):
        raise AssertionError("the watcher did work while outbound integrations were off")

    monkeypatch.setattr(supervisor, "_register_shutdown_handler", _must_not_run)
    monkeypatch.setattr(supervisor, "_reconcile", _must_not_run)
    monkeypatch.setattr(supervisor, "get_db_session", _must_not_run)
    monkeypatch.setattr(supervisor, "EmailConnectionWatcher", _must_not_run)
    monkeypatch.setattr(supervisor.ActivityTracker, "is_sleeping", _must_not_run)

    with caplog.at_level(logging.INFO, logger=supervisor.__name__):
        await supervisor.run_email_idle_watcher()

    assert [
        r.getMessage() for r in caplog.records if r.name == supervisor.__name__
    ] == ["email_idle_watcher_disabled | reason=outbound_integrations_disabled"]
