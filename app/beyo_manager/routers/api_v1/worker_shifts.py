from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.users.pause_worker_shift import pause_worker_shift
from beyo_manager.services.commands.users.resume_worker_shift import resume_worker_shift
from beyo_manager.services.commands.users.toggle_worker_shift import toggle_worker_shift
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service


router = APIRouter()


class WorkerClockBody(BaseModel):
    user_id: str | None = None


class WorkerPauseBody(BaseModel):
    reason: str


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


@router.post("/pause")
async def pause_worker_shift_route(
    body: WorkerPauseBody,
    claims: dict = Depends(require_roles([WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(pause_worker_shift, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/resume")
async def resume_worker_shift_route(
    claims: dict = Depends(require_roles([WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={},
        identity=claims,
        session=session,
    )
    outcome = await run_service(resume_worker_shift, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
