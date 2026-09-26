"""The `priority` query parameter shared by `GET /api/v1/stock-report/items` and the
two version reads (`GET …/snapshots/versions`, `GET …/snapshots/versions/active`),
so the board and its progress always select the same snapshots (owner request
2026-09-26).

`parse_priority_filter` returns one of three shapes, and `priority_predicate`
turns it into the snapshot predicate:

- `[]` — omitted or empty: the **null-priority** snapshots only, not "all rows"
  (ratified owner answer for the board);
- `None` — `all`: no priority predicate at all;
- a list of `StockReportPriorityEnum` — those priorities.
"""

from __future__ import annotations

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)

ALL_PRIORITIES = "all"


def parse_priority_filter(raw):
    """§7A: a comma list of `high|medium|low`; an unknown token is a 422. `all`
    must be the only token: `all,high` is ambiguous and refused."""
    if raw is None:
        return []
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    if ALL_PRIORITIES in tokens:
        if len(tokens) > 1:
            raise ValidationError(
                "STOCK_REPORT_UNKNOWN_PRIORITY_FILTER: 'all' cannot be combined with "
                "other priorities; send it alone."
            )
        return None
    priorities = []
    for token in tokens:
        try:
            priorities.append(StockReportPriorityEnum(token))
        except ValueError:
            raise ValidationError(
                f"STOCK_REPORT_UNKNOWN_PRIORITY_FILTER: '{token}' is not one of "
                "high, medium, low, all."
            ) from None
    return priorities


def priority_predicate(priorities):
    """The `WHERE` clause for a parsed filter, or `None` when there is none (`all`)."""
    if priorities is None:
        return None
    if priorities:
        return StockReportItemSnapshot.priority.in_(priorities)
    return StockReportItemSnapshot.priority.is_(None)
