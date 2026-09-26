"""`load_version_progress` — the one engine behind
`GET /api/v1/stock-report/snapshots/versions/active` and the `progress` carried by each
row of `GET /api/v1/stock-report/snapshots/versions` (addendum 2026-09-26).

What a version set out to do is its selected snapshots' `quantity_requested −
quantity_missing`; what it accomplished is their `quantity_awaiting`, which on the
wire already contains `quantity_resolved` (completion never drops because Scanner
processed a shelf). Counters are the row's live values while a snapshot is active and
its frozen copies once closed — the per-snapshot `closed_at` test, the same one the
item serializer makes, so a row deleted mid-version and a version close agree with the
item payload. A snapshot whose row is soft-deleted leaves the progress: Scanner
withdrew that goal, and keeping its requested would make 100 % unreachable.

**Which snapshots** is the board's own `priority` filter (`_priority_filter.py`; owner
request 2026-09-26, replacing the fixed "prioritised only"): omitted → the
null-priority snapshots, `all` → every snapshot, a list → those priorities. The
progress a client reads therefore sums exactly the snapshots `GET /items` lists under
the same `priority` value (before its outstanding / missing rules, which hide rows
but do not change what a version set out to do).

Beside `progress`, each version gets **`filtered_snapshot_count`** (owner request
2026-09-26): the stored `snapshot_count` under the same filter — the version's
snapshots the `priority` value selects, **deleted rows included**, because
`snapshot_count` counts them too (with `priority=all` the two are equal). That is why
the deleted-row exclusion is a `FILTER` on each progress aggregate rather than a
`WHERE`: one statement yields both.

One statement for any number of versions (`GROUP BY version_id, priority`;
22_performance), folded per version by `fold_version_progress`. Every requested id
is present in the result, zeros when the version has no selected snapshot.
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
from beyo_manager.services.queries.stock_report._priority_filter import (
    priority_predicate,
)


def _live_or_frozen(row_column, snapshot_column):
    return case(
        (StockReportItemSnapshot.closed_at.is_(None), row_column),
        else_=snapshot_column,
    )


def _live_sum(expression, live):
    # `SUM … FILTER` over no row is NULL, not 0: a group whose rows are all deleted.
    return func.coalesce(func.sum(expression).filter(live), 0)


async def load_version_progress(
    session, workspace_id, version_ids, *, priorities
) -> dict[str, dict]:
    """`priorities` — the parsed filter (`parse_priority_filter`); required, so every
    caller decides which snapshots count. Returns, per version id, the two keys the
    version reads add to a version: `{"filtered_snapshot_count", "progress"}`."""
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
    live = r.is_deleted.is_(False)

    statement = (
        select(
            s.version_id.label("version_id"),
            s.priority.label("priority"),
            func.count().label("filtered_snapshot_count"),
            func.count().filter(live).label("items_total"),
            _live_sum(case((awaiting >= target, 1), else_=0), live).label(
                "items_completed"
            ),
            _live_sum(s.quantity_requested, live).label("quantity_requested"),
            _live_sum(s.quantity_missing, live).label("quantity_missing"),
            _live_sum(target, live).label("quantity_target"),
            _live_sum(in_queue, live).label("quantity_in_queue"),
            _live_sum(in_progress, live).label("quantity_in_progress"),
            _live_sum(awaiting, live).label("quantity_awaiting"),
            _live_sum(s.quantity_resolved, live).label("quantity_resolved"),
            _live_sum(func.least(target, awaiting), live).label("quantity_completed"),
        )
        .join(r, r.client_id == s.stock_report_item_id)
        .where(
            s.workspace_id == workspace_id,
            s.version_id.in_(version_ids),
        )
        .group_by(s.version_id, s.priority)
    )
    predicate = priority_predicate(priorities)
    if predicate is not None:
        statement = statement.where(predicate)
    groups_by_version: dict[str, list] = {version_id: [] for version_id in version_ids}
    for group in (await session.execute(statement)).mappings().all():
        groups_by_version[group["version_id"]].append(group)
    return {
        version_id: {
            "filtered_snapshot_count": sum(
                int(group["filtered_snapshot_count"]) for group in groups
            ),
            "progress": (
                fold_version_progress(groups) if groups else empty_version_progress()
            ),
        }
        for version_id, groups in groups_by_version.items()
    }
