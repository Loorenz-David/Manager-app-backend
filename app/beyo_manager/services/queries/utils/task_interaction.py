from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep


def _interaction_filters(workspace_id: str, working_section_ids: list[str] | None):
    """The single definition of "this task was interacted with".

    A PENDING record is written when a step is created, so counting it would date every
    untouched step to its creation and turn the sort into a slow synonym for created_at.
    Only transitions someone actually drove count.

    Step state records are not soft-deleted when a step is removed, so the step's own
    is_deleted flag is what excludes records belonging to removed work.
    """
    filters = [
        StepStateRecord.workspace_id == workspace_id,
        StepStateRecord.is_deleted.is_(False),
        StepStateRecord.state != TaskStepStateEnum.PENDING,
        TaskStep.workspace_id == workspace_id,
        TaskStep.is_deleted.is_(False),
    ]
    if working_section_ids:
        filters.append(TaskStep.working_section_id.in_(working_section_ids))
    return filters


def build_last_interacted_at_column(
    workspace_id: str,
    task_id_column,
    working_section_ids: list[str] | None = None,
):
    """Correlated scalar subquery: the newest interaction timestamp for one task.

    Scoped to working_section_ids when the caller filtered by section, so the ordering
    answers the same question the visible list does — steps in sections the caller is not
    looking at must not decide a task's position. NULL when nothing in scope was ever
    touched, so callers must sort NULLs last.
    """
    return (
        select(func.max(StepStateRecord.entered_at))
        .select_from(StepStateRecord)
        .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
        .where(
            *_interaction_filters(workspace_id, working_section_ids),
            TaskStep.task_id == task_id_column,
        )
        .correlate(Task)
        .scalar_subquery()
    )


async def load_last_interacted_at_map(
    session: AsyncSession,
    workspace_id: str,
    task_ids: list[str],
    working_section_ids: list[str] | None = None,
) -> dict[str, datetime]:
    """The same aggregate, batched for one page of tasks.

    Shares _interaction_filters with the sort column on purpose: a payload value computed
    under different rules than the ORDER BY would contradict the order being displayed.
    """
    if not task_ids:
        return {}
    result = await session.execute(
        select(
            TaskStep.task_id.label("task_id"),
            func.max(StepStateRecord.entered_at).label("last_interacted_at"),
        )
        .select_from(StepStateRecord)
        .join(TaskStep, TaskStep.client_id == StepStateRecord.step_id)
        .where(
            *_interaction_filters(workspace_id, working_section_ids),
            TaskStep.task_id.in_(task_ids),
        )
        .group_by(TaskStep.task_id)
    )
    return {row.task_id: row.last_interacted_at for row in result.all()}
