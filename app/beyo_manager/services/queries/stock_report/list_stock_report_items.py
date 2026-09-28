"""`GET /api/v1/stock-report/items` — the board's read (master plan §6.5, phase 12;
intention §7A "Read order"), a **snapshot read** since 2026-09-26.

By default a row is on the board only through its **active item snapshot** (the
active pair — a draft's snapshot is open too but is never the board, 2026-09-28):
the statement inner-joins the snapshot, the priority filter and ordering are the
snapshot's, and "zero requested" means the snapshot's effective `quantity_requested −
quantity_missing <= 0` (the workers' outstanding count, not Scanner's live demand).
`live_stock=true` is the old read of the mirror itself — every live row, the active
snapshot attached when there is one and `null` otherwise; the snapshot filters
(`priority`, `missing_only`) are refused on it because they have nothing to filter.

`version_id=<srv_…>` (draft versions, 2026-09-28; plan §6) reads **that** version's
snapshots in any state — a draft to prepare, a closed version to browse — with the
same ordering, `priority`, `missing_only` and pagination, scoped by the join;
absent/foreign → 404, and with `live_stock=true` → 422. A draft's rows show live
counters beside the live (or overridden) requested, and its outstanding and
`missing_only` rules read the **effective** missing (typed, else the board's).

Every non-live read carries **one more `LEFT JOIN`**: the row's active snapshot, whose
`quantity_missing` becomes the payload's `active_quantity_missing` and the borrowed
value a draft row reads (`_predicates.effective_quantity_missing`). On the default
read that join lands on the very snapshot already joined; it is kept so the
`version_id` read is the same statement with one predicate swapped.

**Paginated since 2026-09-26** (owner decision; it was unpaginated by the earlier
ratified answer in master plan §5). Offset pagination per `07_queries_local`:
`limit` (default 20 by owner ruling, max 200) and `offset`, `limit + 1` rows fetched
for `has_more`, `stock_report_items_pagination` on every path. Every branch orders by
a total key (ending in `client_id`), so pages never overlap or skip a row.
"""

from __future__ import annotations

from sqlalchemy import and_, case, select
from sqlalchemy.orm import aliased

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.services.commands.stock_report._predicates import (
    active_snapshot_of_row,
    effective_quantity_missing,
    effective_quantity_requested,
    snapshot_is_active,
)
from beyo_manager.services.commands.stock_report._versions import find_version
from beyo_manager.services.queries.stock_report._priority_filter import (
    parse_priority_filter,
)

# §7A: `high` before `medium` before `low`. Ordering by the `priority` column itself
# would sort by the enum's text — `high, low, medium`.
# Written as explicit `when` pairs, not `case({...}, value=...)`: the mapping form
# binds each key as a bare parameter, and asyncpg then rejects the enum member
# (`invalid input for query argument … expected str`). Comparing the column takes
# the column's own type for the bind.
_PRIORITY_RANK = case(
    (StockReportItemSnapshot.priority == StockReportPriorityEnum.HIGH, 1),
    (StockReportItemSnapshot.priority == StockReportPriorityEnum.MEDIUM, 2),
    (StockReportItemSnapshot.priority == StockReportPriorityEnum.LOW, 3),
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 20  # owner ruling 2026-09-26: 20, not the contract's 50

_ACTIVE_SNAPSHOT_JOIN = and_(
    StockReportItemSnapshot.stock_report_item_id == StockReportItem.client_id,
    snapshot_is_active(),
)


async def list_stock_report_items(ctx) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    raw_priority = ctx.query_params.get("priority")
    # Omitted → null-priority snapshots; `all` → `None`, no predicate; else a list.
    priorities = parse_priority_filter(raw_priority)
    include_zero_requested = ctx.query_params.get("include_zero_requested", False)
    item_major_categories = ctx.query_params.get("item_major_categories")
    item_category_ids = ctx.query_params.get("item_category_ids")
    live_stock = bool(ctx.query_params.get("live_stock", False))
    missing_only = bool(ctx.query_params.get("missing_only", False))
    version_id = ctx.query_params.get("version_id")

    if live_stock and (
        raw_priority is not None or missing_only or version_id is not None
    ):
        raise ValidationError(
            "STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT: `priority`, `missing_only` and "
            "`version_id` filter a version's snapshots and cannot be combined with "
            "`live_stock`."
        )

    s = StockReportItemSnapshot
    r = StockReportItem
    # The row's active snapshot, for `active_quantity_missing` and the borrowed
    # missing; a second copy of the table, so an alias.
    a = aliased(StockReportItemSnapshot, name="active_snapshot")

    if version_id is not None:
        # That version's snapshots in **any state** (a draft to prepare, a closed
        # version to browse); absent/foreign → 404 before any row is read.
        await find_version(ctx.session, ctx.workspace_id, version_id)
        snapshot_join = and_(
            s.stock_report_item_id == r.client_id, s.version_id == version_id
        )
    else:
        snapshot_join = _ACTIVE_SNAPSHOT_JOIN

    if live_stock:
        # The outer-joined snapshot *is* the active one: its own column is the
        # active missing (None when the row has no snapshot).
        statement = (
            select(r, s, s.quantity_missing.label("active_quantity_missing"))
            .where(r.workspace_id == ctx.workspace_id, r.is_deleted.is_(False))
            .outerjoin(s, _ACTIVE_SNAPSHOT_JOIN)
        )
        if not include_zero_requested:
            statement = statement.where(r.quantity_requested > 0)
        statement = statement.order_by(r.created_at.asc(), r.client_id.asc())
    else:
        statement = (
            select(r, s, a.quantity_missing.label("active_quantity_missing"))
            .where(r.workspace_id == ctx.workspace_id, r.is_deleted.is_(False))
            .join(s, snapshot_join)
            .outerjoin(a, active_snapshot_of_row(a, r.client_id))
        )
        requested = effective_quantity_requested(s, r)
        missing = effective_quantity_missing(s, a)
        # The outstanding rule is the worker's view: a snapshot whose every unit is
        # missing has nothing left to do, so the board hides it. The buyer's list
        # (`missing_only`) is the opposite view, and a fully missing snapshot is the
        # one it most needs — so the rule does not apply there (fix 2026-09-26: the
        # list came back empty while the missing-summary counted the row). No empty
        # snapshot can slip in: `0 < missing <= requested`.
        if not include_zero_requested and not missing_only:
            statement = statement.where((requested - missing) > 0)
        if missing_only:
            statement = statement.where(missing > 0)
        if priorities is None:
            # `priority=all`: every snapshot of the version. The board order is the
            # two filtered reads concatenated — prioritised first (high, medium, low,
            # then `priority_order`), then the unprioritised by creation. Postgres
            # sorts NULL last on ASC by default; it is stated, not assumed.
            statement = statement.order_by(
                _PRIORITY_RANK.asc().nulls_last(),
                s.priority_order.asc().nulls_last(),
                r.created_at.asc(),
                r.client_id.asc(),
            )
        elif priorities:
            statement = statement.where(s.priority.in_(priorities)).order_by(
                _PRIORITY_RANK,
                s.priority_order.asc(),
                # Unique already while groups are dense; the tie-breaker keeps pages
                # stable even if a group ever is not (a repairable divergence).
                r.client_id.asc(),
            )
        else:
            statement = statement.where(s.priority.is_(None)).order_by(
                r.created_at.asc(), r.client_id.asc()
            )

    if item_major_categories is not None:
        # Deliberately no category `is_deleted` predicate: rows keep their category
        # identity after a category soft-delete and remain filterable by its major
        # category, just as they remain serializable below.
        statement = statement.join(
            ItemCategory, ItemCategory.client_id == r.item_category_id
        ).where(
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.major_category.in_(item_major_categories),
        )
    if item_category_ids is not None:
        statement = statement.where(r.item_category_id.in_(item_category_ids))

    # Three values per result row: `.scalars()` would keep only the first and drop
    # the snapshot silently, so the triples are read whole.
    fetched = (
        await ctx.session.execute(
            statement.offset(offset)
            .limit(limit + 1)  # one extra row decides `has_more`
            .execution_options(populate_existing=True)
        )
    ).all()
    has_more = len(fetched) > limit
    triples = fetched[:limit]

    # Categories are batch-loaded **by id**, with no `is_deleted` filter: MC-16 says
    # a row whose category was soft-deleted keeps working and still serializes the
    # deleted category's name. An inner join carrying that filter would drop the row
    # from the payload entirely.
    categories_by_id = {}
    category_ids = {row.item_category_id for row, _snapshot, _missing in triples}
    if category_ids:
        categories = (
            (
                await ctx.session.execute(
                    select(ItemCategory).where(
                        ItemCategory.client_id.in_(sorted(category_ids))
                    )
                )
            )
            .scalars()
            .all()
        )
        categories_by_id = {category.client_id: category for category in categories}

    return {
        "stock_report_items": [
            serialize_stock_report_item(
                row,
                category=categories_by_id[row.item_category_id],
                snapshot=snapshot,
                active_quantity_missing=active_quantity_missing,
            )
            for row, snapshot, active_quantity_missing in triples
        ],
        "stock_report_items_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
