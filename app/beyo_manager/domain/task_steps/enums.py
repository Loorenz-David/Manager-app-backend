import enum


class TaskStepStateEnum(enum.Enum):
    PENDING = "pending"
    WORKING = "working"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStepReadinessStatusEnum(enum.Enum):
    BLOCKED = "blocked"
    PARTIAL = "partial"
    READY = "ready"


class StepStateRecordAccuracyMeasuredByEnum(enum.Enum):
    USER = "user"
    AI = "ai"
