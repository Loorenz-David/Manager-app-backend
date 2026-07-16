"""The insights engine (pure).

``evaluate`` is a pure function of the worker's daily history and the target date.
No IO, no session — the query layer injects the data. This is what makes the hard
logic exhaustively unit-testable without a database.
"""

from __future__ import annotations

from datetime import date, timedelta

from beyo_manager.domain.analytics.insights.config import DEFAULT_CONFIG, InsightsConfig
from beyo_manager.domain.analytics.insights.metrics import METRICS
from beyo_manager.domain.analytics.insights.results import DailyStats, Insight
from beyo_manager.domain.analytics.insights.stats import is_material, median, severity, zscore

_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}


def _same_weekday_dates(target: date, weeks: int) -> list[date]:
    """The same weekday on each of the previous ``weeks`` weeks (excludes target)."""
    return [target - timedelta(days=7 * k) for k in range(1, weeks + 1)]


def _active_samples(
    daily_by_date: dict[date, DailyStats], dates: list[date], metric_key: str
) -> list[float]:
    extract = METRICS[metric_key].extract
    values: list[float] = []
    for dt in dates:
        row = daily_by_date.get(dt)
        if row is None or not row.is_active:
            continue
        value = extract(row)
        if value is not None:
            values.append(value)
    return values


def _detect_streak(
    daily_by_date: dict[date, DailyStats], target_date: date, config: InsightsConfig
) -> Insight | None:
    """Consecutive days (ending at target) at/above the worker's own recent bar."""
    lookback = [target_date - timedelta(days=k) for k in range(config.streak_lookback_days)]
    completed = [
        float(daily_by_date[d].completed_count)
        for d in lookback
        if d in daily_by_date and daily_by_date[d].is_active and daily_by_date[d].completed_count > 0
    ]
    if len(completed) < config.min_samples:
        return None
    bar = median(completed)

    run = 0
    cursor = target_date
    while True:
        row = daily_by_date.get(cursor)
        if row is None or not row.is_active or float(row.completed_count) < bar:
            break
        run += 1
        cursor -= timedelta(days=1)

    if run < config.streak_min_days:
        return None
    return Insight(
        code="on_a_roll",
        polarity="positive",
        metric="completed_count",
        target_value=float(run),
        baseline_value=round(bar, 3),
        delta=float(run),
        delta_pct=None,
        sample_size=len(completed),
        severity="high" if run >= config.streak_min_days + 2 else "medium",
    )


def _dedupe_correlated(candidates: list[Insight]) -> list[Insight]:
    """Drop the weaker of a correlated pair telling the same story.

    Throughput and completion move together; if a completion insight of the same
    polarity is present, the throughput one is redundant.
    """
    completion_polarities = {
        i.polarity for i in candidates if i.metric == "completed_count"
    }
    return [
        i
        for i in candidates
        if not (i.metric == "throughput" and i.polarity in completion_polarities)
    ]


def _rank_and_cap(candidates: list[Insight], top_k: int) -> list[Insight]:
    ranked = sorted(
        _dedupe_correlated(candidates),
        key=lambda i: (_SEVERITY_RANK.get(i.severity, 0), abs(i.delta_pct or 0.0)),
        reverse=True,
    )
    return ranked[:top_k]


def evaluate(
    daily_by_date: dict[date, DailyStats],
    target_date: date,
    config: InsightsConfig = DEFAULT_CONFIG,
    *,
    target_in_progress: bool = False,
) -> list[Insight]:
    """Produce the surfaced insights for one worker on ``target_date``.

    Returns ``[]`` when the day has no activity, there is not enough baseline
    history, or nothing crosses the materiality/statistical gates.
    """
    target = daily_by_date.get(target_date)
    if target is None or not target.is_active:
        return []

    baseline_dates = _same_weekday_dates(target_date, config.baseline_weeks)
    candidates: list[Insight] = []

    for rule in config.rules:
        metric = METRICS[rule.metric_key]
        # A cumulative volume compared mid-day looks low simply because the day
        # isn't over — only ratio metrics are fair while in progress.
        if target_in_progress and not metric.intraday_safe:
            continue

        target_value = metric.extract(target)
        if target_value is None:
            continue

        samples = _active_samples(daily_by_date, baseline_dates, rule.metric_key)
        if len(samples) < config.min_samples:
            continue

        baseline = median(samples)
        delta = target_value - baseline
        if delta == 0:
            continue

        improved = (delta > 0) == metric.higher_is_better
        code = rule.code_positive if improved else rule.code_negative
        if code is None:
            continue

        if not is_material(delta, baseline, rule.abs_threshold, rule.rel_threshold):
            continue

        z = zscore(target_value, samples)
        if len(samples) >= config.z_min_samples and z is not None and abs(z) < config.z_threshold:
            continue

        candidates.append(
            Insight(
                code=code,
                polarity="positive" if improved else "negative",
                metric=metric.key,
                target_value=round(target_value, 3),
                baseline_value=round(baseline, 3),
                delta=round(delta, 3),
                delta_pct=round(delta / baseline, 3) if baseline else None,
                sample_size=len(samples),
                severity=severity(delta, baseline, z),
            )
        )

    if not target_in_progress:
        streak = _detect_streak(daily_by_date, target_date, config)
        if streak is not None:
            candidates.append(streak)

    return _rank_and_cap(candidates, config.top_k)
