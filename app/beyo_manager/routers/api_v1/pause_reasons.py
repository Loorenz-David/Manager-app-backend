from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.pause_reasons.create_pause_reason import (
    create_pause_reason,
)
from beyo_manager.services.commands.pause_reasons.delete_pause_reason import (
    delete_pause_reason,
)
from beyo_manager.services.commands.pause_reasons.update_pause_reason import (
    update_pause_reason,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.pause_reasons.get_pause_reason import (
    get_pause_reason,
)
from beyo_manager.services.queries.pause_reasons.list_pause_reasons import (
    list_pause_reasons,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


class _CreateBody(BaseModel):
    name: str
    image_url: str | None = None
    pause_type: PauseTypeEnum
    description: str | None = None
    requires_description: bool = False
    linked_user_ids: list[str] = Field(default_factory=list)
    linked_working_section_ids: list[str] = Field(default_factory=list)


class _UpdateBody(BaseModel):
    name: str | None = None
    image_url: str | None = None
    pause_type: PauseTypeEnum | None = None
    description: str | None = None
    requires_description: bool | None = None
    linked_user_ids: list[str] | None = None
    linked_working_section_ids: list[str] | None = None


@router.put("")
async def route_create_pause_reason(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(), identity=claims, session=session
    )
    outcome = await run_service(create_pause_reason, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_pause_reasons(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pause_type: PauseTypeEnum | None = Query(None),
    user_ids: list[str] | None = Query(None),
    working_section_ids: list[str] | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "pause_type": pause_type,
            "user_ids": user_ids,
            "working_section_ids": working_section_ids,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_pause_reasons, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_pause_reason(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id}, identity=claims, session=session
    )
    outcome = await run_service(get_pause_reason, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_pause_reason(
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
    outcome = await run_service(update_pause_reason, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_pause_reason(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id}, identity=claims, session=session
    )
    outcome = await run_service(delete_pause_reason, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
