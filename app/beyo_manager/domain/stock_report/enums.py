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


class StockDemandOutcomeEnum(enum.Enum):
    """Per-entry outcome of the demand webhook (batch B2, plan 6 — master plan §6.1
    blocker B4). Only this one name is added here; the other five names batch B
    projection found missing (`StockDemandDeletedOutcomeEnum`,
    `ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum`,
    `REPAIR_TRIGGER_MANUAL`, `INLINE_REPAIR_TRIGGERS`) belong to phases 9 and 13A and
    are not shipped here (charter rule 4 — no constant with no caller)."""

    APPLIED = "applied"
    CATEGORY_NOT_FOUND = "category_not_found"
