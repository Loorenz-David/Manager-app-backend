"""Pause a task's working steps when a case is raised on it.

Raising a case means work has stopped. Without this the timeline shows a worker still
working while the problem is being discussed.

**Why a `transition_reason` and not a `pause_reason_id`.** The worker does not pick "case
created" from the pause sheet — the *system* stops the step because a case was raised. So
the record carries `transition_reason = case_created` and `pause_reason_id = NULL`, and
therefore works in a workspace holding zero `pause_reasons` rows. Reviving the retired
`pause_case_created` catalog row would put a mandatory system behaviour back on top of a
workspace-editable row that may not exist.

**Why it cannot fail the case.** The case is the user's intent; the pause is a side effect.
This module owns its own transaction and never raises — the same reasoning that puts
clock-out analytics outside the clock-out write transaction. A failure here logs and leaves
a created case behind, which is the right trade: a case with a still-running step is a
wrong timeline, a lost case is a lost conversation.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, select

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps._step_transition_core import (
    _apply_step_transition,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events.worker_shift_realtime import emit_steps_paused


logger = logging.getLogger(__name__)


def build_case_created_description(type_label: str | None) -> str:
    """`transition_reason` says what class of thing happened; the description says which
    one — the same split as the task-switch auto-pause's "started working with {sku}".

    `type_label` is the case type's name when the case carries a `case_type_id`
    (`create_case.py` resolves it), and free text when the caller supplied one instead.
    Both `case_type_id` and `type_label` are nullable, so the bare form is a real case and
    not a defensive branch.
    """
    label = (type_label or "").strip()
    return f"case created: {label}" if label else "case created"


async def _load_open_working_step_rows_for_task(
    session,
    workspace_id: str,
    task_id: str,
):
    """Every step of this task with an open WORKING record.

    Scoped by task rather than by worker: a case links to the task, and a task may have
    several steps WORKING at once under `allows_batch_working`. Leaving a sibling step
    running would contradict the reason for pausing at all.

    Locked, and shaped as `(record, step, task)`, mirroring
    `_clock_worker_shift._load_open_working_step_rows`.
    """
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
            TaskStep.task_id == task_id,
        )
        .order_by(StepStateRecord.entered_at, StepStateRecord.client_id)
        .with_for_update()
    )
    return list(result.all())


async def pause_task_working_steps_for_case(
    ctx: ServiceContext,
    *,
    entity_type: CaseLinkEntityTypeEnum | None,
    entity_client_id: str | None,
    case_client_id: str,
    type_label: str | None,
) -> int:
    """Pause every working step of the task this case was raised on. Returns how many.

    Never raises: call it after the case has committed. Closing the case does **not**
    resume the step — a case closing does not mean the worker is back at the bench, and
    auto-resuming would show someone working who is not there.
    """
    # A case links to a TASK or to a CUSTOMER, never to a step. A customer has no task and
    # therefore no step: skipped here, explicitly, so this reads as decided rather than as
    # something that happens to fall out of a null check downstream.
    if entity_type is CaseLinkEntityTypeEnum.CUSTOMER:
        return 0
    if entity_type is not CaseLinkEntityTypeEnum.TASK or entity_client_id is None:
        return 0

    try:
        async with maybe_begin(ctx.session):
            open_working_rows = await _load_open_working_step_rows_for_task(
                ctx.session, ctx.workspace_id, entity_client_id
            )
            if not open_working_rows:
                return 0

            now = datetime.now(timezone.utc)
            description = build_case_created_description(type_label)
            for closing_record, step, task in open_working_rows:
                await _apply_step_transition(
                    ctx,
                    step,
                    task,
                    # The step's already-open record, closed by the core in the same
                    # transaction that opens the pause. The partial unique index on
                    # `(workspace_id, step_id) WHERE exited_at IS NULL` rejects a second
                    # open record, so this is not optional.
                    closing_record,
                    new_state=TaskStepStateEnum.PAUSED,
                    # System transition: typed from the code-owned vocabulary, never
                    # resolved from the workspace catalog, so this works in a workspace
                    # holding zero pause reasons.
                    pause_reason_id=None,
                    transition_reason=TransitionReasonEnum.CASE_CREATED.value,
                    description=description,
                    # Credited to whoever the interrupted work belonged to, not to the
                    # case creator — a manager raising a case on a worker's task must not
                    # acquire a pause segment on their own shift timeline. Falls back to
                    # the actor only when the closed record names nobody.
                    credited_user_id=(
                        closing_record.credited_user_id
                        or closing_record.created_by_id
                        or ctx.user_id
                    ),
                    now=now,
                )

            paused_step_ids = [step.client_id for _, step, _ in open_working_rows]
            logger.info(
                "cases.case_created_step_pause | "
                "workspace_id=%s case_id=%s task_id=%s actor_id=%s paused_steps=%s",
                ctx.workspace_id,
                case_client_id,
                entity_client_id,
                ctx.user_id,
                len(open_working_rows),
            )
    except Exception:
        logger.exception(
            "cases.case_created_step_pause_failed | "
            "workspace_id=%s case_id=%s task_id=%s actor_id=%s",
            ctx.workspace_id,
            case_client_id,
            entity_client_id,
            ctx.user_id,
        )
        return 0

    # Broadcast after the pause has committed. This one is not optional the way clock-out's
    # is: a manager raised the case, and the worker whose step just stopped is somewhere
    # else in the building with a cache that still says `working`. The workers app guards
    # its own transitions on that cache, so without the event their next action fails
    # against a step the server already paused.
    await emit_steps_paused(ctx.workspace_id, paused_step_ids)
    return len(paused_step_ids)
