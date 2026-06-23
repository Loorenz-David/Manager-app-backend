"""Shared query helper: find an open WORKING StepStateRecord for a set of users in the workspace."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task_step import TaskStep


async def fetch_open_user_working_record(
    session: AsyncSession,
    user_ids: list[str],
    workspace_id: str,
    exclude_step_id: str,
) -> tuple[StepStateRecord, TaskStep] | tuple[None, None]:
    """Return the open StepStateRecord in WORKING state for any of the given users, excluding the given step.

    Accepts a list of user IDs so the caller can pass both the performer (ctx.user_id) and the
    credited user (credited_user_id) when they differ — e.g. a manager transitioning a step on
    behalf of a worker. This ensures the one-active-step rule fires regardless of who originally
    created the conflicting WORKING record.
    """
    result = await session.execute(
        select(StepStateRecord, TaskStep)
        .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
        .where(
            StepStateRecord.workspace_id == workspace_id,
            StepStateRecord.created_by_id.in_(user_ids),
            StepStateRecord.state == TaskStepStateEnum.WORKING,
            StepStateRecord.exited_at.is_(None),
            StepStateRecord.step_id != exclude_step_id,
            TaskStep.is_deleted.is_(False),
            TaskStep.allows_batch_working.is_(False),
        )
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None, None
    return row[0], row[1]
