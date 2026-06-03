import enum


class TaskStepStateEnum(enum.Enum):
    PENDING = "pending"
    WORKING = "working"
    PAUSED = "paused"
    ENDED_SHIFT = "ended_shift"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStepReadinessStatusEnum(enum.Enum):
    BLOCKED = "blocked"
    PARTIAL = "partial"
    READY = "ready"


class StepEventReasonEnum(enum.Enum):
    WAITING_FOR_UPHOLSTERY = "waiting_for_upholstery"
    PAUSE_LUNCH_BREAK = "pause_lunch_break"
    PAUSE_COFFEE_BREAK = "pause_coffee_break"
    PAUSE_ENDED_SHIFT = "pause_ended_shift"
    PAUSE_CASE_CREATED = "pause_case_created"
    PAUSE_MEETING = "pause_meeting"
    PAUSE_OTHER_TASK_PRIORITY = "pause_other_task_priority"


class StepStateRecordAccuracyMeasuredByEnum(enum.Enum):
    USER = "user"
    AI = "ai"
