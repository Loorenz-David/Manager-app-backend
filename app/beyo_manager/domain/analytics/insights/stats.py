"""Small statistical helpers for the insights engine (pure)."""

from __future__ import annotations

from statistics import median as _median, pstdev


def median(values: list[float]) -> float:
    return float(_median(values))


def zscore(value: float, samples: list[float]) -> float | None:
    """z of ``value`` against the sample distribution; None when undefined.

    Robust-ish: needs at least 2 samples and non-zero dispersion.
    """
    if len(samples) < 2:
        return None
    sd = pstdev(samples)
    if sd == 0:
        return None
    return (value - median(samples)) / sd


def is_material(delta: float, baseline: float, abs_threshold: float, rel_threshold: float) -> bool:
    """A delta must clear both an absolute and a relative bar to count.

    When the baseline is 0 the relative bar is undefined, so the absolute bar
    alone decides (prevents 0 -> small noise from firing on percentage alone).
    """
    if abs(delta) < abs_threshold:
        return False
    if baseline == 0:
        return True
    return abs(delta) / abs(baseline) >= rel_threshold


def severity(delta: float, baseline: float, z: float | None) -> str:
    """Bucket a candidate's strength. Uses z when we have enough samples, else
    falls back to relative magnitude."""
    if z is not None:
        magnitude = abs(z)
        if magnitude >= 2.0:
            return "high"
        if magnitude >= 1.3:
            return "medium"
        return "low"
    rel = abs(delta) / abs(baseline) if baseline else 1.0
    if rel >= 1.0:
        return "high"
    if rel >= 0.6:
        return "medium"
    return "low"
