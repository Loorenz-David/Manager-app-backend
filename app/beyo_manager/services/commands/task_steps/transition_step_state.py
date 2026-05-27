"""CMD-12: Atomic step state machine driver with StepStateRecord management and outbox event."""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness
from beyo_manager.services.commands.task_steps.requests import parse_transition_step_state_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.services.infra.execution.task_factory import create_instant_task


_TERMINAL_STEP_STATES = frozenset({
    TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED,
    TaskStepStateEnum.FAILED,
    TaskStepStateEnum.CANCELLED,
})

_TERMINAL_TASK_STATES = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})

_ALLOWED_TRANSITIONS: dict[TaskStepStateEnum, set[TaskStepStateEnum]] = {
    TaskStepStateEnum.PENDING:      {TaskStepStateEnum.WORKING},
    TaskStepStateEnum.WORKING:      {
        TaskStepStateEnum.PAUSED, TaskStepStateEnum.ENDED_SHIFT,
        TaskStepStateEnum.COMPLETED, TaskStepStateEnum.FAILED,
        TaskStepStateEnum.CANCELLED
    },
    TaskStepStateEnum.PAUSED:       {
        TaskStepStateEnum.WORKING, TaskStepStateEnum.ENDED_SHIFT,
        TaskStepStateEnum.FAILED, TaskStepStateEnum.CANCELLED
    },
    TaskStepStateEnum.ENDED_SHIFT:  {
        TaskStepStateEnum.WORKING, TaskStepStateEnum.FAILED,
        TaskStepStateEnum.CANCELLED
    },
    TaskStepStateEnum.COMPLETED:    set(),
    TaskStepStateEnum.SKIPPED:      set(),
    TaskStepStateEnum.FAILED:       set(),
    TaskStepStateEnum.CANCELLED:    set(),
    TaskStepStateEnum.BLOCKED:      set(),
}


async def _dispatch_section_side_effects(
    step: TaskStep,
    new_state: TaskStepStateEnum,
    session,
) -> None:
    """Extension point for working-section-specific side effects (notifications, socket events).
    
    TODO: Implement when side-effect interface is designed.
    Do not add logic here until requirements are finalized.
    """
    pass


def _resolve_transition_credit_user_id(ctx: ServiceContext, request) -> str:
    return request.credited_user_id or ctx.user_id


async def transition_step_state(ctx: ServiceContext) -> dict:
    """Atomically close current StepStateRecord and open a new one; apply task side effects; publish outbox."""
    request = parse_transition_step_state_request(ctx.incoming_data)
    readiness_changes: list[tuple] = []
    old_task_state = None

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        # 1. Fetch step (scope: task_id + workspace_id)
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == request.step_id,
                TaskStep.task_id == request.task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        # 2. Validate transition
        if step.state in _TERMINAL_STEP_STATES:
            raise ConflictError(
                f"Step is in terminal state {step.state.value} — no further transitions allowed."
            )
        allowed = _ALLOWED_TRANSITIONS.get(step.state, set())
        if request.new_state not in allowed:
            raise ValidationError(
                f"Cannot transition step from {step.state.value} to {request.new_state.value}."
            )

        # 3. Fetch task
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == step.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")
        old_task_state = task.state

        # 4. Close current open StepStateRecord
        open_record_result = await ctx.session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.step_id == step.client_id,
                StepStateRecord.exited_at.is_(None),
            )
        )
        closing_record = open_record_result.scalar_one_or_none()
        if closing_record is None:
            raise ConflictError("No open state record found for this step.")
        closing_record.exited_at = now
        closing_state = closing_record.state  # save before flush
        closing_entered_at = closing_record.entered_at

        # 5. Open new StepStateRecord
        new_record = StepStateRecord(
            workspace_id=ctx.workspace_id,
            step_id=step.client_id,
            state=request.new_state,
            reason=request.reason,
            description=request.description,
            entered_at=now,
            exited_at=None,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(new_record)
        await ctx.session.flush()  # assign new_record.client_id

        # 6. Update step state and latest pointer (circular FK — must be in same transaction)
        step.state = request.new_state
        step.latest_state_record_id = new_record.client_id
        step.updated_at = now
        step.updated_by_id = ctx.user_id

        # If entering a terminal state, set closed_at
        if request.new_state in _TERMINAL_STEP_STATES:
            step.closed_at = now

        # 7. Task state side effects
        if request.new_state == TaskStepStateEnum.WORKING and task.state == TaskStateEnum.ASSIGNED:
            task.state = TaskStateEnum.WORKING
            task.updated_at = now
            task.updated_by_id = ctx.user_id

        credited_user_id = _resolve_transition_credit_user_id(ctx, request)

        if request.new_state == TaskStepStateEnum.COMPLETED:
            # Recalculate readiness on all steps that depended on THIS step
            dependent_edges_result = await ctx.session.execute(
                select(TaskStepDependency).where(
                    TaskStepDependency.workspace_id == ctx.workspace_id,
                    TaskStepDependency.prerequisite_step_id == step.client_id,
                    TaskStepDependency.removed_at.is_(None),
                )
            )
            for edge in dependent_edges_result.scalars().all():
                dep_step_result = await ctx.session.execute(
                    select(TaskStep).where(
                        TaskStep.workspace_id == ctx.workspace_id,
                        TaskStep.client_id == edge.dependent_step_id,
                        TaskStep.is_deleted.is_(False),
                    )
                )
                dep_step = dep_step_result.scalar_one_or_none()
                if dep_step is not None:
                    old_dep_readiness = dep_step.readiness_status
                    dep_step.completed_dependencies += 1
                    recalculate_readiness(dep_step)
                    readiness_changes.append((dep_step, old_dep_readiness))

            # Check if all non-deleted steps are now terminal → task READY
            all_steps_result = await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            all_steps = all_steps_result.scalars().all()
            if all_steps and all(s.state in _TERMINAL_STEP_STATES for s in all_steps):
                if task.state not in _TERMINAL_TASK_STATES:
                    task.state = TaskStateEnum.READY
                    task.updated_at = now
                    task.updated_by_id = ctx.user_id

        # 8. Extension point for section-specific side effects (stub)
        await _dispatch_section_side_effects(step, request.new_state, ctx.session)

        # 9. Publish outbox event for analytics worker (atomic with domain write)
        payload = StepTransitionPayload(
            step_id=step.client_id,
            task_id=task.client_id,
            workspace_id=ctx.workspace_id,
            closing_record_id=closing_record.client_id,
            closing_state=closing_state.value,
            new_state=request.new_state.value,
            performed_by_user_id=ctx.user_id,
            credited_user_id=credited_user_id,
            assigned_worker_id=step.assigned_worker_id,
            working_section_id=step.working_section_id,
            working_section_name_snapshot=step.working_section_name_snapshot,
            entered_at=closing_entered_at.isoformat(),
            exited_at=now.isoformat(),
            step_task_id=task.client_id,
        )
        await create_instant_task(
            session=ctx.session,
            task_type=TaskType.PROCESS_STEP_TRANSITION,
            payload=asdict(payload),
        )

        step_pins_result = await ctx.session.execute(
            select(NotificationPin.user_id).where(
                NotificationPin.entity_type == "task_step",
                NotificationPin.entity_client_id == step.client_id,
            )
        )
        step_pin_user_ids = [
            uid for uid in step_pins_result.scalars().all()
            if uid != ctx.user_id
        ]
        if step_pin_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_step_state_changed",
                    user_ids=step_pin_user_ids,
                    title="Step state changed",
                    body="A step you are following has changed state.",
                    entity_type="task_step",
                    entity_client_id=step.client_id,
                    exclude_viewing=[{"entity_type": "task_step", "entity_client_id": step.client_id}],
                )),
            )

    pending_events: list = [
        build_workspace_event(step, "task:step-state-changed", extra={"new_state": request.new_state.value}),
    ]
    for dep_step, old_dep_readiness in readiness_changes:
        if dep_step.readiness_status != old_dep_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=dep_step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": dep_step.readiness_status.value},
            ))
    if task.state != old_task_state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
    return {"step_id": step.client_id, "new_state": request.new_state.value}
