"""Shared readiness recalculation for task steps. Pure function — no DB access."""

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep


def recalculate_readiness(step: TaskStep) -> None:
    """
    Set step.readiness_status based on dependency counters.
    Caller is responsible for flushing after this call.
    """
    if step.total_dependencies == 0:
        step.readiness_status = TaskStepReadinessStatusEnum.READY
    elif step.completed_dependencies == step.total_dependencies:
        step.readiness_status = TaskStepReadinessStatusEnum.READY
    elif step.completed_dependencies == 0:
        step.readiness_status = TaskStepReadinessStatusEnum.BLOCKED
    else:
        step.readiness_status = TaskStepReadinessStatusEnum.PARTIAL
