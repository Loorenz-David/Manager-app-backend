"""When a recurring scheduler is due — a fixed grid, pure and importable.

A recurring job fires on the grid ``anchor + k * interval`` with ``anchor = created_at``.
It is never re-anchored to when it actually fired:

- ``grid_point(now)`` is the latest grid point at or before ``now``;
- the job is due iff it has never fired (``last_interval is None``) or its last fire was
  recorded for an earlier grid point (``last_interval < grid_point(now)``);
- on fire, ``last_interval`` is set to ``grid_point(now)`` — the slot served, not the wall
  time — so a late fire does not push every later fire back (no drift);
- any number of missed slots (production asleep, a crash, a delayed deploy) collapse into
  ONE fire at the next wake, and the schedule continues on the same grid.

A legacy ``last_interval`` written as the actual fire time (the pre-grid behaviour) lies
between two grid points; the ``<`` comparison realigns it on the next slot without a data
migration.

``MONTHS`` is a fixed 30 days, as it always was — not a calendar month.

Nothing here touches the database or the runner loop, so an eligibility CLI can import it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from beyo_manager.domain.schedulers.enums import RecurringSchedulerIntervalValueEnum


INTERVAL_UNIT_TO_SECONDS: dict[RecurringSchedulerIntervalValueEnum, int] = {
    RecurringSchedulerIntervalValueEnum.SECONDS: 1,
    RecurringSchedulerIntervalValueEnum.MINUTES: 60,
    RecurringSchedulerIntervalValueEnum.DAYS:    86_400,
    RecurringSchedulerIntervalValueEnum.MONTHS:  2_592_000,  # fixed 30 days
}


class RecurringGridFields(Protocol):
    """The four fields the grid reads — a `RecurringScheduler` row satisfies it."""

    created_at: datetime
    interval: int
    interval_value: RecurringSchedulerIntervalValueEnum
    last_interval: datetime | None


def recurring_interval(
    interval: int,
    interval_value: RecurringSchedulerIntervalValueEnum,
) -> timedelta:
    seconds = interval * INTERVAL_UNIT_TO_SECONDS[interval_value]
    if seconds <= 0:
        raise ValueError("A recurring interval must be positive.")
    return timedelta(seconds=seconds)


def grid_point(anchor: datetime, interval: timedelta, now: datetime) -> datetime:
    """The latest ``anchor + k * interval`` (integer ``k``) at or before ``now``."""
    return anchor + ((now - anchor) // interval) * interval


def recurring_grid_point(job: RecurringGridFields, now: datetime) -> datetime:
    return grid_point(
        job.created_at,
        recurring_interval(job.interval, job.interval_value),
        now,
    )


def recurring_is_due(job: RecurringGridFields, now: datetime) -> bool:
    """Due iff never fired or last fired for an earlier slot than ``grid_point(now)``.

    A job whose anchor is still in the future is not due yet.
    """
    if now < job.created_at:
        return False
    return job.last_interval is None or job.last_interval < recurring_grid_point(job, now)


def recurring_next_run_at(job: RecurringGridFields, now: datetime) -> datetime:
    """When the job should next fire, as seen at ``now``.

    A value ``<= now`` means it is due now (its current grid point, not yet served);
    otherwise it is the next grid point, ``grid_point(now) + interval``.
    """
    if now < job.created_at:
        return job.created_at
    current_slot = recurring_grid_point(job, now)
    if job.last_interval is None or job.last_interval < current_slot:
        return current_slot
    return current_slot + recurring_interval(job.interval, job.interval_value)
