"""Result/input dataclasses for the worker-insights engine (pure domain layer)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DailyStats:
    """One worker's aggregated stats for a single day (mirrors user_daily_work_stats).

    Pure input to the engine — no ORM, no session. The query layer builds these.
    """

    work_date: date
    working_seconds: int
    pause_seconds: int
    ended_shift_seconds: int
    completed_count: int
    working_count: int
    pause_count: int
    ended_shift_count: int
    issues_count: int
    issues_resolved_count: int

    @property
    def is_active(self) -> bool:
        """A day counts as active if the worker did anything measurable on it.

        Days off are excluded from baselines so they can't deflate the average
        and manufacture fake surges.
        """
        return bool(
            self.working_seconds
            or self.pause_seconds
            or self.completed_count
            or self.working_count
        )


@dataclass(frozen=True)
class Insight:
    """A single, materially-significant observation about a worker's day.

    Carries codes + numbers only — copy is rendered client-side (i18n). The
    ``sample_size`` is surfaced so the UI can be honest about how much history
    the comparison is based on.
    """

    code: str          # e.g. "completion_surge", "rising_pauses"
    polarity: str      # "positive" | "negative"
    metric: str        # metric key the insight is derived from
    target_value: float
    baseline_value: float
    delta: float
    delta_pct: float | None
    sample_size: int
    severity: str      # "low" | "medium" | "high"
