"""QUERY-1: List IssueCategoryConfigs | QUERY-2: Get IssueCategoryConfig by ID."""

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select

from beyo_manager.domain.issue_types.serializers import serialize_issue_category_config
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_issue_category_configs(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    item_category_id = ctx.query_params.get("item_category_id")

    stmt = (
        select(IssueCategoryConfig, IssueType.name.label("issue_type_name"))
        .join(
            IssueType,
            and_(
                IssueType.client_id == IssueCategoryConfig.issue_type_id,
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.is_deleted.is_(False),
            ),
        )
        .where(
            IssueCategoryConfig.workspace_id == ctx.workspace_id,
            IssueCategoryConfig.is_deleted.is_(False),
        )
    )

    if q:
        stmt = stmt.where(IssueType.name.ilike(f"%{q}%"))

    if item_category_id:
        stmt = stmt.where(IssueCategoryConfig.item_category_id == item_category_id)

    now = datetime.now(timezone.utc)
    stmt = stmt.where(
        or_(IssueCategoryConfig.effective_from.is_(None), IssueCategoryConfig.effective_from <= now),
        or_(IssueCategoryConfig.effective_to.is_(None), IssueCategoryConfig.effective_to >= now),
    )

    stmt = stmt.order_by(IssueCategoryConfig.created_at.asc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "issue_category_configs": [
            serialize_issue_category_config(config, name) for config, name in page
        ],
        "issue_category_configs_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_issue_category_config(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(IssueCategoryConfig, IssueType.name.label("issue_type_name"))
        .join(
            IssueType,
            and_(
                IssueType.client_id == IssueCategoryConfig.issue_type_id,
                IssueType.workspace_id == ctx.workspace_id,
                IssueType.is_deleted.is_(False),
            ),
        )
        .where(
            IssueCategoryConfig.workspace_id == ctx.workspace_id,
            IssueCategoryConfig.client_id == client_id,
            IssueCategoryConfig.is_deleted.is_(False),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise NotFound("Issue category config not found.")

    config, issue_type_name = row
    return {"issue_category_config": serialize_issue_category_config(config, issue_type_name)}
