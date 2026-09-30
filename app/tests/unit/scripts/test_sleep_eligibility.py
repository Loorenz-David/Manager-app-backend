"""scripts/sleep_eligibility.py (B-4): the pure verdict, the CLI contract, fail-closed.

`evaluate` is exercised from hand-built Facts; `main` with the gather step stubbed (or
with its Redis/DB unreachable, for the exit-2 paths). The task-count queries run
against the test database in tests/integration/scripts/test_sleep_eligibility_queries.py.
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from beyo_manager.config import settings
from beyo_manager.services.infra.activity.human_activity import HumanActivity
from beyo_manager.services.infra.execution.task_router import QUEUE_MAP
from beyo_manager.services.infra.redis import async_client
from scripts import sleep_eligibility as se
from tests.helpers.fake_async_redis import FakeAsyncRedis

pytestmark = pytest.mark.unit

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
N = 3600.0
WORKERS_DIR = Path(se.__file__).resolve().parents[1] / "beyo_manager" / "workers"


def _idle_activity(seconds: float = 2 * N) -> HumanActivity:
    at = NOW.timestamp() - seconds
    return HumanActivity(last_at=at, by_scope={"floor": at}, last_source="http")


def _facts(**overrides) -> se.Facts:
    values = {
        "activity": _idle_activity(),
        "api_heartbeat": {"at": NOW.timestamp(), "started_at": NOW.timestamp() - 86400, "sockets": 2, "users": 1},
        "task_counts": {},
        "retry_due": {},
        "queue_lengths": {name: 0 for name in se.ALL_QUEUES},
    }
    values.update(overrides)
    return se.Facts(**values)


def _evaluate(facts: se.Facts, *, since=None, host_reasons=(), horizon=300.0) -> dict:
    return se.evaluate(facts, N, horizon, since, list(host_reasons), NOW)


def _codes(result: dict) -> list[str]:
    return [reason["code"] for reason in result["reasons"]]


# ── consumed vs orphan queues ────────────────────────────────────────────────────


def _queues_consumed_by_worker_modules() -> set[str]:
    consumed: set[str] = set()
    for path in WORKERS_DIR.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", getattr(node.func, "attr", None)) == "run_worker"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.startswith("queue:")
            ):
                consumed.add(node.args[0].value)
    return consumed


def test_consumed_queues_match_the_worker_modules():
    assert se.CONSUMED_QUEUES == _queues_consumed_by_worker_modules()


def test_orphan_queues_are_the_routed_queues_nobody_consumes():
    assert se.ORPHAN_QUEUES == {"queue:uploads", "queue:webhooks", "queue:reports"}
    assert se.ORPHAN_QUEUES == set(QUEUE_MAP.values()) - se.CONSUMED_QUEUES


def test_migration_lock_halves():
    high, low = se.migration_lock_halves()
    assert (high << 32) | low == se.MIGRATION_LOCK_KEY


# ── evaluate: eligible ───────────────────────────────────────────────────────────


def test_idle_and_empty_is_eligible_with_the_documented_shape():
    result = _evaluate(_facts())

    assert result["eligible"] is True
    assert result["reasons"] == []
    assert result["schema"] == 1
    assert result["checked_at"] == NOW.isoformat()
    assert result["thresholds"] == {"idle_seconds": 3600, "retry_horizon_seconds": 300}
    metrics = result["metrics"]
    assert metrics["idle_basis"] == "human_activity"
    assert metrics["idle_seconds"] == pytest.approx(2 * N)
    assert metrics["last_by_scope"]["floor"] == metrics["last_human_activity_at"]
    assert metrics["last_source"] == "http"
    assert set(metrics["tasks"]) == {
        "open", "pending", "in_progress", "retrying", "retry_scheduled",
        "retry_due_within_horizon", "orphan",
    }
    assert metrics["tasks"]["orphan"] == {"queue:reports": 0, "queue:uploads": 0, "queue:webhooks": 0}
    assert set(metrics["queues"]) == se.ALL_QUEUES
    assert metrics["api_heartbeat"] == {
        "at": NOW.isoformat(),
        "started_at": (NOW - timedelta(days=1)).isoformat(),
        "sockets": 2,
        "users": 1,
    }
    assert metrics["db_sessions"] == {"migrate": 0, "db_copy": 0}
    json.dumps(result)  # serialisable as is


# ── evaluate: one test per blocking reason ───────────────────────────────────────


def test_recent_human_activity_blocks():
    result = _evaluate(_facts(activity=_idle_activity(N - 1)))
    assert _codes(result) == ["recent_human_activity"]
    assert result["reasons"][0]["detail"]["basis"] == "human_activity"


def test_idle_exactly_at_threshold_is_eligible():
    assert _evaluate(_facts(activity=_idle_activity(N)))["eligible"] is True


def test_missing_activity_key_measures_from_api_started_at():
    no_key = HumanActivity(last_at=None)
    fresh = {"at": NOW.timestamp(), "started_at": NOW.timestamp() - 60, "sockets": 0, "users": 0}
    old = {"at": NOW.timestamp(), "started_at": NOW.timestamp() - 2 * N, "sockets": 0, "users": 0}

    fresh_result = _evaluate(_facts(activity=no_key, api_heartbeat=fresh))
    old_result = _evaluate(_facts(activity=no_key, api_heartbeat=old))

    assert _codes(fresh_result) == ["recent_human_activity"]
    assert fresh_result["metrics"]["idle_basis"] == "api_started_at"
    assert fresh_result["metrics"]["idle_seconds"] == pytest.approx(60)
    assert fresh_result["reasons"][0]["detail"]["basis"] == "api_started_at"
    assert old_result["eligible"] is True
    assert old_result["metrics"]["idle_basis"] == "api_started_at"
    assert old_result["metrics"]["last_human_activity_at"] is None


def test_a_fresh_start_is_not_idle_however_old_the_last_activity_is():
    # Woken 60 s ago; the last human activity is from before the sleep, days old.
    started = {"at": NOW.timestamp(), "started_at": NOW.timestamp() - 60, "sockets": 0, "users": 0}
    result = _evaluate(_facts(activity=_idle_activity(3 * 86_400), api_heartbeat=started))

    assert _codes(result) == ["recent_human_activity"]
    assert result["metrics"]["idle_basis"] == "api_started_at"
    assert result["metrics"]["idle_seconds"] == pytest.approx(60)


def test_no_activity_key_and_no_heartbeat_is_activity_unknown():
    result = _evaluate(_facts(activity=HumanActivity(last_at=None), api_heartbeat=None))
    assert _codes(result) == ["activity_unknown"]
    assert result["metrics"]["idle_seconds"] is None
    assert result["metrics"]["idle_basis"] is None
    assert result["metrics"]["api_heartbeat"] is None


def test_human_activity_since_blocks_even_when_idle_enough():
    facts = _facts()  # idle 2N: eligible on idle alone
    last_at = datetime.fromtimestamp(facts.activity.last_at, timezone.utc)

    at_t = _evaluate(facts, since=last_at)
    after = _evaluate(facts, since=last_at + timedelta(seconds=1))

    assert _codes(at_t) == ["human_activity_since"]
    assert at_t["reasons"][0]["detail"]["since"] == last_at.isoformat()
    assert after["eligible"] is True


def test_tasks_in_progress_counts_in_progress_and_retrying():
    result = _evaluate(_facts(task_counts={
        ("send_push_notification", "in_progress"): 1,
        ("record_view_end", "retrying"): 2,
    }))
    assert _codes(result) == ["tasks_in_progress"]
    assert result["reasons"][0]["detail"] == {
        "count": 3, "types": {"record_view_end": 2, "send_push_notification": 1},
    }
    assert result["metrics"]["tasks"]["in_progress"] == 1
    assert result["metrics"]["tasks"]["retrying"] == 2


def test_tasks_open_blocks():
    result = _evaluate(_facts(task_counts={("record_view_start", "open"): 4}))
    assert _codes(result) == ["tasks_open"]
    assert result["reasons"][0]["detail"] == {"count": 4, "types": {"record_view_start": 4}}


def test_tasks_pending_blocks():
    result = _evaluate(_facts(task_counts={("process_step_transition", "pending"): 2}))
    assert _codes(result) == ["tasks_pending"]


def test_retry_due_within_horizon_blocks():
    result = _evaluate(_facts(
        task_counts={("create_notifications", "retry_scheduled"): 3},
        retry_due={"create_notifications": 2},
    ))
    assert _codes(result) == ["retry_due_within_horizon"]
    assert result["reasons"][0]["detail"] == {"count": 2, "types": {"create_notifications": 2}}
    assert result["metrics"]["tasks"]["retry_scheduled"] == 3
    assert result["metrics"]["tasks"]["retry_due_within_horizon"] == 2


def test_retry_scheduled_beyond_horizon_is_not_blocking():
    result = _evaluate(_facts(task_counts={("create_notifications", "retry_scheduled"): 3}))
    assert result["eligible"] is True
    assert result["metrics"]["tasks"]["retry_scheduled"] == 3


def test_consumed_queue_not_empty_blocks():
    lengths = {name: 0 for name in se.ALL_QUEUES} | {"queue:presence": 5}
    result = _evaluate(_facts(queue_lengths=lengths))
    assert _codes(result) == ["queue_not_empty"]
    assert result["reasons"][0]["detail"] == {"queues": {"queue:presence": 5}}


def test_migration_lock_blocks():
    result = _evaluate(_facts(migration_lock_present=True))
    assert _codes(result) == ["migration_running"]
    assert result["reasons"][0]["detail"] == {"advisory_lock": True, "sessions": 0}


def test_migrate_session_blocks():
    result = _evaluate(_facts(migrate_sessions=1))
    assert _codes(result) == ["migration_running"]
    assert result["metrics"]["db_sessions"]["migrate"] == 1


def test_db_copy_session_blocks():
    result = _evaluate(_facts(db_copy_sessions=2))
    assert _codes(result) == ["db_copy_running"]
    assert result["metrics"]["db_sessions"] == {"migrate": 0, "db_copy": 2}


def test_host_reasons_are_merged_in_order():
    result = _evaluate(_facts(), host_reasons=[("deploy_lock_held", None), ("container_unhealthy", "api")])
    assert result["reasons"] == [
        {"code": "deploy_lock_held", "detail": None},
        {"code": "container_unhealthy", "detail": "api"},
    ]
    assert result["eligible"] is False


def test_every_reason_at_once_keeps_a_stable_order():
    result = _evaluate(
        _facts(
            activity=_idle_activity(10),
            task_counts={
                ("record_view_end", "in_progress"): 1,
                ("record_view_end", "open"): 1,
                ("record_view_end", "pending"): 1,
            },
            retry_due={"record_view_end": 1},
            queue_lengths={"queue:tasks": 1},
            migration_lock_present=True,
            db_copy_sessions=1,
        ),
        since=NOW - timedelta(minutes=1),
        host_reasons=[("deploy_lock_held", None)],
    )
    assert _codes(result) == [
        "recent_human_activity", "human_activity_since", "tasks_in_progress", "tasks_open",
        "tasks_pending", "retry_due_within_horizon", "queue_not_empty", "migration_running",
        "db_copy_running", "deploy_lock_held",
    ]


# ── evaluate: never blocking ─────────────────────────────────────────────────────


def test_orphan_types_and_queues_are_reported_not_blocking():
    result = _evaluate(_facts(
        task_counts={
            ("upload_image", "open"): 2,          # queue:uploads
            ("deliver_webhook", "pending"): 1,    # queue:webhooks
            ("recurring_send_report", "open"): 3, # queue:reports
            ("delayed_send_report", "retry_scheduled"): 1,
        },
        retry_due={"delayed_send_report": 1},
        queue_lengths={name: 0 for name in se.ALL_QUEUES} | {"queue:reports": 40, "queue:uploads": 7},
    ))

    assert result["eligible"] is True
    tasks = result["metrics"]["tasks"]
    assert tasks["orphan"] == {"queue:reports": 4, "queue:uploads": 2, "queue:webhooks": 1}
    assert tasks["open"] == tasks["pending"] == tasks["retry_due_within_horizon"] == 0
    assert result["metrics"]["queues"]["queue:reports"] == 40


def test_unknown_task_type_counts_as_unmapped_orphan():
    result = _evaluate(_facts(task_counts={("no_such_type", "open"): 1}))
    assert result["eligible"] is True
    assert result["metrics"]["tasks"]["orphan"]["unmapped"] == 1


def test_due_delayed_and_recurring_jobs_are_informational_only():
    overdue = NOW - timedelta(hours=1)
    result = _evaluate(_facts(
        delayed_next_due_at=overdue,
        recurring_next_due_at={"auto_clock_out_open_shifts": NOW, "reminder": NOW + timedelta(hours=2)},
    ))
    assert result["eligible"] is True
    assert result["metrics"]["delayed_next_due_at"] == overdue.isoformat()
    assert result["metrics"]["recurring_next_due_at"] == {
        "auto_clock_out_open_shifts": NOW.isoformat(),
        "reminder": (NOW + timedelta(hours=2)).isoformat(),
    }


def test_open_sockets_are_informational_only():
    heartbeat = {"at": NOW.timestamp(), "started_at": NOW.timestamp() - 86400, "sockets": 12, "users": 5}
    result = _evaluate(_facts(api_heartbeat=heartbeat))
    assert result["eligible"] is True
    assert result["metrics"]["api_heartbeat"]["sockets"] == 12


# ── argument parsing ─────────────────────────────────────────────────────────────


def test_idle_seconds_is_required(capsys):
    assert se.main([]) == se.EXIT_CHECK_FAILED
    result = json.loads(capsys.readouterr().out)
    assert _codes(result) == ["check_failed"]
    assert "idle-seconds" in result["reasons"][0]["detail"]


@pytest.mark.parametrize("bad", ["Deploy", "has-dash", "", "a b", "=detail"])
def test_host_reason_code_is_validated(capsys, bad):
    assert se.main(["--idle-seconds", "10", "--host-reason", bad]) == se.EXIT_CHECK_FAILED
    assert _codes(json.loads(capsys.readouterr().out)) == ["check_failed"]


def test_host_reason_parsing():
    assert se.parse_host_reason("deploy_lock_held") == ("deploy_lock_held", None)
    assert se.parse_host_reason("container_unhealthy=api=x") == ("container_unhealthy", "api=x")
    assert se.parse_host_reason("db_copy_container_running=") == ("db_copy_container_running", "")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1790000000", datetime.fromtimestamp(1790000000, timezone.utc)),
        ("1790000000.5", datetime.fromtimestamp(1790000000.5, timezone.utc)),
        ("2026-09-30T12:00:00Z", NOW),
        ("2026-09-30T14:00:00+02:00", NOW),
        ("2026-09-30T12:00:00", NOW),
    ],
)
def test_since_parsing(text, expected):
    assert se.parse_since(text) == expected


def test_negative_idle_seconds_is_refused(capsys):
    assert se.main(["--idle-seconds", "-1"]) == se.EXIT_CHECK_FAILED
    capsys.readouterr()


# ── main: exit codes and fail-closed ─────────────────────────────────────────────


@pytest.fixture
def stub_gather(monkeypatch):
    holder: dict = {"facts": _facts(), "calls": []}

    async def _gather(now, retry_horizon):
        holder["calls"].append((now, retry_horizon))
        if isinstance(holder["facts"], BaseException):
            raise holder["facts"]
        return holder["facts"]

    monkeypatch.setattr(se, "gather_facts", _gather)
    monkeypatch.setattr(se, "evaluate", _evaluate_at_now_of_call(se.evaluate))
    return holder


def _evaluate_at_now_of_call(real):
    # main() uses the wall clock; pin evaluation to NOW so the stub facts stay idle.
    def _wrapped(facts, idle, horizon, since, host_reasons, _now):
        return real(facts, idle, horizon, since, host_reasons, NOW)
    return _wrapped


def test_exit_0_when_eligible(capsys, stub_gather):
    assert se.main(["--idle-seconds", str(N)]) == se.EXIT_ELIGIBLE
    out = capsys.readouterr().out
    assert out.count("\n") == 1  # exactly one JSON object
    assert json.loads(out)["eligible"] is True
    assert stub_gather["calls"][0][1] == 300.0  # default retry horizon


def test_exit_1_when_not_eligible(capsys, stub_gather):
    stub_gather["facts"] = _facts(task_counts={("record_view_end", "in_progress"): 1})
    assert se.main(["--idle-seconds", str(N), "--retry-horizon", "60"]) == se.EXIT_NOT_ELIGIBLE
    result = json.loads(capsys.readouterr().out)
    assert _codes(result) == ["tasks_in_progress"]
    assert result["thresholds"] == {"idle_seconds": 3600, "retry_horizon_seconds": 60}
    assert stub_gather["calls"][0][1] == 60.0


def test_exit_1_with_host_reason_and_since(capsys, stub_gather):
    code = se.main([
        "--idle-seconds", str(N), "--since", "2020-01-01T00:00:00Z",
        "--host-reason", "deploy_lock_held", "--host-reason", "container_unhealthy=worker",
    ])
    assert code == se.EXIT_NOT_ELIGIBLE
    assert _codes(json.loads(capsys.readouterr().out)) == [
        "human_activity_since", "deploy_lock_held", "container_unhealthy",
    ]


def test_exit_2_on_unexpected_gather_error(capsys, stub_gather):
    stub_gather["facts"] = RuntimeError("password=hunter2 host=db.internal")
    assert se.main(["--idle-seconds", str(N)]) == se.EXIT_CHECK_FAILED
    out = capsys.readouterr().out
    result = json.loads(out)
    assert result["eligible"] is False
    assert _codes(result) == ["check_failed"]
    assert "hunter2" not in out and "db.internal" not in out


@pytest.fixture
def fake_redis(monkeypatch) -> FakeAsyncRedis:
    redis = FakeAsyncRedis()
    monkeypatch.setattr(async_client, "get_async_redis", lambda: redis)
    return redis


SECRET_URL = "postgresql+asyncpg://sleepcheck_user:Sup3r-S3cret-PW@127.0.0.1:1/sleepcheck_db"


def test_db_down_exits_2_with_check_failed_and_no_secret(monkeypatch, capsys, fake_redis):
    monkeypatch.setattr(settings, "database_url", SECRET_URL)
    monkeypatch.setattr(se, "CONNECT_TIMEOUT_SECONDS", 2.0)

    assert se.main(["--idle-seconds", str(N)]) == se.EXIT_CHECK_FAILED

    out = capsys.readouterr().out
    result = json.loads(out)
    assert _codes(result) == ["check_failed"]
    assert result["eligible"] is False
    for secret in ("Sup3r-S3cret-PW", "sleepcheck_user", "sleepcheck_db", "127.0.0.1", "postgresql"):
        assert secret not in out


def test_redis_down_exits_2_not_eligible(monkeypatch, capsys, fake_redis):
    fake_redis.fail = ConnectionError("Error 111 connecting to redis://:pw@redis-host:6379")
    connected: list[str] = []

    async def _no_db(*_args, **_kwargs):
        connected.append("db")
        raise AssertionError("must not reach the database")

    monkeypatch.setattr(se, "connect", _no_db)

    assert se.main(["--idle-seconds", str(N)]) == se.EXIT_CHECK_FAILED

    out = capsys.readouterr().out
    result = json.loads(out)
    assert result["eligible"] is False
    assert _codes(result) == ["check_failed"]
    assert "redis-host" not in out and ":pw@" not in out
    assert connected == []


def test_hanging_redis_fails_closed(monkeypatch, capsys, fake_redis):
    fake_redis.delay = 5
    monkeypatch.setattr(se, "REDIS_TIMEOUT_SECONDS", 0.05)
    assert se.main(["--idle-seconds", str(N)]) == se.EXIT_CHECK_FAILED
    assert _codes(json.loads(capsys.readouterr().out)) == ["check_failed"]


def test_full_success_output_contains_no_secret(monkeypatch, capsys, stub_gather):
    monkeypatch.setattr(settings, "database_url", SECRET_URL)
    se.main(["--idle-seconds", str(N)])
    out = capsys.readouterr().out
    assert "Sup3r-S3cret-PW" not in out and "sleepcheck" not in out
