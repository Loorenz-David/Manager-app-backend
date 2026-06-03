from sqlalchemy import or_, select

from beyo_manager.domain.items.serializers import serialize_item_issue
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_ALLOWED_STRING_COLUMNS = {
    "issue_type_snapshot": ItemIssue.issue_type_snapshot,
    "placement_of_issue_snapshot": ItemIssue.placement_of_issue_snapshot,
}


async def get_item_issues(ctx: ServiceContext) -> dict:
    item_id = ctx.incoming_data.get("item_id")
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    working_section_id = ctx.query_params.get("working_section_id")
    item_category_id = ctx.query_params.get("item_category_id")
    issue_type_id = ctx.query_params.get("issue_type_id")

    item = await ctx.session.scalar(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id == item_id,
            Item.is_deleted.is_(False),
        )
    )
    if item is None:
        raise NotFound("Item not found.")

    stmt = select(ItemIssue).where(
        ItemIssue.workspace_id == ctx.workspace_id,
        ItemIssue.item_id == item_id,
        ItemIssue.is_deleted.is_(False),
    )
    if working_section_id:
        supported_subq = (
            select(WorkingSectionSupportedIssueType.issue_type_id)
            .where(
                WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
                WorkingSectionSupportedIssueType.working_section_id == working_section_id,
            )
            .scalar_subquery()
        )
        stmt = stmt.where(
            or_(
                ItemIssue.issue_type_id.in_(supported_subq),
                ItemIssue.issue_type_id.is_(None) & (ItemIssue.working_section_id == working_section_id),
            )
        )
    if item_category_id:
        stmt = stmt.where(ItemIssue.item_category_id == item_category_id)
    if issue_type_id:
        stmt = stmt.where(ItemIssue.issue_type_id == issue_type_id)

    stmt = apply_string_filter(stmt, q, None, _ALLOWED_STRING_COLUMNS)
    stmt = stmt.order_by(ItemIssue.created_at.asc()).offset(offset).limit(limit + 1)

    rows = (await ctx.session.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "item_issues_pagination": {
            "items": [serialize_item_issue(row) for row in page],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
