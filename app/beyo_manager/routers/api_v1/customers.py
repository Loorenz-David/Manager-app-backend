"""Router: /api/v1/customers"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.customers.enums import CustomerStatusEnum, CustomerTypeEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.customers.create_customer import create_customer
from beyo_manager.services.commands.customers.delete_customer import delete_customer
from beyo_manager.services.commands.customers.find_or_create_customer import find_or_create_customer
from beyo_manager.services.commands.customers.update_customer import update_customer
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.customers.customers import get_customer, list_customers
from beyo_manager.services.run_service import run_service

router = APIRouter()


class _CreateCustomerBody(BaseModel):
    display_name: str
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None


class _UpdateCustomerBody(BaseModel):
    display_name: str | None = None
    customer_type: CustomerTypeEnum | None = None
    status: CustomerStatusEnum | None = None
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None


class _FindOrCreateCustomerBody(BaseModel):
    display_name: str
    primary_email: str | None = None
    primary_phone_number: str | None = None
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    address: dict | None = None


@router.put("")
async def route_create_customer(
    body: _CreateCustomerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_customers(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    string_filters: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q, "string_filters": string_filters},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_customers, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/find-or-create")
async def route_find_or_create_customer(
    body: _FindOrCreateCustomerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(find_or_create_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{client_id}")
async def route_get_customer(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_customer(
    client_id: str,
    body: _UpdateCustomerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_customer(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
