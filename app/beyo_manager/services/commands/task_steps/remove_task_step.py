from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness
from beyo_manager.services.commands.task_steps.requests import parse_remove_task_step_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

_TERMINAL_STEP_STATES = frozenset({
    TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED,
    TaskStepStateEnum.FAILED,
    TaskStepStateEnum.CANCELLED,
})


async def remove_task_step(ctx: ServiceContext) -> dict:
    request = parse_remove_task_step_request(ctx.incoming_data)
    readiness_changes: list[tuple] = []
    old_task_state_rts = None

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        # 1. Fetch step
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == request.step_id,
                TaskStep.task_id == request.task_id,
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")
        if step.is_deleted:
            raise ConflictError("Task step is already deleted.")

        # 2. Fetch task
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")
        old_task_state_rts = task.state

        # 3. Set step state to SKIPPED (terminal)
        step.state = TaskStepStateEnum.SKIPPED
        step.closed_at = now
        step.updated_at = now
        step.updated_by_id = ctx.user_id

        # 4. Close the open StepStateRecord
        open_record_result = await ctx.session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.step_id == step.client_id,
                StepStateRecord.exited_at.is_(None),
            )
        )
        open_record = open_record_result.scalar_one_or_none()
        if open_record is not None:
            open_record.exited_at = now

        # 5. Soft-delete the step
        step.is_deleted = True
        step.deleted_at = now
        step.deleted_by_id = ctx.user_id

        # 6a. Soft-remove active edges where this step is the dependent
        dependent_edges_result = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.dependent_step_id == step.client_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        for edge in dependent_edges_result.scalars().all():
            edge.removed_at = now
            edge.removed_by_id = ctx.user_id

        # 6b. Soft-remove active edges where this step is a prerequisite
        #     and recalculate readiness for the dependent steps
        prerequisite_edges_result = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.prerequisite_step_id == step.client_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        for edge in prerequisite_edges_result.scalars().all():
            edge.removed_at = now
            edge.removed_by_id = ctx.user_id

            affected_step_result = await ctx.session.execute(
                select(TaskStep).where(
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.client_id == edge.dependent_step_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
            affected_step = affected_step_result.scalar_one_or_none()
            if affected_step is not None:
                old_aff_readiness = affected_step.readiness_status
                if affected_step.total_dependencies > 0:
                    affected_step.total_dependencies -= 1
                if affected_step.completed_dependencies > affected_step.total_dependencies:
                    affected_step.completed_dependencies = affected_step.total_dependencies
                recalculate_readiness(affected_step)
                readiness_changes.append((affected_step, old_aff_readiness))

        # 7. Check remaining non-deleted steps (exclude the just-deleted step)
        remaining_steps_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == task.client_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        remaining_steps = [
            s for s in remaining_steps_result.scalars().all()
            if s.client_id != step.client_id
        ]

        if len(remaining_steps) == 0:
            # Last step removed → task reverts to PENDING
            task.state = TaskStateEnum.PENDING
            task.updated_at = now
            task.updated_by_id = ctx.user_id
        elif all(s.state in _TERMINAL_STEP_STATES for s in remaining_steps):
            # All remaining steps are terminal → task → READY
            task.state = TaskStateEnum.READY
            task.updated_at = now
            task.updated_by_id = ctx.user_id

        await ctx.session.flush()

    pending_events: list = [
        build_workspace_event(task, "task:updated"),
    ]
    for affected_step, old_aff_readiness in readiness_changes:
        if affected_step.readiness_status != old_aff_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=affected_step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": affected_step.readiness_status.value},
            ))
    if task.state != old_task_state_rts:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)
    return {"step_id": step.client_id}
