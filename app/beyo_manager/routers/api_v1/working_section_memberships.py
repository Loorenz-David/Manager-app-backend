from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.list_working_section_members import (
    list_working_section_members,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.get("/{working_section_id}/members")
async def list_working_section_members_route(
    working_section_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"working_section_id": working_section_id},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_working_section_members, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
