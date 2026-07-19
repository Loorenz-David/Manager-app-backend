"""Read-time loader for trusted per-step estimation samples."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions

ESTIMATION_LOOKBACK_DAYS = 28
ESTIMATION_MIN_SAMPLE = 4
# Minimum trusted completed steps backing a `mean` fill; below this the estimate is
# too thin to be meaningful (a tiny denominator explodes the per-step average), so the
# fill is suppressed to 0. Mirrors ESTIMATION_MIN_SAMPLE for the median/iqr sample.
ESTIMATION_MIN_TRUSTED_STEPS = 4


async def load_trusted_step_duration_sample(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> dict[tuple[str, str], list[float]]:
    """Load trusted completed-step durations grouped by section and state.

    Each sample point is one step's positive, concurrency-averaged duration in a
    state. Incomplete, open, deleted, or flagged steps are excluded.
    """
    contributions = await compute_record_contributions(
        session, workspace_id, user_id, window_start, window_end, now
    )
    per_step_state: dict[tuple[str, str, str], float] = defaultdict(float)
    for contribution in contributions:
        if (
            contribution.is_open
            or contribution.step_is_deleted
            or not contribution.step_is_completed
            or contribution.marked_wrong
            or not (window_start <= contribution.entered_at < window_end)
        ):
            continue
        per_step_state[
            (contribution.working_section_id, contribution.state, contribution.step_id)
        ] += contribution.seconds

    samples: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (section_id, state, _step_id), seconds in per_step_state.items():
        if seconds > 0:
            samples[(section_id, state)].append(float(seconds))
    return dict(samples)


def estimation_window(date_to, *, days: int = ESTIMATION_LOOKBACK_DAYS):
    """Return the half-open UTC window ending after the inclusive ``date_to``."""
    from datetime import time, timezone

    end = datetime.combine(date_to, time.min, tzinfo=timezone.utc) + timedelta(days=1)
    return end - timedelta(days=days), end
