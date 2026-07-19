from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_daily_step_breakdown import (
    get_worker_daily_step_breakdown,
)
from beyo_manager.services.queries.worker_stats.list_workers_insights import list_workers_insights
from beyo_manager.services.queries.worker_stats.list_workers_last_interacted_step import (
    list_workers_last_interacted_step,
)
from beyo_manager.services.queries.worker_stats.list_workers_totals import list_workers_totals
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.get("/last-interacted-steps")
async def get_workers_last_interacted_step_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    work_date: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            **({"work_date": work_date} if work_date else {}),
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_workers_last_interacted_step, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/totals")
async def get_workers_totals_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    time_strategy: str = Query("median"),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            **({"date_from": date_from} if date_from else {}),
            **({"date_to": date_to} if date_to else {}),
            "time_strategy": time_strategy,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_workers_totals, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/insights")
async def get_workers_insights_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    work_date: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            **({"work_date": work_date} if work_date else {}),
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_workers_insights, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{user_id}/daily-steps")
async def get_worker_daily_step_breakdown_route(
    user_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort_by: str = Query("contribution"),
    order: str = Query("desc"),
    time_strategy: str = Query("median"),
    only_inaccurate: bool = Query(False),
):
    ctx = ServiceContext(
        incoming_data={"user_id": user_id},
        query_params={
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "order": order,
            "time_strategy": time_strategy,
            "only_inaccurate": only_inaccurate,
            **({"date_from": date_from} if date_from else {}),
            **({"date_to": date_to} if date_to else {}),
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_worker_daily_step_breakdown, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
