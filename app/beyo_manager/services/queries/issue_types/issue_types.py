"""QUERY-1: List IssueTypes | QUERY-2: Get IssueType by ID."""

from sqlalchemy import select

from beyo_manager.domain.issue_types.serializers import serialize_issue_type
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_issue_types(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")

    stmt = select(IssueType).where(
        IssueType.workspace_id == ctx.workspace_id,
        IssueType.is_deleted.is_(False),
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(IssueType.name.ilike(pattern))

    stmt = stmt.order_by(IssueType.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "issue_types": [serialize_issue_type(r) for r in page],
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

    return {"issue_type": serialize_issue_type(issue_type)}
