import logging
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
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
) -> None:
    current = await load_open_worker_shift_for_update(session, workspace_id, user_id)
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


async def _load_open_working_step_rows(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
):
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
        .where(
            StepStateRecord.workspace_id == workspace_id,
            StepStateRecord.is_deleted.is_(False),
            StepStateRecord.exited_at.is_(None),
            StepStateRecord.state == TaskStepStateEnum.WORKING,
            _credited_user_id() == user_id,
        )
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
        .with_for_update()
    )
    return list(result.all())


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
    """
    # Cross-command lock order: shift row -> declared row. Phase 3 declaration
    # commands must preserve this order to avoid deadlocks with clock-out/reconcile.
    current = await load_open_worker_shift_for_update(session, workspace_id, user_id)
    if current is None:
        raise ConflictError("Worker is not clocked in.")

    # Rebuild the shift's middle (working/in_pause/idle) deterministically from step history
    # + manual pauses, so the closed shift is correct even if the live reconcile lagged. Run
    # this BEFORE closing working steps (a still-open working step then clamps to clock-out),
    # and against the shift's real start marker. It replaces `current` and all other
    # durationful rows for the shift; the STARTED_SHIFT marker is preserved.
    shift_start = await session.scalar(
        select(func.max(UserShiftStateRecord.entered_at)).where(
            UserShiftStateRecord.workspace_id == workspace_id,
            UserShiftStateRecord.user_id == user_id,
            UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT,
            UserShiftStateRecord.entered_at <= clock_out_at,
        )
    ) or current.entered_at

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
        open_declared.exited_at = clock_out_at
        open_declared.closed_by_id = None
        logger.info(
            "worker_shift.clock_out_declared_clamp | "
            "workspace_id=%s user_id=%s declared_record_id=%s exited_at=%s",
            workspace_id,
            user_id,
            open_declared.client_id,
            clock_out_at.isoformat(),
        )

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
