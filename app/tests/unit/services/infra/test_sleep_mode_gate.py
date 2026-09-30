"""In-app sleep is gated on SLEEP_MODE_ENABLED inside ActivityTracker (B-1 / R3).

With the setting false, a leftover ``{prefix}:system:sleeping`` key (it has no TTL)
must not stall the task router or the schedulers, and no tracker call may create a
Redis client. With it true (legacy), the key still blocks.

The Redis client factory is patched at its source (``redis.from_url`` as used by
``services/infra/redis/client.py``), so a tracker call that reaches Redis at all is
seen, whichever import path it went through.
"""

from __future__ import annotations

import asyncio

import pytest

from beyo_manager.config import settings
from beyo_manager.services.infra.execution import task_router
from beyo_manager.services.infra.redis import client as redis_client_module
from beyo_manager.services.infra.schedulers import (
    delayed_scheduler_runner,
    recurring_scheduler_runner,
)
from beyo_manager.services.infra.sleep.activity_tracker import (
    _SLEEP_KEY,
    ActivityTracker,
    _key,
)

pytestmark = pytest.mark.unit


class _Stop(BaseException):
    """Escapes the runners' `except Exception` so an endless loop can end a test."""


class _FakeRedis:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.commands: list[str] = []

    def exists(self, key: str) -> int:
        self.commands.append("exists")
        return int(key in self.values)

    def delete(self, key: str) -> int:
        self.commands.append("delete")
        return int(self.values.pop(key, None) is not None)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.commands.append("set")
        self.values[key] = value

    def get(self, key: str) -> str | None:
        self.commands.append("get")
        return self.values.get(key)


@pytest.fixture
def leftover_sleep_key(monkeypatch):
    """Redis, as the tracker would see it, holding a leftover sleeping key.

    Returns the list of client-factory calls (one per client the tracker creates)
    and the fake store.
    """
    monkeypatch.setattr(settings, "redis_url", "redis://sleep-gate-test:6379/0")
    fake = _FakeRedis({_key(_SLEEP_KEY): "1"})
    factory_calls: list[str] = []

    def _from_url(url, **_kwargs):
        factory_calls.append(url)
        return fake

    monkeypatch.setattr(redis_client_module.redis, "from_url", _from_url)
    return factory_calls, fake


def _flag(monkeypatch, value: bool) -> None:
    monkeypatch.setattr(settings, "sleep_mode_enabled", value)


# ---------------------------------------------------------------------------
# The tracker itself
# ---------------------------------------------------------------------------


def test_disabled_tracker_is_inert_and_creates_no_redis_client(
    monkeypatch, leftover_sleep_key
) -> None:
    factory_calls, fake = leftover_sleep_key
    _flag(monkeypatch, False)

    assert ActivityTracker.is_sleeping() is False
    assert ActivityTracker.idle_seconds() == 0.0
    assert ActivityTracker.touch() is None
    assert ActivityTracker.enter_sleep() is None

    assert factory_calls == []
    assert fake.commands == []
    # The leftover key is ignored, not cleared: touch() did not run.
    assert _key(_SLEEP_KEY) in fake.values


def test_disabled_tracker_never_constructs_a_client_via_the_tracker_import(
    monkeypatch,
) -> None:
    """Belt and braces: the tracker's own bound factory is never called either."""
    from beyo_manager.services.infra.sleep import activity_tracker

    calls: list[str] = []

    def _must_not_run(*args, **kwargs):
        calls.append("called")
        raise AssertionError("no Redis client may be created when sleep mode is off")

    monkeypatch.setattr(activity_tracker, "get_redis_client", _must_not_run)
    _flag(monkeypatch, False)

    ActivityTracker.touch()
    ActivityTracker.enter_sleep()
    assert ActivityTracker.is_sleeping() is False
    assert ActivityTracker.idle_seconds() == 0.0
    assert calls == []


def test_enabled_tracker_still_reads_the_sleeping_key(
    monkeypatch, leftover_sleep_key
) -> None:
    factory_calls, fake = leftover_sleep_key
    _flag(monkeypatch, True)

    assert ActivityTracker.is_sleeping() is True
    assert factory_calls  # legacy path reaches Redis

    ActivityTracker.touch()
    assert _key(_SLEEP_KEY) not in fake.values
    assert ActivityTracker.is_sleeping() is False

    ActivityTracker.enter_sleep()
    assert ActivityTracker.is_sleeping() is True


def test_gate_is_read_at_call_time(monkeypatch, leftover_sleep_key) -> None:
    _flag(monkeypatch, True)
    assert ActivityTracker.is_sleeping() is True
    _flag(monkeypatch, False)
    assert ActivityTracker.is_sleeping() is False


# ---------------------------------------------------------------------------
# Task router
# ---------------------------------------------------------------------------


@pytest.fixture
def router_harness(monkeypatch):
    """Runs the real `run_task_router` loop with its side tasks and I/O stubbed."""
    routed: list[object] = []

    async def _idle() -> None:
        return None

    async def _route(_redis) -> None:
        routed.append(_redis)
        raise _Stop

    queue_client = object()
    monkeypatch.setattr(task_router, "_listen_for_task_events", _idle)
    monkeypatch.setattr(task_router, "_sleep_monitor", _idle)
    monkeypatch.setattr(task_router, "get_redis_client", lambda _url: queue_client)
    monkeypatch.setattr(task_router, "_route_open_tasks", _route)
    monkeypatch.setattr(task_router, "FALLBACK_POLL_SECONDS", 0.01)
    # A module-level Event binds to the first loop that waits on it; give this
    # test's loop its own.
    monkeypatch.setattr(task_router, "_notify_event", asyncio.Event())
    return routed, queue_client


async def test_router_routes_despite_leftover_key_when_sleep_mode_off(
    monkeypatch, leftover_sleep_key, router_harness
) -> None:
    factory_calls, _fake = leftover_sleep_key
    routed, queue_client = router_harness
    _flag(monkeypatch, False)

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert routed == [queue_client]
    assert factory_calls == []  # the tracker's is_sleeping() gate never touched Redis


async def test_router_still_blocked_by_sleeping_key_when_sleep_mode_on(
    monkeypatch, leftover_sleep_key, router_harness
) -> None:
    factory_calls, _fake = leftover_sleep_key
    routed, _queue_client = router_harness
    _flag(monkeypatch, True)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(task_router.run_task_router(), timeout=0.3)

    assert routed == []
    assert factory_calls  # legacy: the key was read and it blocked routing


# ---------------------------------------------------------------------------
# Schedulers
# ---------------------------------------------------------------------------

_SCHEDULERS = [
    pytest.param(
        delayed_scheduler_runner,
        "run_delayed_scheduler_runner",
        "_fire_due_schedulers",
        id="delayed",
    ),
    pytest.param(
        recurring_scheduler_runner,
        "run_recurring_scheduler_runner",
        "_fire_due_recurring_schedulers",
        id="recurring",
    ),
]


def _stub_fire(monkeypatch, module, fire_name: str) -> list[int]:
    fired: list[int] = []

    async def _fire() -> None:
        fired.append(1)
        raise _Stop

    monkeypatch.setattr(module, fire_name, _fire)
    return fired


@pytest.mark.parametrize(("module", "runner_name", "fire_name"), _SCHEDULERS)
async def test_scheduler_fires_despite_leftover_key_when_sleep_mode_off(
    monkeypatch, leftover_sleep_key, module, runner_name, fire_name
) -> None:
    factory_calls, _fake = leftover_sleep_key
    fired = _stub_fire(monkeypatch, module, fire_name)
    _flag(monkeypatch, False)

    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner_name)(), timeout=5)

    assert fired == [1]
    assert factory_calls == []


@pytest.mark.parametrize(("module", "runner_name", "fire_name"), _SCHEDULERS)
async def test_scheduler_still_blocked_by_sleeping_key_when_sleep_mode_on(
    monkeypatch, leftover_sleep_key, module, runner_name, fire_name
) -> None:
    factory_calls, _fake = leftover_sleep_key
    fired = _stub_fire(monkeypatch, module, fire_name)
    _flag(monkeypatch, True)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(getattr(module, runner_name)(), timeout=0.3)

    assert fired == []
    assert factory_calls
