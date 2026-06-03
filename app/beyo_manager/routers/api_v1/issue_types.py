from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.issue_types.enums import IssueModeEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.issue_types.create_issue_type import create_issue_type
from beyo_manager.services.commands.issue_types.delete_issue_types import delete_issue_types
from beyo_manager.services.commands.issue_types.update_issue_type import update_issue_type
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.issue_types.issue_types import (
    get_issue_type,
    list_issue_types,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/issue-types", tags=["issue-types"])


class _ItemCategoryLinkBody(BaseModel):
    item_category_id: str
    placement_of_issue: str | None = None


class _CreateIssueTypeBody(BaseModel):
    issue_type_name: str
    issue_mode: IssueModeEnum
    linked_working_section_ids: list[str] = []
    linked_item_category_ids: list[_ItemCategoryLinkBody] = []


class _UpdateIssueTypeBody(BaseModel):
    issue_type_name: str | None = None
    issue_mode: IssueModeEnum | None = None
    linked_working_section_ids: list[str] | None = None
    linked_item_category_ids: list[_ItemCategoryLinkBody] | None = None


class _DeleteIssueTypeInput(BaseModel):
    issue_type_id: str


class _DeleteIssueTypesBody(BaseModel):
    issues: list[_DeleteIssueTypeInput]


@router.get("")
async def route_list_issue_types(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    working_section_id: str | None = Query(None),
    item_category_id: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "working_section_id": working_section_id,
            "item_category_id": item_category_id,
        },
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


@router.put("")
async def route_create_issue_type(
    body: _CreateIssueTypeBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_issue_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_issue_type(
    client_id: str,
    body: _UpdateIssueTypeBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"issue_type_id": client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_issue_type, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("")
async def route_delete_issue_types(
    body: _DeleteIssueTypesBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"issues": [entry.model_dump() for entry in body.issues]},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_issue_types, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
