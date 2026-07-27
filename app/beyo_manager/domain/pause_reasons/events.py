from enum import StrEnum


class PauseReasonEvent(StrEnum):
    CREATED = "pause_reason:created"
    UPDATED = "pause_reason:updated"
    DELETED = "pause_reason:deleted"
