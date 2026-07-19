"""Shared IO primitive for concurrency-averaged time.

Fetches one worker's time-bearing step records overlapping a window (joined to
`TaskStep` for `allows_batch_working`), runs the pure sweep, and returns per-record
averaged seconds with the metadata callers need to bucket by step / day / section /
state. The analytics worker recompute, the worker-stats endpoints, and the backfill
all go through here, so the aggregates are a deterministic projection of the records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.analytics.concurrency import (
    TimeInterval,
    averaged_seconds_by_record,
    wasted_seconds_by_record,
)
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep

_TIME_STATES = (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT)


@dataclass(frozen=True)
class RecordContribution:
    record_id: str
    step_id: str
    working_section_id: str
    state: str                 # "working" | "paused" | "ended_shift"
    entered_at: datetime
    exited_at: datetime | None
    is_open: bool              # exited_at IS NULL (running)
    step_is_deleted: bool
    step_is_completed: bool
    marked_wrong: bool
    seconds: float             # concurrency-averaged share
    wasted_seconds: float      # flagged-only concurrency-averaged share


async def compute_record_contributions(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> list[RecordContribution]:
    """Averaged per-record seconds for ``user_id`` over records overlapping the window.

    Attribution is ``COALESCE(credited_user_id, created_by_id)`` (matches the analytics
    pipeline). The window should generously cover the intervals of the records being
    reconstructed (e.g. a day ± buffer) so concurrency is computed against all overlaps.
    Callers filter/bucket the result (settled = not open; per-step/day/section/state).
    """
    rows = (
        await session.execute(
            select(
                StepStateRecord.client_id.label("record_id"),
                StepStateRecord.step_id.label("step_id"),
                StepStateRecord.state.label("state"),
                StepStateRecord.entered_at.label("entered_at"),
                StepStateRecord.exited_at.label("exited_at"),
                StepStateRecord.recorded_time_marked_wrong.label("marked_wrong"),
                TaskStep.working_section_id.label("working_section_id"),
                TaskStep.allows_batch_working.label("is_batchable"),
                TaskStep.is_deleted.label("step_is_deleted"),
                TaskStep.recorded_time_marked_wrong.label("step_marked_wrong"),
                TaskStep.state.label("step_state"),
            )
            .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
            .where(
                StepStateRecord.workspace_id == workspace_id,
                func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id) == user_id,
                StepStateRecord.is_deleted.is_(False),
                StepStateRecord.state.in_(_TIME_STATES),
                StepStateRecord.entered_at < window_end,
                # overlaps the window: still open, or exited after it starts
                (StepStateRecord.exited_at.is_(None)) | (StepStateRecord.exited_at > window_start),
            )
        )
    ).all()

    intervals = [
        TimeInterval(
            record_id=row.record_id,
            step_id=row.step_id,
            state=row.state.value,
            entered_at=row.entered_at,
            exited_at=row.exited_at,
            marked_wrong=bool(row.marked_wrong or row.step_marked_wrong),
            is_batchable=row.is_batchable,
        )
        for row in rows
    ]
    seconds_by_record = averaged_seconds_by_record(intervals, now)
    wasted_by_record = wasted_seconds_by_record(intervals, now)

    return [
        RecordContribution(
            record_id=row.record_id,
            step_id=row.step_id,
            working_section_id=row.working_section_id,
            state=row.state.value,
            entered_at=row.entered_at,
            exited_at=row.exited_at,
            is_open=row.exited_at is None,
            step_is_deleted=row.step_is_deleted,
            step_is_completed=row.step_state == TaskStepStateEnum.COMPLETED,
            marked_wrong=bool(row.marked_wrong or row.step_marked_wrong),
            seconds=seconds_by_record.get(row.record_id, 0.0),
            wasted_seconds=wasted_by_record.get(row.record_id, 0.0),
        )
        for row in rows
    ]
