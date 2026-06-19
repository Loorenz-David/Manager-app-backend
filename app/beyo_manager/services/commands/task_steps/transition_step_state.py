"""CMD-12: Atomic step state machine driver with StepStateRecord management and outbox event."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.execution.payloads.step_transition import StepTransitionPayload
from beyo_manager.domain.schedulers.enums import (
    DelayedSchedulerTypeEnum,
    SchedulerOriginSourceEnum,
    SchedulerStateEnum,
)
from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES, TERMINAL_TASK_STATES
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum
from beyo_manager.domain.tasks.serializers import serialize_step_state_record_light
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps._user_working_record import fetch_open_user_working_record
from beyo_manager.services.commands.task_steps.requests import parse_transition_step_state_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.execution.task_factory import create_instant_task


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
    old_task_state = None
    auto_paused_step: TaskStep | None = None

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
        if step.state in TERMINAL_STEP_STATES:
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

        # Resolve credit user early — needed for both auto-pause enforcement and outbox event.
        credited_user_id = _resolve_transition_credit_user_id(ctx, request)
        # Deduplicated: covers records created by the performer AND by the credited worker,
        # so the auto-pause fires correctly when a manager acts on behalf of a worker.
        effective_user_ids = list({ctx.user_id, credited_user_id})

        # COMPLETED transitions are deferred to a delayed scheduler to provide an undo window.
        # NOTE: Undo-window scheduling is temporarily disabled — COMPLETED falls through to the
        # normal transition path below. Keep this block intact for future re-enablement.
        # if request.new_state == TaskStepStateEnum.COMPLETED:
        #     existing_scheduler_result = await ctx.session.execute(
        #         select(DelayedScheduler).where(
        #             DelayedScheduler.event_client_id == step.client_id,
        #             DelayedScheduler.type == DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION,
        #             DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
        #         )
        #     )
        #     existing_scheduler = existing_scheduler_result.scalar_one_or_none()
        #     if existing_scheduler is not None:
        #         raise ConflictError("A pending completion already exists for this step.")
        #
        #     completion_delay_seconds = 5
        #     scheduled_for = now + timedelta(seconds=completion_delay_seconds)
        #
        #     scheduler = DelayedScheduler(
        #         type=DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION,
        #         state=SchedulerStateEnum.ACTIVE,
        #         origin_source=SchedulerOriginSourceEnum.COMMAND,
        #         event_client_id=step.client_id,
        #         scheduled_for=scheduled_for,
        #         payload_snapshot={
        #             "step_id": step.client_id,
        #             "task_id": task.client_id,
        #             "workspace_id": ctx.workspace_id,
        #             "completion_requested_at": now.isoformat(),
        #             "performed_by_user_id": ctx.user_id,
        #             "credited_user_id": credited_user_id,
        #             "reason": request.reason.value if request.reason else None,
        #             "description": request.description,
        #         },
        #     )
        #     ctx.session.add(scheduler)
        #     await ctx.session.flush()
        #
        #     return {
        #         "pending_completion_id": scheduler.client_id,
        #         "expires_at": scheduled_for.isoformat(),
        #     }

        # 4. Auto-pause any other WORKING record for this user (one-active-step rule)
        if request.new_state == TaskStepStateEnum.WORKING:
            conflicting_record, conflicting_step = await fetch_open_user_working_record(
                ctx.session, effective_user_ids, ctx.workspace_id, exclude_step_id=step.client_id
            )
            if conflicting_record is not None:
                conflicting_closing_entered_at = conflicting_record.entered_at
                conflicting_record.exited_at = now

                # Build description referencing the new step's item (article_number or SKU fallback)
                auto_pause_description: str | None = None
                primary_task_item_result = await ctx.session.execute(
                    select(TaskItem).where(
                        TaskItem.workspace_id == ctx.workspace_id,
                        TaskItem.task_id == task.client_id,
                        TaskItem.removed_at.is_(None),
                        TaskItem.role == TaskItemRoleEnum.PRIMARY,
                    )
                )
                primary_task_item = primary_task_item_result.scalar_one_or_none()
                if primary_task_item is not None:
                    item_result = await ctx.session.execute(
                        select(Item).where(
                            Item.workspace_id == ctx.workspace_id,
                            Item.client_id == primary_task_item.item_id,
                            Item.is_deleted.is_(False),
                        )
                    )
                    new_item = item_result.scalar_one_or_none()
                    if new_item is not None:
                        identifier = new_item.article_number or new_item.sku
                        if identifier:
                            auto_pause_description = f"started working with {identifier}"

                auto_pause_record = StepStateRecord(
                    workspace_id=ctx.workspace_id,
                    step_id=conflicting_step.client_id,
                    state=TaskStepStateEnum.PAUSED,
                    reason=StepEventReasonEnum.PAUSE_OTHER_TASK_PRIORITY,
                    description=auto_pause_description,
                    entered_at=now,
                    exited_at=None,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(auto_pause_record)
                await ctx.session.flush()

                conflicting_step.state = TaskStepStateEnum.PAUSED
                conflicting_step.latest_state_record_id = auto_pause_record.client_id
                conflicting_step.updated_at = now
                conflicting_step.updated_by_id = ctx.user_id

                auto_paused_step = conflicting_step

                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.PROCESS_STEP_TRANSITION,
                    payload=asdict(StepTransitionPayload(
                        step_id=conflicting_step.client_id,
                        task_id=conflicting_step.task_id,
                        workspace_id=ctx.workspace_id,
                        closing_record_id=conflicting_record.client_id,
                        closing_state=TaskStepStateEnum.WORKING.value,
                        new_state=TaskStepStateEnum.PAUSED.value,
                        performed_by_user_id=ctx.user_id,
                        credited_user_id=ctx.user_id,
                        assigned_worker_id=conflicting_step.assigned_worker_id,
                        working_section_id=conflicting_step.working_section_id,
                        working_section_name_snapshot=conflicting_step.working_section_name_snapshot,
                        entered_at=conflicting_closing_entered_at.isoformat(),
                        exited_at=now.isoformat(),
                        step_task_id=conflicting_step.task_id,
                    )),
                )

        # 5. Close current open StepStateRecord
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

        # 6. Open new StepStateRecord
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
        if request.new_state in TERMINAL_STEP_STATES:
            step.closed_at = now

        # 7. Task state side effects
        if request.new_state == TaskStepStateEnum.WORKING and task.state == TaskStateEnum.ASSIGNED:
            task.state = TaskStateEnum.WORKING
            task.updated_at = now
            task.updated_by_id = ctx.user_id

        if request.new_state in TERMINAL_STEP_STATES:
            all_steps_result = await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task.client_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            all_steps = all_steps_result.scalars().all()
            if all_steps and all(s.state in TERMINAL_STEP_STATES for s in all_steps):
                if task.state not in TERMINAL_TASK_STATES:
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
    if auto_paused_step is not None:
        pending_events.append(
            build_workspace_event(auto_paused_step, "task:step-state-changed", extra={"new_state": TaskStepStateEnum.PAUSED.value})
        )
    if task.state != old_task_state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
    return {
        "step_id": step.client_id,
        "new_state": request.new_state.value,
        "last_state_record": serialize_step_state_record_light(new_record),
    }
