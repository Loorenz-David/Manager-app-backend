"""Force a task to READY by administratively skipping every step still open.

**Why this is not a `task.state = READY` write.** The organic route into ``READY`` is
every step reaching a terminal state, evaluated by ``maybe_evaluate_task_ready`` — and
that transition owns real side effects: the post-handling and customer-coordination
instances are created there, via ``reconcile_task_side_effects``. A command that set the
column directly would land on ``READY`` without them, and the natural path that would
have created them later short-circuits on ``task.state == READY``, so they would never
appear. This command therefore drives the *steps* and lets the existing predicate make
the call, exactly as a worker closing the last step does. One entry point into READY,
one copy of the policy.

**Why SKIPPED and not COMPLETED.** A forced close is not throughput. ``COMPLETED``
credits the closer in worker stats and the completed-count backfills (see
``process_step_transition``, which gates its completion bookkeeping on that state);
``SKIPPED`` is equally terminal, satisfies the readiness predicate identically, and is
already treated as terminal by the worker-facing views. The steps did not happen — the
record must not claim they did.

**Why a private transition map.** ``_ALLOWED_TRANSITIONS`` is shared with the
worker-facing single and batch step endpoints. Adding ``-> SKIPPED`` edges there would
hand every WORKER the ability to skip steps through the normal route, which is the exact
authority this endpoint exists to gate. ``_apply_step_transition`` validates nothing —
its docstring makes preconditions the caller's job — so each driver owning its own
legality map is the established contract here, not a workaround.

DRIFT NOTE: this is one of several drivers over ``_apply_step_transition`` — that
core's docstring carries the canonical list. (Note ``transition_step_state`` is NOT
among them: it owns its own hand-mirrored copy of the body and never calls the core.)
It deliberately uses the narrowest possible slice — a single hop to a terminal state,
never to ``WORKING`` — so the auto-pause guard and the completion cascade in that core
are both unreachable from here. That narrowness does not exempt it: changes to record
close/open, the PROCESS_STEP_TRANSITION outbox, or the task side-effect hooks reach
this driver like any other, and must also be evaluated against the two hand-mirrored
copies of the body named in the core's docstring.
"""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TERMINAL_TASK_STATES
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.domain.tasks.notification_targets import resolve_task_notification_targets
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.task_steps._step_transition_core import _apply_step_transition
from beyo_manager.services.commands.tasks._task_state_transitions import maybe_evaluate_task_ready
from beyo_manager.services.commands.tasks.requests import parse_force_task_ready_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


# Legal sources for an administrative skip. Every non-terminal step state is here,
# including BLOCKED — which `_ALLOWED_TRANSITIONS` leaves as a dead end with no exit at
# all. Nothing writes BLOCKED today, so this is latent rather than active, but a task
# holding one must not become unforceable the day something starts.
_FORCE_READY_TRANSITIONS: dict[TaskStepStateEnum, set[TaskStepStateEnum]] = {
    TaskStepStateEnum.PENDING: {TaskStepStateEnum.SKIPPED},
    TaskStepStateEnum.WORKING: {TaskStepStateEnum.SKIPPED},
    TaskStepStateEnum.PAUSED: {TaskStepStateEnum.SKIPPED},
    TaskStepStateEnum.BLOCKED: {TaskStepStateEnum.SKIPPED},
}


async def force_task_ready(ctx: ServiceContext) -> dict:
    """Skip every open step, then let `maybe_evaluate_task_ready` flip the task."""
    request = parse_force_task_ready_request(ctx.incoming_data)

    step_changed_items: list[dict] = []
    skipped_step_ids: list[str] = []
    task: Task

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        task = await ctx.session.scalar(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.client_id,
                Task.is_deleted.is_(False),
            )
        )
        if task is None:
            raise NotFound("Task not found.")
        if task.state in TERMINAL_TASK_STATES:
            raise ConflictError("Task is already in a terminal state.")
        if task.state == TaskStateEnum.READY:
            raise ConflictError("Task is already ready.")

        original_state = task.state.value

        # Same `is_deleted` filter the readiness predicate uses, so the set this command
        # closes is exactly the set that predicate will re-check.
        steps = (
            await ctx.session.execute(
                select(TaskStep)
                .where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
                .order_by(TaskStep.sequence_order, TaskStep.client_id)
            )
        ).scalars().all()
        open_steps = [step for step in steps if step.state not in TERMINAL_STEP_STATES]

        # --- Validate everything before mutating anything (all-or-nothing) ---
        errors = [
            f"{step.client_id}: cannot skip a step in state {step.state.value}."
            for step in open_steps
            if TaskStepStateEnum.SKIPPED not in _FORCE_READY_TRANSITIONS.get(step.state, set())
        ]
        if errors:
            raise ValidationError("Cannot force this task ready — " + " ".join(errors))

        open_records = (
            (
                await ctx.session.execute(
                    select(StepStateRecord).where(
                        StepStateRecord.workspace_id == ctx.workspace_id,
                        StepStateRecord.step_id.in_([step.client_id for step in open_steps]),
                        StepStateRecord.exited_at.is_(None),
                    )
                )
            ).scalars().all()
            if open_steps
            else []
        )
        open_record_by_step = {record.step_id: record for record in open_records}

        missing = [step.client_id for step in open_steps if step.client_id not in open_record_by_step]
        if missing:
            raise ValidationError(
                "Cannot force this task ready — no open state record for: " + ", ".join(missing)
            )

        # --- Apply one terminal hop per open step ---
        for step in open_steps:
            closing_record = open_record_by_step[step.client_id]
            applied = await _apply_step_transition(
                ctx,
                step,
                task,
                closing_record,
                new_state=TaskStepStateEnum.SKIPPED,
                pause_reason_id=None,
                description=request.reason,
                # Credit the worker whose time is being closed, NOT the manager pressing
                # the button. A WORKING/PAUSED record carries real accrued seconds and
                # the analytics worker recomputes them against `credited_user_id`; using
                # `ctx.user_id` would move another person's hours onto the manager.
                credited_user_id=closing_record.credited_user_id or ctx.user_id,
                now=now,
                transition_reason=TransitionReasonEnum.FORCED_READY.value,
                mark_closing_record_inaccurate=request.mark_inaccurate,
            )
            step_changed_items.append(applied.step_changed_item)
            skipped_step_ids.append(step.client_id)

        # With at least one step, the final `_apply_step_transition` above already ran
        # the predicate and flipped the task. This call is what covers the stepless task,
        # and no-ops otherwise (it early-returns once the state is READY) — so both cases
        # reach READY through the same function and get the same side effects.
        await maybe_evaluate_task_ready(
            ctx.session,
            task,
            workspace_id=ctx.workspace_id,
            now=now,
            updated_by_id=ctx.user_id,
            allow_stepless=True,
        )
        if task.state != TaskStateEnum.READY:
            # Unreachable via the paths above; a guard against a future change to the
            # predicate silently turning this endpoint into a no-op that reports success.
            raise ConflictError("Task could not be marked ready.")

        username = ctx.identity.get("username")
        actor = username or "Someone"
        await _create_history_record_in_session(
            session=ctx.session,
            entity_type=HistoryRecordEntityTypeEnum.TASK,
            entity_client_id=task.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            # The step-driven route into READY writes no history record, so this is the
            # only audit trail an override leaves. It carries the justification and the
            # blast radius, not just the resulting state.
            description=(
                f"{actor} forced task to ready, skipping {len(skipped_step_ids)} open step(s)"
                f" — {request.reason}"
            ),
            field_name="state",
            from_value={"state": original_state},
            to_value={"state": TaskStateEnum.READY.value},
            created_by_id=ctx.user_id,
            username_snapshot=username,
        )

        # One task-level notification. The per-step recipients `_apply_step_transition`
        # resolved are deliberately discarded: a forced close is one administrative act,
        # not N step updates, and pinging every step watcher would say otherwise.
        task_pin_user_ids = list(
            await resolve_task_notification_targets(
                ctx.session,
                ctx.workspace_id,
                task.client_id,
                task.created_by_id,
                ctx.user_id,
                {"state": task.state.value},
            )
        )
        if task_pin_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(
                    NotificationPayload(
                        notification_type="task_state_changed",
                        user_ids=task_pin_user_ids,
                        title=f"Task #{task.task_scalar_id} marked ready",
                        body=f"#{task.task_scalar_id} · forced by {actor}",
                        entity_type="task",
                        entity_client_id=task.client_id,
                        exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                    )
                ),
            )

    pending_events: list = []
    if step_changed_items:
        pending_events.append(
            BatchWorkspaceEvent(
                event_name="task:step-state-changed",
                workspace_id=ctx.workspace_id,
                items=step_changed_items,
            )
        )
    pending_events.append(
        build_workspace_event(task, "task:state-changed", extra={"new_state": TaskStateEnum.READY.value})
    )
    await event_bus.dispatch(pending_events)

    return {
        "client_id": task.client_id,
        "state": TaskStateEnum.READY.value,
        "skipped_step_ids": skipped_step_ids,
    }
