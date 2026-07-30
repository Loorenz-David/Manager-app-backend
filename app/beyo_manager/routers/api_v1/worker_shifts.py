from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.users.close_declared_worker_state import (
    close_declared_worker_state,
)
from beyo_manager.services.commands.users.clock_in_worker_shift import clock_in_worker_shift
from beyo_manager.services.commands.users.clock_out_worker_shift import clock_out_worker_shift
from beyo_manager.services.commands.users.declare_worker_state import declare_worker_state
from beyo_manager.services.commands.users.toggle_worker_shift import toggle_worker_shift
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.get_current_worker_shift_state import (
    get_current_worker_shift_state,
)
from beyo_manager.services.run_service import run_service


router = APIRouter()


class WorkerClockBody(BaseModel):
    user_id: str | None = None


class WorkerDeclareStateBody(BaseModel):
    user_id: str | None = None
    pause_reason_id: str
    description: str | None = None


class WorkerCloseDeclaredStateBody(BaseModel):
    user_id: str | None = None


@router.get("/current")
async def get_current_worker_shift_state_route(
    user_id: str | None = None,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"user_id": user_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_current_worker_shift_state, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/clock-in")
async def clock_in_worker_shift_route(
    body: WorkerClockBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(clock_in_worker_shift, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/clock-out")
async def clock_out_worker_shift_route(
    body: WorkerClockBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(clock_out_worker_shift, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/clock")
async def toggle_worker_shift_route(
    body: WorkerClockBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(toggle_worker_shift, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/declared-states")
async def declare_worker_state_route(
    body: WorkerDeclareStateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(declare_worker_state, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/declared-states/close")
async def close_declared_worker_state_route(
    body: WorkerCloseDeclaredStateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(close_declared_worker_state, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
