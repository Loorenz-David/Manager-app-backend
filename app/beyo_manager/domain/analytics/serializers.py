from collections.abc import Iterable
from datetime import date, datetime

from beyo_manager.domain.analytics.insights.results import Insight

_RUNNING_STATES = ("working", "paused", "ended_shift")


def build_running_totals(open_records: Iterable[tuple[str, datetime]], now: datetime) -> dict:
    """Live add-on to the settled daily totals: the running time of currently-open
    (not-yet-booked) intervals, summed per state.

    ``open_records`` is ``(state_value, entered_at)`` pairs (time-bearing states only).
    The client shows ``daily_stats + running`` and ticks each metric by
    ``<state>_open_count × (now − as_of)``. Kept separate from settled totals so those
    stay reconcilable with the maintained table.
    """
    seconds = {state: 0 for state in _RUNNING_STATES}
    counts = {state: 0 for state in _RUNNING_STATES}
    for state, entered_at in open_records:
        if state not in seconds:
            continue
        seconds[state] += max(0, int((now - entered_at).total_seconds()))
        counts[state] += 1
    return {
        "working_seconds": seconds["working"],
        "pause_seconds": seconds["paused"],
        "ended_shift_seconds": seconds["ended_shift"],
        "working_open_count": counts["working"],
        "pause_open_count": counts["paused"],
        "ended_shift_open_count": counts["ended_shift"],
        "as_of": now.isoformat(),
    }


def serialize_insight(insight: Insight) -> dict:
    return {
        "code": insight.code,
        "polarity": insight.polarity,
        "metric": insight.metric,
        "target_value": insight.target_value,
        "baseline_value": insight.baseline_value,
        "delta": insight.delta,
        "delta_pct": insight.delta_pct,
        "sample_size": insight.sample_size,
        "severity": insight.severity,
    }


def serialize_step_contribution(
    working_seconds: int = 0,
    pause_seconds: int = 0,
    ended_shift_seconds: int = 0,
    completed_count: int = 0,
) -> dict:
    return {
        "working_seconds": working_seconds,
        "pause_seconds": pause_seconds,
        "ended_shift_seconds": ended_shift_seconds,
        "completed_count": completed_count,
    }


def serialize_user_daily_work_stats_full(
    work_date: date,
    total_working_seconds: int = 0,
    total_pause_seconds: int = 0,
    total_ended_shift_seconds: int = 0,
    total_completed_count: int = 0,
) -> dict:
    return {
        "work_date": work_date.isoformat(),
        "total_working_seconds": total_working_seconds,
        "total_pause_seconds": total_pause_seconds,
        "total_ended_shift_seconds": total_ended_shift_seconds,
        "total_completed_count": total_completed_count,
    }


def serialize_user_daily_work_stats(
    work_date: date,
    total_working_seconds: int = 0,
    total_pause_seconds: int = 0,
    total_completed_count: int = 0,
) -> dict:
    return {
        "work_date": work_date.isoformat(),
        "total_working_seconds": total_working_seconds,
        "total_pause_seconds": total_pause_seconds,
        "total_completed_count": total_completed_count,
    }
