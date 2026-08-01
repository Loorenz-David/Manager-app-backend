from beyo_manager.domain.analytics.time_buckets import ENDED_SHIFT_BUCKET, bucket_for
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep


def increment_step_time_metrics(
    step: TaskStep,
    closing_state: TaskStepStateEnum,
    interval_seconds: int,
    transition_reason: str | None = None,
) -> None:
    """Increment TaskStep time/count aggregate columns for a closed state record.

    **This function has no callers.** The step's totals are written by the analytics
    pipeline (`services/tasks/analytics/process_step_transition.py`), which recomputes them
    from the records rather than incrementing. It is kept here only because deleting it is a
    separate cleanup; it buckets through the shared rule so that it would be *correct* rather
    than quietly wrong if it were ever wired up.

    Only call this when closing_record.recorded_time_marked_wrong is False.
    """
    bucket = bucket_for(closing_state.value, transition_reason)
    if bucket == TaskStepStateEnum.WORKING.value:
        step.total_working_seconds += interval_seconds
        step.total_working_count += 1
    elif bucket == TaskStepStateEnum.PAUSED.value:
        step.total_pause_seconds += interval_seconds
        step.total_pause_count += 1
    elif bucket == ENDED_SHIFT_BUCKET:
        step.total_ended_shift_seconds += interval_seconds
        step.total_ended_shift_count += 1
