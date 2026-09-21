"""Errors for the stock-report project (master plan §6.4).

This file is created in batch B2 (plans 6-7); phase 8 adds the two structured
assignment errors here (`StockAssignmentRefused`, `StockAssignmentPropertyMismatch`).
`IllegalAssignmentMove` is a programming error, not a domain error, and lives beside
`move_assignment` in `_move_assignment.py`.
"""

from beyo_manager.errors.base import DomainError
from beyo_manager.errors.validation import ConflictError, ValidationError


class LocationTrackerWebhookAuthError(DomainError):
    """Any failure of MC-8 steps 2-4 (config, key, workspace). Always renders the
    same body — the cause is logged, never returned (MC-8 "All 401 bodies are
    identical")."""

    http_status = 401

    def __init__(self, message: str = "Unauthorized.") -> None:
        super().__init__(message)


class StockDemandDeadlineExceeded(DomainError):
    """Raised by the demand webhook (phase 6/7) and the delete webhook (phase 13A,
    §14E E9) when the request's MC-9 time budget is exhausted immediately before
    commit."""

    http_status = 503

    def __init__(
        self, message: str = "Stock demand request exceeded its time limit."
    ) -> None:
        super().__init__(message)


class StockAssignmentRefused(ValidationError):
    """MC-13's batch-refusal error (master plan §6.4). `details` is a list of
    `{"index", "reason"}`, one entry per offending index, `reason` drawn from MC-13's
    closed vocabulary (`duplicate_item_in_batch`, `duplicate_task_in_batch`,
    `stock_report_item_not_found`, `task_not_found`, `item_not_found`,
    `item_not_task_primary`, `already_processed_by_scanner`, `task_failed_or_cancelled`,
    `item_already_assigned`, `item_has_no_category`, `category_mismatch`). Raised only
    when nothing has been written for the request."""

    http_status = 422
    code = "stock_assignment_refused"

    def __init__(self, details: list[dict]) -> None:
        self.details = details
        super().__init__("Stock assignment refused.")


class StockAssignmentPropertyMismatch(ConflictError):
    """MC-13's matcher-mismatch error (master plan §6.4). `details` is a list of
    `{"index", "stock_report_item_id", "task_id", "item_id", "failures"}`, `failures`
    a list of `{"key", "reason"}` sorted by key. Raised only when nothing has been
    written for the request."""

    http_status = 409
    code = "stock_assignment_property_mismatch"

    def __init__(self, details: list[dict]) -> None:
        self.details = details
        super().__init__("Stock assignment property mismatch.")
