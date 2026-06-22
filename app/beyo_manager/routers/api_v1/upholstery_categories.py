from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.upholstery.create_upholstery_category import (
    create_upholstery_category,
)
from beyo_manager.services.commands.upholstery.delete_upholstery_category import (
    delete_upholstery_category,
)
from beyo_manager.services.commands.upholstery.mark_upholstery_category_favorite import (
    mark_upholstery_category_favorite,
)
from beyo_manager.services.commands.upholstery.update_upholstery_category import (
    update_upholstery_category,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.upholstery_categories import (
    get_upholstery_category,
    list_upholstery_categories,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-categories", tags=["upholstery-categories"])


class _CreateBody(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    favorite: bool = False


class _UpdateBody(BaseModel):
    name: str | None = None
    image_url: str | None = None


class _FavoriteBody(BaseModel):
    favorite: bool


@router.put("")
async def route_create_upholstery_category(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholstery_categories(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    favorite: bool | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "favorite": favorite,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_categories, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_upholstery_category(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(get_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_upholstery_category(
    client_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    data["client_id"] = client_id
    ctx = ServiceContext(incoming_data=data, identity=claims, session=session)
    outcome = await run_service(update_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_upholstery_category(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(delete_upholstery_category, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}/favorite")
async def route_mark_upholstery_category_favorite(
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
    outcome = await run_service(mark_upholstery_category_favorite, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
