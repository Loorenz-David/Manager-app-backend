from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.cases.create_case_type import create_case_type
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.cases.case_types import get_case_type, list_case_types
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/case-types", tags=["case-types"])


class _CreateCaseTypeBody(BaseModel):
    client_id: str | None = None
    name: str
    image_url: str | None = None
    description: str | None = None
    entity_type: str


@router.post("")
async def route_create_case_type(
    body: _CreateCaseTypeBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_case_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_case_types(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    entity_type: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "entity_type": entity_type,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_case_types, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_case_type(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_case_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
