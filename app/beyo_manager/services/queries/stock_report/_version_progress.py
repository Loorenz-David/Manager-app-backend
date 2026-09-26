"""`load_version_progress` — the one engine behind
`GET /api/v1/stock-report/snapshots/versions/active` and the `progress` carried by each
row of `GET /api/v1/stock-report/snapshots/versions` (addendum 2026-09-26).

What a version set out to do is its **prioritised** snapshots' `quantity_requested −
quantity_missing`; what it accomplished is their `quantity_awaiting`, which on the
wire already contains `quantity_resolved` (completion never drops because Scanner
processed a shelf). Counters are the row's live values while a snapshot is active and
its frozen copies once closed — the per-snapshot `closed_at` test, the same one the
item serializer makes, so a row deleted mid-version and a version close agree with the
item payload. A snapshot whose row is soft-deleted leaves the progress: Scanner
withdrew that goal, and keeping its requested would make 100 % unreachable.

One statement for any number of versions (`GROUP BY version_id, priority`;
22_performance), folded per version by `fold_version_progress`. Every requested id
is present in the result, zeros when the version has no prioritised snapshot.
"""

from __future__ import annotations

from sqlalchemy import case, func, select

from beyo_manager.domain.stock_report.snapshot_rules import (
    empty_version_progress,
    fold_version_progress,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)


def _live_or_frozen(row_column, snapshot_column):
    return case(
        (StockReportItemSnapshot.closed_at.is_(None), row_column),
        else_=snapshot_column,
    )


async def load_version_progress(session, workspace_id, version_ids) -> dict[str, dict]:
    version_ids = list(dict.fromkeys(version_ids))
    if not version_ids:
        return {}

    s = StockReportItemSnapshot
    r = StockReportItem
    in_queue = _live_or_frozen(r.quantity_in_queue, s.quantity_in_queue)
    in_progress = _live_or_frozen(r.quantity_in_progress, s.quantity_in_progress)
    awaiting = (
        _live_or_frozen(r.quantity_awaiting, s.quantity_awaiting) + s.quantity_resolved
    )
    target = func.greatest(0, s.quantity_requested - s.quantity_missing)

    statement = (
        select(
            s.version_id.label("version_id"),
            s.priority.label("priority"),
            func.count().label("items_total"),
            func.sum(case((awaiting >= target, 1), else_=0)).label("items_completed"),
            func.sum(s.quantity_requested).label("quantity_requested"),
            func.sum(s.quantity_missing).label("quantity_missing"),
            func.sum(target).label("quantity_target"),
            func.sum(in_queue).label("quantity_in_queue"),
            func.sum(in_progress).label("quantity_in_progress"),
            func.sum(awaiting).label("quantity_awaiting"),
            func.sum(s.quantity_resolved).label("quantity_resolved"),
            func.sum(func.least(target, awaiting)).label("quantity_completed"),
        )
        .join(r, r.client_id == s.stock_report_item_id)
        .where(
            s.workspace_id == workspace_id,
            s.version_id.in_(version_ids),
            s.priority.is_not(None),
            r.is_deleted.is_(False),
        )
        .group_by(s.version_id, s.priority)
    )
    groups_by_version: dict[str, list] = {version_id: [] for version_id in version_ids}
    for group in (await session.execute(statement)).mappings().all():
        groups_by_version[group["version_id"]].append(group)
    return {
        version_id: (
            fold_version_progress(groups) if groups else empty_version_progress()
        )
        for version_id, groups in groups_by_version.items()
    }
