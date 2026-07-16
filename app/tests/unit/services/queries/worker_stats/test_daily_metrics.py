from datetime import date

import pytest

from beyo_manager.domain.analytics.serializers import serialize_user_daily_work_stats
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.queries.worker_stats.list_workers_last_interacted_step import (
    _resolve_work_date,
)


def test_daily_stats_serializer_returns_zero_filled_shape():
    assert serialize_user_daily_work_stats(date(2026, 7, 15)) == {
        "work_date": "2026-07-15",
        "total_working_seconds": 0,
        "total_pause_seconds": 0,
        "total_completed_count": 0,
    }


def test_work_date_defaults_to_utc_date_when_missing(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls, tz):
            return cls()

        def date(self):
            return date(2026, 7, 15)

    monkeypatch.setattr(
        "beyo_manager.services.queries.worker_stats.list_workers_last_interacted_step.datetime",
        FixedDateTime,
    )
    assert _resolve_work_date(None) == date(2026, 7, 15)


def test_invalid_work_date_raises_validation_error():
    with pytest.raises(ValidationError):
        _resolve_work_date("not-a-date")
