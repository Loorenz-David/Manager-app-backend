"""The human-activity recorder/reader and the API heartbeat, below the HTTP layer."""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi import FastAPI

import beyo_manager
from beyo_manager.config import settings
from beyo_manager.models import database
from beyo_manager.services.infra.activity import api_heartbeat, human_activity
from beyo_manager.services.infra.redis import async_client
from tests.helpers.fake_async_redis import FakeAsyncRedis

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _fresh_throttle():
    human_activity.reset_for_tests()
    yield
    human_activity.reset_for_tests()


@pytest.fixture
def fake_redis(monkeypatch) -> FakeAsyncRedis:
    redis = FakeAsyncRedis()
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    return redis


# ── recorder / reader ────────────────────────────────────────────────────────────

async def test_record_then_read_round_trip(fake_redis):
    assert await human_activity.record_human_activity(app_scope="manager", source="http")
    assert await human_activity.record_human_activity(app_scope="floor", source="socket")

    activity = await human_activity.read_human_activity()

    assert activity.last_source == "socket"
    assert set(activity.by_scope) == {"manager", "floor"}
    assert activity.last_at == activity.by_scope["floor"]
    assert activity.by_scope["manager"] <= activity.last_at <= time.time()
    key = f"{settings.redis_key_prefix}:activity:human"
    assert await fake_redis.ttl(key) == -1  # no TTL


async def test_missing_key_reads_as_never_recorded(fake_redis):
    activity = await human_activity.read_human_activity()

    assert activity == human_activity.HumanActivity(last_at=None, by_scope={}, last_source=None)


async def test_read_propagates_redis_errors(fake_redis):
    # "Redis unreachable" must not read as "nobody active".
    fake_redis.fail = ConnectionError("down")

    with pytest.raises(ConnectionError):
        await human_activity.read_human_activity()


async def test_a_scopeless_identity_is_recorded_as_unknown(fake_redis):
    await human_activity.record_human_activity(app_scope=None, source="http")

    [(_, fields)] = fake_redis.hset_calls
    assert "last_at:unknown" in fields


async def test_a_hung_redis_is_bounded_and_does_not_raise(fake_redis, monkeypatch):
    monkeypatch.setattr(human_activity, "WRITE_TIMEOUT_SECONDS", 0.05)
    fake_redis.delay = 5

    started = time.monotonic()
    written = await human_activity.record_human_activity(app_scope="manager", source="http")

    assert written is False
    assert time.monotonic() - started < 1


async def test_a_failed_attempt_still_holds_the_throttle_slot(fake_redis):
    """An outage costs one attempt per scope per window, not one per request."""
    fake_redis.fail = ConnectionError("down")
    attempts = []
    real_hset = fake_redis.hset

    async def _hset(key, *, mapping):
        attempts.append(key)
        return await real_hset(key, mapping=mapping)

    fake_redis.hset = _hset

    for _ in range(5):
        assert await human_activity.record_human_activity(app_scope="manager", source="http") is False

    assert len(attempts) == 1


# ── heartbeat ────────────────────────────────────────────────────────────────────

async def test_heartbeat_content_and_ttl(fake_redis):
    before = time.time()
    await api_heartbeat.write_heartbeat(started_at=123.5, socket_counts=lambda: (3, 2))

    [(key, raw, ex)] = fake_redis.set_calls
    assert key == f"{settings.redis_key_prefix}:system:api_heartbeat"
    assert ex == 45
    payload = json.loads(raw)
    assert set(payload) == {"at", "started_at", "sockets", "users"}
    assert payload["started_at"] == 123.5
    assert payload["sockets"] == 3 and payload["users"] == 2
    assert before <= payload["at"] <= time.time()

    assert await api_heartbeat.read_api_heartbeat() == payload


async def test_heartbeat_absent_reads_as_none(fake_redis):
    assert await api_heartbeat.read_api_heartbeat() is None


async def test_heartbeat_beats_on_its_interval_and_survives_failures(fake_redis, caplog):
    fake_redis.fail = ConnectionError("down")
    task = asyncio.create_task(
        api_heartbeat.run_api_heartbeat(
            started_at=1.0, socket_counts=lambda: (0, 0), interval_seconds=0.01
        )
    )
    await asyncio.sleep(0.05)
    fake_redis.fail = None
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(fake_redis.set_calls) >= 2  # kept beating after the failures
    failures = [r for r in caplog.records if "api_heartbeat.write_failed" in r.getMessage()]
    assert len(failures) == 1  # several failed beats, one log line


async def test_default_interval_and_ttl():
    assert api_heartbeat.HEARTBEAT_INTERVAL_SECONDS == 15
    assert api_heartbeat.HEARTBEAT_TTL_SECONDS == 45


async def test_lifespan_starts_the_heartbeat_and_cancels_it_on_shutdown(fake_redis, monkeypatch):
    async def _noop() -> None:
        return None

    monkeypatch.setattr(database, "init_db", _noop)
    monkeypatch.setattr(database, "close_db", _noop)
    started: list[asyncio.Task] = []
    real_start = beyo_manager._start_api_heartbeat

    def _capture():
        task = real_start()
        started.append(task)
        return task

    monkeypatch.setattr(beyo_manager, "_start_api_heartbeat", _capture)

    before = time.time()
    async with beyo_manager.lifespan(FastAPI()):
        for _ in range(100):
            if fake_redis.set_calls:
                break
            await asyncio.sleep(0.01)
        [task] = started
        assert not task.done()

    assert task.cancelled()
    payload = json.loads(fake_redis.set_calls[0][1])
    assert before <= payload["started_at"] <= payload["at"]
