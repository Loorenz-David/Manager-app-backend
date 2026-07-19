"""Manager drill-down over the worker's recorded on-shift state intervals."""

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select

from beyo_manager.domain.analytics.serializers import (
    serialize_linear_timeline,
    serialize_recorded_shift_segment,
)
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats._roster import (
    count_completed_steps,
    resolve_date_range,
)
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    build_recorded_shift_timeline,
    load_recorded_shift_records,
)


_MAX_SEGMENTS = 5000
_PUBLIC_SHIFT_STATES = {
    UserShiftStateEnum.STARTED_SHIFT: "started_shift",
    UserShiftStateEnum.WORKING: "working",
    UserShiftStateEnum.IN_PAUSE: "paused",
    UserShiftStateEnum.IDLE: "idle",
    UserShiftStateEnum.ENDED_SHIFT: "ended_shift",
}
_STEP_STATE_FOR_SHIFT = {
    UserShiftStateEnum.WORKING: TaskStepStateEnum.WORKING,
    UserShiftStateEnum.IN_PAUSE: TaskStepStateEnum.PAUSED,
}
_MARKER_ORDER = {
    UserShiftStateEnum.ENDED_SHIFT: 0,
    UserShiftStateEnum.STARTED_SHIFT: 1,
}


@dataclass(frozen=True)
class _ShiftSegment:
    record: UserShiftStateRecord
    start: datetime
    end: datetime


@dataclass(frozen=True)
class _StepTimelineRecord:
    record_id: str
    step_id: str
    state: str
    reason: str | None
    entered_at: datetime
    exited_at: datetime | None

    @property
    def is_open(self) -> bool:
        return self.exited_at is None


async def _load_record_outcomes(
    ctx: ServiceContext,
    step_ids: list[str],
    window_start: datetime,
    window_end: datetime,
) -> tuple[dict[str, list[datetime]], dict[str, list[str]]]:
    if not step_ids:
        return {}, {}
    rows = await ctx.session.execute(
        select(
            StepStateRecord.step_id,
            StepStateRecord.entered_at,
            StepStateRecord.state,
        )
        .where(
            StepStateRecord.workspace_id == ctx.workspace_id,
            StepStateRecord.step_id.in_(step_ids),
            StepStateRecord.is_deleted.is_(False),
            StepStateRecord.entered_at >= window_start,
            StepStateRecord.entered_at < window_end + timedelta(days=1),
        )
        .order_by(StepStateRecord.step_id, StepStateRecord.entered_at)
    )
    entered_by_step: dict[str, list[datetime]] = defaultdict(list)
    states_by_step: dict[str, list[str]] = defaultdict(list)
    for row in rows.all():
        entered_by_step[row.step_id].append(row.entered_at)
        states_by_step[row.step_id].append(row.state.value)
    return entered_by_step, states_by_step


async def _load_step_and_primary_item(
    ctx: ServiceContext,
    step_ids: list[str],
) -> tuple[dict[str, TaskStep], dict[str, Item]]:
    if not step_ids:
        return {}, {}

    steps = (
        await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id.in_(step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    steps_by_id = {step.client_id: step for step in steps}

    task_ids = list({step.task_id for step in steps})
    item_by_task: dict[str, Item] = {}
    if task_ids:
        task_items = (
            await ctx.session.execute(
                select(TaskItem.task_id, TaskItem.item_id).where(
                    TaskItem.workspace_id == ctx.workspace_id,
                    TaskItem.task_id.in_(task_ids),
                    TaskItem.removed_at.is_(None),
                    TaskItem.role == TaskItemRoleEnum.PRIMARY,
                )
            )
        ).all()
        item_to_task = {row.item_id: row.task_id for row in task_items}
        if item_to_task:
            items = (
                await ctx.session.execute(
                    select(Item).where(
                        Item.workspace_id == ctx.workspace_id,
                        Item.client_id.in_(list(item_to_task)),
                        Item.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            item_by_task = {
                item_to_task[item.client_id]: item
                for item in items
            }

    return steps_by_id, item_by_task


async def _load_step_timeline_records(
    ctx: ServiceContext,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
) -> list[_StepTimelineRecord]:
    credited = func.coalesce(
        StepStateRecord.credited_user_id,
        StepStateRecord.created_by_id,
    )
    rows = await ctx.session.execute(
        select(
            StepStateRecord.client_id.label("record_id"),
            StepStateRecord.step_id,
            StepStateRecord.state,
            StepStateRecord.reason,
            StepStateRecord.entered_at,
            StepStateRecord.exited_at,
        )
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            StepStateRecord.workspace_id == ctx.workspace_id,
            StepStateRecord.is_deleted.is_(False),
            credited == user_id,
            StepStateRecord.state.in_(
                (TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED)
            ),
            StepStateRecord.entered_at < window_end,
            (
                StepStateRecord.exited_at.is_(None)
                | (StepStateRecord.exited_at > window_start)
            ),
        )
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
    )
    return [
        _StepTimelineRecord(
            record_id=row.record_id,
            step_id=row.step_id,
            state=row.state.value,
            reason=row.reason.value if row.reason is not None else None,
            entered_at=row.entered_at,
            exited_at=row.exited_at,
        )
        for row in rows.all()
    ]


def _build_shift_segments(
    records: list[UserShiftStateRecord],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> list[_ShiftSegment]:
    segments: list[_ShiftSegment] = []
    ordered = sorted(
        records,
        key=lambda record: (
            record.entered_at,
            _MARKER_ORDER.get(record.state, 2),
            record.client_id,
        ),
    )
    for record in ordered:
        if record.state in {
            UserShiftStateEnum.STARTED_SHIFT,
            UserShiftStateEnum.ENDED_SHIFT,
        }:
            if window_start <= record.entered_at < window_end:
                segments.append(
                    _ShiftSegment(record, record.entered_at, record.entered_at)
                )
            continue
        start = max(record.entered_at, window_start)
        end = min(record.exited_at or now, window_end)
        if end > start:
            segments.append(_ShiftSegment(record, start, end))
    return segments


async def get_worker_linear_timeline_breakdown(ctx: ServiceContext) -> dict:
    user_id = ctx.incoming_data.get("user_id")
    date_from, date_to = resolve_date_range(ctx.query_params)

    user = (
        await ctx.session.execute(
            select(User)
            .join(
                WorkspaceMembership,
                and_(
                    WorkspaceMembership.user_id == User.client_id,
                    WorkspaceMembership.workspace_id == ctx.workspace_id,
                    WorkspaceMembership.is_active.is_(True),
                ),
            )
            .where(User.client_id == user_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise NotFound("Worker not found in this workspace.")

    now = datetime.now(timezone.utc)
    window_start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    window_end = datetime.combine(
        date_to + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    records = (
        await load_recorded_shift_records(
            ctx,
            [user_id],
            window_start,
            window_end,
        )
    ).get(user_id, [])
    timeline = build_recorded_shift_timeline(
        records,
        window_start,
        window_end,
        now,
    )
    completed = await count_completed_steps(
        ctx.session,
        ctx.workspace_id,
        [user_id],
        window_start,
        window_end,
    )

    shift_segments = _build_shift_segments(
        records,
        window_start,
        window_end,
        now,
    )
    truncated = len(shift_segments) > _MAX_SEGMENTS
    shift_segments = shift_segments[:_MAX_SEGMENTS]

    step_records = await _load_step_timeline_records(
        ctx,
        user_id,
        window_start,
        window_end,
    )
    all_step_ids = sorted({record.step_id for record in step_records})
    steps_by_id, item_by_task = await _load_step_and_primary_item(ctx, all_step_ids)
    entered_by_step, states_by_step = await _load_record_outcomes(
        ctx,
        all_step_ids,
        window_start,
        window_end,
    )

    def ended_by(record: _StepTimelineRecord) -> str:
        if record.exited_at is None:
            return "still_open"
        entered = entered_by_step.get(record.step_id, [])
        index = bisect_left(entered, record.exited_at)
        if index < len(entered):
            return states_by_step[record.step_id][index]
        return "unknown"

    def record_detail(record: _StepTimelineRecord) -> dict | None:
        step = steps_by_id.get(record.step_id)
        if step is None:
            return None
        item = item_by_task.get(step.task_id)
        return {
            "record_id": record.record_id,
            "step_id": step.client_id,
            "task_id": step.task_id,
            "working_section_id": step.working_section_id,
            "working_section_name": step.working_section_name_snapshot,
            "item": (
                {
                    "client_id": item.client_id,
                    "article_number": item.article_number,
                    "sku": item.sku,
                }
                if item is not None
                else None
            ),
            "state": record.state,
            "reason": record.reason,
            "entered_at": record.entered_at.isoformat(),
            "exited_at": (
                record.exited_at.isoformat()
                if record.exited_at is not None
                else None
            ),
            "is_open": record.is_open,
            "ended_by": ended_by(record),
        }

    serialized_segments = []
    for segment in shift_segments:
        desired_step_state = _STEP_STATE_FOR_SHIFT.get(segment.record.state)
        details: list[dict] = []
        if desired_step_state is not None:
            for step_record in step_records:
                step_end = step_record.exited_at or now
                if (
                    step_record.state == desired_step_state.value
                    and step_record.entered_at < segment.end
                    and step_end > segment.start
                ):
                    detail = record_detail(step_record)
                    if detail is not None:
                        details.append(detail)
        serialized_segments.append(
            serialize_recorded_shift_segment(
                start=segment.start,
                end=segment.end,
                state=_PUBLIC_SHIFT_STATES[segment.record.state],
                reason=(
                    segment.record.reason
                    if segment.record.state is UserShiftStateEnum.IN_PAUSE
                    else None
                ),
                is_open=(
                    segment.record.exited_at is None
                    and segment.end == now
                ),
                manually_recorded=segment.record.manually_recorded,
                steps=details,
            )
        )

    return {
        "user": serialize_user_worker_stat(user),
        "timeline": serialize_linear_timeline(
            date_from,
            date_to,
            timeline,
            completed.get(user_id, 0),
        ),
        "segments": serialized_segments,
        "segments_truncated": truncated,
    }
