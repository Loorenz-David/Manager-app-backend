from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.schedulers.enums import DelayedSchedulerTypeEnum, SchedulerStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def cancel_pending_step_completion(ctx: ServiceContext) -> dict:
    step_id = ctx.incoming_data["step_id"]
    task_id = ctx.incoming_data["task_id"]

    async with maybe_begin(ctx.session):
        now = datetime.now(timezone.utc)

        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == step_id,
                TaskStep.task_id == task_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        scheduler_result = await ctx.session.execute(
            select(DelayedScheduler).where(
                DelayedScheduler.event_client_id == step.client_id,
                DelayedScheduler.type == DelayedSchedulerTypeEnum.PENDING_STEP_COMPLETION,
                DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
            )
        )
        scheduler = scheduler_result.scalar_one_or_none()
        if scheduler is None:
            raise ConflictError(
                "No active pending completion found for this step. The undo window may have expired."
            )

        scheduler.state = SchedulerStateEnum.CANCELED
        scheduler.updated_at = now

    return {"cancelled": True}
