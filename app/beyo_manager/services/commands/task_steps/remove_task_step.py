from datetime import datetime, timezone

from sqlalchemy import or_, select

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.domain.task_steps.readiness import recalculate_readiness
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.tasks._task_state_transitions import maybe_evaluate_task_ready
from beyo_manager.services.commands.task_steps.requests import (
    parse_remove_task_step_request,
    parse_remove_task_steps_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent


def _dedupe_step_ids(step_ids: list[str]) -> list[str]:
    unique_step_ids: list[str] = []
    seen: set[str] = set()

    for step_id in step_ids:
        if step_id in seen:
            raise ConflictError("Duplicate step_id provided in step batch.")
        seen.add(step_id)
        unique_step_ids.append(step_id)

    return unique_step_ids


def _count_removed_prerequisite_edges(
    edges: list[TaskStepDependency],
    removed_step_ids: set[str],
    completed_removed_step_ids: set[str],
) -> dict[str, tuple[int, int]]:
    counts_by_dependent_step_id: dict[str, tuple[int, int]] = {}

    for edge in edges:
        if edge.prerequisite_step_id not in removed_step_ids:
            continue
        if edge.dependent_step_id in removed_step_ids:
            continue

        removed_total, removed_completed = counts_by_dependent_step_id.get(
            edge.dependent_step_id,
            (0, 0),
        )
        removed_total += 1
        if edge.prerequisite_step_id in completed_removed_step_ids:
            removed_completed += 1

        counts_by_dependent_step_id[edge.dependent_step_id] = (
            removed_total,
            removed_completed,
        )

    return counts_by_dependent_step_id


def _apply_removed_dependency_counts(
    step: TaskStep,
    *,
    removed_total: int,
    removed_completed: int,
) -> None:
    step.total_dependencies = max(step.total_dependencies - removed_total, 0)
    step.completed_dependencies = max(step.completed_dependencies - removed_completed, 0)
    if step.completed_dependencies > step.total_dependencies:
        step.completed_dependencies = step.total_dependencies
    recalculate_readiness(step)


async def _remove_task_steps_in_session(
    *,
    ctx: ServiceContext,
    task_id: str,
    step_ids: list[str],
) -> tuple[Task, TaskStateEnum, list[tuple[TaskStep, object]], list[TaskStep]]:
    now = datetime.now(timezone.utc)
    requested_step_ids = set(step_ids)

    task_result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise NotFound("Task not found.")
    old_task_state = task.state

    step_result = await ctx.session.execute(
        select(TaskStep).where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task_id,
            TaskStep.client_id.in_(requested_step_ids),
        )
    )
    found_steps = step_result.scalars().all()
    steps_by_id = {step.client_id: step for step in found_steps}

    missing_step_ids = sorted(requested_step_ids - set(steps_by_id))
    if missing_step_ids:
        raise NotFound(f"Task step(s) not found: {', '.join(missing_step_ids)}")

    already_deleted_ids = sorted(
        step.client_id
        for step in found_steps
        if step.is_deleted
    )
    if already_deleted_ids:
        raise ConflictError(f"Task step(s) already deleted: {', '.join(already_deleted_ids)}")

    steps_to_remove = [steps_by_id[step_id] for step_id in step_ids]
    completed_removed_step_ids = {
        step.client_id
        for step in steps_to_remove
        if step.state == TaskStepStateEnum.COMPLETED
    }

    for step in steps_to_remove:
        step.state = TaskStepStateEnum.SKIPPED
        step.closed_at = now
        step.updated_at = now
        step.updated_by_id = ctx.user_id
        step.is_deleted = True
        step.deleted_at = now
        step.deleted_by_id = ctx.user_id

    open_record_result = await ctx.session.execute(
        select(StepStateRecord).where(
            StepStateRecord.workspace_id == ctx.workspace_id,
            StepStateRecord.step_id.in_(requested_step_ids),
            StepStateRecord.exited_at.is_(None),
        )
    )
    for record in open_record_result.scalars().all():
        record.exited_at = now

    edge_result = await ctx.session.execute(
        select(TaskStepDependency).where(
            TaskStepDependency.workspace_id == ctx.workspace_id,
            TaskStepDependency.removed_at.is_(None),
            or_(
                TaskStepDependency.dependent_step_id.in_(requested_step_ids),
                TaskStepDependency.prerequisite_step_id.in_(requested_step_ids),
            ),
        )
    )
    edges = edge_result.scalars().all()
    for edge in edges:
        edge.removed_at = now
        edge.removed_by_id = ctx.user_id

    dependency_counts = _count_removed_prerequisite_edges(
        edges=edges,
        removed_step_ids=requested_step_ids,
        completed_removed_step_ids=completed_removed_step_ids,
    )

    readiness_changes: list[tuple[TaskStep, object]] = []
    if dependency_counts:
        affected_step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id.in_(list(dependency_counts)),
                TaskStep.is_deleted.is_(False),
            )
        )
        affected_steps = {
            step.client_id: step
            for step in affected_step_result.scalars().all()
        }
        for dependent_step_id, (removed_total, removed_completed) in dependency_counts.items():
            affected_step = affected_steps.get(dependent_step_id)
            if affected_step is None:
                continue
            old_readiness = affected_step.readiness_status
            _apply_removed_dependency_counts(
                affected_step,
                removed_total=removed_total,
                removed_completed=removed_completed,
            )
            readiness_changes.append((affected_step, old_readiness))

    remaining_steps_result = await ctx.session.execute(
        select(TaskStep).where(
            TaskStep.workspace_id == ctx.workspace_id,
            TaskStep.task_id == task.client_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    remaining_steps = remaining_steps_result.scalars().all()

    if len(remaining_steps) == 0:
        task.state = TaskStateEnum.PENDING
        task.updated_at = now
        task.updated_by_id = ctx.user_id
    else:
        await maybe_evaluate_task_ready(
            ctx.session,
            task,
            workspace_id=ctx.workspace_id,
            now=now,
            updated_by_id=ctx.user_id,
        )

    await ctx.session.flush()
    return task, old_task_state, readiness_changes, steps_to_remove


async def _dispatch_remove_step_events(
    *,
    ctx: ServiceContext,
    task: Task,
    old_task_state: TaskStateEnum,
    readiness_changes: list[tuple[TaskStep, object]],
    removed_steps: list[TaskStep],
) -> None:
    pending_events: list = [
        build_workspace_event(task, "task:updated"),
        BatchWorkspaceEvent(
            event_name="task:step-deleted",
            workspace_id=ctx.workspace_id,
            items=[
                {
                    "client_id": step.client_id,
                    "working_section_id": step.working_section_id,
                }
                for step in removed_steps
            ],
        ),
    ]
    readiness_items = [
        {
            "client_id": affected_step.client_id,
            "new_readiness": affected_step.readiness_status.value,
        }
        for affected_step, old_aff_readiness in readiness_changes
        if affected_step.readiness_status != old_aff_readiness
    ]
    if readiness_items:
        pending_events.append(
            BatchWorkspaceEvent(
                event_name="task:step-readiness-changed",
                workspace_id=ctx.workspace_id,
                items=readiness_items,
            )
        )
    if task.state != old_task_state:
        pending_events.append(
            build_workspace_event(task, "task:state-changed", extra={"new_state": task.state.value})
        )
    await event_bus.dispatch(pending_events)


async def remove_task_step(ctx: ServiceContext) -> dict:
    request = parse_remove_task_step_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        task, old_task_state, readiness_changes, removed_steps = await _remove_task_steps_in_session(
            ctx=ctx,
            task_id=request.task_id,
            step_ids=[request.step_id],
        )

    await _dispatch_remove_step_events(
        ctx=ctx,
        task=task,
        old_task_state=old_task_state,
        readiness_changes=readiness_changes,
        removed_steps=removed_steps,
    )
    return {"step_id": request.step_id}


async def remove_task_steps(ctx: ServiceContext) -> dict:
    request = parse_remove_task_steps_request(ctx.incoming_data)
    step_ids = _dedupe_step_ids(request.step_ids)

    async with maybe_begin(ctx.session):
        task, old_task_state, readiness_changes, removed_steps = await _remove_task_steps_in_session(
            ctx=ctx,
            task_id=request.task_id,
            step_ids=step_ids,
        )

    await _dispatch_remove_step_events(
        ctx=ctx,
        task=task,
        old_task_state=old_task_state,
        readiness_changes=readiness_changes,
        removed_steps=removed_steps,
    )
    return {"step_ids": step_ids}
