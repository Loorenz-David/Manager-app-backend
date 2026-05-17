from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.items.apply_surplus_to_requirement import apply_surplus_to_requirement
from beyo_manager.services.commands.items.complete_single_and_reallocate import (
    complete_single_requirement,
    reallocate_stock,
)
from beyo_manager.services.commands.items.create_item_upholstery import create_item_upholstery
from beyo_manager.services.commands.items.mark_requirements_completed import mark_requirements_completed
from beyo_manager.services.commands.items.mark_requirements_in_use import mark_requirements_in_use
from beyo_manager.services.commands.items.mark_requirements_ordered import mark_requirements_ordered
from beyo_manager.services.commands.items.resolve_requirements_after_stock import resolve_requirements_after_stock
from beyo_manager.services.commands.items.set_requirement_quantity import set_requirement_quantity
from beyo_manager.services.commands.items.update_and_delete_item_upholstery import (
    delete_item_upholstery,
    update_item_upholstery,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.item_upholsteries import (
    get_item_upholstery,
    get_upholstery_requirement,
    list_item_upholsteries,
    list_upholstery_requirements,
)
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/item-upholsteries", tags=["item-upholsteries"])
requirements_router = APIRouter(
    prefix="/api/v1/upholstery-requirements", tags=["upholstery-requirements"]
)


# ── Request body models ────────────────────────────────────────────────────────

class _CreateBody(BaseModel):
    item_id: str
    upholstery_id: str | None = None
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    source: ItemUpholsterySourceEnum
    time_to_fix_in_seconds: int | None = None


class _UpdateBody(BaseModel):
    name: str | None = None
    code: str | None = None
    amount_meters: Decimal | None = None
    time_to_fix_in_seconds: int | None = None


class _MarkOrderedBody(BaseModel):
    upholstery_id: str
    ordered_quantity: Decimal
    priority_item_upholstery_ids: list[str] = []


class _ResolveAfterStockBody(BaseModel):
    upholstery_id: str
    priority_item_upholstery_ids: list[str] = []


class _ReallocateBody(BaseModel):
    upholstery_id: str
    donor_item_upholstery_ids: list[str] = []
    priority_item_upholstery_ids: list[str] = []


class _ApplySurplusBody(BaseModel):
    surplus_amount_meters: Decimal


class _SetQuantityBody(BaseModel):
    amount_meters: Decimal


# ── Static collection-level routes (declared before wildcard /{client_id}) ─────

@router.put("")
async def route_create_item_upholstery(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_item_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_item_upholsteries(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
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
    outcome = await run_service(list_item_upholsteries, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/mark-ordered")
async def route_mark_ordered(
    body: _MarkOrderedBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(mark_requirements_ordered, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/resolve-after-stock")
async def route_resolve_after_stock(
    body: _ResolveAfterStockBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(resolve_requirements_after_stock, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/reallocate-stock")
async def route_reallocate_stock(
    body: _ReallocateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(reallocate_stock, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ── Wildcard /{client_id} routes ───────────────────────────────────────────────

@router.post("/{client_id}/mark-in-use")
async def route_mark_in_use(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_requirements_in_use, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{client_id}/complete")
async def route_mark_completed(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_requirements_completed, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{client_id}/apply-surplus")
async def route_apply_surplus(
    client_id: str,
    body: _ApplySurplusBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "item_upholstery_id": client_id,
            "surplus_amount_meters": body.surplus_amount_meters,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(apply_surplus_to_requirement, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{client_id}/set-quantity")
async def route_set_quantity(
    client_id: str,
    body: _SetQuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "item_upholstery_id": client_id,
            "amount_meters": body.amount_meters,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(set_requirement_quantity, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}/requirements")
async def route_list_requirements(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"item_upholstery_id": client_id},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_requirements, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_item_upholstery(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(get_item_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_item_upholstery(
    client_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    data["client_id"] = client_id
    ctx = ServiceContext(incoming_data=data, identity=claims, session=session)
    outcome = await run_service(update_item_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_item_upholstery(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(delete_item_upholstery, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ── Upholstery requirements sub-router (/api/v1/upholstery-requirements) ───────

@requirements_router.get("/{client_id}")
async def route_get_requirement(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(get_upholstery_requirement, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@requirements_router.post("/{client_id}/complete")
async def route_complete_single_requirement(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(complete_single_requirement, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
