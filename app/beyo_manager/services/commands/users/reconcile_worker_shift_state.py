import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.shift_state_machine import (
    derive_target_state,
    is_valid_shift_state_transition,
)
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.users._clock_worker_shift import (
    load_open_worker_shift_for_update,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShiftReconcileOutcome:
    changed: bool
    state: UserShiftStateEnum | None
    auto_clocked_in: bool = False


def _credited_user_id():
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)


async def _load_open_steps(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    *,
    states: tuple[TaskStepStateEnum, ...],
    entered_at_or_after: datetime | None = None,
) -> list[StepStateRecord]:
    conditions = [
        StepStateRecord.workspace_id == workspace_id,
        StepStateRecord.is_deleted.is_(False),
        StepStateRecord.exited_at.is_(None),
        _credited_user_id() == user_id,
        StepStateRecord.state.in_(states),
    ]
    if entered_at_or_after is not None:
        conditions.append(StepStateRecord.entered_at >= entered_at_or_after)

    result = await session.execute(
        select(StepStateRecord)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == StepStateRecord.step_id,
                TaskStep.workspace_id == workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(*conditions)
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
    )
    return list(result.scalars().all())


async def _reconcile_once(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    now: datetime,
) -> ShiftReconcileOutcome:
    # Cross-command lock order: shift row -> declared row. Phase 3 declaration
    # commands must preserve this order to avoid deadlocks with reconcile/clock-out.
    current = await load_open_worker_shift_for_update(
        session,
        workspace_id,
        user_id,
    )

    auto_clocked_in = False
    shift_started_at: datetime | None = None
    if current is None:
        open_working = await _load_open_steps(
            session,
            workspace_id,
            user_id,
            states=(TaskStepStateEnum.WORKING,),
        )
        if not open_working:
            logger.info(
                "worker_shift.reconcile_no_open_shift | workspace_id=%s user_id=%s",
                workspace_id,
                user_id,
            )
            return ShiftReconcileOutcome(changed=False, state=None)

        latest_ended_at = await session.scalar(
            select(func.max(UserShiftStateRecord.entered_at)).where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.state == UserShiftStateEnum.ENDED_SHIFT,
            )
        )
        shift_started_at = open_working[0].entered_at
        if latest_ended_at is not None:
            shift_started_at = max(shift_started_at, latest_ended_at)

        session.add(
            UserShiftStateRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=shift_started_at,
                exited_at=shift_started_at,
                changed_by_id=None,
                reason=None,
                manually_recorded=False,
            )
        )
        auto_clocked_in = True
        logger.info(
            "worker_shift.auto_clock_in | workspace_id=%s user_id=%s entered_at=%s",
            workspace_id,
            user_id,
            shift_started_at.isoformat(),
        )

    if shift_started_at is None:
        shift_started_at = await session.scalar(
            select(UserShiftStateRecord.entered_at)
            .where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.state == UserShiftStateEnum.STARTED_SHIFT,
                UserShiftStateRecord.entered_at <= now,
            )
            .order_by(UserShiftStateRecord.entered_at.desc())
            .limit(1)
        )
    if shift_started_at is None:
        raise RuntimeError("Open worker shift is missing its STARTED_SHIFT marker.")

    open_declared = (
        await session.execute(
            select(UserDeclaredStateRecord)
            .where(
                UserDeclaredStateRecord.workspace_id == workspace_id,
                UserDeclaredStateRecord.user_id == user_id,
                UserDeclaredStateRecord.exited_at.is_(None),
                # F6: a declaration belongs only to the shift in which it was
                # entered. Ignore stale/corrupt open rows from an older shift.
                UserDeclaredStateRecord.entered_at >= shift_started_at,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    open_steps = await _load_open_steps(
        session,
        workspace_id,
        user_id,
        states=(TaskStepStateEnum.WORKING, TaskStepStateEnum.PAUSED),
        entered_at_or_after=shift_started_at,
    )
    open_working_count = sum(record.state is TaskStepStateEnum.WORKING for record in open_steps)
    open_paused = [record for record in open_steps if record.state is TaskStepStateEnum.PAUSED]
    open_declared_count = int(open_declared is not None)
    target = derive_target_state(
        open_working_count,
        open_declared_count,
        len(open_paused),
    )
    declared_is_source = open_working_count == 0 and open_declared is not None

    declared_closed = False
    if target is UserShiftStateEnum.WORKING and open_declared is not None:
        open_declared.exited_at = now
        open_declared.closed_by_id = None
        declared_closed = True
        logger.info(
            "worker_shift.reconcile_declared_close | "
            "workspace_id=%s user_id=%s declared_record_id=%s exited_at=%s",
            workspace_id,
            user_id,
            open_declared.client_id,
            now.isoformat(),
        )

    reason = None
    transition_reason = None
    manually_recorded = False
    if declared_is_source:
        reason = open_declared.pause_reason_id
        # A declaration carries both: the catalog row the worker chose, and the typed
        # transition saying this segment is a declaration projection (T3 — the declared
        # table has no column of its own).
        transition_reason = TransitionReasonEnum.WORKER_DECLARED_STATE.value
        manually_recorded = True
    elif target is UserShiftStateEnum.IN_PAUSE:
        # Both representations are copied from the owning step record. A system auto-pause
        # carries no catalog id, so guarding this on `pause_reason_id is not None` would
        # drop its transition and project the pause as unattributed.
        reason = open_paused[0].pause_reason_id
        transition_reason = open_paused[0].transition_reason

    current_is_declared_projection = (
        current is not None
        and current.state is UserShiftStateEnum.IN_PAUSE
        and current.manually_recorded
        and current.changed_by_id is None
    )
    declared_projection_involved = declared_is_source or current_is_declared_projection
    if (
        current is not None
        and current.state is target
        and (
            target is not UserShiftStateEnum.IN_PAUSE
            or not declared_projection_involved
            or (
                current.reason == reason
                and current.transition_reason == transition_reason
                and current.manually_recorded is manually_recorded
            )
        )
    ):
        return ShiftReconcileOutcome(changed=declared_closed, state=current.state)

    transition_from = current.state if current is not None else UserShiftStateEnum.STARTED_SHIFT
    assert is_valid_shift_state_transition(transition_from, target)

    if current is not None:
        current.exited_at = now

    session.add(
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            state=target,
            entered_at=now,
            exited_at=None,
            changed_by_id=None,
            reason=reason,
            transition_reason=transition_reason,
            manually_recorded=manually_recorded,
        )
    )
    logger.info(
        "worker_shift.reconcile_transition | workspace_id=%s user_id=%s from_state=%s to_state=%s",
        workspace_id,
        user_id,
        transition_from.value,
        target.value,
    )
    return ShiftReconcileOutcome(
        changed=True,
        state=target,
        auto_clocked_in=auto_clocked_in,
    )


async def reconcile_worker_shift_state(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    now: datetime,
) -> ShiftReconcileOutcome:
    for attempt in range(2):
        try:
            async with session.begin_nested():
                outcome = await _reconcile_once(session, workspace_id, user_id, now)
                await session.flush()
            return outcome
        except IntegrityError:
            if attempt == 1:
                raise
            logger.warning(
                "worker_shift.reconcile_unique_retry | workspace_id=%s user_id=%s",
                workspace_id,
                user_id,
            )

    raise AssertionError("unreachable")
