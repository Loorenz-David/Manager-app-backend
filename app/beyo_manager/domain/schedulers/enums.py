import enum


class DelayedSchedulerTypeEnum(enum.Enum):
    NOTIFY_TO_CUSTOMER  = "notify_to_customer"
    SEND_REPORT         = "send_report"
    REMINDER            = "reminder"
    BATCH_NOTIFICATION  = "batch_notification"


class RecurringSchedulerTypeEnum(enum.Enum):
    SEND_REPORT = "send_report"
    REMINDER    = "reminder"
    PIN_TASK    = "pin_task"


class RecurringSchedulerIntervalValueEnum(enum.Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    DAYS    = "days"
    MONTHS  = "months"


class SchedulerStateEnum(enum.Enum):
    ACTIVE   = "active"
    FIRED    = "fired"     # delayed only — fired once, now terminal
    PAUSED   = "paused"    # recurring only — temporarily suspended
    CANCELED = "canceled"
    ERROR    = "error"


class SchedulerOriginSourceEnum(enum.Enum):
    COMMAND = "command"  # created directly by an HTTP request command
    WORKER  = "worker"   # created by a background worker handling a task
