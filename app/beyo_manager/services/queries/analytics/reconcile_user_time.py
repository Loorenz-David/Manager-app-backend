"""Recompute-and-SET a worker's day time metrics from records (concurrency-averaged).

The single write path for time seconds/counts/cost across the analytics tables:
- `user_daily_work_stats` + `user_section_daily_work_stats`: **SET** from the sweep
  (idempotent — records are the source of truth).
- `working_section_daily_work_stats` + `user_lifetime_stats`: kept consistent by
  **applying the delta** (they are Σ over users / Σ over days of the per-user rows).

Issue counts, completed counts, and the count-of-transitions cost inputs other than
time are untouched here (they stay in the worker's completion path).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.queries.analytics.averaged_time import compute_record_contributions

# Records worked across midnight are rare; ±1 day covers concurrency overlaps for a day.
_WINDOW_BUFFER = timedelta(days=1)


@dataclass
class _TimeTotals:
    working_seconds: int = 0
    pause_seconds: int = 0
    ended_shift_seconds: int = 0
    working_count: int = 0
    pause_count: int = 0
    ended_shift_count: int = 0
    inaccurate_working_seconds: int = 0
    inaccurate_pause_seconds: int = 0
    inaccurate_ended_shift_seconds: int = 0
    inaccurate_step_count: int = 0
    cost_minor: int = 0

    def as_delta(self, previous: "_TimeTotals") -> "_TimeTotals":
        return _TimeTotals(
            working_seconds=self.working_seconds - previous.working_seconds,
            pause_seconds=self.pause_seconds - previous.pause_seconds,
            ended_shift_seconds=self.ended_shift_seconds - previous.ended_shift_seconds,
            working_count=self.working_count - previous.working_count,
            pause_count=self.pause_count - previous.pause_count,
            ended_shift_count=self.ended_shift_count - previous.ended_shift_count,
            inaccurate_working_seconds=(
                self.inaccurate_working_seconds - previous.inaccurate_working_seconds
            ),
            inaccurate_pause_seconds=self.inaccurate_pause_seconds - previous.inaccurate_pause_seconds,
            inaccurate_ended_shift_seconds=(
                self.inaccurate_ended_shift_seconds - previous.inaccurate_ended_shift_seconds
            ),
            inaccurate_step_count=self.inaccurate_step_count - previous.inaccurate_step_count,
            cost_minor=self.cost_minor - previous.cost_minor,
        )


@dataclass
class DayReconcileResult:
    """Deltas the caller applies to the Σ tables (lifetime, section-wide)."""

    user_delta: _TimeTotals
    section_deltas: dict[str, _TimeTotals] = field(default_factory=dict)  # working_section_id -> delta


def _cost_minor(rate_per_hour: Decimal | None, working_seconds: int, pause_seconds: int) -> int:
    # Cost applies to working + pause time (ended-shift is not costed), like the old path.
    if rate_per_hour is None:
        return 0
    costed = Decimal(working_seconds + pause_seconds)
    return int(((costed / Decimal(3600)) * rate_per_hour * Decimal(100)).to_integral_value())


def _snapshot(row) -> _TimeTotals:
    return _TimeTotals(
        working_seconds=row.total_working_seconds,
        pause_seconds=row.total_pause_seconds,
        ended_shift_seconds=row.total_ended_shift_seconds,
        working_count=row.total_working_count,
        pause_count=row.total_pause_count,
        ended_shift_count=row.total_ended_shift_count,
        inaccurate_working_seconds=row.inaccurate_working_seconds,
        inaccurate_pause_seconds=row.inaccurate_pause_seconds,
        inaccurate_ended_shift_seconds=row.inaccurate_ended_shift_seconds,
        inaccurate_step_count=row.inaccurate_step_count,
        cost_minor=row.total_cost_minor or 0,
    )


def _apply_set(row, totals: _TimeTotals) -> None:
    row.total_working_seconds = totals.working_seconds
    row.total_pause_seconds = totals.pause_seconds
    row.total_ended_shift_seconds = totals.ended_shift_seconds
    row.total_working_count = totals.working_count
    row.total_pause_count = totals.pause_count
    row.total_ended_shift_count = totals.ended_shift_count
    row.inaccurate_working_seconds = totals.inaccurate_working_seconds
    row.inaccurate_pause_seconds = totals.inaccurate_pause_seconds
    row.inaccurate_ended_shift_seconds = totals.inaccurate_ended_shift_seconds
    row.inaccurate_step_count = totals.inaccurate_step_count
    row.total_cost_minor = totals.cost_minor


def _apply_delta(row, delta: _TimeTotals) -> None:
    row.total_working_seconds += delta.working_seconds
    row.total_pause_seconds += delta.pause_seconds
    row.total_ended_shift_seconds += delta.ended_shift_seconds
    row.total_working_count += delta.working_count
    row.total_pause_count += delta.pause_count
    row.total_ended_shift_count += delta.ended_shift_count
    row.inaccurate_working_seconds += delta.inaccurate_working_seconds
    row.inaccurate_pause_seconds += delta.inaccurate_pause_seconds
    row.inaccurate_ended_shift_seconds += delta.inaccurate_ended_shift_seconds
    row.inaccurate_step_count += delta.inaccurate_step_count
    row.total_cost_minor = (row.total_cost_minor or 0) + delta.cost_minor


_STATE_TO_FIELDS = {
    "working": ("working_seconds", "working_count"),
    "paused": ("pause_seconds", "pause_count"),
    "ended_shift": ("ended_shift_seconds", "ended_shift_count"),
}

_STATE_TO_INACCURATE_FIELDS = {
    "working": "inaccurate_working_seconds",
    "paused": "inaccurate_pause_seconds",
    "ended_shift": "inaccurate_ended_shift_seconds",
}


def _accumulate(target: _TimeTotals, state: str, seconds: int) -> None:
    fields = _STATE_TO_FIELDS.get(state)
    if fields is None:
        return
    sec_field, cnt_field = fields
    setattr(target, sec_field, getattr(target, sec_field) + seconds)
    setattr(target, cnt_field, getattr(target, cnt_field) + 1)


def _accumulate_inaccurate(target: _TimeTotals, state: str, seconds: int) -> None:
    field = _STATE_TO_INACCURATE_FIELDS.get(state)
    if field is not None:
        setattr(target, field, getattr(target, field) + seconds)


async def _rate(session: AsyncSession, user_id: str, workspace_id: str) -> Decimal | None:
    profile = (
        await session.execute(
            select(UserWorkProfile).where(
                UserWorkProfile.user_id == user_id,
                UserWorkProfile.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    return profile.salary_per_hour_before_tax if profile else None


async def _get_or_create_user_daily(session, ws, user_id, display, work_date) -> UserDailyWorkStats:
    row = (
        await session.execute(
            select(UserDailyWorkStats).where(
                UserDailyWorkStats.workspace_id == ws,
                UserDailyWorkStats.user_id == user_id,
                UserDailyWorkStats.work_date == work_date,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserDailyWorkStats(
            workspace_id=ws, user_id=user_id, user_display_name_snapshot=display, work_date=work_date
        )
        session.add(row)
        await session.flush()
    return row


async def _get_or_create_user_section_daily(session, ws, user_id, section_id, work_date, display, section_name):
    row = (
        await session.execute(
            select(UserSectionDailyWorkStats).where(
                UserSectionDailyWorkStats.workspace_id == ws,
                UserSectionDailyWorkStats.user_id == user_id,
                UserSectionDailyWorkStats.working_section_id == section_id,
                UserSectionDailyWorkStats.work_date == work_date,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserSectionDailyWorkStats(
            workspace_id=ws, user_id=user_id, working_section_id=section_id,
            section_name_snapshot=section_name or "", user_display_name_snapshot=display, work_date=work_date,
        )
        session.add(row)
        await session.flush()
    return row


async def _get_or_create_section_daily(session, ws, section_id, work_date, section_name) -> WorkingSectionDailyWorkStats:
    row = (
        await session.execute(
            select(WorkingSectionDailyWorkStats).where(
                WorkingSectionDailyWorkStats.workspace_id == ws,
                WorkingSectionDailyWorkStats.working_section_id == section_id,
                WorkingSectionDailyWorkStats.work_date == work_date,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = WorkingSectionDailyWorkStats(
            workspace_id=ws, working_section_id=section_id,
            section_name_snapshot=section_name or "", work_date=work_date,
        )
        session.add(row)
        await session.flush()
    return row


async def _get_or_create_user_lifetime(session, ws, user_id, display) -> UserLifetimeStats:
    row = (
        await session.execute(
            select(UserLifetimeStats).where(
                UserLifetimeStats.workspace_id == ws,
                UserLifetimeStats.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserLifetimeStats(workspace_id=ws, user_id=user_id, user_display_name_snapshot=display)
        session.add(row)
        await session.flush()
    return row


async def _section_name(session, ws, section_id) -> str:
    section = (
        await session.execute(
            select(WorkingSection.name).where(
                WorkingSection.workspace_id == ws, WorkingSection.client_id == section_id
            )
        )
    ).scalar_one_or_none()
    return section or ""


async def reconcile_user_day_time(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    display_name: str,
    work_date: date,
    now: datetime,
) -> DayReconcileResult:
    """SET the user's daily + user-section-daily **time** fields for ``work_date`` from
    the concurrency-averaged sweep; return the deltas to apply to the Σ tables."""
    day_start = datetime.combine(work_date, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    contributions = await compute_record_contributions(
        session, workspace_id, user_id, day_start - _WINDOW_BUFFER, day_end + _WINDOW_BUFFER, now
    )
    # Settled records entered on the target day (deleted steps included — daily reflects work done).
    settled = [c for c in contributions if not c.is_open and c.entered_at.date() == work_date]

    rate = await _rate(session, user_id, workspace_id)

    day_totals = _TimeTotals()
    per_section: dict[str, _TimeTotals] = defaultdict(_TimeTotals)
    flagged_steps: set[str] = set()
    flagged_steps_by_section: dict[str, set[str]] = defaultdict(set)
    for c in settled:
        if c.marked_wrong:
            _accumulate_inaccurate(day_totals, c.state, int(round(c.wasted_seconds)))
            _accumulate_inaccurate(
                per_section[c.working_section_id], c.state, int(round(c.wasted_seconds))
            )
            flagged_steps.add(c.step_id)
            flagged_steps_by_section[c.working_section_id].add(c.step_id)
        else:
            seconds = int(round(c.seconds))
            _accumulate(day_totals, c.state, seconds)
            _accumulate(per_section[c.working_section_id], c.state, seconds)

    day_totals.inaccurate_step_count = len(flagged_steps)
    for section_id, step_ids in flagged_steps_by_section.items():
        per_section[section_id].inaccurate_step_count = len(step_ids)

    day_totals.cost_minor = _cost_minor(rate, day_totals.working_seconds, day_totals.pause_seconds)
    for section_totals in per_section.values():
        section_totals.cost_minor = _cost_minor(rate, section_totals.working_seconds, section_totals.pause_seconds)

    # --- user_daily: SET, capture delta for lifetime ---
    user_daily = await _get_or_create_user_daily(session, workspace_id, user_id, display_name, work_date)
    user_prev = _snapshot(user_daily)
    _apply_set(user_daily, day_totals)
    user_daily.updated_at = now
    user_delta = day_totals.as_delta(user_prev)

    # --- user_section_daily: SET each section that has time; zero sections that dropped to nil ---
    section_deltas: dict[str, _TimeTotals] = {}
    existing_sections = (
        await session.execute(
            select(UserSectionDailyWorkStats).where(
                UserSectionDailyWorkStats.workspace_id == workspace_id,
                UserSectionDailyWorkStats.user_id == user_id,
                UserSectionDailyWorkStats.work_date == work_date,
            )
        )
    ).scalars().all()
    existing_by_section = {row.working_section_id: row for row in existing_sections}
    all_section_ids = set(per_section) | set(existing_by_section)

    for section_id in all_section_ids:
        new_totals = per_section.get(section_id, _TimeTotals())
        row = existing_by_section.get(section_id)
        if row is None:
            name = await _section_name(session, workspace_id, section_id)
            row = await _get_or_create_user_section_daily(
                session, workspace_id, user_id, section_id, work_date, display_name, name
            )
        prev = _snapshot(row)
        _apply_set(row, new_totals)
        row.updated_at = now
        section_deltas[section_id] = new_totals.as_delta(prev)

    return DayReconcileResult(user_delta=user_delta, section_deltas=section_deltas)


async def apply_reconcile_deltas(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    display_name: str,
    work_date: date,
    now: datetime,
    result: DayReconcileResult,
) -> None:
    """Apply the reconcile deltas to the Σ tables (lifetime, section-wide)."""
    lifetime = await _get_or_create_user_lifetime(session, workspace_id, user_id, display_name)
    _apply_delta(lifetime, result.user_delta)
    lifetime.updated_at = now

    for section_id, delta in result.section_deltas.items():
        name = await _section_name(session, workspace_id, section_id)
        section_daily = await _get_or_create_section_daily(session, workspace_id, section_id, work_date, name)
        _apply_delta(section_daily, delta)
        section_daily.updated_at = now
