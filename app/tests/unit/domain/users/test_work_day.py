"""`work_day_end` — the single work-day boundary (owner decision Q1: UTC midnight)."""

from datetime import datetime, timedelta, timezone

import pytest

from beyo_manager.domain.users.work_day import (
    is_past_work_day_end,
    work_day_end,
    work_day_start,
)


TODAY = datetime(2026, 7, 15, tzinfo=timezone.utc)
YESTERDAY = TODAY - timedelta(days=1)


def test_work_day_end_is_the_first_utc_midnight_strictly_after() -> None:
    assert work_day_end(datetime(2026, 7, 14, 8, tzinfo=timezone.utc)) == TODAY
    assert work_day_end(datetime(2026, 7, 14, 23, 59, 59, 999999, tzinfo=timezone.utc)) == TODAY
    # Exactly midnight opens a day, so it ends at the NEXT midnight.
    assert work_day_end(TODAY) == TODAY + timedelta(days=1)


def test_work_day_is_normalized_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    # 01:30 at UTC+02:00 is 23:30 UTC the previous day.
    assert work_day_end(datetime(2026, 7, 15, 1, 30, tzinfo=plus_two)) == TODAY
    assert work_day_start(datetime(2026, 7, 15, 1, 30, tzinfo=plus_two)) == YESTERDAY
    assert work_day_end(datetime(2026, 7, 15, 1, 30, tzinfo=plus_two)).tzinfo is timezone.utc


def test_work_day_end_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError):
        work_day_end(datetime(2026, 7, 14, 8))


def test_is_past_work_day_end_is_inclusive_of_the_boundary() -> None:
    started = datetime(2026, 7, 14, 8, tzinfo=timezone.utc)
    assert is_past_work_day_end(started, TODAY) is True
    assert is_past_work_day_end(started, TODAY - timedelta(microseconds=1)) is False
    # Equivalent SQL-prefilter form: started_at < work_day_start(now).
    for now in (TODAY, TODAY + timedelta(hours=9), TODAY - timedelta(seconds=1)):
        assert is_past_work_day_end(started, now) is (started < work_day_start(now))
