"""Tunable configuration for the insights engine (pure).

Widening the lookback later is a one-line change here (``baseline_weeks``); the
statistical gate then earns more samples and self-tightens with no code change.
"""

from __future__ import annotations

from dataclasses import dataclass

from beyo_manager.domain.analytics.insights.rules import DEFAULT_RULES, InsightRule


@dataclass(frozen=True)
class InsightsConfig:
    baseline_weeks: int = 4        # same-weekday samples looked back (use fewer if missing)
    min_samples: int = 2           # sufficiency gate — below this, stay silent
    z_min_samples: int = 3         # apply the statistical gate only once we have this many
    z_threshold: float = 1.0       # |z| a candidate must clear when the gate applies
    top_k: int = 3                 # max insights surfaced per worker
    streak_min_days: int = 3       # "on a roll" needs at least this many consecutive days
    streak_lookback_days: int = 14
    rules: tuple[InsightRule, ...] = DEFAULT_RULES


DEFAULT_CONFIG = InsightsConfig()


def lookback_days(config: InsightsConfig) -> int:
    """How many days of history the engine needs behind the target date."""
    return max(config.baseline_weeks * 7, config.streak_lookback_days)
