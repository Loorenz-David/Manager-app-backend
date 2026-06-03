from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
from beyo_manager.domain.task_steps.readiness import recalculate_readiness
from beyo_manager.services.commands.task_steps.requests import parse_remove_step_dependency_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


async def remove_step_dependency(ctx: ServiceContext) -> dict:
    request = parse_remove_step_dependency_request(ctx.incoming_data)
    old_readiness = None

    async with maybe_begin(ctx.session):
        edge_result = await ctx.session.execute(
            select(TaskStepDependency).where(
                TaskStepDependency.workspace_id == ctx.workspace_id,
                TaskStepDependency.client_id == request.dependency_id,
                TaskStepDependency.removed_at.is_(None),
            )
        )
        edge = edge_result.scalar_one_or_none()
        if edge is None:
            raise NotFound("Dependency edge not found or already removed.")

        # Load dependent step for counter update
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == edge.dependent_step_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        edge.removed_at = now
        edge.removed_by_id = ctx.user_id

        if step is not None:
            old_readiness = step.readiness_status
            # Defensive decrement
            if step.total_dependencies > 0:
                step.total_dependencies -= 1
            if step.completed_dependencies > step.total_dependencies:
                step.completed_dependencies = step.total_dependencies
            recalculate_readiness(step)

        await ctx.session.flush()

    if step is not None:
        pending_events: list = [
            WorkspaceEvent(
                event_name="task:updated",
                client_id=step.task_id,
                workspace_id=ctx.workspace_id,
                extra={},
            ),
        ]
        if old_readiness is not None and step.readiness_status != old_readiness:
            pending_events.append(WorkspaceEvent(
                event_name="task:step-readiness-changed",
                client_id=step.client_id,
                workspace_id=ctx.workspace_id,
                extra={"new_readiness": step.readiness_status.value},
            ))
        await event_bus.dispatch(pending_events)
    return {"dependency_id": edge.client_id}
