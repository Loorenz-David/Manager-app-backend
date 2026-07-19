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


def build_running_totals_averaged(
    open_records: Iterable[tuple[str, float]], now: datetime
) -> dict:
    """Same shape as :func:`build_running_totals`, but each open record contributes its
    **concurrency-averaged** running seconds (a batch step ticks at ``1/k``, so the
    worker-level total advances at real time). ``open_records`` is ``(state, seconds)``.

    Tick note (differs from the raw builder): advance the worker-level total by ``1/sec``
    per state while its ``*_open_count`` > 0 — not ``open_count × elapsed``.
    """
    seconds = {state: 0.0 for state in _RUNNING_STATES}
    counts = {state: 0 for state in _RUNNING_STATES}
    for state, secs in open_records:
        if state not in seconds:
            continue
        seconds[state] += secs
        counts[state] += 1
    return {
        "working_seconds": int(round(seconds["working"])),
        "pause_seconds": int(round(seconds["paused"])),
        "ended_shift_seconds": int(round(seconds["ended_shift"])),
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


def serialize_time_quality(
    trusted: int,
    wasted: int,
    inaccurate_step_count: int,
    estimated_fill: float,
    trusted_sample_size: int,
) -> dict:
    """Serialize one state's trusted/wasted/estimated alternatives.

    ``trusted_sample_size`` is the number of trusted steps that actually backed the
    ``estimated_fill`` under the selected strategy — the view-range trusted-completed
    count for ``mean``, the lookback sample count for ``median``/``iqr``. It's the
    frontend's confidence gate (low → treat the estimate as weak / suppress).
    """
    return {
        "trusted": trusted,
        "wasted": wasted,
        "inaccurate_step_count": inaccurate_step_count,
        "estimated_fill": float(estimated_fill),
        "trusted_sample_size": trusted_sample_size,
    }


def serialize_estimated_fill_by_strategy(
    *, mean: float, median: float, iqr: float
) -> dict[str, float]:
    return {"mean": float(mean), "median": float(median), "iqr": float(iqr)}


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


def serialize_user_range_work_stats(
    date_from: date,
    date_to: date,
    total_working_seconds: int = 0,
    total_pause_seconds: int = 0,
    total_completed_count: int = 0,
    time_quality: dict | None = None,
) -> dict:
    """Roster totals summed over an inclusive ``[date_from, date_to]`` range."""
    result = {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_working_seconds": total_working_seconds,
        "total_pause_seconds": total_pause_seconds,
        "total_completed_count": total_completed_count,
    }
    if time_quality is not None:
        result["time_quality"] = time_quality
    return result


def serialize_user_range_work_stats_full(
    date_from: date,
    date_to: date,
    total_working_seconds: int = 0,
    total_pause_seconds: int = 0,
    total_ended_shift_seconds: int = 0,
    total_completed_count: int = 0,
    time_quality: dict | None = None,
) -> dict:
    """Breakdown daily-stats summed over an inclusive range (includes ended-shift)."""
    result = {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_working_seconds": total_working_seconds,
        "total_pause_seconds": total_pause_seconds,
        "total_ended_shift_seconds": total_ended_shift_seconds,
        "total_completed_count": total_completed_count,
    }
    if time_quality is not None:
        result["time_quality"] = time_quality
    return result
