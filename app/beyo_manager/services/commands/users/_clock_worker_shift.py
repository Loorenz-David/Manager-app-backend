from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.services.commands.task_steps._step_transition_core import _apply_step_transition
from beyo_manager.services.context import ServiceContext


def _credited_user_id():
    return func.coalesce(StepStateRecord.credited_user_id, StepStateRecord.created_by_id)


async def load_open_worker_shift_for_update(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> UserShiftStateRecord | None:
    return (
        await session.execute(
            select(UserShiftStateRecord)
            .where(
                UserShiftStateRecord.workspace_id == workspace_id,
                UserShiftStateRecord.user_id == user_id,
                UserShiftStateRecord.exited_at.is_(None),
            )
            .with_for_update()
        )
    ).scalar_one_or_none()


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
) -> int:
    current = await load_open_worker_shift_for_update(session, workspace_id, user_id)
    if current is None:
        raise ConflictError("Worker is not clocked in.")

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
            new_state=TaskStepStateEnum.ENDED_SHIFT,
            reason=StepEventReasonEnum.PAUSE_ENDED_SHIFT,
            description=None,
            credited_user_id=user_id,
            now=clock_out_at,
        )

    current.exited_at = clock_out_at
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
    return len(open_working_rows)
