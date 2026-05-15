import enum


class TaskTypeEnum(enum.Enum):
    RETURN = "return"
    PRE_ORDER = "pre_order"
    INTERNAL = "internal"


class TaskPriorityEnum(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStateEnum(enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    WORKING = "working"
    STALLED = "stalled"
    READY = "ready"
    RESOLVED = "resolved"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskReturnSourceEnum(enum.Enum):
    AFTER_PURCHASE = "after_purchase"
    BEFORE_PURCHASE = "before_purchase"
    STORE_RETURN = "store_return"


class TaskItemLocationEnum(enum.Enum):
    STORE = "store"
    CUSTOMER = "customer"


class TaskReturnMethodEnum(enum.Enum):
    DROP_OFF_BY_CUSTOMER = "drop_off_by_customer"
    PICKUP = "pickup"


class TaskFulfillmentMethodEnum(enum.Enum):
    PICKUP_AT_STORE = "pickup_at_store"
    DELIVERY = "delivery"


class TaskNoteTypeEnum(enum.Enum):
    USER_NOTE = "user_note"
    SYSTEM_NOTE = "system_note"
    CORRECTION_NOTE = "correction_note"
    RETRACTION_NOTE = "retraction_note"


class TaskItemRoleEnum(enum.Enum):
    PRIMARY = "primary"
    RELATED = "related"


class TaskEventTypeEnum(enum.Enum):
    TASK_CREATED = "task_created"
    TASK_STATE_CHANGED = "task_state_changed"
    TASK_STEP_STATE_CHANGED = "task_step_state_changed"
    TASK_ASSIGNMENT_CHANGED = "task_assignment_changed"
    TASK_RESOLVED = "task_resolved"


class TaskDomainEventLifecycleStateEnum(enum.Enum):
    RECORDED = "recorded"
    SUPERSEDED = "superseded"
    COMPENSATED = "compensated"
    IGNORED = "ignored"


class TaskEventErrorCodeEnum(enum.Enum):
    VALIDATION_FAILED = "validation_failed"
    ORCHESTRATION_CONFLICT = "orchestration_conflict"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    UNKNOWN = "unknown"
