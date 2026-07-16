"""Metric definitions for the insights engine (pure).

Each metric extracts a single number from a :class:`DailyStats`. Extractors return
``None`` when the metric is undefined for that day (e.g. a zero denominator) so the
engine skips it cleanly instead of dividing by zero.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from beyo_manager.domain.analytics.insights.results import DailyStats


@dataclass(frozen=True)
class MetricSpec:
    key: str
    higher_is_better: bool
    # True when the metric is a distribution ratio that stays fair mid-day;
    # False for cumulative volumes that are only comparable once the day is done.
    intraday_safe: bool
    extract: Callable[[DailyStats], float | None]


def _focus_ratio(d: DailyStats) -> float | None:
    active = d.working_seconds + d.pause_seconds
    return d.working_seconds / active if active > 0 else None


def _throughput(d: DailyStats) -> float | None:
    hours = d.working_seconds / 3600
    return d.completed_count / hours if hours > 0 else None


def _avg_pause_seconds(d: DailyStats) -> float | None:
    return d.pause_seconds / d.pause_count if d.pause_count > 0 else None


def _fragmentation(d: DailyStats) -> float | None:
    return d.working_count / d.completed_count if d.completed_count > 0 else None


def _resolve_rate(d: DailyStats) -> float | None:
    return d.issues_resolved_count / d.issues_count if d.issues_count > 0 else None


METRICS: dict[str, MetricSpec] = {
    "completed_count": MetricSpec(
        "completed_count", higher_is_better=True, intraday_safe=False,
        extract=lambda d: float(d.completed_count),
    ),
    "focus_ratio": MetricSpec(
        "focus_ratio", higher_is_better=True, intraday_safe=True, extract=_focus_ratio,
    ),
    "throughput": MetricSpec(
        "throughput", higher_is_better=True, intraday_safe=False, extract=_throughput,
    ),
    "avg_pause_seconds": MetricSpec(
        "avg_pause_seconds", higher_is_better=False, intraday_safe=True,
        extract=_avg_pause_seconds,
    ),
    "fragmentation": MetricSpec(
        "fragmentation", higher_is_better=False, intraday_safe=False, extract=_fragmentation,
    ),
    "shift_end_count": MetricSpec(
        "shift_end_count", higher_is_better=False, intraday_safe=False,
        extract=lambda d: float(d.ended_shift_count),
    ),
    "resolve_rate": MetricSpec(
        "resolve_rate", higher_is_better=True, intraday_safe=False, extract=_resolve_rate,
    ),
}
