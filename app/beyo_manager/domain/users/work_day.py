"""The work-day boundary — the single definition every shift rule reads.

A work day ends at **UTC midnight** (owner decision Q1, 2026-09-30). There is deliberately
no workspace or Stockholm timezone here: one boundary, one function, so the kiosk, the
nightly sweep and the live reconcile can never disagree about which day a shift belongs to.

An open shift that outlives its work day is *stale*. It is closed at its own
``work_day_end(started_at)`` — never at the moment someone happens to notice (Q2) — so the
result is the same whether the sweep ran on time, late, or after production slept.
"""

from datetime import datetime, time, timedelta, timezone


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
        raise ValueError("work-day arithmetic requires a timezone-aware datetime.")
    return ts.astimezone(timezone.utc)


def work_day_start(ts: datetime) -> datetime:
    """The UTC midnight at or before ``ts`` — the start of the work day containing it."""
    utc = _as_utc(ts)
    return datetime.combine(utc.date(), time.min, tzinfo=timezone.utc)


def work_day_end(ts: datetime) -> datetime:
    """The first UTC midnight strictly after ``ts``.

    ``ts`` exactly at midnight belongs to the day that midnight opens, so its end is the
    *next* midnight: a work day is the half-open interval ``[midnight, next midnight)``.
    """
    return work_day_start(ts) + timedelta(days=1)


def is_past_work_day_end(started_at: datetime, now: datetime) -> bool:
    """True when a shift started at ``started_at`` has outlived its work day at ``now``.

    Equivalent to ``started_at < work_day_start(now)``, which is the form a SQL prefilter
    can use.
    """
    return work_day_end(started_at) <= _as_utc(now)
