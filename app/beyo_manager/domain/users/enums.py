import enum


class UserShiftStateEnum(enum.Enum):
    STARTED_SHIFT = "started_shift"
    WORKING = "working"
    IN_PAUSE = "in_pause"
    IDLE = "idle"
    ENDED_SHIFT = "ended_shift"
