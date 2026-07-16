from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment


async def mark_step_obligations_acknowledged(
    session: AsyncSession,
    *,
    workspace_id: str,
    step_ids: Iterable[str],
    now: datetime,
) -> None:
    """Acknowledge every still-pending obligation for the given steps.

    Called when a step transitions to WORKING: starting the work fulfills the
    reassignment, so all outstanding acknowledgment obligations for that step
    (across every section member) are marked acknowledged. Acknowledging implies
    seen, so ``first_seen_at`` is backfilled when unset. Already-acknowledged and
    deleted rows are skipped by the filter. No transaction management — must run
    inside the caller's open transaction.
    """
    step_id_list = list(step_ids)
    if not step_id_list:
        return

    await session.execute(
        update(TaskStepAcknowledgment)
        .where(
            TaskStepAcknowledgment.workspace_id == workspace_id,
            TaskStepAcknowledgment.step_id.in_(step_id_list),
            TaskStepAcknowledgment.acknowledged_at.is_(None),
            TaskStepAcknowledgment.is_deleted.is_(False),
        )
        .values(
            acknowledged_at=now,
            first_seen_at=func.coalesce(TaskStepAcknowledgment.first_seen_at, now),
            updated_at=now,
        )
    )
