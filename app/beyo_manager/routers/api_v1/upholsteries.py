from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.upholstery.create_upholstery import create_upholstery
from beyo_manager.services.commands.upholstery.delete_upholstery import delete_upholstery
from beyo_manager.services.commands.upholstery.mark_upholsteries_favorite import (
    mark_upholsteries_favorite,
)
from beyo_manager.services.commands.upholstery.mark_upholstery_favorite import (
    mark_upholstery_favorite,
)
from beyo_manager.services.commands.upholstery.update_upholstery import update_upholstery
from beyo_manager.services.commands.upholstery.update_upholstery_list_order import (
    update_upholstery_list_order,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.list_nevotex_upholsteries import (
    list_nevotex_upholsteries,
)
from beyo_manager.services.queries.upholstery.upholsteries import (
    get_upholstery,
    list_upholsteries,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholsteries", tags=["upholsteries"])


class _InlineCategoryBody(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    favorite: bool = False


class _CreateBody(BaseModel):
    client_id: str | None = None
    name: str
    code: str | None = None
    image_url: str | None = None
    favorite: bool = False
    current_stored_amount_meters: Decimal | None = None
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None
    upholstery_category_id: str | None = None
    upholstery_category_name: str | None = None
    create_category: _InlineCategoryBody | None = None
    upholstery_inventory_id: str | None = None


class _UpdateBody(BaseModel):
    name: str | None = None
    code: str | None = None
    image_url: str | None = None
    favorite: bool | None = None
    upholstery_category_id: str | None = None


class _FavoriteBody(BaseModel):
    favorite: bool


class _BatchFavoriteBody(BaseModel):
    upholstery_ids: list[str]
    favorite: bool


class _ListOrderBody(BaseModel):
    list_order: int | None = None


@router.put("")
async def route_create_upholstery(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholsteries(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    in_stock: bool | None = Query(None),
    favorite: bool | None = Query(None),
    upholstery_category_ids: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "in_stock": in_stock,
            "favorite": favorite,
            "upholstery_category_ids": upholstery_category_ids,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholsteries, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/external/nevotex")
async def route_list_nevotex_upholsteries(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(7, ge=1, le=20),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"q": q, "limit": limit},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_nevotex_upholsteries, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/favorite")
async def route_mark_upholsteries_favorite(
    body: _BatchFavoriteBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(mark_upholsteries_favorite, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_upholstery(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(get_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_upholstery(
    client_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    data["client_id"] = client_id
    ctx = ServiceContext(incoming_data=data, identity=claims, session=session)
    outcome = await run_service(update_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_upholstery(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(delete_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}/favorite")
async def route_mark_upholstery_favorite(
    client_id: str,
    body: _FavoriteBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, "favorite": body.favorite},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_upholstery_favorite, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}/list-order")
async def route_update_upholstery_list_order(
    client_id: str,
    body: _ListOrderBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, "list_order": body.list_order},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_upholstery_list_order, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
