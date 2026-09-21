"""`GET /api/v1/stock-report/items` — the board's read (master plan §6.5, phase 12;
intention §7A "Read order").

**Unpaginated by ratified owner answer** (master plan §5 overrides
`07_queries_local`'s pagination gate for this endpoint): no `_pagination` key is
emitted and none is accepted.
"""

from __future__ import annotations

from sqlalchemy import case, select

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.domain.stock_report.serializers import serialize_stock_report_item
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem

# §7A: `high` before `medium` before `low`. Ordering by the `priority` column itself
# would sort by the enum's text — `high, low, medium`.
# Written as explicit `when` pairs, not `case({...}, value=...)`: the mapping form
# binds each key as a bare parameter, and asyncpg then rejects the enum member
# (`invalid input for query argument … expected str`). Comparing the column takes
# the column's own type for the bind.
_PRIORITY_RANK = case(
    (StockReportItem.priority == StockReportPriorityEnum.HIGH, 1),
    (StockReportItem.priority == StockReportPriorityEnum.MEDIUM, 2),
    (StockReportItem.priority == StockReportPriorityEnum.LOW, 3),
)


def _parse_priority_filter(raw):
    """§7A: a comma list of `high|medium|low`. **Omitted or empty means the
    null-priority rows**, not "all rows" (ratified owner answer); an unknown token
    is a 422."""
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
    priorities = _parse_priority_filter(ctx.query_params.get("priority"))

    statement = select(StockReportItem).where(
        StockReportItem.workspace_id == ctx.workspace_id,
        StockReportItem.is_deleted.is_(False),
    )
    if priorities:
        statement = statement.where(
            StockReportItem.priority.in_(priorities)
        ).order_by(_PRIORITY_RANK, StockReportItem.priority_order.asc())
    else:
        statement = statement.where(StockReportItem.priority.is_(None)).order_by(
            StockReportItem.created_at.asc(), StockReportItem.client_id.asc()
        )

    rows = (
        (await ctx.session.execute(statement.execution_options(populate_existing=True)))
        .scalars()
        .all()
    )

    # Categories are batch-loaded **by id**, with no `is_deleted` filter: MC-16 says
    # a row whose category was soft-deleted keeps working and still serializes the
    # deleted category's name. An inner join carrying that filter would drop the row
    # from the payload entirely.
    categories_by_id = {}
    category_ids = {row.item_category_id for row in rows}
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
                row, category=categories_by_id[row.item_category_id]
            )
            for row in rows
        ]
    }
