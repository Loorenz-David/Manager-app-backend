"""The progress file behind the router/scheduler readiness check (B-10).

WORKER_PROGRESS_FILE is touched by the task router and both schedulers only after a
loop iteration whose database work returned. An iteration that raises leaves it
alone (and the loop keeps going after a backoff); a database call that hangs never
reaches the touch, so the file goes stale. Unset, nothing is written.

The real loops run here with their database functions stubbed; `_Stop` is a
BaseException, so it escapes the loops' `except Exception` and ends a test.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from beyo_manager.config import settings
from beyo_manager.services.infra.execution import task_router
from beyo_manager.services.infra.schedulers import (
    delayed_scheduler_runner,
    recurring_scheduler_runner,
)
from beyo_manager.workers import heartbeat

pytestmark = pytest.mark.unit


class _Stop(BaseException):
    pass


class _AwakeTracker:
    @staticmethod
    def is_sleeping() -> bool:
        return False

    @staticmethod
    def touch() -> None:
        return None


class _SleepingTracker(_AwakeTracker):
    @staticmethod
    def is_sleeping() -> bool:
        return True


@pytest.fixture
def progress_path(monkeypatch, tmp_path):
    path = tmp_path / "progress"
    monkeypatch.setattr(settings, "worker_progress_file", str(path))
    return path


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    for module in (task_router, delayed_scheduler_runner, recurring_scheduler_runner):
        monkeypatch.setattr(module, "error_backoff_seconds", lambda _n: 0)


def _make_stale(path) -> int:
    path.touch()
    old = time.time() - 3600
    os.utime(path, (old, old))
    return os.stat(path).st_mtime_ns


# ---------------------------------------------------------------------------
# touch_progress / backoff
# ---------------------------------------------------------------------------


def test_unset_env_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "worker_progress_file", None)
    heartbeat.touch_progress()
    assert list(tmp_path.iterdir()) == []
    assert heartbeat.progress_enabled() is False


def test_touch_progress_writes_the_file(progress_path):
    heartbeat.touch_progress()
    assert progress_path.exists()


def test_error_backoff_grows_and_is_capped():
    values = [heartbeat.error_backoff_seconds(n) for n in range(1, 8)]
    assert values[0] == heartbeat.ERROR_BACKOFF_BASE_SECONDS
    assert values == sorted(values)
    assert max(values) == heartbeat.ERROR_BACKOFF_MAX_SECONDS


def test_idle_cadences_stay_well_inside_the_60s_readiness_window():
    # A loop must finish an iteration (and touch progress) at least every ~30 s idle.
    assert task_router.FALLBACK_POLL_SECONDS <= 30
    assert delayed_scheduler_runner.POLL_INTERVAL_SECONDS <= 30
    assert recurring_scheduler_runner.POLL_INTERVAL_SECONDS <= 30
    assert heartbeat.PROGRESS_MAX_IDLE_SECONDS <= 30


# ---------------------------------------------------------------------------
# Task router
# ---------------------------------------------------------------------------


@pytest.fixture
def router(monkeypatch):
    """The real run_task_router with side tasks and database functions stubbed.

    Returns a dict of call counters and a `route` hook the test replaces.
    """
    state: dict = {"route_calls": 0, "tail_calls": 0}

    async def _idle() -> None:
        return None

    async def _ok() -> None:
        return None

    async def _tail() -> None:
        state["tail_calls"] += 1
        stop_after = state.get("stop_after_tail")
        if stop_after is not None and state["tail_calls"] >= stop_after:
            raise _Stop

    monkeypatch.setattr(task_router, "_listen_for_task_events", _idle)
    monkeypatch.setattr(task_router, "_sleep_monitor", _idle)
    monkeypatch.setattr(task_router, "get_redis_client", lambda _url: object())
    monkeypatch.setattr(task_router, "_requeue_retry_scheduled_tasks", _ok)
    monkeypatch.setattr(task_router, "_cleanup_stale_tasks", _ok)
    monkeypatch.setattr(task_router, "_recover_stuck_pending_tasks", _tail)
    monkeypatch.setattr(task_router, "FALLBACK_POLL_SECONDS", 0.01)
    monkeypatch.setattr(task_router, "_notify_event", asyncio.Event())
    monkeypatch.setattr(task_router, "ActivityTracker", _AwakeTracker)
    return state


async def test_router_touches_progress_after_a_successful_iteration(
    monkeypatch, progress_path, router
):
    async def _route(_redis) -> None:
        router["route_calls"] += 1

    monkeypatch.setattr(task_router, "_route_open_tasks", _route)
    router["stop_after_tail"] = 2  # stop inside the second iteration

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert router["route_calls"] == 2
    assert progress_path.exists()  # touched once, after iteration 1


async def test_router_does_not_touch_progress_when_the_db_call_raises(
    monkeypatch, progress_path, router
):
    async def _route(_redis) -> None:
        router["route_calls"] += 1
        if router["route_calls"] >= 3:
            raise _Stop
        raise ConnectionRefusedError("db down")

    monkeypatch.setattr(task_router, "_route_open_tasks", _route)

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert router["route_calls"] == 3  # the loop survived two failed iterations
    assert not progress_path.exists()


async def test_router_survives_a_transient_db_error_and_touches_after_recovery(
    monkeypatch, progress_path, router
):
    async def _route(_redis) -> None:
        router["route_calls"] += 1
        if router["route_calls"] == 1:
            raise ConnectionRefusedError("db down")

    monkeypatch.setattr(task_router, "_route_open_tasks", _route)
    router["stop_after_tail"] = 2

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert router["route_calls"] == 3
    assert progress_path.exists()


async def test_router_progress_goes_stale_while_a_db_call_hangs(
    monkeypatch, progress_path, router
):
    before = _make_stale(progress_path)
    hanging = asyncio.Event()

    async def _route(_redis) -> None:
        router["route_calls"] += 1
        await hanging.wait()  # never set

    monkeypatch.setattr(task_router, "_route_open_tasks", _route)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(task_router.run_task_router(), timeout=0.3)

    assert router["route_calls"] == 1
    assert os.stat(progress_path).st_mtime_ns == before


async def test_router_is_sleeping_error_is_caught_not_fatal(
    monkeypatch, progress_path, router
):
    calls = {"n": 0}

    class _FlakyTracker(_AwakeTracker):
        @staticmethod
        def is_sleeping() -> bool:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("redis down")
            return False

    async def _route(_redis) -> None:
        router["route_calls"] += 1

    monkeypatch.setattr(task_router, "ActivityTracker", _FlakyTracker)
    monkeypatch.setattr(task_router, "_route_open_tasks", _route)
    router["stop_after_tail"] = 2

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert calls["n"] >= 3
    assert progress_path.exists()


async def test_router_without_progress_file_writes_nothing(monkeypatch, tmp_path, router):
    monkeypatch.setattr(settings, "worker_progress_file", None)

    async def _route(_redis) -> None:
        router["route_calls"] += 1

    monkeypatch.setattr(task_router, "_route_open_tasks", _route)
    router["stop_after_tail"] = 2

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert list(tmp_path.iterdir()) == []


async def test_router_in_app_sleeping_still_pings_and_touches_when_progress_on(
    monkeypatch, progress_path, router
):
    pings = {"n": 0}

    async def _ping() -> None:
        pings["n"] += 1
        if pings["n"] >= 3:
            raise _Stop

    async def _route(_redis) -> None:  # must never run while sleeping
        raise AssertionError("routed while sleeping")

    monkeypatch.setattr(task_router, "ActivityTracker", _SleepingTracker)
    monkeypatch.setattr(task_router, "PROGRESS_MAX_IDLE_SECONDS", 0.01)
    monkeypatch.setattr(task_router, "_ping_database", _ping)
    monkeypatch.setattr(task_router, "_route_open_tasks", _route)

    with pytest.raises(_Stop):
        await asyncio.wait_for(task_router.run_task_router(), timeout=5)

    assert progress_path.exists()


# ---------------------------------------------------------------------------
# Schedulers
# ---------------------------------------------------------------------------

_SCHEDULERS = [
    pytest.param(
        delayed_scheduler_runner,
        "run_delayed_scheduler_runner",
        "_fire_due_schedulers",
        "_get_next_scheduled_for",
        id="delayed",
    ),
    pytest.param(
        recurring_scheduler_runner,
        "run_recurring_scheduler_runner",
        "_fire_due_recurring_schedulers",
        "_get_next_run_at",
        id="recurring",
    ),
]


def _stub_scheduler(monkeypatch, module, fire_name, next_name, *, fire=None, next_due=None):
    state = {"fire": 0, "next": 0}
    far_future = datetime.now(timezone.utc) + timedelta(hours=5)

    async def _fire() -> None:
        if fire is not None:
            await fire(state)
        else:
            state["fire"] += 1

    async def _next():
        state["next"] += 1
        stop_after = state.get("stop_after_next")
        if stop_after is not None and state["next"] >= stop_after:
            raise _Stop
        return next_due if next_due is not None else far_future

    async def _ok() -> None:
        return None

    monkeypatch.setattr(module, fire_name, _fire)
    monkeypatch.setattr(module, next_name, _next)
    if hasattr(module, "_retry_errored_schedulers"):
        monkeypatch.setattr(module, "_retry_errored_schedulers", _ok)
    monkeypatch.setattr(module, "POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(module, "ActivityTracker", _AwakeTracker)
    return state


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_scheduler_touches_progress_after_a_successful_iteration(
    monkeypatch, progress_path, module, runner, fire_name, next_name
):
    state = _stub_scheduler(monkeypatch, module, fire_name, next_name)
    state["stop_after_next"] = 2

    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner)(), timeout=5)

    assert state["fire"] == 2
    assert progress_path.exists()


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_scheduler_does_not_touch_progress_when_the_db_call_raises(
    monkeypatch, progress_path, module, runner, fire_name, next_name
):
    async def _failing_fire(state) -> None:
        state["fire"] += 1
        if state["fire"] >= 3:
            raise _Stop
        raise ConnectionRefusedError("db down")

    state = _stub_scheduler(monkeypatch, module, fire_name, next_name, fire=_failing_fire)

    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner)(), timeout=5)

    assert state["fire"] == 3  # the loop survived two failed iterations
    assert state["next"] == 0
    assert not progress_path.exists()


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_scheduler_next_due_query_error_is_caught_not_fatal(
    monkeypatch, progress_path, module, runner, fire_name, next_name
):
    """_get_next_* used to run outside the try: a DB error there ended the process."""
    state = _stub_scheduler(monkeypatch, module, fire_name, next_name)
    calls = {"n": 0}

    async def _next():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionRefusedError("db down")
        if calls["n"] >= 3:
            raise _Stop
        return datetime.now(timezone.utc) + timedelta(hours=5)

    monkeypatch.setattr(module, next_name, _next)

    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner)(), timeout=5)

    assert calls["n"] == 3
    assert state["fire"] == 3
    assert progress_path.exists()  # touched after iteration 2, the first that succeeded


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_scheduler_progress_goes_stale_while_a_db_call_hangs(
    monkeypatch, progress_path, module, runner, fire_name, next_name
):
    before = _make_stale(progress_path)
    hanging = asyncio.Event()

    async def _hanging_fire(state) -> None:
        state["fire"] += 1
        await hanging.wait()  # never set

    state = _stub_scheduler(monkeypatch, module, fire_name, next_name, fire=_hanging_fire)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(getattr(module, runner)(), timeout=0.3)

    assert state["fire"] == 1
    assert os.stat(progress_path).st_mtime_ns == before


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_idle_scheduler_keeps_polling_when_next_run_is_hours_away(
    monkeypatch, progress_path, module, runner, fire_name, next_name
):
    """Awake (SLEEP_MODE_ENABLED=false): the loop does not sleep until the next due
    time; it polls every POLL_INTERVAL_SECONDS and touches each time."""
    state = _stub_scheduler(monkeypatch, module, fire_name, next_name)
    touches: list[float] = []
    real_touch = module.touch_progress

    def _counting_touch() -> None:
        touches.append(time.monotonic())
        real_touch()

    monkeypatch.setattr(module, "touch_progress", _counting_touch)
    state["stop_after_next"] = 4

    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner)(), timeout=5)

    assert len(touches) == 3
    assert progress_path.exists()


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_in_app_sleeping_scheduler_wakes_to_poll_and_touch_when_progress_on(
    monkeypatch, progress_path, module, runner, fire_name, next_name
):
    """In-app sleeping, next run hours away: with the progress file on, the runner
    wakes every PROGRESS_MAX_IDLE_SECONDS (not SCHEDULER_SLEEP_CAP_SECONDS), polls the
    next due time from the database and touches — without firing."""
    state = _stub_scheduler(monkeypatch, module, fire_name, next_name)
    monkeypatch.setattr(module, "ActivityTracker", _SleepingTracker)
    monkeypatch.setattr(module, "PROGRESS_MAX_IDLE_SECONDS", 0.02)
    monkeypatch.setattr(module, "WAKE_CHECK_INTERVAL_SECONDS", 0.005)
    state["stop_after_next"] = 3

    started = time.monotonic()
    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner)(), timeout=5)

    assert time.monotonic() - started < 2  # never the 300 s cap
    assert state["fire"] == 0
    assert progress_path.exists()


@pytest.mark.parametrize(("module", "runner", "fire_name", "next_name"), _SCHEDULERS)
async def test_scheduler_without_progress_file_writes_nothing(
    monkeypatch, tmp_path, module, runner, fire_name, next_name
):
    monkeypatch.setattr(settings, "worker_progress_file", None)
    state = _stub_scheduler(monkeypatch, module, fire_name, next_name)
    state["stop_after_next"] = 3

    with pytest.raises(_Stop):
        await asyncio.wait_for(getattr(module, runner)(), timeout=5)

    assert list(tmp_path.iterdir()) == []
