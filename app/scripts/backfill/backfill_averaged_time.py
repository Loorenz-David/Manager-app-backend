"""Rebuild all time aggregates concurrency-averaged from step_state_records.

Corrects the historical batch over-count: recomputes user-daily, user-section-daily,
working-section-daily, user-lifetime time fields (+ TaskStep.total_*) from the sweep.
Idempotent (absolute SET) — safe to re-run. Run with the analytics queue drained.

Dry-run by default; ``--execute`` writes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated

import typer
from sqlalchemy import func, select, update

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.tasks.analytics.process_step_transition import _recompute_step_time_totals
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    _get_or_create_section_daily,
    _get_or_create_user_lifetime,
    _section_name,
    reconcile_user_day_time,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)

_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT)
_TIME_FIELDS = (
    "total_working_seconds", "total_pause_seconds", "total_ended_shift_seconds",
    "total_working_count", "total_pause_count", "total_ended_shift_count", "total_cost_minor",
)
_INACCURATE_FIELDS = (
    "inaccurate_working_seconds",
    "inaccurate_pause_seconds",
    "inaccurate_ended_shift_seconds",
    "inaccurate_step_count",
)


async def _zero_time_fields(session, model) -> None:
    values = {
        f: 0
        for f in (*_TIME_FIELDS, *_INACCURATE_FIELDS)
        if hasattr(model, f)
    }
    await session.execute(update(model).values(**values).execution_options(synchronize_session=False))


async def _run(*, dry_run: bool) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            now = datetime.now(timezone.utc)

            # Sources: distinct (workspace, credited-user) and distinct steps, from time records.
            credited = func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)
            user_rows = (
                await session.execute(
                    select(StepStateRecord.workspace_id, credited.label("uid"))
                    .where(StepStateRecord.is_deleted.is_(False), StepStateRecord.state.in_(_TIME_STATES))
                    .distinct()
                )
            ).all()
            step_rows = (
                await session.execute(
                    select(StepStateRecord.workspace_id, StepStateRecord.step_id)
                    .where(StepStateRecord.is_deleted.is_(False), StepStateRecord.state.in_(_TIME_STATES))
                    .distinct()
                )
            ).all()

            typer.echo(
                f"averaged_time_backfill | users={len(user_rows)} steps={len(step_rows)}"
            )
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return

            # Reset every time aggregate (rows with no records collapse to zero).
            for model in (
                UserDailyWorkStats,
                UserSectionDailyWorkStats,
                WorkingSectionDailyWorkStats,
                UserLifetimeStats,
                TaskStep,
            ):
                await _zero_time_fields(session, model)

            # Per (user, day): SET user_daily + user_section_daily from the sweep.
            for row in user_rows:
                if row.uid is None:
                    continue
                days = (
                    await session.execute(
                        select(StepStateRecord.entered_at).where(
                            StepStateRecord.workspace_id == row.workspace_id,
                            credited == row.uid,
                            StepStateRecord.is_deleted.is_(False),
                            StepStateRecord.state.in_(_TIME_STATES),
                        )
                    )
                ).scalars().all()
                for work_date in {d.date() for d in days}:
                    await reconcile_user_day_time(session, row.workspace_id, row.uid, "", work_date, now)

            # Derive the Σ tables by summation (SET), matching the live delta maintenance.
            await _rebuild_section_wide(session, now)
            await _rebuild_lifetime(session, now)

            # TaskStep.total_* per step (averaged).
            for row in step_rows:
                await _recompute_step_time_totals(session, row.workspace_id, row.step_id, now)

            await session.commit()
            typer.echo("averaged_time_backfill | rebuilt and committed")
    finally:
        await close_db()


async def _rebuild_section_wide(session, now: datetime) -> None:
    """working_section_daily = Σ over users of user_section_daily (per section, day)."""
    grouped = (
        await session.execute(
            select(
                UserSectionDailyWorkStats.workspace_id,
                UserSectionDailyWorkStats.working_section_id,
                UserSectionDailyWorkStats.work_date,
                func.sum(UserSectionDailyWorkStats.total_working_seconds),
                func.sum(UserSectionDailyWorkStats.total_pause_seconds),
                func.sum(UserSectionDailyWorkStats.total_ended_shift_seconds),
                func.sum(UserSectionDailyWorkStats.total_working_count),
                func.sum(UserSectionDailyWorkStats.total_pause_count),
                func.sum(UserSectionDailyWorkStats.total_ended_shift_count),
                func.sum(UserSectionDailyWorkStats.total_cost_minor),
                func.sum(UserSectionDailyWorkStats.inaccurate_working_seconds),
                func.sum(UserSectionDailyWorkStats.inaccurate_pause_seconds),
                func.sum(UserSectionDailyWorkStats.inaccurate_ended_shift_seconds),
                func.sum(UserSectionDailyWorkStats.inaccurate_step_count),
            ).group_by(
                UserSectionDailyWorkStats.workspace_id,
                UserSectionDailyWorkStats.working_section_id,
                UserSectionDailyWorkStats.work_date,
            )
        )
    ).all()
    for ws, section_id, day, work, pause, ended, wc, pc, ec, cost, iwork, ipause, iended, isteps in grouped:
        name = await _section_name(session, ws, section_id)
        row = await _get_or_create_section_daily(session, ws, section_id, day, name)
        row.total_working_seconds = int(work or 0)
        row.total_pause_seconds = int(pause or 0)
        row.total_ended_shift_seconds = int(ended or 0)
        row.total_working_count = int(wc or 0)
        row.total_pause_count = int(pc or 0)
        row.total_ended_shift_count = int(ec or 0)
        row.total_cost_minor = int(cost or 0)
        row.inaccurate_working_seconds = int(iwork or 0)
        row.inaccurate_pause_seconds = int(ipause or 0)
        row.inaccurate_ended_shift_seconds = int(iended or 0)
        row.inaccurate_step_count = int(isteps or 0)
        row.updated_at = now


async def _rebuild_lifetime(session, now: datetime) -> None:
    """user_lifetime = Σ over days of user_daily (per user)."""
    grouped = (
        await session.execute(
            select(
                UserDailyWorkStats.workspace_id,
                UserDailyWorkStats.user_id,
                func.sum(UserDailyWorkStats.total_working_seconds),
                func.sum(UserDailyWorkStats.total_pause_seconds),
                func.sum(UserDailyWorkStats.total_ended_shift_seconds),
                func.sum(UserDailyWorkStats.total_working_count),
                func.sum(UserDailyWorkStats.total_pause_count),
                func.sum(UserDailyWorkStats.total_ended_shift_count),
                func.sum(UserDailyWorkStats.total_cost_minor),
                func.sum(UserDailyWorkStats.inaccurate_working_seconds),
                func.sum(UserDailyWorkStats.inaccurate_pause_seconds),
                func.sum(UserDailyWorkStats.inaccurate_ended_shift_seconds),
                func.sum(UserDailyWorkStats.inaccurate_step_count),
            ).group_by(UserDailyWorkStats.workspace_id, UserDailyWorkStats.user_id)
        )
    ).all()
    for ws, user_id, work, pause, ended, wc, pc, ec, cost, iwork, ipause, iended, isteps in grouped:
        row = await _get_or_create_user_lifetime(session, ws, user_id, "")
        row.total_working_seconds = int(work or 0)
        row.total_pause_seconds = int(pause or 0)
        row.total_ended_shift_seconds = int(ended or 0)
        row.total_working_count = int(wc or 0)
        row.total_pause_count = int(pc or 0)
        row.total_ended_shift_count = int(ec or 0)
        row.total_cost_minor = int(cost or 0)
        row.inaccurate_working_seconds = int(iwork or 0)
        row.inaccurate_pause_seconds = int(ipause or 0)
        row.inaccurate_ended_shift_seconds = int(iended or 0)
        row.inaccurate_step_count = int(isteps or 0)
        row.updated_at = now


@app.command("backfill-averaged-time")
def main(dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True) -> None:
    """Rebuild all time aggregates concurrency-averaged from records."""
    asyncio.run(_run(dry_run=dry_run))


if __name__ == "__main__":
    app()
