"""The lookup engine shared by both Scanner stock webhooks (intention §14E E4:
"the same engine as find-or-create"). Phase 6 (demand) is the first caller; phase
13A (delete) reuses both functions unchanged with `DemandDeleteEntry`.

Both functions take a list of any entry type exposing `item_category_key` and
`properties_signature` for category resolution; `discover_live_rows_by_identity`
takes the already-resolved `(item_category_id, properties_signature)` identity
tuples directly, matching its own return type `dict[tuple[str, str], str]`
(master plan §6.5).
"""

from sqlalchemy import func, select, tuple_

from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem


async def resolve_categories_for_entries(session, *, workspace_id, entries):
    """MC-8 category resolution: exact `strip(itemCategory)` match first, else a
    unique case-insensitive match, else unresolved (`None`). One `SELECT` of
    candidates; resolution itself happens in memory. Returns `item_category_key ->
    category client_id | None`.
    """
    keys = {entry.item_category_key for entry in entries}
    if not keys:
        return {}
    candidates = (
        await session.execute(
            select(ItemCategory.client_id, ItemCategory.name).where(
                ItemCategory.workspace_id == workspace_id,
                ItemCategory.is_deleted.is_(False),
                func.lower(ItemCategory.name).in_(keys),
            )
        )
    ).all()
    resolved: dict[str, str | None] = {}
    for entry in entries:
        key = entry.item_category_key
        if key in resolved:
            continue
        raw = entry.item_category_raw.strip()
        exact = [candidate for candidate in candidates if candidate.name == raw]
        if len(exact) == 1:
            resolved[key] = exact[0].client_id
            continue
        case_insensitive = [
            candidate for candidate in candidates if candidate.name.lower() == key
        ]
        resolved[key] = (
            case_insensitive[0].client_id if len(case_insensitive) == 1 else None
        )
    return resolved


async def discover_live_rows_by_identity(session, *, workspace_id, identities):
    """Unlocked identity discovery (D6 step 4): one `SELECT` of the identity columns
    only, no ORM entity load (an unlocked read only discovers ids, MC-1). Returns
    `(item_category_id, properties_signature) -> row client_id`.
    """
    identities = list(identities)
    if not identities:
        return {}
    rows = (
        await session.execute(
            select(
                StockReportItem.client_id,
                StockReportItem.item_category_id,
                StockReportItem.properties_signature,
            ).where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.is_deleted.is_(False),
                tuple_(
                    StockReportItem.item_category_id,
                    StockReportItem.properties_signature,
                ).in_(identities),
            )
        )
    ).all()
    return {
        (row.item_category_id, row.properties_signature): row.client_id
        for row in rows
    }
