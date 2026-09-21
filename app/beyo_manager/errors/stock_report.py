"""Errors for the stock-report project (master plan §6.4).

This file is created in batch B2 (plans 6-7); later phases (8) add the two
structured assignment errors here (`StockAssignmentRefused`,
`StockAssignmentPropertyMismatch`). `IllegalAssignmentMove` is a programming error,
not a domain error, and lives beside `move_assignment` in `_move_assignment.py`.
"""

from beyo_manager.errors.base import DomainError


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
