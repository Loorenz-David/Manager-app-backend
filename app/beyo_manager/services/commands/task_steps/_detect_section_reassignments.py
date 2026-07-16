from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.tasks.task_step import TaskStep


async def detect_reassigned_section_ids(
    session: AsyncSession,
    *,
    workspace_id: str,
    task_id: str,
    candidate_section_ids: set[str],
) -> set[str]:
    """Return the candidate sections that now hold more than one step in the task.

    Used on the non-reopen path (the task did not transition ready -> working):
    a working section that already carried a step and just received another is a
    reassignment — the section's members should be notified and asked to
    acknowledge. Sections with a single step are the normal first assignment and
    are excluded.

    One grouped-count query over the just-flushed steps, regardless of how many
    steps were added.
    """
    if not candidate_section_ids:
        return set()

    result = await session.execute(
        select(TaskStep.working_section_id, func.count())
        .where(
            TaskStep.workspace_id == workspace_id,
            TaskStep.task_id == task_id,
            TaskStep.is_deleted.is_(False),
            TaskStep.working_section_id.in_(candidate_section_ids),
        )
        .group_by(TaskStep.working_section_id)
    )
    return {section_id for section_id, step_count in result.all() if step_count > 1}
