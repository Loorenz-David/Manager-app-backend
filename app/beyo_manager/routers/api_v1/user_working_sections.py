from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.working_sections.assign_user_to_working_sections import (
    assign_user_to_working_sections,
)
from beyo_manager.services.commands.working_sections.unassign_user_from_working_sections import (
    unassign_user_from_working_sections,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


class AssignSectionsBody(BaseModel):
    working_section_ids: list[str]


class UnassignSectionsBody(BaseModel):
    working_section_ids: list[str]


@router.post("/{user_id}/working-sections")
async def assign_working_sections_route(
    user_id: str,
    body: AssignSectionsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_id": user_id, "working_section_ids": body.working_section_ids},
        identity=claims,
        session=session,
    )
    outcome = await run_service(assign_user_to_working_sections, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{user_id}/working-sections")
async def unassign_working_sections_route(
    user_id: str,
    body: UnassignSectionsBody = Body(...),
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"user_id": user_id, "working_section_ids": body.working_section_ids},
        identity=claims,
        session=session,
    )
    outcome = await run_service(unassign_user_from_working_sections, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
