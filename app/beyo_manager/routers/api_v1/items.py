"""Router: /api/v1/items"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemUpholsterySourceEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.items.batch_create_item_issues import batch_create_item_issues
from beyo_manager.services.commands.items.batch_delete_item_issues import batch_delete_item_issues
from beyo_manager.services.commands.items.batch_update_item_positions import batch_update_item_positions
from beyo_manager.services.commands.items.create_item import create_item
from beyo_manager.services.commands.items.delete_item import delete_item
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.items.update_item import update_item
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.get_item_issues import get_item_issues
from beyo_manager.services.queries.items.lookup_item_by_article_number import lookup_item_by_article_number
from beyo_manager.services.queries.items.items import (
    get_item,
    list_item_upholstery_by_item_id,
    list_items,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


class _ItemIssueBody(BaseModel):
    client_id: str | None = None
    issue_type_id: str | None = None
    step_id: str
    worker_id: str
    working_section_id: str
    item_category_id: str
    issue_type_snapshot: str
    placement_of_issue_snapshot: str | None = None
    intensity: int


class _ItemUpholsteryBody(BaseModel):
    client_id: str | None = None
    upholstery_id: str | None = None
    source: ItemUpholsterySourceEnum
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    time_to_fix_in_seconds: int | None = None


class _CreateItemBody(BaseModel):
    client_id: str | None = None
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int = 1
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None
    item_issues: list[_ItemIssueBody] | None = None
    item_upholstery: _ItemUpholsteryBody | None = None


class _UpdateItemBody(BaseModel):
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int | None = None
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None


class _FindOrCreateItemBody(BaseModel):
    client_id: str | None = None
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int = 1
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None


class _BatchCreateIssuesBody(BaseModel):
    issues: list[_ItemIssueBody]


class _BatchDeleteIssueInput(BaseModel):
    item_issue_id: str


class _BatchDeleteIssuesBody(BaseModel):
    issues: list[_BatchDeleteIssueInput]


class _ItemPositionEntry(BaseModel):
    client_id: str
    item_position: str | None = None


class _BatchUpdateItemPositionsBody(BaseModel):
    entries: list[_ItemPositionEntry]


@router.put("")
async def route_create_item(
    body: _CreateItemBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_items(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_items, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}/issues")
async def route_delete_item_issues(
    client_id: str,
    body: _BatchDeleteIssuesBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_id": client_id, "issues": [entry.model_dump() for entry in body.issues]},
        identity=claims,
        session=session,
    )
    outcome = await run_service(batch_delete_item_issues, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{client_id}/issues")
async def route_create_item_issues(
    client_id: str,
    body: _BatchCreateIssuesBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_id": client_id, "issues": [entry.model_dump() for entry in body.issues]},
        identity=claims,
        session=session,
    )
    outcome = await run_service(batch_create_item_issues, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/find-or-create")
async def route_find_or_create_item(
    body: _FindOrCreateItemBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(exclude_unset=True),
        identity=claims,
        session=session,
    )
    outcome = await run_service(find_or_create_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}/issues")
async def route_list_item_issues(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    q: str | None = Query(None, max_length=200),
    working_section_id: str | None = Query(None),
    item_category_id: str | None = Query(None),
    issue_type_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"item_id": client_id},
        query_params={
            "q": q,
            "working_section_id": working_section_id,
            "item_category_id": item_category_id,
            "issue_type_id": issue_type_id,
            "limit": limit,
            "offset": offset,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_item_issues, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}/upholstery")
async def route_list_item_upholstery(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_item_upholstery_by_item_id, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/lookup")
async def route_lookup_item_by_article_number(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
    article_number: str | None = Query(None, min_length=1, max_length=128),
    sku: str | None = Query(None, min_length=1, max_length=128),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"article_number": article_number, "sku": sku},
        identity=claims,
        session=session,
    )
    outcome = await run_service(lookup_item_by_article_number, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_item(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/positions")
async def route_batch_update_item_positions(
    body: _BatchUpdateItemPositionsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"entries": [entry.model_dump() for entry in body.entries]},
        identity=claims,
        session=session,
    )
    outcome = await run_service(batch_update_item_positions, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_item(
    client_id: str,
    body: _UpdateItemBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_item(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_item, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
