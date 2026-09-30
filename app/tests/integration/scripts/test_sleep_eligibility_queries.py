"""The sleep-eligibility gather queries against the real test database (B-4/B-5).

Rows are inserted inside a transaction on one asyncpg connection, the queries run on
that same connection, and the transaction is rolled back — the worker database keeps
whatever it had, so every assertion is a delta against a baseline taken first.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import asyncpg
import pytest

from beyo_manager.services.infra.redis import async_client
from scripts import sleep_eligibility as se
from tests.helpers.fake_async_redis import FakeAsyncRedis

pytestmark = pytest.mark.integration


def _dsn() -> str:
    return se.asyncpg_dsn()


async def _insert_task(connection, task_type: str, state: str, next_retry_at=None) -> None:
    await connection.execute(
        """
        INSERT INTO execution_tasks (client_id, task_type, state, try_count, max_try, created_at, next_retry_at)
        VALUES ($1, $2::task_type_enum, $3::execution_task_state_enum, 0, 3, now(), $4)
        """,
        f"task_{uuid4().hex}", task_type, state, next_retry_at,
    )


def _delta(after: dict, before: dict) -> dict:
    keys = set(after) | set(before)
    return {k: after.get(k, 0) - before.get(k, 0) for k in keys if after.get(k, 0) != before.get(k, 0)}


async def test_task_count_and_retry_due_queries():
    now = datetime.now(timezone.utc)
    connection = await asyncpg.connect(_dsn())
    transaction = connection.transaction()
    await transaction.start()
    try:
        counts_before = await se.query_task_counts(connection)
        due_before = await se.query_retry_due(connection, now + timedelta(seconds=300))

        await _insert_task(connection, "record_view_start", "open")
        await _insert_task(connection, "record_view_start", "open")
        await _insert_task(connection, "process_step_transition", "pending")
        await _insert_task(connection, "create_notifications", "in_progress")
        await _insert_task(connection, "create_notifications", "retrying")
        await _insert_task(connection, "send_push_notification", "retry_scheduled", now + timedelta(seconds=60))
        await _insert_task(connection, "send_push_notification", "retry_scheduled", now + timedelta(hours=2))
        await _insert_task(connection, "upload_image", "open")          # orphan: queue:uploads
        await _insert_task(connection, "record_view_end", "completed")  # terminal: not counted
        await _insert_task(connection, "record_view_end", "fail")
        await _insert_task(connection, "record_view_end", "cancel")

        counts_after = await se.query_task_counts(connection)
        due_after = await se.query_retry_due(connection, now + timedelta(seconds=300))
    finally:
        await transaction.rollback()
        await connection.close()

    assert _delta(counts_after, counts_before) == {
        ("record_view_start", "open"): 2,
        ("process_step_transition", "pending"): 1,
        ("create_notifications", "in_progress"): 1,
        ("create_notifications", "retrying"): 1,
        ("send_push_notification", "retry_scheduled"): 2,
        ("upload_image", "open"): 1,
    }
    assert _delta(due_after, due_before) == {"send_push_notification": 1}

    summary = se.summarize_tasks(_delta(counts_after, counts_before), _delta(due_after, due_before))
    assert summary.by_state == {
        "open": 2, "pending": 1, "in_progress": 1, "retrying": 1, "retry_scheduled": 2,
    }
    assert summary.retry_due == 1
    assert summary.orphan["queue:uploads"] == 1


async def test_scheduler_next_due_queries():
    now = datetime.now(timezone.utc)
    connection = await asyncpg.connect(_dsn())
    transaction = connection.transaction()
    await transaction.start()
    try:
        await connection.execute("DELETE FROM delayed_schedulers")
        await connection.execute("DELETE FROM recurring_schedulers")
        soon = now + timedelta(minutes=10)
        await connection.execute(
            """
            INSERT INTO delayed_schedulers (client_id, type, state, origin_source, scheduled_for, payload_snapshot, created_at)
            VALUES ($1, 'reminder', 'active', 'command', $2, '{}', now()),
                   ($3, 'reminder', 'fired', 'command', $4, '{}', now())
            """,
            f"dsch_{uuid4().hex}", soon, f"dsch_{uuid4().hex}", now - timedelta(days=1),
        )
        created = now - timedelta(hours=1, minutes=30)
        await connection.execute(
            """
            INSERT INTO recurring_schedulers (client_id, type, state, origin_source, "interval", interval_value,
                                              last_interval, payload_snapshot, created_at)
            VALUES ($1, 'reminder', 'active', 'command', 1, 'days', NULL, '{}', $2),
                   ($3, 'pin_task', 'paused', 'command', 1, 'minutes', NULL, '{}', $2)
            """,
            f"rsch_{uuid4().hex}", created, f"rsch_{uuid4().hex}",
        )

        delayed = await se.query_delayed_next_due(connection)
        recurring = await se.query_recurring_next_due(connection, now)
    finally:
        await transaction.rollback()
        await connection.close()

    assert delayed == soon
    # Never fired: due now, at its current grid slot (the anchor itself).
    assert recurring == {"reminder": created}


async def test_migration_lock_and_named_sessions_are_seen():
    observer = await se.connect()
    holder = await asyncpg.connect(_dsn(), server_settings={"application_name": se.MIGRATE_APPLICATION_NAME})
    copier = await asyncpg.connect(_dsn(), server_settings={"application_name": "managerbeyo:db-copy-dump"})
    try:
        assert await se.query_migration_lock(observer) is False

        assert await holder.fetchval("SELECT pg_try_advisory_lock($1)", se.MIGRATION_LOCK_KEY)
        try:
            assert await se.query_migration_lock(observer) is True
        finally:
            await holder.execute("SELECT pg_advisory_unlock($1)", se.MIGRATION_LOCK_KEY)

        migrate, db_copy = await se.query_sessions(observer)
        assert migrate >= 1
        assert db_copy >= 1
        own_name = await observer.fetchval("SELECT current_setting('application_name')")
        assert own_name == se.APPLICATION_NAME
    finally:
        await copier.close()
        await holder.close()
        await observer.close()


async def test_gather_facts_end_to_end_against_the_test_database(monkeypatch):
    redis = FakeAsyncRedis()
    redis.lists["queue:tasks"] = ["task_1"]
    redis.lists["queue:reports"] = ["task_2", "task_3"]
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    now = datetime.now(timezone.utc)

    facts = await se.gather_facts(now, 300)
    result = se.evaluate(facts, 3600, 300, None, [], now)

    assert facts.queue_lengths["queue:tasks"] == 1
    assert facts.queue_lengths["queue:reports"] == 2
    codes = [reason["code"] for reason in result["reasons"]]
    assert "activity_unknown" in codes  # empty fake Redis: no key, no heartbeat
    assert "queue_not_empty" in codes
    assert result["reasons"][codes.index("queue_not_empty")]["detail"] == {"queues": {"queue:tasks": 1}}
    json.dumps(result)
