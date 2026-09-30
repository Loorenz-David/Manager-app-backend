"""scripts/sleep_drain.py (B-5): wait for consumed work to finish, bounded, abortable.

The database connection and the two reads are stubbed with scripted sequences; the
queries themselves are covered in tests/integration/scripts/test_sleep_eligibility_queries.py.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import time

import pytest

from beyo_manager.config import settings
from beyo_manager.services.infra.redis import async_client
from scripts import sleep_drain as sd
from scripts import sleep_eligibility
from tests.helpers.fake_async_redis import FakeAsyncRedis

pytestmark = pytest.mark.unit


class _FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    def terminate(self) -> None:
        self.closed = True


@pytest.fixture
def scripted(monkeypatch):
    """Scripted polls: each entry is (task_counts, queue_lengths) or an exception."""
    state: dict = {"polls": [], "i": 0, "connections": []}

    async def _connect(application_name):
        state["application_name"] = application_name
        connection = _FakeConnection()
        state["connections"].append(connection)
        return connection

    def _current():
        polls = state["polls"]
        return polls[min(state["i"], len(polls) - 1)]

    async def _task_counts(_connection):
        entry = _current()
        if isinstance(entry, BaseException):
            raise entry
        return entry[0]

    async def _queue_lengths(queues):
        entry = _current()
        state["i"] += 1
        assert queues == sd.CONSUMED_QUEUES
        return {name: entry[1].get(name, 0) for name in queues}

    monkeypatch.setattr(sd, "connect", _connect)
    monkeypatch.setattr(sd, "query_task_counts", _task_counts)
    monkeypatch.setattr(sd, "read_queue_lengths", _queue_lengths)
    return state


IDLE = ({}, {})


def _run(capsys, *args) -> tuple[int, dict, str]:
    code = sd.main(list(args))
    captured = capsys.readouterr()
    assert captured.out.count("\n") == 1
    return code, json.loads(captured.out), captured.err


def test_returns_0_once_counts_reach_zero(capsys, scripted):
    scripted["polls"] = [
        ({("record_view_end", "open"): 1, ("create_notifications", "pending"): 2}, {"queue:presence": 1}),
        ({("create_notifications", "pending"): 1}, {}),
        IDLE,
    ]
    code, result, err = _run(capsys, "--timeout", "10", "--poll", "0.01")

    assert code == sd.EXIT_DRAINED
    assert result["drained"] is True
    assert result["outcome"] == "drained"
    assert result["remaining"] == {"open": 0, "pending": 0, "in_progress": 0, "retrying": 0, "queues": {}}
    assert scripted["i"] == 3
    assert "waiting" in err and "drained after" in err
    assert scripted["application_name"] == "managerbeyo:sleep-drain"
    assert all(c.closed for c in scripted["connections"])


def test_blocks_while_in_progress_then_times_out(capsys, scripted):
    scripted["polls"] = [({("send_push_notification", "in_progress"): 1}, {})]
    started = time.monotonic()
    code, result, _err = _run(capsys, "--timeout", "0.2", "--poll", "0.02")

    assert code == sd.EXIT_NOT_DRAINED
    assert result["drained"] is False
    assert result["outcome"] == "timeout"
    assert result["remaining"]["in_progress"] == 1
    assert result["waited_seconds"] >= 0.2
    assert time.monotonic() - started < 2
    assert scripted["i"] > 2  # kept polling until the deadline


def test_retrying_blocks(capsys, scripted):
    scripted["polls"] = [({("record_view_end", "retrying"): 1}, {})]
    code, result, _ = _run(capsys, "--timeout", "0.05", "--poll", "0.01")
    assert code == sd.EXIT_NOT_DRAINED
    assert result["remaining"]["retrying"] == 1


def test_consumed_queue_not_empty_blocks(capsys, scripted):
    scripted["polls"] = [({}, {"queue:tasks": 3}), ({}, {"queue:tasks": 3}), IDLE]
    code, result, _ = _run(capsys, "--timeout", "10", "--poll", "0.01")
    assert code == sd.EXIT_DRAINED
    assert scripted["i"] == 3


def test_consumed_queue_that_never_empties_times_out(capsys, scripted):
    scripted["polls"] = [({}, {"queue:notifications": 1})]
    code, result, _ = _run(capsys, "--timeout", "0.05", "--poll", "0.01")
    assert code == sd.EXIT_NOT_DRAINED
    assert result["remaining"]["queues"] == {"queue:notifications": 1}


def test_orphan_types_are_ignored(capsys, scripted):
    scripted["polls"] = [
        ({("upload_image", "open"): 4, ("deliver_webhook", "pending"): 1, ("recurring_send_report", "open"): 2}, {}),
    ]
    code, result, _ = _run(capsys, "--timeout", "5", "--poll", "0.01")
    assert code == sd.EXIT_DRAINED
    assert result["orphan"] == {"queue:reports": 2, "queue:uploads": 4, "queue:webhooks": 1}


def test_retry_scheduled_is_not_waited_for(capsys, scripted):
    scripted["polls"] = [({("create_notifications", "retry_scheduled"): 5}, {})]
    code, _result, _ = _run(capsys, "--timeout", "5", "--poll", "0.01")
    assert code == sd.EXIT_DRAINED


def test_sigterm_exits_1_promptly_with_aborted(capsys, scripted):
    scripted["polls"] = [({("send_push_notification", "in_progress"): 1}, {})]

    async def _send_sigterm_soon():
        await asyncio.sleep(0.1)
        os.kill(os.getpid(), signal.SIGTERM)

    async def _run_drain():
        killer = asyncio.ensure_future(_send_sigterm_soon())
        try:
            return await sd.drain(600, 30)  # a 30 s poll: only the signal ends it quickly
        finally:
            killer.cancel()

    started = time.monotonic()
    result = asyncio.run(_run_drain())

    assert time.monotonic() - started < 3
    assert result["outcome"] == "aborted"
    assert result["drained"] is False
    assert sd.exit_code_for(result) == sd.EXIT_NOT_DRAINED
    assert result["remaining"]["in_progress"] == 1
    assert all(c.closed for c in scripted["connections"])
    capsys.readouterr()


def test_db_failure_during_poll_exits_2(capsys, scripted):
    scripted["polls"] = [ConnectionResetError("lost db at db.internal:5432")]
    code, result, _ = _run(capsys, "--timeout", "5", "--poll", "0.01")
    assert code == sd.EXIT_FAILED
    assert result["outcome"] == "failed"
    assert result["drained"] is False
    assert "db.internal" not in json.dumps(result)


def test_db_unreachable_exits_2_without_secrets(monkeypatch, capsys):
    redis = FakeAsyncRedis()
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    monkeypatch.setattr(
        settings, "database_url", "postgresql+asyncpg://drain_user:Dr41n-S3cret@127.0.0.1:1/drain_db"
    )
    code, result, err = _run(capsys, "--timeout", "5")
    assert code == sd.EXIT_FAILED
    for text in (json.dumps(result), err):
        assert "Dr41n-S3cret" not in text and "drain_user" not in text and "127.0.0.1" not in text


def test_redis_failure_exits_2(monkeypatch, capsys, scripted):
    redis = FakeAsyncRedis()
    redis.fail = ConnectionError("redis down")
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    monkeypatch.setattr(sd, "read_queue_lengths", sleep_eligibility.read_queue_lengths)
    scripted["polls"] = [IDLE]
    code, result, _ = _run(capsys, "--timeout", "5", "--poll", "0.01")
    assert code == sd.EXIT_FAILED


@pytest.mark.parametrize("args", [[], ["--timeout", "0"], ["--timeout", "x"], ["--timeout", "5", "--poll", "-1"]])
def test_bad_arguments_exit_2(capsys, args):
    code, result, _ = _run(capsys, *args)
    assert code == sd.EXIT_FAILED
    assert result["outcome"] == "failed"
    assert result["error"].startswith("invalid arguments")
