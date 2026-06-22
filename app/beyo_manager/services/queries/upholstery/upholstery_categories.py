from sqlalchemy import and_, distinct, func, or_, select

from beyo_manager.domain.upholstery.serializers import serialize_upholstery_category
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.upholstery.upholstery_category import UpholsteryCategory
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_upholstery_categories(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    favorite_raw = ctx.query_params.get("favorite")

    stmt = select(UpholsteryCategory).where(
        UpholsteryCategory.workspace_id == ctx.workspace_id,
        UpholsteryCategory.is_deleted.is_(False),
    )

    if q:
        q_like = f"%{q}%"
        q_subq = (
            select(distinct(UpholsteryCategory.client_id))
            .select_from(UpholsteryCategory)
            .join(
                Upholstery,
                and_(
                    Upholstery.upholstery_category_id == UpholsteryCategory.client_id,
                    Upholstery.workspace_id == ctx.workspace_id,
                    Upholstery.is_deleted.is_(False),
                ),
                isouter=True,
            )
            .where(
                UpholsteryCategory.workspace_id == ctx.workspace_id,
                UpholsteryCategory.is_deleted.is_(False),
                or_(
                    UpholsteryCategory.name.ilike(q_like),
                    Upholstery.name.ilike(q_like),
                    Upholstery.code.ilike(q_like),
                ),
            )
        )
        stmt = stmt.where(UpholsteryCategory.client_id.in_(q_subq))

    if favorite_raw is not None:
        favorite = str(favorite_raw).strip().lower() == "true"
        stmt = stmt.where(UpholsteryCategory.favorite.is_(favorite))

    stmt = (
        stmt.order_by(
            UpholsteryCategory.favorite.desc(),
            UpholsteryCategory.created_at.asc(),
        )
        .offset(offset)
        .limit(limit + 1)
    )

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]
    category_ids = [row.client_id for row in page]

    count_map: dict[str, int] = {}
    if category_ids:
        count_result = await ctx.session.execute(
            select(
                Upholstery.upholstery_category_id,
                func.count(Upholstery.client_id),
            )
            .where(
                Upholstery.workspace_id == ctx.workspace_id,
                Upholstery.is_deleted.is_(False),
                Upholstery.upholstery_category_id.in_(category_ids),
            )
            .group_by(Upholstery.upholstery_category_id)
        )
        count_map = {
            category_id: count
            for category_id, count in count_result.all()
            if category_id is not None
        }

    return {
        "upholstery_categories": [
            serialize_upholstery_category(row, upholstery_count=count_map.get(row.client_id, 0))
            for row in page
        ],
        "upholstery_categories_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


async def get_upholstery_category(ctx: ServiceContext) -> dict:
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(UpholsteryCategory).where(
            UpholsteryCategory.workspace_id == ctx.workspace_id,
            UpholsteryCategory.client_id == client_id,
            UpholsteryCategory.is_deleted.is_(False),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise NotFound("Upholstery category not found.")

    count_result = await ctx.session.execute(
        select(func.count(Upholstery.client_id)).where(
            Upholstery.workspace_id == ctx.workspace_id,
            Upholstery.upholstery_category_id == category.client_id,
            Upholstery.is_deleted.is_(False),
        )
    )
    upholstery_count = int(count_result.scalar() or 0)

    return {
        "upholstery_category": serialize_upholstery_category(
            category,
            upholstery_count=upholstery_count,
        )
    }
