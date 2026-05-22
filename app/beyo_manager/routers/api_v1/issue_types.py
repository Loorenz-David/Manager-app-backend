from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.issue_types.issue_category_configs import (
    get_issue_category_config,
    list_issue_category_configs,
)
from beyo_manager.services.queries.issue_types.issue_types import (
    get_issue_type,
    list_issue_types,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/issue-types", tags=["issue-types"])
category_configs_router = APIRouter(
    prefix="/api/v1/issue-category-configs", tags=["issue-category-configs"]
)


@router.get("")
async def route_list_issue_types(
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
    outcome = await run_service(list_issue_types, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_issue_type(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_issue_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@category_configs_router.get("")
async def route_list_issue_category_configs(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    item_category_id: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "item_category_id": item_category_id,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_issue_category_configs, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@category_configs_router.get("/{client_id}")
async def route_get_issue_category_config(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_issue_category_config, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
