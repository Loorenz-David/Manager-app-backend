import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.shift_state_machine import DURATIONFUL_STATES
from beyo_manager.domain.users.work_day import work_day_end
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.task_steps._step_transition_core import _apply_step_transition
from beyo_manager.services.commands.users._reconstruct_shift_middle import reconstruct_shift_middle
from beyo_manager.services.context import ServiceContext


logger = logging.getLogger(__name__)


def _credited_user_id():
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)


async def load_open_worker_shift_for_update(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> UserShiftStateRecord | None:
    statement = (
        select(UserShiftStateRecord)
        .where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
            UserShiftStateRecord.exited_at.is_(None),
        )
        .with_for_update()
    )
    current = (await session.execute(statement)).scalar_one_or_none()
    if current is not None:
        return current

    # Under READ COMMITTED, EvalPlanQual can filter a row that was closed while this
    # SELECT waited for its lock, without rescanning for the replacement open row
    # inserted under the partial unique index. One fresh statement snapshot finds it.
    # This retry is intentionally bounded: pathological sustained contention can still
    # produce a false None. Callers surface a retryable conflict or converge on the next
    # trigger, and clock-out always reconstructs the correct closed timeline.
    return (await session.execute(statement)).scalar_one_or_none()


async def clock_in_shift_for_user(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    clock_in_at: datetime,
    changed_by_id: str,
) -> list[str]:
    """Open a shift at ``clock_in_at``; returns the ids of steps a stale closure paused.

    A shift still open past its own work-day end is not "already clocked in": it is closed
    at that boundary first (see `close_stale_open_shift`), and the new shift opens here.
    The list is empty unless that happened; callers broadcast it after commit.
    """
    current = await load_open_worker_shift_for_update(session, workspace_id, user_id)
    stale = await close_stale_open_shift(session, workspace_id, user_id, current, clock_in_at)
    if stale is not None:
        current = None
    if current is not None:
        raise ConflictError("Worker is already clocked in.")

    session.add_all(
        [
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=clock_in_at,
                exited_at=clock_in_at,
                changed_by_id=changed_by_id,
                reason=None,
                manually_recorded=False,
            ),
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.IDLE,
                entered_at=clock_in_at,
                exited_at=None,
                changed_by_id=changed_by_id,
                reason=None,
                manually_recorded=False,
            ),
        ]
    )
    await session.flush()
    return list(stale.paused_step_ids) if stale is not None else []


async def _load_open_working_step_rows(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    *,
    entered_before: datetime | None = None,
):
    conditions = [
        StepStateRecord.workspace_id == workspace_id,
        StepStateRecord.is_deleted.is_(False),
        StepStateRecord.exited_at.is_(None),
        StepStateRecord.state == TaskStepStateEnum.WORKING,
        _credited_user_id() == user_id,
    ]
    if entered_before is not None:
        conditions.append(StepStateRecord.entered_at < entered_before)
    result = await session.execute(
        select(StepStateRecord, TaskStep, Task)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .join(
            Task,
            and_(
                Task.client_id == TaskStep.task_id,
                Task.workspace_id == workspace_id,
                Task.is_deleted.is_(False),
            ),
        )
        .where(*conditions)
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
        .with_for_update()
    )
    return list(result.all())


@dataclass(frozen=True)
class StaleShiftClosure:
    """A shift closed at its own work-day end because it outlived it."""

    closed_at: datetime
    paused_step_ids: list[str]


async def _open_shift_started_at(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    current: UserShiftStateRecord,
    at: datetime,
) -> datetime:
    """The open shift's STARTED_SHIFT marker time (latest marker at or before ``at``)."""
    return await session.scalar(
        select(func.max(UserShiftStateRecord.entered_at)).where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
            UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT,
            UserShiftStateRecord.entered_at <= at,
        )
    ) or current.entered_at


async def close_stale_open_shift(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    current: UserShiftStateRecord | None,
    now: datetime,
) -> StaleShiftClosure | None:
    """Close ``current`` at ``work_day_end(started_at)`` if that boundary is ``<= now``.

    Call it right after `load_open_worker_shift_for_update`, under that row lock, with the
    row it returned. Returns ``None`` (and writes nothing) when there is no open shift or
    the shift is still inside its work day.

    The shift is closed at its **own** boundary, never at ``now``: whatever woke the system
    up — the nightly sweep running late, a kiosk tap after production slept, a step
    transition — the closed shift is identical. Activity recorded at or after the boundary
    is not part of it (see `_close_open_shift`); it belongs to the next work day, whose
    shift the live reconcile opens from any still-open working step.
    """
    if current is None:
        return None
    shift_start = await _open_shift_started_at(session, workspace_id, user_id, current, now)
    boundary = work_day_end(shift_start)
    if boundary > now:
        return None
    paused_step_ids = await _close_open_shift(
        session,
        workspace_id,
        user_id,
        shift_start=shift_start,
        clock_out_at=boundary,
        # Nobody clocked out at midnight: the boundary closed it, so no actor is recorded
        # (the same attribution the nightly sweep has always written).
        changed_by_id=None,
    )
    logger.info(
        "worker_shift.stale_shift_closed | "
        "workspace_id=%s user_id=%s shift_started_at=%s closed_at=%s paused_steps=%s",
        workspace_id,
        user_id,
        shift_start.isoformat(),
        boundary.isoformat(),
        len(paused_step_ids),
    )
    return StaleShiftClosure(closed_at=boundary, paused_step_ids=paused_step_ids)


async def clock_out_shift_for_user(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    clock_out_at: datetime,
    changed_by_id: str | None,
) -> list[str]:
    """Close the shift; returns the ids of the steps it force-paused.

    The ids, not just the count: every caller broadcasts them as `task:step-state-changed`
    once its transaction commits, so the worker's device stops rendering steps this
    clock-out already paused. `len()` is the count callers used to get back.

    A shift that has outlived its work day by ``clock_out_at`` is closed at its own
    boundary instead (`close_stale_open_shift`), never at ``clock_out_at``. A caller that
    needs the actual close time calls `close_stale_open_shift` itself first.
    """
    # Cross-command lock order: shift row -> declared row. Phase 3 declaration
    # commands must preserve this order to avoid deadlocks with clock-out/reconcile.
    current = await load_open_worker_shift_for_update(session, workspace_id, user_id)
    if current is None:
        raise ConflictError("Worker is not clocked in.")

    stale = await close_stale_open_shift(session, workspace_id, user_id, current, clock_out_at)
    if stale is not None:
        return stale.paused_step_ids

    shift_start = await _open_shift_started_at(
        session, workspace_id, user_id, current, clock_out_at
    )
    return await _close_open_shift(
        session,
        workspace_id,
        user_id,
        shift_start=shift_start,
        clock_out_at=clock_out_at,
        changed_by_id=changed_by_id,
    )


async def _drop_projections_from(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    clock_out_at: datetime,
) -> None:
    """Remove this user's derived shift segments entered at or after ``clock_out_at``.

    While a shift stays open past its close instant (a stale shift nobody closed at
    midnight, or a clock-out reported late), the live reconcile keeps appending
    `working`/`in_pause`/`idle` rows for activity *after* that instant. They describe the
    next shift, not this one, and one of them is the open row — left alone it would keep
    the shift "open" after its ENDED marker. They are projections (the table is derived;
    `reconstruct_shift_middle` rebuilds any window from source), so they are dropped and
    the next shift's reconcile/clock-out re-derives that time.

    Frozen legacy manual shift-pauses (`manually_recorded` with a human `changed_by_id`)
    are source rows, not projections, and are kept; one still open is closed where it
    began so it cannot hold the shift open or span the boundary backwards.
    """
    is_legacy_manual = and_(
        UserShiftStateRecord.manually_recorded.is_(True),
        UserShiftStateRecord.changed_by_id.is_not(None),
    )
    after_close = (
        UserShiftStateRecord.workspace_id == workspace_id,
        UserShiftStateRecord.user_id == user_id,
        UserShiftStateRecord.state.in_(DURATIONFUL_STATES),
        UserShiftStateRecord.entered_at >= clock_out_at,
    )
    await session.execute(
        delete(UserShiftStateRecord).where(*after_close, ~is_legacy_manual)
    )
    open_legacy = (
        await session.execute(
            select(UserShiftStateRecord).where(
                *after_close,
                is_legacy_manual,
                UserShiftStateRecord.exited_at.is_(None),
            )
        )
    ).scalars().all()
    for record in open_legacy:
        record.exited_at = record.entered_at


async def _close_open_shift(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    *,
    shift_start: datetime,
    clock_out_at: datetime,
    changed_by_id: str | None,
) -> list[str]:
    """Close the open shift started at ``shift_start`` at exactly ``clock_out_at``.

    The caller holds the open shift row's lock. Everything the worker recorded at or after
    ``clock_out_at`` is left out of this shift rather than folded into it or closed
    backwards (which the `exited_at >= entered_at` checks would reject):

    - a declared state *entered* at/after it is closed where it began (zero length; no
      shift covers it, and any other end would depend on when the closure happened to run);
    - shift segments entered at/after it are dropped (`_drop_projections_from`);
    - working steps *entered* at/after it stay WORKING — they are the next work day's, and
      the live reconcile opens that day's shift from them.
    """
    open_declared = (
        await session.execute(
            select(UserDeclaredStateRecord)
            .where(
                UserDeclaredStateRecord.workspace_id == workspace_id,
                UserDeclaredStateRecord.user_id == user_id,
                UserDeclaredStateRecord.exited_at.is_(None),
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if open_declared is not None:
        open_declared.exited_at = max(clock_out_at, open_declared.entered_at)
        open_declared.closed_by_id = None
        logger.info(
            "worker_shift.clock_out_declared_clamp | "
            "workspace_id=%s user_id=%s declared_record_id=%s exited_at=%s",
            workspace_id,
            user_id,
            open_declared.client_id,
            open_declared.exited_at.isoformat(),
        )

    await _drop_projections_from(session, workspace_id, user_id, clock_out_at)

    # Rebuild the shift's middle (working/in_pause/idle) deterministically from step history
    # + manual pauses, so the closed shift is correct even if the live reconcile lagged. Run
    # this BEFORE closing working steps (a still-open working step then clamps to clock-out),
    # and against the shift's real start marker. It replaces `current` and all other
    # durationful rows for the shift; the STARTED_SHIFT marker is preserved.
    await reconstruct_shift_middle(session, workspace_id, user_id, shift_start, clock_out_at)

    transition_actor_id = changed_by_id or user_id
    transition_ctx = ServiceContext(
        identity={
            "user_id": transition_actor_id,
            "workspace_id": workspace_id,
        },
        incoming_data={},
        session=session,
    )
    open_working_rows = await _load_open_working_step_rows(
        session,
        workspace_id,
        user_id,
        entered_before=clock_out_at,
    )
    for closing_record, step, task in open_working_rows:
        await _apply_step_transition(
            transition_ctx,
            step,
            task,
            closing_record,
            # A step the shift ended under is simply paused. *Why* it stopped is the
            # transition below, not the state: the state says what the step is, the reason
            # says what happened to it. Analytics still bucket this span as `ended_shift`,
            # derived from the pair (see `domain/analytics/time_buckets.py`).
            new_state=TaskStepStateEnum.PAUSED,
            # System transition: typed from the code-owned vocabulary rather than resolved
            # from the workspace catalog. This is the line that made clock-out fail in every
            # workspace without a `pause_ended_shift` row. Every clock source — HTTP,
            # Connecteam, the overnight safeguard — reaches it through this function.
            pause_reason_id=None,
            transition_reason=TransitionReasonEnum.SHIFT_ENDED.value,
            description=None,
            credited_user_id=user_id,
            now=clock_out_at,
        )

    session.add(
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            state=UserShiftStateEnum.ENDED_SHIFT,
            entered_at=clock_out_at,
            exited_at=clock_out_at,
            changed_by_id=changed_by_id,
            reason=None,
            manually_recorded=False,
        )
    )
    await session.flush()
    return [step.client_id for _, step, _ in open_working_rows]
