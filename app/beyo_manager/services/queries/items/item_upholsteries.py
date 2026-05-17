"""Queries for ItemUpholstery and ItemUpholsteryRequirement."""

from sqlalchemy import desc, select

from beyo_manager.domain.items.serializers import (
    serialize_item_upholstery,
    serialize_upholstery_requirement,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


async def list_item_upholsteries(ctx: ServiceContext) -> dict:
    """List ItemUpholsteries with pagination."""
    limit = int(ctx.query_params.get("limit", _DEFAULT_LIMIT))
    offset = int(ctx.query_params.get("offset", 0))

    if limit < 1 or limit > _MAX_LIMIT:
        limit = _DEFAULT_LIMIT

    result = await ctx.session.execute(
        select(ItemUpholstery)
        .where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.is_deleted.is_(False),
        )
        .order_by(desc(ItemUpholstery.created_at))
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]

    iup_ids = [iup.client_id for iup in items]
    reqs_by_iup: dict[str, list[ItemUpholsteryRequirement]] = {}
    if iup_ids:
        req_result = await ctx.session.execute(
            select(ItemUpholsteryRequirement)
            .where(
                ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id.in_(iup_ids),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
            .order_by(ItemUpholsteryRequirement.created_at.asc())
        )
        for req in req_result.scalars().all():
            reqs_by_iup.setdefault(req.item_upholstery_id, []).append(req)

    return {
        "item_upholsteries_pagination": {
            "items": [
                serialize_item_upholstery(iup, reqs_by_iup.get(iup.client_id, []))
                for iup in items
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_item_upholstery(ctx: ServiceContext) -> dict:
    """Get single ItemUpholstery."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(ItemUpholstery).where(
            ItemUpholstery.workspace_id == ctx.workspace_id,
            ItemUpholstery.client_id == client_id,
            ItemUpholstery.is_deleted.is_(False),
        )
    )
    iup = result.scalar_one_or_none()
    if iup is None:
        raise NotFound("ItemUpholstery not found.")

    req_result = await ctx.session.execute(
        select(ItemUpholsteryRequirement)
        .where(
            ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
            ItemUpholsteryRequirement.item_upholstery_id == iup.client_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
        .order_by(ItemUpholsteryRequirement.created_at.asc())
    )
    requirements = req_result.scalars().all()

    return {"item_upholstery": serialize_item_upholstery(iup, requirements)}


async def list_upholstery_requirements(ctx: ServiceContext) -> dict:
    """List requirements for an item upholstery."""
    item_upholstery_id = ctx.incoming_data.get("item_upholstery_id")
    limit = int(ctx.query_params.get("limit", _DEFAULT_LIMIT))
    offset = int(ctx.query_params.get("offset", 0))

    if limit < 1 or limit > _MAX_LIMIT:
        limit = _DEFAULT_LIMIT

    result = await ctx.session.execute(
        select(ItemUpholsteryRequirement)
        .where(
            ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
            ItemUpholsteryRequirement.item_upholstery_id == item_upholstery_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
        .order_by(desc(ItemUpholsteryRequirement.created_at))
        .offset(offset)
        .limit(limit + 1)
    )
    rows = result.scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]

    return {
        "upholstery_requirements_pagination": {
            "items": [serialize_upholstery_requirement(req) for req in items],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_upholstery_requirement(ctx: ServiceContext) -> dict:
    """Get single requirement."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.workspace_id == ctx.workspace_id,
            ItemUpholsteryRequirement.client_id == client_id,
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise NotFound("ItemUpholsteryRequirement not found.")

    return {"requirement": serialize_upholstery_requirement(req)}
