import enum


class EventStateEnum(enum.Enum):
    """Shared state enum for all domain event/operation tables (42_event.md)."""
    REQUESTED   = "requested"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
