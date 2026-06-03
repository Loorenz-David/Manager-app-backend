"""QUERY-1: List IssueTypes | QUERY-2: Get IssueType by ID."""

from sqlalchemy import exists, select

from beyo_manager.domain.issue_types.serializers import serialize_issue_type
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_category_issue_type import ItemCategoryIssueType
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _parse_csv_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


async def _load_issue_type_links(ctx: ServiceContext, issue_type_ids: list[str]) -> tuple[dict[str, list[str]], dict[str, list[dict]]]:
    if not issue_type_ids:
        return {}, {}

    working_section_rows = (
        await ctx.session.execute(
            select(WorkingSectionSupportedIssueType).where(
                WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
                WorkingSectionSupportedIssueType.issue_type_id.in_(issue_type_ids),
            )
        )
    ).scalars().all()
    item_category_rows = (
        await ctx.session.execute(
            select(ItemCategoryIssueType).where(
                ItemCategoryIssueType.workspace_id == ctx.workspace_id,
                ItemCategoryIssueType.issue_type_id.in_(issue_type_ids),
            )
        )
    ).scalars().all()

    working_section_map: dict[str, list[str]] = {}
    for row in working_section_rows:
        working_section_map.setdefault(row.issue_type_id, []).append(row.working_section_id)

    item_category_map: dict[str, list[dict]] = {}
    for row in item_category_rows:
        item_category_map.setdefault(row.issue_type_id, []).append(
            {
                "item_category_id": row.item_category_id,
                "placement_of_issue": row.placement_of_issue,
            }
        )

    return working_section_map, item_category_map


async def list_issue_types(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    working_section_ids = _parse_csv_values(ctx.query_params.get("working_section_id"))
    item_category_ids = _parse_csv_values(ctx.query_params.get("item_category_id"))

    stmt = select(IssueType).where(
        IssueType.workspace_id == ctx.workspace_id,
        IssueType.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(IssueType.name.ilike(pattern))

    if working_section_ids:
        stmt = stmt.where(
            exists(
                select(1).where(
                    WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
                    WorkingSectionSupportedIssueType.issue_type_id == IssueType.client_id,
                    WorkingSectionSupportedIssueType.working_section_id.in_(working_section_ids),
                )
            )
        )

    if item_category_ids:
        stmt = stmt.where(
            exists(
                select(1).where(
                    ItemCategoryIssueType.workspace_id == ctx.workspace_id,
                    ItemCategoryIssueType.issue_type_id == IssueType.client_id,
                    ItemCategoryIssueType.item_category_id.in_(item_category_ids),
                )
            )
        )

    stmt = stmt.order_by(IssueType.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]
    issue_type_ids = [row.client_id for row in page]
    working_section_map, item_category_map = await _load_issue_type_links(ctx, issue_type_ids)

    return {
        "issue_types": [
            serialize_issue_type(
                row,
                linked_working_section_ids=working_section_map.get(row.client_id, []),
                linked_item_category_ids=item_category_map.get(row.client_id, []),
                is_shared=len(working_section_map.get(row.client_id, [])) > 1,
            )
            for row in page
        ],
        "issue_types_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_issue_type(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(IssueType).where(
            IssueType.workspace_id == ctx.workspace_id,
            IssueType.client_id == client_id,
            IssueType.is_deleted.is_(False),
        )
    )
    issue_type = result.scalar_one_or_none()
    if issue_type is None:
        raise NotFound("Issue type not found.")

    working_section_map, item_category_map = await _load_issue_type_links(ctx, [issue_type.client_id])

    section_ids = working_section_map.get(issue_type.client_id, [])
    return {
        "issue_type": serialize_issue_type(
            issue_type,
            linked_working_section_ids=section_ids,
            linked_item_category_ids=item_category_map.get(issue_type.client_id, []),
            is_shared=len(section_ids) > 1,
        )
    }
