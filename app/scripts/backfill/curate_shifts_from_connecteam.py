"""Curate historical worker shift state from real Connecteam clock-in/out bounds.

For each completed Connecteam shift (real clock-in/clock-out), this writes the
``STARTED_SHIFT``/``ENDED_SHIFT`` markers and reconstructs the ``working``/``in_pause``/
``idle`` middle from the worker's step records via ``reconstruct_shift_middle`` — the same
logic clock-out uses, which handles every timeline bug we've fixed (working-wins, clamping,
no cross-day bleed, manual-pause preservation). Unlike the activity-inference backfill, the
shift *bounds* are authoritative (from Connecteam), so step activity outside a real shift is
correctly excluded.

Dry-run by default; ``--execute`` writes. Idempotent per shift (delete-and-rewrite its
window), so reruns/resumes are safe. Connecteam caps a request at 92 days, so the range is
split into ≤92-day windows. Only historical days (strictly before the current UTC day) are
imported. Run with an RDS snapshot taken first and during a quiet window.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

import typer
from sqlalchemy import delete, func, select

from beyo_manager.config import settings
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.commands.users._reconstruct_shift_middle import reconstruct_shift_middle
from beyo_manager.services.infra.connecteam.time_activities_client import (
    ConnecteamShift,
    ConnecteamTimeActivitiesClient,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)

_WINDOW_DAYS = 91  # inclusive span of 92 days — at the API cap, never over


@dataclass
class CurationTotals:
    shifts_pulled: int = 0
    skipped_open: int = 0
    skipped_unmapped: int = 0
    curated: int = 0


async def curate_worker_shift(
    session,
    *,
    workspace_id: str,
    user_id: str,
    start_at: datetime,
    end_at: datetime,
) -> bool:
    """Idempotently (re)write one worker shift: clear the window, write both markers, and
    reconstruct the middle from step history. Returns ``False`` for a degenerate window."""
    if end_at <= start_at:
        return False
    await session.execute(
        delete(UserShiftStateRecord).where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
            UserShiftStateRecord.entered_at >= start_at,
            UserShiftStateRecord.entered_at <= end_at,
        )
    )
    session.add_all(
        [
            UserShiftStateRecord(
                workspace_id=workspace_id, user_id=user_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=start_at, exited_at=start_at,
                changed_by_id=None, reason=None, manually_recorded=False,
            ),
            UserShiftStateRecord(
                workspace_id=workspace_id, user_id=user_id,
                state=UserShiftStateEnum.ENDED_SHIFT,
                entered_at=end_at, exited_at=end_at,
                changed_by_id=None, reason=None, manually_recorded=False,
            ),
        ]
    )
    await reconstruct_shift_middle(session, workspace_id, user_id, start_at, end_at)
    return True


async def _oldest_step_day(session) -> date | None:
    oldest = await session.scalar(select(func.min(StepStateRecord.entered_at)))
    return oldest.date() if oldest is not None else None


async def _resolve_workers(session, connecteam_user_ids: set[str]) -> dict[str, tuple[str, str]]:
    """Bulk-map ``connecteam_user_id -> (workspace_id, user_id)``. Ambiguous ids (claimed by
    more than one profile) are dropped so curation never writes to the wrong worker."""
    if not connecteam_user_ids:
        return {}
    rows = (
        await session.execute(
            select(
                UserWorkProfile.connecteam_user_id,
                UserWorkProfile.workspace_id,
                UserWorkProfile.user_id,
            ).where(UserWorkProfile.connecteam_user_id.in_(connecteam_user_ids))
        )
    ).all()
    mapping: dict[str, tuple[str, str]] = {}
    ambiguous: set[str] = set()
    for cid, workspace_id, user_id in rows:
        if cid in mapping:
            ambiguous.add(cid)
        mapping[cid] = (workspace_id, user_id)
    for cid in ambiguous:
        mapping.pop(cid, None)
    return mapping


def _split_windows(date_from: date, date_to: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    cursor = date_from
    while cursor <= date_to:
        window_end = min(cursor + timedelta(days=_WINDOW_DAYS), date_to)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


async def _curate_shifts(
    session, shifts: list[ConnecteamShift], totals: CurationTotals, *, execute: bool
) -> None:
    mapping = await _resolve_workers(session, {s.connecteam_user_id for s in shifts})
    for shift in shifts:
        resolved = mapping.get(shift.connecteam_user_id)
        if resolved is None:
            totals.skipped_unmapped += 1
            continue
        workspace_id, user_id = resolved
        if execute:
            await curate_worker_shift(
                session,
                workspace_id=workspace_id,
                user_id=user_id,
                start_at=shift.start_at,
                end_at=shift.end_at,
            )
        totals.curated += 1


async def _run(
    *,
    dry_run: bool,
    time_clock_id: str,
    date_from: date | None,
    date_to: date | None,
    user_ids: list[str] | None,
) -> None:
    if not settings.connecteam_api_key:
        raise ValueError("CONNECTEAM_API_KEY is not configured.")
    now = datetime.now(timezone.utc)
    latest_historical = now.date() - timedelta(days=1)
    effective_to = date_to or latest_historical
    if effective_to > latest_historical:
        raise ValueError("date_to must be before the current UTC day.")

    await init_db()
    client = ConnecteamTimeActivitiesClient(
        api_key=settings.connecteam_api_key,
        base_url=settings.connecteam_api_base_url,
    )
    totals = CurationTotals()
    try:
        async for session in get_db_session():
            effective_from = date_from or await _oldest_step_day(session)
            if effective_from is None:
                typer.echo("connecteam_shift_curation | no step records — nothing to curate")
                return
            if effective_from > effective_to:
                raise ValueError("date_from must be on or before date_to.")

            for window_start, window_end in _split_windows(effective_from, effective_to):
                parsed = await client.fetch_shift_activities(
                    time_clock_id=time_clock_id,
                    start_date=window_start,
                    end_date=window_end,
                    user_ids=user_ids,
                )
                totals.shifts_pulled += len(parsed.shifts)
                totals.skipped_open += parsed.skipped_open
                await _curate_shifts(session, parsed.shifts, totals, execute=not dry_run)
                if not dry_run:
                    await session.commit()  # batch-commit per window (resumable)
                typer.echo(
                    f"connecteam_shift_curation | window={window_start}..{window_end} "
                    f"shifts={len(parsed.shifts)} skipped_open={parsed.skipped_open}"
                )
            break
    finally:
        await close_db()

    verb = "would_curate" if dry_run else "curated"
    typer.echo(
        "connecteam_shift_curation | "
        f"shifts_pulled={totals.shifts_pulled} skipped_open={totals.skipped_open} "
        f"skipped_unmapped={totals.skipped_unmapped} {verb}={totals.curated}"
        + (" [dry-run] no changes committed" if dry_run else "")
    )


@app.command("curate-shifts-from-connecteam")
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute")] = True,
    time_clock_id: Annotated[str | None, typer.Option("--time-clock-id")] = None,
    date_from: Annotated[str | None, typer.Option("--date-from")] = None,
    date_to: Annotated[str | None, typer.Option("--date-to")] = None,
    user_ids: Annotated[list[str] | None, typer.Option("--connecteam-user-id")] = None,
) -> None:
    """Import real Connecteam shifts and rebuild each worker's timeline from step history."""
    resolved_clock = time_clock_id or settings.connecteam_time_clock_id
    if not resolved_clock:
        raise typer.BadParameter(
            "Provide --time-clock-id or set CONNECTEAM_TIME_CLOCK_ID "
            "(list clocks: GET /time-clock/v1/time-clocks)."
        )
    try:
        parsed_from = date.fromisoformat(date_from) if date_from else None
        parsed_to = date.fromisoformat(date_to) if date_to else None
        asyncio.run(
            _run(
                dry_run=dry_run,
                time_clock_id=resolved_clock,
                date_from=parsed_from,
                date_to=parsed_to,
                user_ids=user_ids or None,
            )
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


if __name__ == "__main__":
    app()
