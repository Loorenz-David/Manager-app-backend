from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.commands.sku_templates.reserve_sku_scalar import reserve_sku_scalar
from beyo_manager.services.commands.sku_templates.update_sku_template import update_sku_template
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.sku_templates.get_sku_template_by_task_type import get_sku_template_by_task_type
from beyo_manager.services.queries.sku_templates.list_sku_templates import list_sku_templates
from beyo_manager.services.run_service import run_service


router = APIRouter(prefix="/api/v1/sku-templates", tags=["sku-templates"])


class _CreateBody(BaseModel):
    task_type: TaskTypeEnum
    prefix: str
    separator: str = "-"
    pad_width: int = Field(default=0, ge=0)
    initial_scalar: int = Field(default=0, ge=0)


class _UpdateBody(BaseModel):
    prefix: str | None = None
    separator: str | None = None
    pad_width: int | None = Field(default=None, ge=0)
    last_scalar: int | None = Field(default=None, ge=0)


@router.get("")
async def route_list_sku_templates(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_sku_templates, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("")
async def route_create_sku_template(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_sku_template, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/by-task-type/{task_type}")
async def route_get_sku_template_by_task_type(
    task_type: TaskTypeEnum,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"task_type": task_type}, identity=claims, session=session)
    outcome = await run_service(get_sku_template_by_task_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/by-task-type/{task_type}/reserve")
async def route_reserve_sku_scalar(
    task_type: TaskTypeEnum,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"task_type": task_type}, identity=claims, session=session)
    outcome = await run_service(reserve_sku_scalar, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_sku_template(
    client_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_sku_template, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
