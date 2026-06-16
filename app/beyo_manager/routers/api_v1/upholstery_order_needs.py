from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.upholstery_order_needs import (
    get_upholstery_order_need_items,
    get_upholstery_order_needs_count,
    list_upholstery_order_needs,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-order-needs", tags=["upholstery-order-needs"])


@router.get("/count")
async def route_get_upholstery_order_needs_count(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery_order_needs_count, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholstery_order_needs(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_order_needs, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{upholstery_id}/items")
async def route_get_upholstery_order_need_items(
    upholstery_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={"upholstery_id": upholstery_id},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_upholstery_order_need_items, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
