"""Insight rules — the menu, expressed as data (pure).

Positive and negative insights are the *same metric, opposite sign*: the engine
picks ``code_positive`` or ``code_negative`` from whether the day beat or trailed
the baseline (accounting for whether higher is better). A ``None`` code disables
that direction (e.g. we don't celebrate a low pause time, only flag a high one).

Thresholds are v1 starting points, tuned to avoid noise; they live on the rule so
they are trivial to adjust per metric without touching the engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InsightRule:
    metric_key: str
    code_positive: str | None
    code_negative: str | None
    abs_threshold: float   # minimum absolute delta vs baseline to be material
    rel_threshold: float   # minimum relative delta (|delta| / |baseline|)


DEFAULT_RULES: tuple[InsightRule, ...] = (
    InsightRule("completed_count", "completion_surge", "completion_dip",
                abs_threshold=3, rel_threshold=0.40),
    InsightRule("focus_ratio", "deep_focus", None,
                abs_threshold=0.10, rel_threshold=0.30),          # 10 percentage points
    InsightRule("throughput", "faster_pace", "slower_pace",
                abs_threshold=0.40, rel_threshold=0.25),          # steps/hour
    InsightRule("avg_pause_seconds", None, "rising_pauses",
                abs_threshold=120, rel_threshold=0.30),           # 2 minutes/pause
    InsightRule("shift_end_count", None, "leaving_steps_mid_shift",
                abs_threshold=2, rel_threshold=0.50),
    InsightRule("fragmentation", None, "choppy_work",
                abs_threshold=1.0, rel_threshold=0.40),           # +1 work-session/step
    InsightRule("resolve_rate", None, "quality_watch",
                abs_threshold=0.20, rel_threshold=0.25),          # 20 percentage points
)
