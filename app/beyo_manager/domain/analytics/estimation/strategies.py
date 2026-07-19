"""Pure statistical strategies used to fill flagged step durations."""

from __future__ import annotations

from enum import StrEnum
from statistics import median as _median
from statistics import quantiles
from typing import Sequence


class TimeEstimationStrategy(StrEnum):
    MEAN = "mean"
    MEDIAN = "median"
    IQR = "iqr"


def mean(sample: Sequence[float]) -> float:
    """Return the arithmetic mean, or zero for an empty sample."""
    return sum(sample) / len(sample) if sample else 0.0


def median(sample: Sequence[float]) -> float:
    """Return the median, or zero for an empty sample."""
    return float(_median(sample)) if sample else 0.0


def iqr_trimmed_mean(sample: Sequence[float]) -> float:
    """Return the mean after removing Tukey outliers outside 1.5 × IQR."""
    if not sample:
        return 0.0
    if len(sample) == 1:
        return float(sample[0])

    values = sorted(float(value) for value in sample)
    q1, _, q3 = (float(value) for value in quantiles(values, n=4, method="inclusive"))
    iqr = q3 - q1
    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)
    retained = [value for value in values if lower_bound <= value <= upper_bound]
    return mean(retained)


def resolve(strategy: str | TimeEstimationStrategy) -> TimeEstimationStrategy:
    """Resolve a public strategy value into the domain enum."""
    return strategy if isinstance(strategy, TimeEstimationStrategy) else TimeEstimationStrategy(strategy)


def estimate_fill(step_count: int, per_step_value: float) -> float:
    """Return the estimated replacement duration for ``step_count`` flagged steps."""
    return float(step_count) * float(per_step_value)
