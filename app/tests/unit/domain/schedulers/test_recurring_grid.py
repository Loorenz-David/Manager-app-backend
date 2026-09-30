"""Recurring schedulers fire on a fixed grid anchored at ``created_at`` (unit B-7).

Owner decision Q3: work due while production sleeps runs at the next wake; missed
intervals collapse into ONE run, and the schedule stays on its grid (never re-anchored to
the wake time).
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from beyo_manager.domain.schedulers.enums import RecurringSchedulerIntervalValueEnum as Unit
from beyo_manager.domain.schedulers.enums import RecurringSchedulerTypeEnum
from beyo_manager.domain.schedulers.recurring_grid import (
    INTERVAL_UNIT_TO_SECONDS,
    grid_point,
    recurring_grid_point,
    recurring_interval,
    recurring_is_due,
    recurring_next_run_at,
)
from beyo_manager.services.infra.schedulers import recurring_scheduler_runner as runner


ANCHOR = datetime(2026, 7, 20, tzinfo=timezone.utc)  # the clock-out job's midnight anchor
DAY = timedelta(days=1)


@dataclass
class Job:
    created_at: datetime = ANCHOR
    interval: int = 1
    interval_value: Unit = Unit.DAYS
    last_interval: datetime | None = None


def _fire(job: Job, now: datetime) -> None:
    """What the runner does on fire."""
    job.last_interval = recurring_grid_point(job, now)


def test_every_interval_unit_keeps_its_existing_length() -> None:
    assert set(INTERVAL_UNIT_TO_SECONDS) == set(Unit)
    assert recurring_interval(5, Unit.SECONDS) == timedelta(seconds=5)
    assert recurring_interval(5, Unit.MINUTES) == timedelta(minutes=5)
    assert recurring_interval(5, Unit.DAYS) == timedelta(days=5)
    # MONTHS is a fixed 30 days, not a calendar month — unchanged semantics.
    assert recurring_interval(1, Unit.MONTHS) == timedelta(days=30)
    # The runner still exposes the same table.
    assert runner.INTERVAL_UNIT_TO_SECONDS is INTERVAL_UNIT_TO_SECONDS


def test_non_positive_interval_has_no_grid() -> None:
    with pytest.raises(ValueError):
        recurring_interval(0, Unit.DAYS)


def test_grid_point_is_the_latest_slot_at_or_before_now() -> None:
    assert grid_point(ANCHOR, DAY, ANCHOR) == ANCHOR
    assert grid_point(ANCHOR, DAY, ANCHOR + DAY - timedelta(microseconds=1)) == ANCHOR
    assert grid_point(ANCHOR, DAY, ANCHOR + 3 * DAY) == ANCHOR + 3 * DAY
    assert grid_point(ANCHOR, DAY, ANCHOR + 3 * DAY + timedelta(hours=7)) == ANCHOR + 3 * DAY


def test_never_fired_job_is_due_at_its_anchor_but_not_before() -> None:
    job = Job()
    assert recurring_is_due(job, ANCHOR) is True
    assert recurring_next_run_at(job, ANCHOR) == ANCHOR
    assert recurring_is_due(job, ANCHOR - timedelta(seconds=1)) is False
    assert recurring_next_run_at(job, ANCHOR - timedelta(hours=1)) == ANCHOR


def test_on_time_fire_serves_its_slot_and_schedules_the_next() -> None:
    job = Job(last_interval=ANCHOR + 9 * DAY)
    now = ANCHOR + 10 * DAY + timedelta(seconds=4)  # a poll just after the slot

    assert recurring_is_due(job, ANCHOR + 10 * DAY - timedelta(seconds=1)) is False
    assert recurring_is_due(job, now) is True
    _fire(job, now)

    assert job.last_interval == ANCHOR + 10 * DAY
    assert recurring_is_due(job, now) is False
    assert recurring_next_run_at(job, now) == ANCHOR + 11 * DAY


def test_late_fire_does_not_move_the_next_slot() -> None:
    job = Job(last_interval=ANCHOR + 9 * DAY)
    late = ANCHOR + 10 * DAY + timedelta(hours=7, minutes=13)

    assert recurring_is_due(job, late) is True
    _fire(job, late)

    assert job.last_interval == ANCHOR + 10 * DAY
    # Next slot is tomorrow's midnight, not "late + 1 day".
    assert recurring_next_run_at(job, late) == ANCHOR + 11 * DAY
    assert recurring_is_due(job, ANCHOR + 11 * DAY - timedelta(seconds=1)) is False
    assert recurring_is_due(job, ANCHOR + 11 * DAY) is True


def test_a_missed_three_day_gap_fires_once_and_stays_on_the_grid() -> None:
    job = Job(last_interval=ANCHOR + 5 * DAY)
    wake = ANCHOR + 8 * DAY + timedelta(hours=13)  # slots 6, 7 and 8 were all missed

    assert recurring_next_run_at(job, wake) == ANCHOR + 8 * DAY  # due now
    fires = 0
    for poll in range(30):  # the runner keeps polling every 10 s after waking
        now = wake + timedelta(seconds=10 * poll)
        if recurring_is_due(job, now):
            _fire(job, now)
            fires += 1

    assert fires == 1
    assert job.last_interval == ANCHOR + 8 * DAY
    assert recurring_next_run_at(job, wake) == ANCHOR + 9 * DAY


def test_no_drift_over_many_intervals_fired_late() -> None:
    rng = random.Random(20260930)
    job = Job(interval=6, interval_value=Unit.MINUTES)
    step = timedelta(minutes=6)
    now = ANCHOR
    for k in range(500):
        # Wake up somewhere inside slot k — never exactly on time.
        now = ANCHOR + k * step + timedelta(seconds=rng.uniform(0, 300))
        assert recurring_is_due(job, now) is True, k
        _fire(job, now)
        assert job.last_interval == ANCHOR + k * step, k
        assert recurring_next_run_at(job, now) == ANCHOR + (k + 1) * step, k
        assert recurring_is_due(job, now) is False, k


def test_months_is_thirty_days_on_the_grid() -> None:
    anchor = datetime(2026, 1, 31, tzinfo=timezone.utc)
    job = Job(created_at=anchor, interval=1, interval_value=Unit.MONTHS, last_interval=anchor)

    assert recurring_next_run_at(job, anchor + timedelta(days=1)) == anchor + timedelta(days=30)
    assert recurring_is_due(job, anchor + timedelta(days=29, hours=23)) is False
    now = anchor + timedelta(days=61)
    assert recurring_is_due(job, now) is True
    _fire(job, now)
    assert job.last_interval == anchor + timedelta(days=60)
    assert recurring_next_run_at(job, now) == anchor + timedelta(days=90)


def test_a_drifted_legacy_last_interval_is_realigned_without_migration() -> None:
    # The pre-grid runner stored the actual fire time, which had crept past midnight.
    drifted = ANCHOR + 9 * DAY + timedelta(minutes=7, seconds=13)
    job = Job(last_interval=drifted)

    # Still inside slot 9: that slot counts as served.
    assert recurring_is_due(job, ANCHOR + 9 * DAY + timedelta(hours=12)) is False
    # The next slot is the grid's, not drifted + 1 day.
    assert recurring_next_run_at(job, ANCHOR + 9 * DAY + timedelta(hours=12)) == ANCHOR + 10 * DAY
    now = ANCHOR + 10 * DAY + timedelta(seconds=3)
    assert recurring_is_due(job, now) is True
    _fire(job, now)
    assert job.last_interval == ANCHOR + 10 * DAY


class _FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.commits = 0

    async def execute(self, _statement):
        return _FakeResult(self.rows)

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _Row(Job):
    type: object = None
    payload_snapshot: dict | None = None
    client_id: str = "rsch_test"
    event_client_id: str | None = None
    last_error: str | None = None


async def test_runner_records_the_grid_slot_not_the_fire_time(monkeypatch) -> None:
    wake = ANCHOR + 8 * DAY + timedelta(hours=13, minutes=2)
    row = _Row(
        last_interval=ANCHOR + 5 * DAY,
        type=RecurringSchedulerTypeEnum.AUTO_CLOCK_OUT_OPEN_SHIFTS,
        payload_snapshot={},
    )
    not_due = _Row(
        client_id="rsch_not_due",
        last_interval=ANCHOR + 8 * DAY,
        type=RecurringSchedulerTypeEnum.AUTO_CLOCK_OUT_OPEN_SHIFTS,
        payload_snapshot={},
    )
    session = _FakeSession([row, not_due])
    created: list[dict] = []

    async def _sessions():
        yield session

    async def _create_execution_task(**kwargs):
        created.append(kwargs)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return wake

    monkeypatch.setattr(runner, "get_db_session", _sessions)
    monkeypatch.setattr(runner, "create_execution_task", _create_execution_task)
    monkeypatch.setattr(runner.ActivityTracker, "touch", classmethod(lambda cls: None))
    monkeypatch.setattr(runner, "datetime", _FrozenDatetime)

    await runner._fire_due_recurring_schedulers()

    assert len(created) == 1  # three missed slots, one run
    assert created[0]["scheduled_at"] == wake
    assert row.last_interval == ANCHOR + 8 * DAY
    assert not_due.last_interval == ANCHOR + 8 * DAY
    assert session.commits == 1
    assert await runner._get_next_run_at() == ANCHOR + 9 * DAY
