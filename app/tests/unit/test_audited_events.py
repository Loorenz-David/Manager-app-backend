import os
import pytest

from beyo_manager.services.infra.audit.audited_events import (
    _BASE_AUDITED_EVENTS,
    _EXTENSIONS,
    get_audited_events,
    register_audited_events,
)


@pytest.fixture(autouse=True)
def _clear_extensions():
    _EXTENSIONS.clear()
    yield
    _EXTENSIONS.clear()


@pytest.mark.unit
def test_base_defaults_non_empty():
    result = get_audited_events()
    assert len(result) > 0
    assert "auth:signed-in" in result


@pytest.mark.unit
def test_register_extends_set():
    register_audited_events({"domain:custom-event"})
    result = get_audited_events()
    assert "domain:custom-event" in result


@pytest.mark.unit
def test_env_override_merges(monkeypatch):
    monkeypatch.setenv("AUDITED_EVENTS", "env:event-a, env:event-b")
    result = get_audited_events()
    assert "env:event-a" in result
    assert "env:event-b" in result


@pytest.mark.unit
def test_env_override_empty_string_ignored(monkeypatch):
    monkeypatch.setenv("AUDITED_EVENTS", "")
    result = get_audited_events()
    assert result == get_audited_events()  # stable — just base defaults


@pytest.mark.unit
def test_base_events_not_mutated():
    register_audited_events({"extra:event"})
    assert "extra:event" not in _BASE_AUDITED_EVENTS
