"""Deterministically rebuild a shift's durationful states from step history.

The live reconcile (analytics worker) records `working`/`in_pause`/`idle` transitions as
they happen — but only if it processes each event while that state is still current. If
the worker lags or is down during a shift, intermediate states are lost. Clock-out fixes
that: it re-derives the whole middle of the shift from the step records (the source of
truth) plus any manual shift-pauses, so a **closed shift is always correct regardless of
analytics-worker uptime**. The `started_shift`/`ended_shift` markers are left untouched;
only the durationful records between them are replaced.

Manual shift-pauses are folded into the same sweep as `paused` intervals, so they survive
the rebuild (re-emitted with `manually_recorded=True` and their free-text reason) and
correctly occupy their windows instead of collapsing to idle. A worker can only manually
pause from `idle`, so manual and step pauses never overlap — each rebuilt pause is
unambiguously one or the other.
"""

from datetime import datetime

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.analytics.linear_timeline import LinearInterval, compute_linear_segments
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord

_STEP_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED)
_DURATIONFUL_SHIFT_STATES = (
    UserShiftStateEnum.WORKING,
    UserShiftStateEnum.IN_PAUSE,
    UserShiftStateEnum.IDLE,
)
_SEGMENT_TO_SHIFT_STATE = {
    "working": UserShiftStateEnum.WORKING,
    "paused": UserShiftStateEnum.IN_PAUSE,
    "idle": UserShiftStateEnum.IDLE,
}


def _credited():
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)


def _idle_record(workspace_id: str, user_id: str, start: datetime, end: datetime) -> UserShiftStateRecord:
    return UserShiftStateRecord(
        workspace_id=workspace_id,
        user_id=user_id,
        state=UserShiftStateEnum.IDLE,
        entered_at=start,
        exited_at=end,
        changed_by_id=None,
        reason=None,
        manually_recorded=False,
    )


async def reconstruct_shift_middle(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    shift_start: datetime,
    shift_end: datetime,
) -> None:
    """Replace the durationful (`working`/`in_pause`/`idle`) records of one shift with a
    fresh reconstruction from step records + manual pauses over ``[shift_start, shift_end]``.

    Call it at clock-out (or a shift-scoped repair) **before** open working steps are closed,
    so a still-open working step clamps to ``shift_end``. Markers are preserved.
    """
    step_rows = (
        await session.execute(
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
                _credited() == user_id,
                StepStateRecord.state.in_(_STEP_TIME_STATES),
                # Shift-scoped: only steps ENTERED during this shift (matches the live
                # reconcile). A step paused on a previous day and still open at clock-in is
                # a carryover — it must not label this shift's pre-work time with yesterday's
                # reason; that time is idle until the worker actually acts this shift.
                StepStateRecord.entered_at >= shift_start,
                StepStateRecord.entered_at < shift_end,
            )
        )
    ).all()
    intervals = [
        LinearInterval(
            record_id=row.client_id,
            state=row.state.value,
            reason=row.reason.value if row.reason is not None else None,
            entered_at=row.entered_at,
            exited_at=row.exited_at,
            step_id=row.step_id,
        )
        for row in step_rows
    ]

    # Manual shift-pauses in the window, fed into the same sweep so they occupy their
    # windows (as `paused`) and survive the rebuild.
    manual_rows = (
        await session.execute(
            select(
                UserShiftStateRecord.client_id,
                UserShiftStateRecord.reason,
                UserShiftStateRecord.entered_at,
                UserShiftStateRecord.exited_at,
            ).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.state == UserShiftStateEnum.IN_PAUSE,
                UserShiftStateRecord.manually_recorded.is_(True),
                UserShiftStateRecord.entered_at >= shift_start,
                UserShiftStateRecord.entered_at < shift_end,
            )
        )
    ).all()
    manual_ids = {row.client_id for row in manual_rows}
    intervals.extend(
        LinearInterval(
            record_id=row.client_id,
            state="paused",
            reason=row.reason,
            entered_at=row.entered_at,
            exited_at=row.exited_at,
        )
        for row in manual_rows
    )

    segments = compute_linear_segments(intervals, shift_start, shift_end, shift_end)

    # Replace the shift's durationful records; keep the markers.
    await session.execute(
        delete(UserShiftStateRecord).where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
            UserShiftStateRecord.state.in_(_DURATIONFUL_SHIFT_STATES),
            UserShiftStateRecord.entered_at >= shift_start,
            UserShiftStateRecord.entered_at < shift_end,
        )
    )

    records: list[UserShiftStateRecord] = []
    cursor = shift_start
    for segment in segments:
        state = _SEGMENT_TO_SHIFT_STATE.get(segment.state)
        if state is None:  # e.g. an `ended_shift` segment — the real marker handles shift end
            continue
        if segment.start > cursor:  # leading / inter-activity gap not the worker's break → idle
            records.append(_idle_record(workspace_id, user_id, cursor, segment.start))
        is_manual = state is UserShiftStateEnum.IN_PAUSE and bool(set(segment.record_ids) & manual_ids)
        records.append(
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=state,
                entered_at=segment.start,
                exited_at=segment.end,
                changed_by_id=None,
                reason=(segment.reason if state is UserShiftStateEnum.IN_PAUSE else None),
                manually_recorded=is_manual,
            )
        )
        cursor = segment.end
    if cursor < shift_end:  # trailing idle (incl. an empty shift = idle throughout)
        records.append(_idle_record(workspace_id, user_id, cursor, shift_end))

    if records:
        session.add_all(records)
        await session.flush()
