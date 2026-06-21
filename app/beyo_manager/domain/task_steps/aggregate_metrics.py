from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep


def increment_step_time_metrics(
    step: TaskStep,
    closing_state: TaskStepStateEnum,
    interval_seconds: int,
) -> None:
    """Increment TaskStep time/count aggregate columns for a closed state record.

    Called synchronously inside the command transaction so the step row reflects
    correct values immediately on commit. Cost (total_cost_minor) and issue counts
    are still written by the analytics worker.
    Only call this when closing_record.recorded_time_marked_wrong is False.
    """
    if closing_state == TaskStepStateEnum.WORKING:
        step.total_working_seconds += interval_seconds
        step.total_working_count += 1
    elif closing_state == TaskStepStateEnum.PAUSED:
        step.total_pause_seconds += interval_seconds
        step.total_pause_count += 1
    elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
        step.total_ended_shift_seconds += interval_seconds
        step.total_ended_shift_count += 1
