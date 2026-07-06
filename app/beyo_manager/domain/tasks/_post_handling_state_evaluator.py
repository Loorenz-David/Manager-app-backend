from beyo_manager.domain.tasks.enums import TaskPostHandlingStateEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.task import Task


_SUPPORTED_TASK_TYPES = frozenset({TaskTypeEnum.RETURN, TaskTypeEnum.PRE_ORDER})


def evaluate_post_handling_state(task: Task) -> TaskPostHandlingStateEnum | None:
    if task.task_type not in _SUPPORTED_TASK_TYPES:
        return None

    if task.state != TaskStateEnum.READY:
        return TaskPostHandlingStateEnum.PENDING

    if task.task_type == TaskTypeEnum.PRE_ORDER:
        has_fulfillment_method = bool(task.fulfillment_method)
        has_schedule = task.scheduled_start_at is not None or task.scheduled_end_at is not None
        filled = has_fulfillment_method and has_schedule
    elif task.task_type == TaskTypeEnum.RETURN:
        filled = bool(task.assortment)
    else:
        filled = False

    return TaskPostHandlingStateEnum.FILLED if filled else TaskPostHandlingStateEnum.PENDING
