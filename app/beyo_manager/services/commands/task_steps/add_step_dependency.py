from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.services.commands.task_steps._readiness import recalculate_readiness
from beyo_manager.services.commands.task_steps.requests import parse_add_step_dependency_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def add_step_dependency(ctx: ServiceContext) -> dict:
    request = parse_add_step_dependency_request(ctx.incoming_data)
    old_readiness = None

    if request.step_id == request.prerequisite_step_id:
        raise ValidationError("A step cannot depend on itself.")

    async with maybe_begin(ctx.session):
        # Load dependent step — verify it belongs to the task
        dep_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == request.step_id,
                TaskStep.task_id == request.task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        dependent_step = dep_result.scalar_one_or_none()
        if dependent_step is None:
            raise NotFound("Dependent step not found.")

        # Load prerequisite step — verify it belongs to the same task
        pre_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == request.prerequisite_step_id,
                TaskStep.task_id == request.task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        prerequisite_step = pre_result.scalar_one_or_none()
        if prerequisite_step is None:
            raise NotFound("Prerequisite step not found.")

        # Guard: no duplicate active edge
        existing_result = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.dependent_step_id == request.step_id,
                TaskStepDependency.prerequisite_step_id == request.prerequisite_step_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        if existing_result.scalar_one_or_none() is not None:
            raise ConflictError("Dependency edge already exists.")

        edge = TaskStepDependency(
            workspace_id=ctx.workspace_id,
            dependent_step_id=request.step_id,
            prerequisite_step_id=request.prerequisite_step_id,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(edge)

        old_readiness = dependent_step.readiness_status
        dependent_step.total_dependencies += 1
        recalculate_readiness(dependent_step)

        await ctx.session.flush()

    pending_events: list = [
        WorkspaceEvent(
            event_name="task:updated",
            client_id=dependent_step.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ]
    if old_readiness is not None and dependent_step.readiness_status != old_readiness:
        pending_events.append(WorkspaceEvent(
            event_name="task:step-readiness-changed",
            client_id=dependent_step.client_id,
            workspace_id=ctx.workspace_id,
            extra={"new_readiness": dependent_step.readiness_status.value},
        ))
    await event_bus.dispatch(pending_events)
    return {"dependency_id": edge.client_id}
