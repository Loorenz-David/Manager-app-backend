from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps.requests import parse_update_step_ready_by_at_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import BatchWorkspaceEvent


async def update_task_step_ready_by_at(ctx: ServiceContext) -> dict:
    request = parse_update_step_ready_by_at_request(ctx.incoming_data)
    step_ids = [item.step_id for item in request.items]

    async with maybe_begin(ctx.session):
        task_result = await ctx.session.execute(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
                Task.is_deleted.is_(False),
            )
        )
        task = task_result.scalar_one_or_none()
        if task is None:
            raise NotFound("Task not found.")

        steps_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.task_id == request.task_id,
                TaskStep.client_id.in_(step_ids),
                TaskStep.is_deleted.is_(False),
            )
        )
        steps_by_id = {step.client_id: step for step in steps_result.scalars().all()}

        missing_step_ids = sorted(set(step_ids) - set(steps_by_id))
        if missing_step_ids:
            raise NotFound(f"Task step {missing_step_ids[0]!r} not found.")

        now = datetime.now(timezone.utc)
        for item in request.items:
            step = steps_by_id[item.step_id]
            step.ready_by_at = item.ready_by_at
            step.updated_at = now
            step.updated_by_id = ctx.user_id

    await event_bus.dispatch(
        [
            BatchWorkspaceEvent(
                event_name="task:step-updated",
                workspace_id=ctx.workspace_id,
                items=[{"client_id": step_id} for step_id in step_ids],
            )
        ]
    )
    return {"step_ids": step_ids}
