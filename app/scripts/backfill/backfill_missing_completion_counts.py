"""Fold never-processed completions into the analytics rollups.

Completions recorded before the analytics completion path went live were written to
``step_state_records`` but never counted into the rollup tables. This replays them
through the SAME functions the live analytics worker uses
(``reconcile_user_day_completions`` / ``apply_completion_reconcile_deltas``), so the
result is identical to what the worker would have produced at the time.

Only the completion/issue columns are touched. Time, cost and inaccuracy columns are
left alone — use ``backfill_averaged_time`` for those.

Idempotent: each affected (user, day) is recomputed and SET from records, and the Σ
tables receive the difference. Re-running changes nothing, so it is safe to run twice
or to resume after an interruption.

Dry-run by default. Use ``--execute`` to commit.

    # see what would change, whole history
    python scripts/backfill/backfill_missing_completion_counts.py

    # only the days before the completion path went live
    python scripts/backfill/backfill_missing_completion_counts.py --until 2026-07-16

    # commit
    python scripts/backfill/backfill_missing_completion_counts.py --until 2026-07-16 --execute

Operational note: prefer a quiet window with the analytics queue drained. This writes
absolute values per user-day, so a completion the live worker commits between this
script's read and its write would be overwritten (recoverable by re-running).

The measured size and shape of the gap this script exists to close — 497 completions,
uncounted before 2026-07-16, with the re-runnable query and its caveats — is recorded
in docs/architecture/implemented_summaries/completion_counting_gap_20260811.md.
Those figures come from a production snapshot, not from anything in this repo, which
is why they live in a dated note rather than in this docstring.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Annotated

import typer
from sqlalchemy import func, select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.analytics.user_daily_work_stats import UserDailyWorkStats
from beyo_manager.models.tables.analytics.user_lifetime_stats import UserLifetimeStats
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.queries.analytics.reconcile_user_time import (
    apply_completion_reconcile_deltas,
    reconcile_user_day_completions,
)

app = typer.Typer(add_completion=False, no_args_is_help=False)

_ATTRIBUTED_USER = func.coalesce(
    StepStateRecord.credited_user_id, StepStateRecord.created_by_id
)


async def _affected_user_days(session, until: date | None) -> list[tuple[str, str, date]]:
    """(workspace_id, user_id, work_date) for every day that has a COMPLETED record.

    Attribution matches the live worker and the functional index
    ix_step_state_records_ws_credited_entered.
    """
    work_date = func.date(func.timezone("UTC", StepStateRecord.entered_at)).label("work_date")
    stmt = (
        select(StepStateRecord.workspace_id, _ATTRIBUTED_USER.label("user_id"), work_date)
        .where(
            StepStateRecord.state == TaskStepStateEnum.COMPLETED,
            StepStateRecord.is_deleted.is_(False),
            StepStateRecord.created_by_id.is_not(None),
        )
        .group_by(StepStateRecord.workspace_id, _ATTRIBUTED_USER, work_date)
        .order_by(work_date)
    )
    if until is not None:
        stmt = stmt.where(work_date <= until)
    return [(r.workspace_id, r.user_id, r.work_date) for r in (await session.execute(stmt)).all()]


async def _display_name(session, user_id: str) -> str:
    user = await session.scalar(select(User).where(User.client_id == user_id))
    return user.username if user else ""


async def _completed_total(session) -> int:
    return (
        await session.scalar(select(func.coalesce(func.sum(UserDailyWorkStats.total_completed_count), 0)))
    ) or 0


async def _lifetime_total(session) -> int:
    return (
        await session.scalar(select(func.coalesce(func.sum(UserLifetimeStats.total_completed_count), 0)))
    ) or 0


async def _run(*, dry_run: bool, until: date | None) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            now = datetime.now(timezone.utc)

            before_daily = await _completed_total(session)
            before_lifetime = await _lifetime_total(session)
            targets = await _affected_user_days(session, until)

            recorded = (
                await session.scalar(
                    select(func.count())
                    .select_from(StepStateRecord)
                    .where(
                        StepStateRecord.state == TaskStepStateEnum.COMPLETED,
                        StepStateRecord.is_deleted.is_(False),
                        StepStateRecord.created_by_id.is_not(None),
                    )
                )
            ) or 0

            typer.echo(
                f"missing_completion_backfill | user_days={len(targets)} "
                f"completed_records_total={recorded} "
                f"rollup_before(user_daily)={before_daily} lifetime_before={before_lifetime}"
                + (f" until={until.isoformat()}" if until else " until=<all history>")
            )
            if not targets:
                typer.echo("nothing to do")
                return

            names: dict[str, str] = {}
            for workspace_id, user_id, work_date in targets:
                if user_id not in names:
                    names[user_id] = await _display_name(session, user_id)
                result = await reconcile_user_day_completions(
                    session, workspace_id, user_id, names[user_id], work_date, now
                )
                await apply_completion_reconcile_deltas(
                    session, workspace_id, user_id, names[user_id], work_date, now, result
                )
            await session.flush()

            after_daily = await _completed_total(session)
            after_lifetime = await _lifetime_total(session)
            typer.echo(
                f"missing_completion_backfill | rollup_after(user_daily)={after_daily} "
                f"(+{after_daily - before_daily}) lifetime_after={after_lifetime} "
                f"(+{after_lifetime - before_lifetime})"
            )

            if dry_run:
                await session.rollback()
                typer.echo("[dry-run] rolled back — no changes committed")
                return

            await session.commit()
            typer.echo("missing_completion_backfill | committed")
    finally:
        await close_db()


@app.command()
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    until: Annotated[
        datetime | None,
        typer.Option("--until", formats=["%Y-%m-%d"], help="Only reconcile days <= this date."),
    ] = None,
) -> None:
    """Fold never-processed completions into the analytics rollups."""
    asyncio.run(_run(dry_run=dry_run, until=until.date() if until else None))


if __name__ == "__main__":
    app()
