from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.upholstery.enums import UpholsteryCurrencyEnum, UpholsteryOrderStateEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.upholstery.create_upholstery_order import create_upholstery_order
from beyo_manager.services.commands.upholstery.receive_upholstery_order import receive_upholstery_order
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter(prefix="/api/v1/upholstery-orders", tags=["upholstery-orders"])


class _CreateBody(BaseModel):
    client_id: str | None = None
    upholstery_id: str
    order_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    state: UpholsteryOrderStateEnum = UpholsteryOrderStateEnum.ORDERED
    supplier_id: str | None = None
    upholstery_supplier_link_id: str | None = None
    price_minor: int | None = None
    currency: UpholsteryCurrencyEnum | None = None
    order_at: datetime | None = None
    expected_receive_at: datetime | None = None


class _ReceiveBody(BaseModel):
    client_id: str
    received_amount_meters: Decimal
    priority_item_upholstery_ids: list[str] = []
    received_at: datetime | None = None


@router.put("")
async def route_create_upholstery_order(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(create_upholstery_order, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/receive")
async def route_receive_upholstery_order(
    body: _ReceiveBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
    outcome = await run_service(receive_upholstery_order, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
