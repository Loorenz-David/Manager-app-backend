from datetime import datetime, timezone

from sqlalchemy import func, update

from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.services.commands.task_step_acknowledgments.requests import (
    parse_step_acknowledgment_action_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def acknowledge_step_acknowledgments(ctx: ServiceContext) -> dict:
    """Mark the calling worker's pending acknowledgments as acknowledged.

    Scoped to the caller's own obligations and idempotent — already-acknowledged
    rows are skipped by the ``acknowledged_at IS NULL`` filter. Acknowledging
    implies seen, so ``first_seen_at`` is backfilled when it was never set.
    """
    request = parse_step_acknowledgment_action_request(ctx.incoming_data)
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            update(TaskStepAcknowledgment)
            .where(
                TaskStepAcknowledgment.workspace_id == ctx.workspace_id,
                TaskStepAcknowledgment.worker_id == ctx.user_id,
                TaskStepAcknowledgment.step_id.in_(request.step_ids),
                TaskStepAcknowledgment.acknowledged_at.is_(None),
                TaskStepAcknowledgment.is_deleted.is_(False),
            )
            .values(
                acknowledged_at=now,
                first_seen_at=func.coalesce(TaskStepAcknowledgment.first_seen_at, now),
                updated_at=now,
            )
            .returning(TaskStepAcknowledgment.step_id)
        )
        acknowledged_step_ids = sorted(result.scalars().all())

    return {"acknowledged_step_ids": acknowledged_step_ids}
