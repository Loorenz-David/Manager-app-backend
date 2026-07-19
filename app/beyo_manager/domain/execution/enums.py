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
    DELAYED_STEP_COMPLETION     = "delayed_step_completion"

    # Recurring scheduler tasks
    RECURRING_SEND_REPORT = "recurring_send_report"
    RECURRING_REMINDER    = "recurring_reminder"
    RECURRING_PIN_TASK    = "recurring_pin_task"
    AUTO_CLOCK_OUT_OPEN_SHIFTS = "auto_clock_out_open_shifts"

    # Presence view-record tasks (enqueued by socket connect/disconnect handlers)
    RECORD_VIEW_START = "record_view_start"
    RECORD_VIEW_END   = "record_view_end"

    # Analytics — step state transition event
    PROCESS_STEP_TRANSITION = "process_step_transition"

    # Email
    EMAIL_INBOX_SYNC = "email_inbox_sync"
    EMAIL_SYNC_TARGETED = "email_sync_targeted"
    SEND_COORDINATION_EMAIL_BATCH = "send_coordination_email_batch"
    SEND_EMAIL_MESSAGES = "send_email_messages"
    LOCATION_TRACKER_PUSH_LOCATIONS = "location_tracker_push_locations"

    # Shopify
    SHOPIFY_PROCESS_WEBHOOK = "shopify_process_webhook"
    SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP = "shopify_sync_webhooks_for_shop"
    SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP = "shopify_remove_webhooks_for_shop"
    SHOPIFY_RECONCILE_SHOP = "shopify_reconcile_shop"
    SHOPIFY_PROCESS_PRODUCTS = "shopify_process_products"


class EventTaskOriginSourceEnum(enum.Enum):
    DELAYED_SCHEDULER   = "delayed_scheduler"
    RECURRING_SCHEDULER = "recurring_scheduler"
    INSTANT             = "instant"
