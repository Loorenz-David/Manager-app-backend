"""CMD-13: Mark a step state record as inaccurate."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.task_steps.requests import parse_mark_step_time_inaccurate_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


def _apply_inaccurate_time_flag(
    record: StepStateRecord,
    step: TaskStep,
    now: datetime,
) -> None:
    record.recorded_time_marked_wrong = True
    step.taken_from_average = True
    record.updated_at = now
    step.updated_at = now


async def mark_step_time_inaccurate(ctx: ServiceContext) -> dict:
    """Mark a step state record as inaccurate (recorded_time_marked_wrong = True)."""
    request = parse_mark_step_time_inaccurate_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # Fetch the StepStateRecord (scope: workspace_id + record_id)
        record_result = await ctx.session.execute(
            select(StepStateRecord).where(
                StepStateRecord.workspace_id == ctx.workspace_id,
                StepStateRecord.client_id == request.record_id,
                StepStateRecord.is_deleted.is_(False),
            )
        )
        record = record_result.scalar_one_or_none()
        if record is None:
            raise NotFound("State record not found.")

        # Fetch the step to set taken_from_average
        step_result = await ctx.session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.client_id == record.step_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            raise NotFound("Task step not found.")

        now = datetime.now(timezone.utc)
        _apply_inaccurate_time_flag(record, step, now)

    await event_bus.dispatch([
        WorkspaceEvent(
            event_name="task:updated",
            client_id=step.task_id,
            workspace_id=ctx.workspace_id,
            extra={},
        ),
    ])
    return {"record_id": record.client_id}
