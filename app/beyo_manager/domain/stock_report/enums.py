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
    # A user set or reverted a snapshot's manual requested quantity on the active
    # version, or a refresh cleared it (draft versions, 2026-09-28).
    QUANTITY_REQUESTED_OVERRIDE = "quantity_requested_override"


class StockReportSnapshotVersionStateEnum(enum.Enum):
    """Derived from the two dates, never stored (`snapshot_rules.version_state`):
    `draft` = neither set, `active` = `active_at` only, `closed` = both."""

    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class StockReportQuantityRequestedSourceEnum(enum.Enum):
    """Which stored column a snapshot's effective requested quantity comes from:
    the user's `quantity_requested_manual` when set, else Scanner's value (the live
    row on a draft, the frozen `quantity_requested_scanner` once activated)."""

    SCANNER = "scanner"
    MANUAL = "manual"


class StockReportQuantityMissingSourceEnum(enum.Enum):
    """Where a snapshot's effective `quantity_missing` comes from: its own column
    (always once activated; on a draft, when typed), the row's active snapshot
    (a draft borrowing the board's number), or nothing (a draft with no board
    value, reading 0)."""

    OWN = "own"
    ACTIVE = "active"
    NONE = "none"


class StockReportRepairTargetKindEnum(enum.Enum):
    STOCK_REPORT_ITEM = "stock_report_item"
    HISTORY_RECORD = "history_record"
    TASK = "task"
    GROUP = "group"
    # The priority-order repairs target the active snapshot since 2026-09-26.
    ITEM_SNAPSHOT = "item_snapshot"
    # Draft membership and schedule repairs target the version (2026-09-28).
    SNAPSHOT_VERSION = "snapshot_version"


class StockCriteriaMismatchReasonEnum(enum.Enum):
    MISSING_ON_ITEM = "missing_on_item"
    VALUE_NOT_ACCEPTED = "value_not_accepted"
    NO_GROUP_FOR_VALUE = "no_group_for_value"
    CRITERION_NOT_UNDERSTOOD = "criterion_not_understood"


class StockAssignmentCheckResultEnum(enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PASS_BY_CONSTRUCTION = "pass_by_construction"
    NOT_EVALUATED = "not_evaluated"


class StockDemandOutcomeEnum(enum.Enum):
    """Per-entry outcome of the demand webhook (batch B2, plan 6 — master plan §6.1
    blocker B4). Only this one name is added here; the other five names batch B
    projection found missing (`StockDemandDeletedOutcomeEnum`,
    `ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum`,
    `REPAIR_TRIGGER_MANUAL`, `INLINE_REPAIR_TRIGGERS`) belong to phases 9 and 13A and
    are not shipped here (charter rule 4 — no constant with no caller)."""

    APPLIED = "applied"
    CATEGORY_NOT_FOUND = "category_not_found"


class StockDemandDeletedOutcomeEnum(enum.Enum):
    """Per-entry outcome of the Scanner **delete** webhook (phase 13A; §14E E7).

    Added here by phase 13A, the phase that gives it a caller — the §6.1 registry's
    claim that it ships in phase 1 was corrected in batch B2 (blocker B4) and again
    at the batch D2 projection (F-08). `INLINE_REPAIR_TRIGGERS` is deliberately
    **not** added beside it: `write_repair_record` takes a free-form `trigger`
    string, so the frozenset would have no caller (charter rule 4).
    """

    DELETED = "deleted"
    NOT_FOUND = "not_found"
    CATEGORY_NOT_FOUND = "category_not_found"


class ItemsProcessedOutcomeEnum(enum.Enum):
    """Per-entry outcome of the processed webhook (phase 9; §14F F5)."""

    RESOLVED = "resolved"
    IGNORED = "ignored"


class ItemsProcessedReasonEnum(enum.Enum):
    """Per-entry `reason` of the processed webhook, JSON `null` when the outcome is
    `resolved` from `awaiting` (phase 9; §14F F5). `not_awaiting` is retired
    (§14C C48)."""

    ITEM_NOT_FOUND = "item_not_found"
    NO_OPEN_ASSIGNMENT = "no_open_assignment"
    EARLY = "early"
