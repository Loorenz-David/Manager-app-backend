from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum
from beyo_manager.domain.task_steps.readiness import recalculate_readiness
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency


async def cascade_step_completion(
    session: AsyncSession,
    workspace_id: str,
    completed_step: TaskStep,
) -> list[tuple[TaskStep, TaskStepReadinessStatusEnum]]:
    """Increment completed_dependencies and recalculate readiness for every step
    that lists completed_step as a prerequisite.

    Returns (dep_step, old_readiness) only for steps whose readiness_status actually
    changed, so the caller can dispatch task:step-readiness-changed events.
    """
    edges_result = await session.execute(
        select(TaskStepDependency).where(
            TaskStepDependency.workspace_id == workspace_id,
            TaskStepDependency.prerequisite_step_id == completed_step.client_id,
            TaskStepDependency.removed_at.is_(None),
        )
    )
    readiness_changes: list[tuple[TaskStep, TaskStepReadinessStatusEnum]] = []
    for edge in edges_result.scalars().all():
        dep_step_result = await session.execute(
            select(TaskStep).where(
                TaskStep.workspace_id == workspace_id,
                TaskStep.client_id == edge.dependent_step_id,
                TaskStep.is_deleted.is_(False),
            )
        )
        dep_step = dep_step_result.scalar_one_or_none()
        if dep_step is None:
            continue
        old_readiness = dep_step.readiness_status
        dep_step.completed_dependencies += 1
        recalculate_readiness(dep_step)
        if dep_step.readiness_status != old_readiness:
            readiness_changes.append((dep_step, old_readiness))
    return readiness_changes
