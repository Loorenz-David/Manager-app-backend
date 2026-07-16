"""Backfill completed-step counters from StepStateRecord history.

The command is dry-run by default. Use ``--execute`` for the idempotent,
absolute-value write. ``--limit`` limits the source rows inspected in dry-run
mode for staged estimates; execute a complete run for a consistent write.

Attribution matches the live analytics worker: completions are credited to
``credited_user_id`` (falling back to ``created_by_id`` for records written
before that column existed).

Operational note: run this with the analytics task queue drained/paused. It
writes absolute values, so a completion the live worker processes *after* this
script reads the source but *before* it commits would be overwritten (lost until
the next run). A quiet window avoids that race.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Annotated

import typer
from sqlalchemy import and_, select, update

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User

app = typer.Typer(add_completion=False, no_args_is_help=True)

_ZEROABLE_MODELS = (
    UserDailyWorkStats,
    UserLifetimeStats,
    UserSectionDailyWorkStats,
    WorkingSectionDailyWorkStats,
    TaskStep,
)


class _Counts:
    """Aggregated completion counts, keyed per scope."""

    def __init__(self) -> None:
        self.user_daily: defaultdict[tuple, int] = defaultdict(int)
        self.user_lifetime: defaultdict[tuple, int] = defaultdict(int)
        self.user_section_daily: defaultdict[tuple, int] = defaultdict(int)
        self.section_daily: defaultdict[tuple, int] = defaultdict(int)
        self.task_steps: defaultdict[str, int] = defaultdict(int)
        self.credited_user_ids: set[str] = set()
        self.section_names: dict[tuple, str] = {}

    def summary(self) -> str:
        return (
            "completed_count_backfill | "
            f"source_user_daily={len(self.user_daily)} "
            f"source_user_lifetime={len(self.user_lifetime)} "
            f"source_user_section_daily={len(self.user_section_daily)} "
            f"source_section_daily={len(self.section_daily)} "
            f"source_task_steps={len(self.task_steps)}"
        )


async def _collect_counts(session, limit: int | None) -> _Counts:
    """Stream COMPLETED records and aggregate (bounded memory: only the aggregate)."""
    statement = (
        select(
            StepStateRecord.workspace_id,
            StepStateRecord.created_by_id,
            StepStateRecord.credited_user_id,
            StepStateRecord.entered_at,
            StepStateRecord.step_id,
            TaskStep.working_section_id,
            TaskStep.working_section_name_snapshot,
        )
        .outerjoin(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == StepStateRecord.workspace_id,
            ),
        )
        .where(
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.is_deleted.is_(False),
            StepStateRecord.created_by_id.is_not(None),
        )
        .order_by(StepStateRecord.entered_at.asc(), StepStateRecord.client_id.asc())
    )
    if limit is not None:
        statement = statement.limit(limit)

    counts = _Counts()
    result = await session.stream(statement)
    async for row in result:
        # Match the live worker: credit the credited user, fall back to performer.
        credited = row.credited_user_id or row.created_by_id
        # entered_at is asyncpg UTC-aware; .date() is the UTC day (same bucketing
        # the worker uses via exited_at). No SQL ``::date`` -> no session-TZ hazard.
        work_date: date = row.entered_at.date()

        counts.credited_user_ids.add(credited)
        counts.task_steps[row.step_id] += 1
        counts.user_daily[(row.workspace_id, credited, work_date)] += 1
        counts.user_lifetime[(row.workspace_id, credited)] += 1
        if row.working_section_id:
            counts.user_section_daily[
                (row.workspace_id, credited, row.working_section_id, work_date)
            ] += 1
            counts.section_daily[(row.workspace_id, row.working_section_id, work_date)] += 1
            counts.section_names.setdefault(
                (row.workspace_id, row.working_section_id),
                row.working_section_name_snapshot or "",
            )
    return counts


async def _get_row(session, model, **filters):
    result = await session.execute(
        select(model).where(*[getattr(model, k) == v for k, v in filters.items()])
    )
    return result.scalar_one_or_none()


async def _write_counts(session, counts: _Counts) -> None:
    now = datetime.now(timezone.utc)

    # Reset all counters set-based (no full-table load into memory).
    for model in _ZEROABLE_MODELS:
        await session.execute(
            update(model)
            .values(total_completed_count=0)
            .execution_options(synchronize_session=False)
        )

    user_names: dict[str, str] = {}
    if counts.credited_user_ids:
        rows = await session.execute(
            select(User.client_id, User.username).where(
                User.client_id.in_(counts.credited_user_ids)
            )
        )
        user_names = {r.client_id: r.username for r in rows.all()}

    # Only rows that actually have completions are touched (bounded by #groups).
    for (workspace_id, user_id, work_date), count in counts.user_daily.items():
        row = await _get_row(
            session, UserDailyWorkStats,
            workspace_id=workspace_id, user_id=user_id, work_date=work_date,
        )
        if row is None:
            row = UserDailyWorkStats(
                workspace_id=workspace_id,
                user_id=user_id,
                user_display_name_snapshot=user_names.get(user_id, ""),
                work_date=work_date,
            )
            session.add(row)
        row.total_completed_count = count
        row.updated_at = now

    for (workspace_id, user_id), count in counts.user_lifetime.items():
        row = await _get_row(
            session, UserLifetimeStats, workspace_id=workspace_id, user_id=user_id
        )
        if row is None:
            row = UserLifetimeStats(
                workspace_id=workspace_id,
                user_id=user_id,
                user_display_name_snapshot=user_names.get(user_id, ""),
            )
            session.add(row)
        row.total_completed_count = count
        row.updated_at = now

    for (workspace_id, user_id, section_id, work_date), count in counts.user_section_daily.items():
        row = await _get_row(
            session, UserSectionDailyWorkStats,
            workspace_id=workspace_id, user_id=user_id,
            working_section_id=section_id, work_date=work_date,
        )
        if row is None:
            row = UserSectionDailyWorkStats(
                workspace_id=workspace_id,
                user_id=user_id,
                working_section_id=section_id,
                section_name_snapshot=counts.section_names.get((workspace_id, section_id), ""),
                user_display_name_snapshot=user_names.get(user_id, ""),
                work_date=work_date,
            )
            session.add(row)
        row.total_completed_count = count
        row.updated_at = now

    for (workspace_id, section_id, work_date), count in counts.section_daily.items():
        row = await _get_row(
            session, WorkingSectionDailyWorkStats,
            workspace_id=workspace_id, working_section_id=section_id, work_date=work_date,
        )
        if row is None:
            row = WorkingSectionDailyWorkStats(
                workspace_id=workspace_id,
                working_section_id=section_id,
                section_name_snapshot=counts.section_names.get((workspace_id, section_id), ""),
                work_date=work_date,
            )
            session.add(row)
        row.total_completed_count = count
        row.updated_at = now

    for step_id, count in counts.task_steps.items():
        await session.execute(
            update(TaskStep)
            .where(TaskStep.client_id == step_id)
            .values(total_completed_count=count)
            .execution_options(synchronize_session=False)
        )


async def _run(*, dry_run: bool, limit: int | None) -> None:
    if limit is not None and not dry_run:
        raise ValueError("--limit is supported only with --dry-run; execute a complete backfill.")

    await init_db()
    try:
        async for session in get_db_session():
            counts = await _collect_counts(session, limit)
            typer.echo(counts.summary())
            if limit is not None:
                typer.echo(f"[dry-run] source row limit={limit}; no write is permitted")
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return

            await _write_counts(session, counts)
            await session.commit()
            typer.echo("completed_count_backfill | absolute values written and committed")
    finally:
        await close_db()


@app.command("backfill-completed-count")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = None,
) -> None:
    """Set completed-step counters from historical COMPLETED records."""
    try:
        asyncio.run(_run(dry_run=dry_run, limit=limit))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


if __name__ == "__main__":
    app()
