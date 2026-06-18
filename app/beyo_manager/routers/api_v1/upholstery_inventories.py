from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.upholstery.add_ordered_to_inventory import add_ordered_to_inventory
from beyo_manager.services.commands.upholstery.confirm_ordered_to_stock_inventory import (
    confirm_ordered_to_stock_inventory,
)
from beyo_manager.services.commands.upholstery.create_upholstery_inventory import create_upholstery_inventory
from beyo_manager.services.commands.upholstery.delete_upholstery_inventory import delete_upholstery_inventory
from beyo_manager.services.commands.upholstery.set_current_stored_amount_inventory import (
    set_current_stored_amount_inventory,
)
from beyo_manager.services.commands.upholstery.update_upholstery_inventory import update_upholstery_inventory
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.get_upholstery_inventory import get_upholstery_inventory
from beyo_manager.services.queries.upholstery.list_upholstery_inventories import list_upholstery_inventories
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-inventories", tags=["upholstery-inventories"])


class _CreateBody(BaseModel):
    client_id: str | None = None
    upholstery_id: str
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None


class _UpdateBody(BaseModel):
    low_stock_threshold_meters: Decimal | None = None
    minimum_to_have: int | None = None
    maximum_to_have: int | None = None
    projected_inventory_value_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    planning_position: str | None = None


class _QuantityBody(BaseModel):
    quantity: Decimal


class _SetCurrentStoredAmountBody(BaseModel):
    current_stored_amount_meters: Decimal


@router.put("")
async def route_create_upholstery_inventory(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_upholstery_inventories(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    favorite: bool | None = Query(None),
    in_stock: bool | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "favorite": favorite,
            "in_stock": in_stock,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_upholstery_inventories, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_upholstery_inventory(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(get_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_upholstery_inventory(
    client_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    data["client_id"] = client_id
    ctx = ServiceContext(incoming_data=data, identity=claims, session=session)
    outcome = await run_service(update_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}/current-stored-amount")
async def route_set_current_stored_amount(
    client_id: str,
    body: _SetCurrentStoredAmountBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "client_id": client_id,
            "current_stored_amount_meters": body.current_stored_amount_meters,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(set_current_stored_amount_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_upholstery_inventory(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data={"client_id": client_id}, identity=claims, session=session)
    outcome = await run_service(delete_upholstery_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{client_id}/add-ordered")
async def route_add_ordered(
    client_id: str,
    body: _QuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, "quantity": body.quantity},
        identity=claims,
        session=session,
    )
    outcome = await run_service(add_ordered_to_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{client_id}/confirm-ordered")
async def route_confirm_ordered(
    client_id: str,
    body: _QuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, "quantity": body.quantity},
        identity=claims,
        session=session,
    )
    outcome = await run_service(confirm_ordered_to_stock_inventory, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
