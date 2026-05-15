import enum


class ExecutionTaskStateEnum(enum.Enum):
    OPEN             = "open"
    PENDING          = "pending"
    IN_PROGRESS      = "in_progress"
    RETRYING         = "retrying"
    RETRY_SCHEDULED  = "retry_scheduled"
    COMPLETED        = "completed"
    FAIL             = "fail"
    CANCEL           = "cancel"


class TaskType(enum.Enum):
    # Instant tasks — triggered directly by commands
    NOTIFICATION    = "notification"
    UPLOAD_IMAGE    = "upload_image"
    DELIVER_WEBHOOK = "deliver_webhook"

    # CREATE / SEND_PUSH notification tasks (used by notification system)
    CREATE_NOTIFICATIONS    = "create_notifications"
    SEND_PUSH_NOTIFICATION  = "send_push_notification"

    # Delayed scheduler tasks
    DELAYED_NOTIFY_TO_CUSTOMER  = "delayed_notify_to_customer"
    DELAYED_SEND_REPORT         = "delayed_send_report"
    DELAYED_REMINDER            = "delayed_reminder"
    DELAYED_BATCH_NOTIFICATION  = "delayed_batch_notification"

    # Recurring scheduler tasks
    RECURRING_SEND_REPORT = "recurring_send_report"
    RECURRING_REMINDER    = "recurring_reminder"
    RECURRING_PIN_TASK    = "recurring_pin_task"

    # Presence view-record tasks (enqueued by socket connect/disconnect handlers)
    RECORD_VIEW_START = "record_view_start"
    RECORD_VIEW_END   = "record_view_end"


class EventTaskOriginSourceEnum(enum.Enum):
    DELAYED_SCHEDULER   = "delayed_scheduler"
    RECURRING_SCHEDULER = "recurring_scheduler"
    INSTANT             = "instant"
