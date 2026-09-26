"""`GET /api/v1/stock-report/items` — the board's read (master plan §6.5, phase 12;
intention §7A "Read order"), a **snapshot read** since 2026-09-26.

By default a row is on the board only through its **active item snapshot**: the
statement inner-joins the snapshot, the priority filter and ordering are the
snapshot's, and "zero requested" means the snapshot's `quantity_requested −
quantity_missing <= 0` (the workers' outstanding count, not Scanner's live demand).
`live_stock=true` is the old read of the mirror itself — every live row, the snapshot
attached when there is one and `null` otherwise; the snapshot filters (`priority`,
`missing_only`) are refused on it because they have nothing to filter.

**Unpaginated by ratified owner answer** (master plan §5 overrides
`07_queries_local`'s pagination gate for this endpoint): no `_pagination` key is
emitted and none is accepted.
"""

from __future__ import annotations

from sqlalchemy import and_, case, select

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
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

_ACTIVE_SNAPSHOT_JOIN = and_(
    StockReportItemSnapshot.stock_report_item_id == StockReportItem.client_id,
    StockReportItemSnapshot.closed_at.is_(None),
)


def _parse_priority_filter(raw):
    """§7A: a comma list of `high|medium|low`. **Omitted or empty means the
    null-priority snapshots**, not "all rows" (ratified owner answer); an unknown
    token is a 422."""
    if raw is None:
        return []
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    priorities = []
    for token in tokens:
        try:
            priorities.append(StockReportPriorityEnum(token))
        except ValueError:
            raise ValidationError(
                f"STOCK_REPORT_UNKNOWN_PRIORITY_FILTER: '{token}' is not one of "
                "high, medium, low."
            ) from None
    return priorities


async def list_stock_report_items(ctx) -> dict:
    raw_priority = ctx.query_params.get("priority")
    priorities = _parse_priority_filter(raw_priority)
    include_zero_requested = ctx.query_params.get("include_zero_requested", False)
    item_major_categories = ctx.query_params.get("item_major_categories")
    item_category_ids = ctx.query_params.get("item_category_ids")
    live_stock = bool(ctx.query_params.get("live_stock", False))
    missing_only = bool(ctx.query_params.get("missing_only", False))

    if live_stock and (raw_priority is not None or missing_only):
        raise ValidationError(
            "STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT: `priority` and `missing_only` "
            "filter the active snapshot and cannot be combined with `live_stock`."
        )

    statement = select(StockReportItem, StockReportItemSnapshot).where(
        StockReportItem.workspace_id == ctx.workspace_id,
        StockReportItem.is_deleted.is_(False),
    )
    if live_stock:
        statement = statement.outerjoin(StockReportItemSnapshot, _ACTIVE_SNAPSHOT_JOIN)
        if not include_zero_requested:
            statement = statement.where(StockReportItem.quantity_requested > 0)
        statement = statement.order_by(
            StockReportItem.created_at.asc(), StockReportItem.client_id.asc()
        )
    else:
        statement = statement.join(StockReportItemSnapshot, _ACTIVE_SNAPSHOT_JOIN)
        if not include_zero_requested:
            statement = statement.where(
                (
                    StockReportItemSnapshot.quantity_requested
                    - StockReportItemSnapshot.quantity_missing
                )
                > 0
            )
        if missing_only:
            statement = statement.where(StockReportItemSnapshot.quantity_missing > 0)
        if priorities:
            statement = statement.where(
                StockReportItemSnapshot.priority.in_(priorities)
            ).order_by(_PRIORITY_RANK, StockReportItemSnapshot.priority_order.asc())
        else:
            statement = statement.where(
                StockReportItemSnapshot.priority.is_(None)
            ).order_by(StockReportItem.created_at.asc(), StockReportItem.client_id.asc())

    if item_major_categories is not None:
        # Deliberately no category `is_deleted` predicate: rows keep their category
        # identity after a category soft-delete and remain filterable by its major
        # category, just as they remain serializable below.
        statement = statement.join(
            ItemCategory, ItemCategory.client_id == StockReportItem.item_category_id
        ).where(
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.major_category.in_(item_major_categories),
        )
    if item_category_ids is not None:
        statement = statement.where(StockReportItem.item_category_id.in_(item_category_ids))

    # Two entities per result row: `.scalars()` would keep only the first and drop
    # the snapshot silently, so the pairs are read whole.
    pairs = (
        await ctx.session.execute(statement.execution_options(populate_existing=True))
    ).all()

    # Categories are batch-loaded **by id**, with no `is_deleted` filter: MC-16 says
    # a row whose category was soft-deleted keeps working and still serializes the
    # deleted category's name. An inner join carrying that filter would drop the row
    # from the payload entirely.
    categories_by_id = {}
    category_ids = {row.item_category_id for row, _snapshot in pairs}
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
                row, category=categories_by_id[row.item_category_id], snapshot=snapshot
            )
            for row, snapshot in pairs
        ]
    }
