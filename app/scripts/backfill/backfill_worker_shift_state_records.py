"""Reconstruct historical worker shift-state records from the linear step sweep.

The command is dry-run by default. Use ``--execute`` during a quiet rollout window.
Each selected UTC worker-day is deleted and deterministically rewritten, so reruns are
idempotent. Only historical days (strictly before the current UTC day) are accepted.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

import typer
from sqlalchemy import and_, delete, func, select

from beyo_manager.domain.analytics.linear_timeline import (
    LinearInterval,
    compute_linear_segments,
)
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord


app = typer.Typer(add_completion=False, no_args_is_help=True)

_TIME_STATES = (
    TaskStepStateEnum.WORKING,
    TaskStepStateEnum.PAUSED,
    TaskStepStateEnum.ENDED_SHIFT,
)
_SEGMENT_TO_SHIFT_STATE = {
    "working": UserShiftStateEnum.WORKING,
    "paused": UserShiftStateEnum.IN_PAUSE,
    "idle": UserShiftStateEnum.IDLE,
}


@dataclass(frozen=True)
class BackfillDayResult:
    source_segments: int
    records_written: int


async def _load_day_intervals(
    session,
    workspace_id: str,
    user_id: str,
    day_start: datetime,
    day_end: datetime,
) -> list[LinearInterval]:
    credited = func.coalesce(
        StepStateRecord.credited_user_id,
        StepStateRecord.created_by_id,
    )
    rows = await session.execute(
        select(
            StepStateRecord.client_id,
            StepStateRecord.state,
            StepStateRecord.reason,
            StepStateRecord.entered_at,
            StepStateRecord.exited_at,
            StepStateRecord.step_id,
        )
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.workspace_id == workspace_id,
            StepStateRecord.is_deleted.is_(False),
            credited == user_id,
            StepStateRecord.state.in_(_TIME_STATES),
            StepStateRecord.entered_at < day_end,
            (
                StepStateRecord.exited_at.is_(None)
                | (StepStateRecord.exited_at > day_start)
            ),
        )
    )
    return [
        LinearInterval(
            record_id=row.client_id,
            state=row.state.value,
            reason=row.reason.value if row.reason is not None else None,
            entered_at=row.entered_at,
            exited_at=row.exited_at,
            step_id=row.step_id,
        )
        for row in rows.all()
    ]


def _records_from_segments(
    *,
    workspace_id: str,
    user_id: str,
    segments,
) -> list[UserShiftStateRecord]:
    if not segments:
        return []

    records = [
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            state=UserShiftStateEnum.STARTED_SHIFT,
            entered_at=segments[0].start,
            exited_at=segments[0].start,
            changed_by_id=None,
            reason=None,
            manually_recorded=False,
        )
    ]
    ended_at = segments[-1].end
    for segment in segments:
        if segment.state == "ended_shift":
            ended_at = segment.start
            break
        state = _SEGMENT_TO_SHIFT_STATE[segment.state]
        records.append(
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=state,
                entered_at=segment.start,
                exited_at=segment.end,
                changed_by_id=None,
                reason=(segment.reason if state is UserShiftStateEnum.IN_PAUSE else None),
                manually_recorded=False,
            )
        )
    records.append(
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            state=UserShiftStateEnum.ENDED_SHIFT,
            entered_at=ended_at,
            exited_at=ended_at,
            changed_by_id=None,
            reason=None,
            manually_recorded=False,
        )
    )
    return records


async def backfill_worker_shift_day(
    session,
    *,
    workspace_id: str,
    user_id: str,
    work_date: date,
    now: datetime,
    execute: bool,
) -> BackfillDayResult:
    day_start = datetime.combine(work_date, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    intervals = await _load_day_intervals(
        session,
        workspace_id,
        user_id,
        day_start,
        day_end,
    )
    segments = compute_linear_segments(
        intervals,
        day_start,
        day_end,
        max(now, day_end),
    )
    records = _records_from_segments(
        workspace_id=workspace_id,
        user_id=user_id,
        segments=segments,
    )
    if execute:
        await session.execute(
            delete(UserShiftStateRecord).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.entered_at >= day_start,
                UserShiftStateRecord.entered_at < day_end,
            )
        )
        session.add_all(records)
        await session.flush()
    return BackfillDayResult(
        source_segments=len(segments),
        records_written=len(records),
    )


async def _collect_targets(
    session,
    *,
    date_from: date | None,
    date_to: date,
    workspace_id: str | None,
    user_id: str | None,
    now: datetime,
) -> list[tuple[str, str, date]]:
    credited = func.coalesce(
        StepStateRecord.credited_user_id,
        StepStateRecord.created_by_id,
    )
    statement = (
        select(
            StepStateRecord.workspace_id,
            credited.label("user_id"),
            StepStateRecord.entered_at,
            StepStateRecord.exited_at,
        )
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == StepStateRecord.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.is_deleted.is_(False),
            StepStateRecord.state.in_(_TIME_STATES),
            credited.is_not(None),
        )
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
    )
    if workspace_id is not None:
        statement = statement.where(StepStateRecord.workspace_id == workspace_id)
    if user_id is not None:
        statement = statement.where(credited == user_id)

    targets: set[tuple[str, str, date]] = set()
    result = await session.stream(statement)
    async for row in result:
        effective_end = min(row.exited_at or now, datetime.combine(
            date_to + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        ))
        first_day = row.entered_at.date()
        last_day = (
            effective_end - timedelta(microseconds=1)
        ).date() if effective_end > row.entered_at else first_day
        first_day = max(first_day, date_from) if date_from is not None else first_day
        last_day = min(last_day, date_to)
        cursor = first_day
        while cursor <= last_day:
            targets.add((row.workspace_id, row.user_id, cursor))
            cursor += timedelta(days=1)
    return sorted(targets)


async def _run(
    *,
    dry_run: bool,
    date_from: date | None,
    date_to: date | None,
    workspace_id: str | None,
    user_id: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    latest_historical_day = now.date() - timedelta(days=1)
    effective_date_to = date_to or latest_historical_day
    if effective_date_to > latest_historical_day:
        raise ValueError("date_to must be before the current UTC day.")
    if date_from is not None and effective_date_to < date_from:
        raise ValueError("date_to must be on or after date_from.")

    await init_db()
    try:
        async for session in get_db_session():
            targets = await _collect_targets(
                session,
                date_from=date_from,
                date_to=effective_date_to,
                workspace_id=workspace_id,
                user_id=user_id,
                now=now,
            )
            source_segments = 0
            records_written = 0
            for target_workspace_id, target_user_id, work_date in targets:
                result = await backfill_worker_shift_day(
                    session,
                    workspace_id=target_workspace_id,
                    user_id=target_user_id,
                    work_date=work_date,
                    now=now,
                    execute=not dry_run,
                )
                source_segments += result.source_segments
                records_written += result.records_written

            typer.echo(
                "worker_shift_state_backfill | "
                f"worker_days={len(targets)} source_segments={source_segments} "
                f"records={'would_write' if dry_run else 'written'}:{records_written}"
            )
            if dry_run:
                typer.echo("[dry-run] no changes committed")
                return
            await session.commit()
            typer.echo("worker_shift_state_backfill | committed")
    finally:
        await close_db()


@app.command("backfill-worker-shift-state-records")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    date_from: Annotated[str | None, typer.Option("--date-from")] = None,
    date_to: Annotated[str | None, typer.Option("--date-to")] = None,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    user_id: Annotated[str | None, typer.Option("--user-id")] = None,
) -> None:
    """Rebuild historical recorded shifts from step-state history."""
    try:
        parsed_date_from = date.fromisoformat(date_from) if date_from else None
        parsed_date_to = date.fromisoformat(date_to) if date_to else None
        asyncio.run(
            _run(
                dry_run=dry_run,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
                workspace_id=workspace_id,
                user_id=user_id,
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


if __name__ == "__main__":
    app()
