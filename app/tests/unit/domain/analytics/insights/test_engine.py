"""Pure unit tests for the insights engine — no DB, no fixtures."""

from __future__ import annotations

from datetime import date, timedelta

from beyo_manager.domain.analytics.insights.config import InsightsConfig
from beyo_manager.domain.analytics.insights.engine import evaluate
from beyo_manager.domain.analytics.insights.results import DailyStats

TARGET = date(2026, 7, 15)  # a Wednesday


def _day(d: date, *, completed=0, working=0, pause=0, pause_count=0,
         working_count=0, ended_shift_count=0, issues=0, resolved=0) -> DailyStats:
    return DailyStats(
        work_date=d,
        working_seconds=working,
        pause_seconds=pause,
        ended_shift_seconds=0,
        completed_count=completed,
        working_count=working_count,
        pause_count=pause_count,
        ended_shift_count=ended_shift_count,
        issues_count=issues,
        issues_resolved_count=resolved,
    )


def _same_weekday_history(n_weeks: int, **day_kwargs) -> dict[date, DailyStats]:
    return {
        TARGET - timedelta(days=7 * k): _day(TARGET - timedelta(days=7 * k), **day_kwargs)
        for k in range(1, n_weeks + 1)
    }


def _codes(insights) -> set[str]:
    return {i.code for i in insights}


def test_completion_surge_fires_against_same_weekday_baseline():
    history = _same_weekday_history(4, completed=3, working=3600)
    history[TARGET] = _day(TARGET, completed=8, working=3600)
    out = evaluate(history, TARGET)
    surge = next(i for i in out if i.code == "completion_surge")
    assert surge.polarity == "positive"
    assert surge.baseline_value == 3
    assert surge.delta == 5
    assert surge.sample_size == 4


def test_completion_dip_fires_when_below_baseline():
    history = _same_weekday_history(4, completed=8, working=3600)
    history[TARGET] = _day(TARGET, completed=2, working=3600)
    assert "completion_dip" in _codes(evaluate(history, TARGET))


def test_below_threshold_stays_silent():
    # 3 -> 4 completions: fails the absolute (>=3) and relative (>=40%) gates.
    history = _same_weekday_history(4, completed=3, working=3600)
    history[TARGET] = _day(TARGET, completed=4, working=3600)
    assert "completion_surge" not in _codes(evaluate(history, TARGET))


def test_insufficient_history_suppresses_insights():
    history = {TARGET - timedelta(days=7): _day(TARGET - timedelta(days=7), completed=3, working=3600)}
    history[TARGET] = _day(TARGET, completed=9, working=3600)  # only 1 sample < min_samples(2)
    assert evaluate(history, TARGET) == []


def test_undefined_metric_is_skipped_not_crashed():
    # No pauses anywhere -> avg_pause_seconds is undefined; must not divide by zero.
    history = _same_weekday_history(4, completed=3, working=3600, pause=0, pause_count=0)
    history[TARGET] = _day(TARGET, completed=3, working=3600)
    assert evaluate(history, TARGET) == []  # nothing material, and no crash


def test_rising_pauses_is_negative_even_though_value_went_up():
    history = _same_weekday_history(4, completed=3, working=3600, pause=600, pause_count=6)  # 100s/pause
    history[TARGET] = _day(TARGET, completed=3, working=3600, pause=1800, pause_count=6)     # 300s/pause
    rising = next(i for i in evaluate(history, TARGET) if i.code == "rising_pauses")
    assert rising.polarity == "negative"


def test_in_progress_day_suppresses_volume_but_keeps_ratio_insights():
    # Focus ratio (intraday-safe) should still fire; completion (cumulative) must not.
    history = _same_weekday_history(4, completed=8, working=1000, pause=1000)  # focus 0.5
    history[TARGET] = _day(TARGET, completed=1, working=1900, pause=100)       # focus 0.95, few completions
    out = evaluate(history, TARGET, target_in_progress=True)
    codes = _codes(out)
    assert "deep_focus" in codes
    assert "completion_dip" not in codes


def test_top_k_caps_number_of_insights():
    cfg = InsightsConfig(top_k=1)
    history = _same_weekday_history(4, completed=8, working=3600, pause=1800, pause_count=6)
    history[TARGET] = _day(TARGET, completed=1, working=600, pause=3000, pause_count=10)
    assert len(evaluate(history, TARGET, cfg)) <= 1


def test_no_activity_on_target_returns_empty():
    history = _same_weekday_history(4, completed=5, working=3600)
    history[TARGET] = _day(TARGET)  # inactive day
    assert evaluate(history, TARGET) == []
