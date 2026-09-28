"""One SQL spelling of each snapshot-layer predicate and derived value (draft
versions, 2026-09-28) — the §9 rule-16 lesson (`resolved_early`) applied to a
two-column state. No site hand-types the pair or the `COALESCE`.

Two predicates, deliberately distinct:

* **open** — `closed_at IS NULL`: drafts and the active version. The counters'
  live-or-frozen switch, the ordering groups, the cascade, consistency and repair.
* **active** — `active_at IS NOT NULL AND closed_at IS NULL`: "the board". The
  items read's default, the shortcut routes' target, resolved credit, the clamp, the
  webhooks' discovery, the active-version read, the close-freeze, the missing summary.

Two derived values, each as an ORM expression (over the mapped classes or aliases
of them) and as a `text()` fragment over the aliases `s` (snapshot), `r` (row) and
`a` (the row's **active** snapshot) that the raw statements use:

* the effective requested quantity —
  `COALESCE(s.quantity_requested_manual, CASE WHEN s.active_at IS NULL THEN
  r.quantity_requested ELSE s.quantity_requested_scanner END)`;
* the effective missing quantity — an activated snapshot's own column, else
  `COALESCE(s.quantity_missing, a.quantity_missing, 0)`.

The Python twins live in `domain/stock_report/snapshot_rules.py`.
"""

from __future__ import annotations

from sqlalchemy import and_, case, func

from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)

# ---------------------------------------------------------------------------
# `text()` fragments — aliases `s`, `r`, `a`
# ---------------------------------------------------------------------------

SNAPSHOT_OPEN_SQL = "s.closed_at IS NULL"
SNAPSHOT_ACTIVE_SQL = "s.active_at IS NOT NULL AND s.closed_at IS NULL"
SNAPSHOT_DRAFT_SQL = "s.active_at IS NULL"

EFFECTIVE_QUANTITY_REQUESTED_SQL = (
    "COALESCE(s.quantity_requested_manual, "
    "CASE WHEN s.active_at IS NULL THEN r.quantity_requested "
    "ELSE s.quantity_requested_scanner END)"
)
EFFECTIVE_QUANTITY_MISSING_SQL = (
    "CASE WHEN s.active_at IS NOT NULL THEN s.quantity_missing "
    "ELSE COALESCE(s.quantity_missing, a.quantity_missing, 0) END"
)
# The `LEFT JOIN` that gives a statement the alias `a`: the row's active snapshot,
# at most one by `uix_stock_report_item_snapshots_row_active`.
ACTIVE_SNAPSHOT_LEFT_JOIN_SQL = (
    "LEFT JOIN stock_report_item_snapshots AS a "
    "ON a.stock_report_item_id = r.client_id "
    "AND a.active_at IS NOT NULL AND a.closed_at IS NULL"
)


# ---------------------------------------------------------------------------
# ORM clauses — `s` / `v` default to the mapped classes; pass an `aliased()` to
# name a second copy of the table in one statement.
# ---------------------------------------------------------------------------


def snapshot_is_open(s=StockReportItemSnapshot):
    return s.closed_at.is_(None)


def snapshot_is_active(s=StockReportItemSnapshot):
    return and_(s.active_at.is_not(None), s.closed_at.is_(None))


def snapshot_is_draft(s=StockReportItemSnapshot):
    return s.active_at.is_(None)


def version_is_open(v=StockReportSnapshotVersion):
    return v.closed_at.is_(None)


def version_is_active(v=StockReportSnapshotVersion):
    return and_(v.active_at.is_not(None), v.closed_at.is_(None))


def version_is_draft(v=StockReportSnapshotVersion):
    return v.active_at.is_(None)


def version_is_closed(v=StockReportSnapshotVersion):
    return v.closed_at.is_not(None)


def active_snapshot_of_row(a, row_id_column):
    """The join clause for an `aliased(StockReportItemSnapshot)` `a` onto the row
    whose id is `row_id_column` (the row table's `client_id`, or a snapshot's
    `stock_report_item_id`)."""
    return and_(a.stock_report_item_id == row_id_column, snapshot_is_active(a))


def scanner_quantity_requested(s=StockReportItemSnapshot, r=StockReportItem):
    return case((s.active_at.is_(None), r.quantity_requested), else_=s.quantity_requested_scanner)


def effective_quantity_requested(s=StockReportItemSnapshot, r=StockReportItem):
    return func.coalesce(s.quantity_requested_manual, scanner_quantity_requested(s, r))


def effective_quantity_missing(s, a):
    """`a` is the row's active snapshot alias (`active_snapshot_of_row`)."""
    return case(
        (s.active_at.is_not(None), s.quantity_missing),
        else_=func.coalesce(s.quantity_missing, a.quantity_missing, 0),
    )
