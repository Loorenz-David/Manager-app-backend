from __future__ import annotations

import enum


class StockTaskAssignmentStateEnum(enum.Enum):
    IN_QUEUE = "in_queue"
    IN_PROGRESS = "in_progress"
    AWAITING = "awaiting"
    RESOLVED = "resolved"
    FAILED = "failed"
    RESOLVED_EARLY = "resolved_early"


ACTIVE_ASSIGNMENT_STATES = frozenset(
    {
        StockTaskAssignmentStateEnum.IN_QUEUE,
        StockTaskAssignmentStateEnum.IN_PROGRESS,
        StockTaskAssignmentStateEnum.AWAITING,
    }
)
TERMINAL_ASSIGNMENT_STATES = frozenset(
    {
        StockTaskAssignmentStateEnum.RESOLVED,
        StockTaskAssignmentStateEnum.FAILED,
        StockTaskAssignmentStateEnum.RESOLVED_EARLY,
    }
)


class StockReportPriorityEnum(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StockReportHistoryRecordTypeEnum(enum.Enum):
    QUANTITY_REQUESTED_CHANGE = "quantity_requested_change"
    PRIORITY_CHANGE = "priority_change"
    PRIORITY_ORDER_CHANGE = "priority_order_change"


class StockReportRepairTargetKindEnum(enum.Enum):
    STOCK_REPORT_ITEM = "stock_report_item"
    HISTORY_RECORD = "history_record"
    TASK = "task"
    GROUP = "group"


class StockCriteriaMismatchReasonEnum(enum.Enum):
    MISSING_ON_ITEM = "missing_on_item"
    VALUE_NOT_ACCEPTED = "value_not_accepted"
    NO_GROUP_FOR_VALUE = "no_group_for_value"
    CRITERION_NOT_UNDERSTOOD = "criterion_not_understood"
