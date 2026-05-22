from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_categories.item_categories import (
    get_item_category,
    list_item_categories,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/item-categories", tags=["item-categories"])


@router.get("")
async def route_list_item_categories(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_item_categories, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_item_category(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_item_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
