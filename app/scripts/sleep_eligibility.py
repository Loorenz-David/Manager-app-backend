"""Is it semantically safe to stop production now? One JSON verdict, for the host.

    python -m scripts.sleep_eligibility --idle-seconds N [--retry-horizon S] [--since T]
                                        [--host-reason CODE[=DETAIL]]...
    # container: docker compose exec -T api python -m scripts.sleep_eligibility --idle-seconds 7200

The application answers only *whether* stopping is safe; the infrastructure decides
*when* to stop and owns the idle threshold (``--idle-seconds`` is required — there is
no default policy here). This makes no cloud call of any kind.

Prints exactly one JSON object on stdout (schema 1) and exits:

    0  eligible
    1  not eligible (``reasons`` names every blocking condition)
    2  the check itself failed — fail closed (reason ``check_failed``)

Blocking reasons:

- ``recent_human_activity``: idle < N. Idle is measured from the LATER of the last
  human activity and the API's ``started_at`` (``idle_basis`` names which one). A start
  is itself a request for the system — someone woke it — and nothing can be recorded
  while it is stopped, so a freshly started system is never idle for longer than it has
  been running, however old its last recorded activity is.
- ``activity_unknown``: no human-activity key and no API heartbeat.
- ``human_activity_since``: ``--since T`` given and human activity was recorded at or
  after T (the drain's re-check after fencing ingress).
- ``tasks_in_progress``: IN_PROGRESS or RETRYING execution tasks.
- ``tasks_open`` / ``tasks_pending``: OPEN / PENDING execution tasks.
- ``retry_due_within_horizon``: RETRY_SCHEDULED tasks whose ``next_retry_at`` is at or
  before now + ``--retry-horizon`` (default 300 s).
- ``queue_not_empty``: a Redis queue that a queue worker consumes holds ids.
- ``migration_running``: the migration advisory lock (``scripts/migrate.py``) is held or
  awaited, or a ``managerbeyo:migrate`` session is connected.
- ``db_copy_running``: a ``managerbeyo:db-copy*`` session is connected.
- every ``--host-reason CODE[=DETAIL]`` (host-only facts such as ``deploy_lock_held``).

Task types whose queue no worker consumes (``ORPHAN_QUEUES``) never block — they
would block for ever; their counts are reported under ``metrics.tasks.orphan``, their
queue lengths under ``metrics.queues``. Due delayed and recurring jobs and open sockets
are informational only: due scheduled work simply runs at the next wake.

Cost: one short database connection (``managerbeyo:sleep-eligibility``, read-only,
closed before exit) and a few Redis reads. The gather step's queries are reused by
``scripts.sleep_drain``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import asyncpg

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.domain.schedulers.enums import RecurringSchedulerIntervalValueEnum
from beyo_manager.domain.schedulers.recurring_grid import recurring_next_run_at
from beyo_manager.services.infra.activity.api_heartbeat import read_api_heartbeat
from beyo_manager.services.infra.activity.human_activity import (
    HumanActivity,
    read_human_activity,
)
from beyo_manager.services.infra.execution.task_router import QUEUE_MAP
from beyo_manager.services.infra.redis import async_client
from scripts.migrate import MIGRATION_LOCK_KEY

SCHEMA = 1

EXIT_ELIGIBLE = 0
EXIT_NOT_ELIGIBLE = 1
EXIT_CHECK_FAILED = 2

APPLICATION_NAME = "managerbeyo:sleep-eligibility"
MIGRATE_APPLICATION_NAME = "managerbeyo:migrate"
DB_COPY_APPLICATION_PREFIX = "managerbeyo:db-copy"

DEFAULT_RETRY_HORIZON_SECONDS = 300.0
CONNECT_TIMEOUT_SECONDS = 10.0
COMMAND_TIMEOUT_SECONDS = 10.0
REDIS_TIMEOUT_SECONDS = 5.0
GATHER_TIMEOUT_SECONDS = 45.0

# The queues a queue worker drains: `run_worker("queue:…", …)` in
# beyo_manager/workers/{tasks,notification,presence,analytics,shopify}_worker.py.
# tests/unit/scripts/test_sleep_eligibility.py derives the same set from those
# modules, so a new worker (or a removed one) fails the test until this is updated.
CONSUMED_QUEUES: frozenset[str] = frozenset({
    "queue:tasks",
    "queue:notifications",
    "queue:presence",
    "queue:analytics",
    "queue:shopify",
})
ALL_QUEUES: frozenset[str] = frozenset(QUEUE_MAP.values())
# queue:uploads, queue:webhooks, queue:reports today: the router pushes to them, nobody pops.
ORPHAN_QUEUES: frozenset[str] = ALL_QUEUES - CONSUMED_QUEUES
UNMAPPED_ORPHAN_KEY = "unmapped"  # a task type with no QUEUE_MAP entry is never routed

# The five non-terminal states. RETRYING is declared but no code path sets it today
# (worker_base goes IN_PROGRESS -> RETRY_SCHEDULED); a row in it is treated as running.
ACTIVE_STATES: tuple[str, ...] = (
    ExecutionTaskStateEnum.OPEN.value,
    ExecutionTaskStateEnum.PENDING.value,
    ExecutionTaskStateEnum.IN_PROGRESS.value,
    ExecutionTaskStateEnum.RETRYING.value,
    ExecutionTaskStateEnum.RETRY_SCHEDULED.value,
)

HOST_REASON_CODE = re.compile(r"^[a-z0-9_]+$")


# ── facts ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Facts:
    """Everything the verdict depends on, as read. No policy applied yet."""

    activity: HumanActivity
    api_heartbeat: dict | None
    # (task_type value, state value) -> count, active states only
    task_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    # task_type value -> RETRY_SCHEDULED rows with next_retry_at <= now + horizon
    retry_due: dict[str, int] = field(default_factory=dict)
    queue_lengths: dict[str, int] = field(default_factory=dict)
    migration_lock_present: bool = False
    migrate_sessions: int = 0
    db_copy_sessions: int = 0
    delayed_next_due_at: datetime | None = None
    recurring_next_due_at: dict[str, datetime] = field(default_factory=dict)


def queue_for_task_type(task_type_value: str) -> str | None:
    try:
        return QUEUE_MAP.get(TaskType(task_type_value))
    except ValueError:
        return None


def is_orphan_task_type(task_type_value: str) -> bool:
    """No worker will ever pick this type up: its queue is unconsumed or it has none."""
    queue = queue_for_task_type(task_type_value)
    return queue is None or queue not in CONSUMED_QUEUES


@dataclass(frozen=True)
class TaskSummary:
    """Task counts over consumed types, by state; orphan types counted apart."""

    by_state: dict[str, int]
    types_by_state: dict[str, dict[str, int]]
    retry_due: int
    retry_due_types: dict[str, int]
    orphan: dict[str, int]

    def count(self, *states: ExecutionTaskStateEnum) -> int:
        return sum(self.by_state.get(state.value, 0) for state in states)

    def types(self, *states: ExecutionTaskStateEnum) -> dict[str, int]:
        merged: dict[str, int] = {}
        for state in states:
            for task_type, n in self.types_by_state.get(state.value, {}).items():
                merged[task_type] = merged.get(task_type, 0) + n
        return dict(sorted(merged.items()))


def summarize_tasks(
    task_counts: dict[tuple[str, str], int],
    retry_due: dict[str, int],
) -> TaskSummary:
    by_state = {state: 0 for state in ACTIVE_STATES}
    types_by_state: dict[str, dict[str, int]] = {state: {} for state in ACTIVE_STATES}
    orphan = {queue: 0 for queue in sorted(ORPHAN_QUEUES)}
    for (task_type, state), n in task_counts.items():
        if not n:
            continue
        if is_orphan_task_type(task_type):
            key = queue_for_task_type(task_type) or UNMAPPED_ORPHAN_KEY
            orphan[key] = orphan.get(key, 0) + n
            continue
        by_state[state] = by_state.get(state, 0) + n
        bucket = types_by_state.setdefault(state, {})
        bucket[task_type] = bucket.get(task_type, 0) + n
    due_types = {
        task_type: n
        for task_type, n in sorted(retry_due.items())
        if n and not is_orphan_task_type(task_type)
    }
    return TaskSummary(
        by_state=by_state,
        types_by_state=types_by_state,
        retry_due=sum(due_types.values()),
        retry_due_types=due_types,
        orphan=orphan,
    )


def consumed_queue_backlog(queue_lengths: dict[str, int]) -> dict[str, int]:
    return {
        name: n for name, n in sorted(queue_lengths.items()) if name in CONSUMED_QUEUES and n
    }


# ── evaluate (pure) ───────────────────────────────────────────────────────────────


def _iso(value: datetime | float | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(float(value), timezone.utc)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _as_epoch(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _heartbeat_metrics(heartbeat: dict | None) -> dict | None:
    if heartbeat is None:
        return None
    return {
        "at": _iso(_as_epoch(heartbeat.get("at"))),
        "started_at": _iso(_as_epoch(heartbeat.get("started_at"))),
        "sockets": heartbeat.get("sockets"),
        "users": heartbeat.get("users"),
    }


def _reason(code: str, detail: object = None) -> dict:
    return {"code": code, "detail": detail}


def _count_detail(count: int, types: dict[str, int]) -> dict:
    return {"count": count, "types": types}


def evaluate(
    facts: Facts,
    idle_seconds: float,
    retry_horizon: float,
    since: datetime | None,
    host_reasons: Sequence[tuple[str, str | None]],
    now: datetime,
) -> dict:
    """The verdict, from facts alone. No I/O; ``now`` is an aware UTC datetime."""
    now_epoch = now.timestamp()
    reasons: list[dict] = []

    # Activity
    activity = facts.activity
    started_at = _as_epoch((facts.api_heartbeat or {}).get("started_at"))
    if activity.last_at is not None and (started_at is None or activity.last_at >= started_at):
        idle_basis, reference = "human_activity", activity.last_at
    elif started_at is not None:
        idle_basis, reference = "api_started_at", started_at
    else:
        idle_basis, reference = None, None
    idle = None if reference is None else now_epoch - reference
    if idle is None:
        reasons.append(_reason("activity_unknown", {
            "message": "no human activity recorded and no API heartbeat",
        }))
    elif idle < idle_seconds:
        reasons.append(_reason("recent_human_activity", {
            "idle_seconds": round(idle, 3),
            "threshold_seconds": _number(idle_seconds),
            "basis": idle_basis,
        }))
    if since is not None and activity.last_at is not None and activity.last_at >= since.timestamp():
        reasons.append(_reason("human_activity_since", {
            "since": _iso(since),
            "last_human_activity_at": _iso(activity.last_at),
        }))

    # Tasks
    tasks = summarize_tasks(facts.task_counts, facts.retry_due)
    running = (ExecutionTaskStateEnum.IN_PROGRESS, ExecutionTaskStateEnum.RETRYING)
    if tasks.count(*running):
        reasons.append(_reason("tasks_in_progress", _count_detail(tasks.count(*running), tasks.types(*running))))
    for code, state in (
        ("tasks_open", ExecutionTaskStateEnum.OPEN),
        ("tasks_pending", ExecutionTaskStateEnum.PENDING),
    ):
        if tasks.count(state):
            reasons.append(_reason(code, _count_detail(tasks.count(state), tasks.types(state))))
    if tasks.retry_due:
        reasons.append(_reason("retry_due_within_horizon", _count_detail(tasks.retry_due, tasks.retry_due_types)))

    # Queues
    backlog = consumed_queue_backlog(facts.queue_lengths)
    if backlog:
        reasons.append(_reason("queue_not_empty", {"queues": backlog}))

    # Database sessions
    if facts.migration_lock_present or facts.migrate_sessions:
        reasons.append(_reason("migration_running", {
            "advisory_lock": facts.migration_lock_present,
            "sessions": facts.migrate_sessions,
        }))
    if facts.db_copy_sessions:
        reasons.append(_reason("db_copy_running", {"sessions": facts.db_copy_sessions}))

    # Host-only facts, merged by the host script
    for code, detail in host_reasons:
        reasons.append(_reason(code, detail))

    return {
        "schema": SCHEMA,
        "checked_at": _iso(now),
        "eligible": not reasons,
        "reasons": reasons,
        "metrics": {
            "last_human_activity_at": _iso(activity.last_at),
            "idle_seconds": None if idle is None else round(idle, 3),
            "idle_basis": idle_basis,
            "last_by_scope": {scope: _iso(at) for scope, at in sorted(activity.by_scope.items())},
            "last_source": activity.last_source,
            "tasks": {
                "open": tasks.count(ExecutionTaskStateEnum.OPEN),
                "pending": tasks.count(ExecutionTaskStateEnum.PENDING),
                "in_progress": tasks.count(ExecutionTaskStateEnum.IN_PROGRESS),
                "retrying": tasks.count(ExecutionTaskStateEnum.RETRYING),
                "retry_scheduled": tasks.count(ExecutionTaskStateEnum.RETRY_SCHEDULED),
                "retry_due_within_horizon": tasks.retry_due,
                "orphan": tasks.orphan,
            },
            "queues": dict(sorted(facts.queue_lengths.items())),
            "delayed_next_due_at": _iso(facts.delayed_next_due_at),
            "recurring_next_due_at": {
                kind: _iso(at) for kind, at in sorted(facts.recurring_next_due_at.items())
            },
            "api_heartbeat": _heartbeat_metrics(facts.api_heartbeat),
            "db_sessions": {"migrate": facts.migrate_sessions, "db_copy": facts.db_copy_sessions},
        },
        "thresholds": _thresholds(idle_seconds, retry_horizon),
    }


def _number(value: float | None) -> float | int | None:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _thresholds(idle_seconds: float | None, retry_horizon: float | None) -> dict:
    return {"idle_seconds": _number(idle_seconds), "retry_horizon_seconds": _number(retry_horizon)}


def check_failed_result(message: str, now: datetime, idle_seconds: float | None, retry_horizon: float | None) -> dict:
    return {
        "schema": SCHEMA,
        "checked_at": _iso(now),
        "eligible": False,
        "reasons": [_reason("check_failed", message)],
        "metrics": None,
        "thresholds": _thresholds(idle_seconds, retry_horizon),
    }


# ── gather (I/O) ──────────────────────────────────────────────────────────────────

_TASK_COUNTS_SQL = """
SELECT task_type::text AS task_type, state::text AS state, count(*) AS n
FROM execution_tasks
WHERE state::text = ANY($1::text[])
GROUP BY 1, 2
"""

_RETRY_DUE_SQL = """
SELECT task_type::text AS task_type, count(*) AS n
FROM execution_tasks
WHERE state::text = $1 AND (next_retry_at IS NULL OR next_retry_at <= $2)
GROUP BY 1
"""

# A bigint advisory lock shows in pg_locks as classid = high 32 bits, objid = low 32
# bits, objsubid = 1. Held or awaited, in this database.
_MIGRATION_LOCK_SQL = """
SELECT EXISTS (
    SELECT 1 FROM pg_locks
    WHERE locktype = 'advisory'
      AND database = (SELECT oid FROM pg_database WHERE datname = current_database())
      AND classid::bigint = $1 AND objid::bigint = $2 AND objsubid = 1
)
"""

# application_name is readable for every session, also by a non-superuser role
# without pg_read_all_stats (only query/state are hidden for other roles' sessions).
_SESSIONS_SQL = """
SELECT
    count(*) FILTER (WHERE application_name = $1) AS migrate,
    count(*) FILTER (WHERE application_name LIKE $2) AS db_copy
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
"""

_DELAYED_NEXT_SQL = """
SELECT min(scheduled_for) FROM delayed_schedulers WHERE state::text = 'active'
"""

_RECURRING_SQL = """
SELECT type::text AS type, created_at, "interval" AS interval,
       interval_value::text AS interval_value, last_interval
FROM recurring_schedulers
WHERE state::text = 'active'
"""


def migration_lock_halves(key: int = MIGRATION_LOCK_KEY) -> tuple[int, int]:
    return (key >> 32) & 0xFFFFFFFF, key & 0xFFFFFFFF


def asyncpg_dsn() -> str:
    return (settings.database_url or "").replace("postgresql+asyncpg://", "postgresql://", 1)


async def connect(application_name: str = APPLICATION_NAME) -> asyncpg.Connection:
    """One connection — the whole database cost of a check (no pool)."""
    return await asyncpg.connect(
        asyncpg_dsn(),
        timeout=CONNECT_TIMEOUT_SECONDS,
        command_timeout=COMMAND_TIMEOUT_SECONDS,
        server_settings={"application_name": application_name, "timezone": "UTC"},
    )


async def query_task_counts(connection: asyncpg.Connection) -> dict[tuple[str, str], int]:
    rows = await connection.fetch(_TASK_COUNTS_SQL, list(ACTIVE_STATES))
    return {(row["task_type"], row["state"]): int(row["n"]) for row in rows}


async def query_retry_due(connection: asyncpg.Connection, cutoff: datetime) -> dict[str, int]:
    rows = await connection.fetch(
        _RETRY_DUE_SQL, ExecutionTaskStateEnum.RETRY_SCHEDULED.value, cutoff
    )
    return {row["task_type"]: int(row["n"]) for row in rows}


async def query_migration_lock(connection: asyncpg.Connection) -> bool:
    high, low = migration_lock_halves()
    return bool(await connection.fetchval(_MIGRATION_LOCK_SQL, high, low))


async def query_sessions(connection: asyncpg.Connection) -> tuple[int, int]:
    row = await connection.fetchrow(
        _SESSIONS_SQL, MIGRATE_APPLICATION_NAME, f"{DB_COPY_APPLICATION_PREFIX}%"
    )
    return int(row["migrate"]), int(row["db_copy"])


async def query_delayed_next_due(connection: asyncpg.Connection) -> datetime | None:
    return await connection.fetchval(_DELAYED_NEXT_SQL)


async def query_recurring_next_due(connection: asyncpg.Connection, now: datetime) -> dict[str, datetime]:
    """Earliest next run per recurring type, by B-7's grid rule (a value <= now is due)."""
    result: dict[str, datetime] = {}
    for row in await connection.fetch(_RECURRING_SQL):
        try:
            job = SimpleNamespace(
                created_at=row["created_at"],
                interval=row["interval"],
                interval_value=RecurringSchedulerIntervalValueEnum(row["interval_value"]),
                last_interval=row["last_interval"],
            )
            next_at = recurring_next_run_at(job, now)
        except (ValueError, TypeError, KeyError):
            continue  # a row the runner itself skips (non-positive interval)
        current = result.get(row["type"])
        if current is None or next_at < current:
            result[row["type"]] = next_at
    return result


async def read_queue_lengths(queues: frozenset[str] = ALL_QUEUES) -> dict[str, int]:
    redis = async_client.get_async_redis()
    lengths: dict[str, int] = {}
    for name in sorted(queues):
        lengths[name] = int(
            await asyncio.wait_for(redis.llen(name), timeout=REDIS_TIMEOUT_SECONDS)
        )
    return lengths


async def gather_facts(now: datetime, retry_horizon: float) -> Facts:
    """Read Redis, then the database over one read-only connection, closed on return."""
    activity = await asyncio.wait_for(read_human_activity(), timeout=REDIS_TIMEOUT_SECONDS)
    heartbeat = await asyncio.wait_for(read_api_heartbeat(), timeout=REDIS_TIMEOUT_SECONDS)
    queue_lengths = await read_queue_lengths()

    connection = await connect()
    try:
        async with connection.transaction(readonly=True):
            task_counts = await query_task_counts(connection)
            retry_due = await query_retry_due(connection, now + timedelta(seconds=retry_horizon))
            lock_present = await query_migration_lock(connection)
            migrate_sessions, db_copy_sessions = await query_sessions(connection)
            delayed_next = await query_delayed_next_due(connection)
            recurring_next = await query_recurring_next_due(connection, now)
    finally:
        await connection.close()

    return Facts(
        activity=activity,
        api_heartbeat=heartbeat,
        task_counts=task_counts,
        retry_due=retry_due,
        queue_lengths=queue_lengths,
        migration_lock_present=lock_present,
        migrate_sessions=migrate_sessions,
        db_copy_sessions=db_copy_sessions,
        delayed_next_due_at=delayed_next,
        recurring_next_due_at=recurring_next,
    )


async def close_redis() -> None:
    client = async_client._async_client
    if client is None:
        return
    async_client._async_client = None
    try:
        await client.aclose()
    except Exception:  # closing is best effort; the process is exiting
        pass


# ── CLI ───────────────────────────────────────────────────────────────────────────


def safe_error(exc: BaseException) -> str:
    """The exception *type* only: driver messages can carry a host, user or URL."""
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "TimeoutError: a Redis or database call did not answer in time"
    return f"{type(exc).__name__}: the check could not read its facts"


class ArgumentError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # argparse would print usage and exit 2 without JSON
        raise ArgumentError(message)


def parse_since(value: str) -> datetime:
    text = value.strip()
    try:
        return datetime.fromtimestamp(float(text), timezone.utc)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise argparse.ArgumentTypeError("expected epoch seconds or ISO-8601") from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_host_reason(value: str) -> tuple[str, str | None]:
    code, sep, detail = value.partition("=")
    if not HOST_REASON_CODE.match(code):
        raise argparse.ArgumentTypeError("CODE must match [a-z0-9_]+")
    return code, (detail if sep else None)


def _non_negative(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a number") from None
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("expected a finite number >= 0")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="python -m scripts.sleep_eligibility",
        description="Print one JSON verdict: is it semantically safe to stop production now?",
    )
    parser.add_argument("--idle-seconds", type=_non_negative, required=True,
                        help="required: minimum seconds without human activity (policy of the caller)")
    parser.add_argument("--retry-horizon", type=_non_negative, default=DEFAULT_RETRY_HORIZON_SECONDS,
                        help="block on retries due within this many seconds (default 300)")
    parser.add_argument("--since", type=parse_since, default=None,
                        help="block on human activity recorded at or after T (epoch seconds or ISO-8601)")
    parser.add_argument("--host-reason", type=parse_host_reason, action="append", default=[],
                        metavar="CODE[=DETAIL]", help="a host-only blocking reason; repeatable")
    return parser


def logs_to_stderr() -> None:
    """Keep stdout for the one JSON object: importing beyo_manager logs to stdout."""
    loggers = [logging.getLogger()] + [
        logger for logger in logging.Logger.manager.loggerDict.values()
        if isinstance(logger, logging.Logger)
    ]
    for logger in loggers:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
                handler.setStream(sys.stderr)


def emit(result: dict) -> None:
    sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=False) + "\n")
    sys.stdout.flush()


def exit_code_for(result: dict) -> int:
    if any(reason["code"] == "check_failed" for reason in result["reasons"]):
        return EXIT_CHECK_FAILED
    return EXIT_ELIGIBLE if result["eligible"] else EXIT_NOT_ELIGIBLE


async def _check(args: argparse.Namespace, now: datetime) -> dict:
    try:
        facts = await asyncio.wait_for(
            gather_facts(now, args.retry_horizon), timeout=GATHER_TIMEOUT_SECONDS
        )
    finally:
        await close_redis()
    return evaluate(facts, args.idle_seconds, args.retry_horizon, args.since, args.host_reason, now)


def main(argv: Sequence[str] | None = None) -> int:
    logs_to_stderr()
    now = datetime.now(timezone.utc)
    try:
        args = build_parser().parse_args(argv)
    except ArgumentError as exc:
        result = check_failed_result(f"invalid arguments: {exc}", now, None, None)
        emit(result)
        return EXIT_CHECK_FAILED
    try:
        result = asyncio.run(_check(args, now))
    except Exception as exc:  # fail closed: anything unexpected is "not safe to stop"
        result = check_failed_result(safe_error(exc), now, args.idle_seconds, args.retry_horizon)
    emit(result)
    return exit_code_for(result)


if __name__ == "__main__":
    sys.exit(main())
