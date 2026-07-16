"""Pure unit tests for the live 'running' totals builder — no DB."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from beyo_manager.domain.analytics.serializers import build_running_totals

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def test_empty_is_all_zero_with_as_of():
    out = build_running_totals([], NOW)
    assert out == {
        "working_seconds": 0, "pause_seconds": 0, "ended_shift_seconds": 0,
        "working_open_count": 0, "pause_open_count": 0, "ended_shift_open_count": 0,
        "as_of": NOW.isoformat(),
    }


def test_sums_per_state_and_counts_multiple_open_pauses():
    records = [
        ("working", NOW - timedelta(hours=1)),                  # 3600
        ("paused", NOW - timedelta(hours=2)),                   # 7200
        ("paused", NOW - timedelta(minutes=90)),                # 5400
        ("paused", NOW - timedelta(minutes=75)),                # 4500
    ]
    out = build_running_totals(records, NOW)
    assert out["working_seconds"] == 3600
    assert out["working_open_count"] == 1
    assert out["pause_seconds"] == 7200 + 5400 + 4500
    assert out["pause_open_count"] == 3
    assert out["ended_shift_open_count"] == 0


def test_negative_clamped_and_unknown_state_ignored():
    records = [
        ("working", NOW + timedelta(minutes=5)),   # future entered_at -> clamp to 0
        ("completed", NOW - timedelta(hours=1)),   # not time-bearing -> ignored
    ]
    out = build_running_totals(records, NOW)
    assert out["working_seconds"] == 0
    assert out["working_open_count"] == 1
    assert out["pause_open_count"] == 0
