"""Pause every working step of a task because the task itself stopped existing.

`delete_task` calls this so a deleted task never leaves a step WORKING: nothing else can
close that record while the task is deleted (clock-out and every step command skip
deleted tasks), so the open interval would keep accruing work time for as long as the
task stays deleted. `restore_task` calls it for tasks deleted before that rule existed,
closing the stale interval at the moment of deletion.

Runs inside the caller's transaction and dispatches nothing: the caller broadcasts the
returned step ids with `emit_steps_paused` once it has committed.
"""

from datetime import datetime

from sqlalchemy import and_, select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps._step_transition_core import (
    _apply_step_transition,
)
from beyo_manager.services.context import ServiceContext


TASK_DELETED_DESCRIPTION = "task deleted"


async def pause_task_working_steps_in_session(
    ctx: ServiceContext,
    task: Task,
    *,
    paused_at: datetime,
) -> list[str]:
    """Pause the task's open WORKING steps at `paused_at`; returns their ids.

    `paused_at` is clamped to each record's own start, so a pause can never end a working
    interval before it began.
    """
    rows = (
        await ctx.session.execute(
            select(StepStateRecord, TaskStep)
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
                StepStateRecord.exited_at.is_(None),
                StepStateRecord.state == TaskStepStateEnum.WORKING,
                TaskStep.task_id == task.client_id,
            )
            .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
            .with_for_update(of=StepStateRecord)
        )
    ).all()

    paused_step_ids: list[str] = []
    for closing_record, step in rows:
        await _apply_step_transition(
            ctx,
            step,
            task,
            closing_record,
            new_state=TaskStepStateEnum.PAUSED,
            # System transition, like a case pause: never a workspace pause reason.
            pause_reason_id=None,
            transition_reason=TransitionReasonEnum.TASK_DELETED.value,
            description=TASK_DELETED_DESCRIPTION,
            # The interrupted work stays with the worker who was doing it, not with the
            # manager who deleted the task.
            credited_user_id=(
                closing_record.credited_user_id
                or closing_record.created_by_id
                or ctx.user_id
            ),
            now=max(paused_at, closing_record.entered_at),
        )
        paused_step_ids.append(step.client_id)
    return paused_step_ids
