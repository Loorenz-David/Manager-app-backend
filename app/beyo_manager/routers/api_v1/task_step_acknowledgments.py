from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.task_step_acknowledgments.acknowledge_step_acknowledgments import (
    acknowledge_step_acknowledgments,
)
from beyo_manager.services.commands.task_step_acknowledgments.mark_step_acknowledgments_seen import (
    mark_step_acknowledgments_seen,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.task_step_acknowledgments.list_pending_step_acknowledgments import (
    list_pending_step_acknowledgments,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


class StepAcknowledgmentActionBody(BaseModel):
    step_ids: list[str]


@router.get("/pending")
async def list_pending_step_acknowledgments_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_pending_step_acknowledgments, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/seen")
async def mark_step_acknowledgments_seen_route(
    body: StepAcknowledgmentActionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_step_acknowledgments_seen, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/acknowledge")
async def acknowledge_step_acknowledgments_route(
    body: StepAcknowledgmentActionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(acknowledge_step_acknowledgments, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
