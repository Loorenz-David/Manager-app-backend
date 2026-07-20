"""One-time heal to make today's in-progress shifts correct.

Two problems it fixes for shifts that are still open today:

  1. **Missing shift** — a worker who was already mid-shift when the shift-recording
     feature deployed had their shift-opening transition consumed by the *pre-feature*
     analytics worker, so no `started_shift` was ever written.
  2. **Lossy middle** — a worker who *was* auto-clocked-in live has a `started_shift`,
     but the live reconcile only records the *current* state per transition, so the middle
     (working / idle / pause segments) can be incomplete or wrong if it lagged.

Both are healed the same way, purely from the step records already in the DB (today's
shift is still open, so there is no external clock-out bound to fetch):

  * shift_start = the worker's first credited step of the current shift (clamped to any
    prior `ended_shift`, mirroring the live auto-clock-in clamp),
  * exactly one `started_shift` marker at shift_start,
  * the durationful middle rebuilt by the same tested sweep used at clock-out
    (`reconstruct_shift_middle`) over [shift_start, now] — this REPLACES whatever the live
    reconcile left, so the timeline is accurate,
  * the **current** (latest) segment left OPEN and NO `ended_shift` marker — the shift is
    still running, so the live worker keeps extending it from there.

A worker who has already clocked out today (their shift was reconstructed at clock-out) or
has no current-shift activity is skipped. Deterministic and idempotent — safe to re-run.

Dry-run by default; ``--execute`` writes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated

import typer
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._reconstruct_shift_middle import (
    reconstruct_shift_middle,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)

_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED)
_DURATIONFUL = (
    UserShiftStateEnum.WORKING,
    UserShiftStateEnum.IN_PAUSE,
    UserShiftStateEnum.IDLE,
)


def _credited():
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)


async def heal_current_shift(
    session,
    workspace_id: str,
    user_id: str,
    day_start: datetime,
    now: datetime,
    *,
    execute: bool,
) -> str:
    """Rebuild the worker's current (open) shift from step records. Returns an outcome tag."""
    # The current shift begins no earlier than the last clock-out (any date). For today's
    # workers that marker is from a previous day, so the scope is simply "today".
    latest_ended = await session.scalar(
        select(func.max(UserShiftStateRecord.entered_at)).where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
            UserShiftStateRecord.state == UserShiftStateEnum.ENDED_SHIFT,
        )
    )
    scope_start = day_start
    if latest_ended is not None and latest_ended > scope_start:
        scope_start = latest_ended

    first_step = await session.scalar(
        select(func.min(StepStateRecord.entered_at))
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
            _credited() == user_id,
            StepStateRecord.state.in_(_TIME_STATES),
            StepStateRecord.entered_at >= scope_start,
        )
    )
    if first_step is None:
        # No time-bearing work since the last clock-out — nothing in progress to heal.
        return "skipped_no_current_shift_activity"
    shift_start = first_step

    if not execute:
        return f"would_heal shift_start={shift_start.isoformat()}"

    # Normalize to exactly one started_shift marker at shift_start (create, or fix the one
    # the live auto-clock-in wrote — its clamp may have landed on a later task).
    marker = (
        await session.execute(
            select(UserShiftStateRecord)
            .where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT,
                UserShiftStateRecord.entered_at >= scope_start,
            )
            .order_by(UserShiftStateRecord.entered_at.desc())
        )
    ).scalars().all()
    if not marker:
        session.add(
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=shift_start,
                exited_at=shift_start,
                changed_by_id=None,
                reason=None,
                manually_recorded=False,
            )
        )
    else:
        marker[0].entered_at = shift_start
        marker[0].exited_at = shift_start
        for extra in marker[1:]:  # collapse any accidental duplicates
            await session.delete(extra)
    await session.flush()

    # Rebuild the middle from step records (replaces any lossy live-reconcile records).
    await reconstruct_shift_middle(session, workspace_id, user_id, shift_start, now)

    # Leave the current (latest) segment OPEN so the live reconcile extends it and the
    # invariant "one open record ⟺ worker on shift" holds. No ended_shift marker.
    tail = (
        await session.execute(
            select(UserShiftStateRecord)
            .where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.state.in_(_DURATIONFUL),
                UserShiftStateRecord.entered_at >= shift_start,
            )
            .order_by(UserShiftStateRecord.entered_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if tail is not None:
        tail.exited_at = None
        await session.flush()
    return f"healed shift_start={shift_start.isoformat()} current={tail.state.value if tail else 'none'}"


async def _run(*, dry_run: bool, workspace_id: str | None) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            now = datetime.now(timezone.utc)
            day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

            conditions = [
                StepStateRecord.is_deleted.is_(False),
                StepStateRecord.state.in_(_TIME_STATES),
                StepStateRecord.entered_at >= day_start,
            ]
            if workspace_id:
                conditions.append(StepStateRecord.workspace_id == workspace_id)
            workers = (
                await session.execute(
                    select(StepStateRecord.workspace_id, _credited().label("uid"))
                    .where(*conditions)
                    .distinct()
                )
            ).all()

            typer.echo(
                f"heal_open_shifts_today | day={day_start.date()} candidates={len(workers)} "
                f"mode={'dry-run' if dry_run else 'execute'}"
            )
            tally: dict[str, int] = {}
            for row in workers:
                if row.uid is None:
                    continue
                try:
                    outcome = await heal_current_shift(
                        session, row.workspace_id, row.uid, day_start, now, execute=not dry_run
                    )
                    if not dry_run:
                        await session.commit()  # per-worker: one race can't lose the batch
                except IntegrityError:
                    # The live reconcile touched this worker's open record mid-run (unique
                    # open-record index). It's being tracked live — skip cleanly.
                    await session.rollback()
                    outcome = "skipped_raced_live_reconcile"
                key = outcome.split(" ", 1)[0]
                tally[key] = tally.get(key, 0) + 1
                typer.echo(f"  {row.workspace_id} {row.uid} -> {outcome}")

            typer.echo(f"heal_open_shifts_today | done {tally}")
    finally:
        await close_db()


@app.command("heal-open-shifts-today")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
) -> None:
    """Rebuild today's in-progress shifts (missing or lossy) from step records."""
    asyncio.run(_run(dry_run=dry_run, workspace_id=workspace_id))


if __name__ == "__main__":
    app()
