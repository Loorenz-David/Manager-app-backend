from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum

TERMINAL_STEP_STATES: frozenset[TaskStepStateEnum] = frozenset({
    TaskStepStateEnum.COMPLETED,
    TaskStepStateEnum.SKIPPED,
    TaskStepStateEnum.FAILED,
    TaskStepStateEnum.CANCELLED,
})

TERMINAL_TASK_STATES: frozenset[TaskStateEnum] = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})
