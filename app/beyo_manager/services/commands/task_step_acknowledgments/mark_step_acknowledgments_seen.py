from datetime import datetime, timezone

from sqlalchemy import update

from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.services.commands.task_step_acknowledgments.requests import (
    parse_step_acknowledgment_action_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def mark_step_acknowledgments_seen(ctx: ServiceContext) -> dict:
    """Record the first time the calling worker viewed their pending obligations.

    Only sets ``first_seen_at`` when it was never set (idempotent, preserves the
    original view timestamp). Does not acknowledge — that is an explicit action.
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
                TaskStepAcknowledgment.first_seen_at.is_(None),
                TaskStepAcknowledgment.is_deleted.is_(False),
            )
            .values(first_seen_at=now, updated_at=now)
            .returning(TaskStepAcknowledgment.step_id)
        )
        seen_step_ids = sorted(result.scalars().all())

    return {"seen_step_ids": seen_step_ids}
