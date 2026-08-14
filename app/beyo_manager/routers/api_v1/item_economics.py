from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.item_economics.add_section_to_cost_group import add_section_to_cost_group
from beyo_manager.services.commands.item_economics.create_cost_model_version import create_cost_model_version
from beyo_manager.services.commands.item_economics.create_production_cost_basis_version import create_production_cost_basis_version
from beyo_manager.services.commands.item_economics.create_production_cost_group import create_production_cost_group
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import commit_item_cost_evaluation
from beyo_manager.services.commands.item_economics.create_item_cost_projection import create_item_cost_projection
from beyo_manager.services.commands.item_economics.delete_cost_model_version import delete_cost_model_version
from beyo_manager.services.commands.item_economics.delete_item_valuation import delete_item_valuation
from beyo_manager.services.commands.item_economics.delete_item_cost_projection import delete_item_cost_projection
from beyo_manager.services.commands.item_economics.delete_production_cost_basis_version import delete_production_cost_basis_version
from beyo_manager.services.commands.item_economics.delete_production_cost_group import delete_production_cost_group
from beyo_manager.services.commands.item_economics.remove_section_from_cost_group import remove_section_from_cost_group
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.commands.item_economics.promote_item_cost_projection import promote_item_cost_projection
from beyo_manager.services.commands.item_economics.update_production_cost_group import update_production_cost_group
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_economics_configuration_status import get_economics_configuration_status
from beyo_manager.services.queries.item_economics.get_item_lifetime_economics import get_item_lifetime_economics
from beyo_manager.services.queries.item_economics.get_task_budget_status import get_task_budget_status
from beyo_manager.services.queries.item_economics.get_task_budget_status_worker import get_task_budget_status_worker
from beyo_manager.services.queries.item_economics.list_cost_model_versions import list_cost_model_versions
from beyo_manager.services.queries.item_economics.list_production_cost_basis_versions import list_production_cost_basis_versions
from beyo_manager.services.queries.item_economics.list_production_cost_groups import list_production_cost_groups
from beyo_manager.services.queries.item_economics.get_item_valuation_history import get_item_valuation_history
from beyo_manager.services.queries.item_economics.list_task_evaluations import list_task_evaluations
from beyo_manager.services.run_service import run_service
from beyo_manager.domain.item_economics.serializers import (
    serialize_task_budget_status,
)

router = APIRouter()


class _CreateGroupBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    major_category: ItemMajorCategoryEnum


class _UpdateGroupBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    major_category: ItemMajorCategoryEnum | None = None


class _SectionBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    working_section_id: str


class _BasisVersionBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    effective_from: date | None = None
    fixed_monthly_cost_minor: int
    currency: ItemCurrencyEnum
    monthly_paid_hours: Decimal
    planning_utilization_percent: Decimal


_PERCENT_DESCRIPTION = (
    "Planning allocation percentage, never legally payable tax. "
    "For a statutory 25% VAT-on-net example, enter 20.00 against the gross base; this is not a tax calculation."
)


class _CostModelTermBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    calculation_type: CostModelTermCalculationTypeEnum
    percent_value: Decimal | None = Field(default=None, description=_PERCENT_DESCRIPTION)
    fixed_amount_minor: int | None = None


class _CostModelVersionBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    effective_from: date | None = None
    currency: ItemCurrencyEnum
    terms: list[_CostModelTermBody] = Field(default_factory=list)


class _ItemValuationBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    expected_sale_price_minor: int | None = Field(default=None, ge=0)
    purchase_cost_minor: int | None = Field(default=None, ge=0)
    currency: ItemCurrencyEnum


class _CommitEvaluationBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    expected_sale_price_minor: int | None = Field(default=None, ge=0)
    purchase_cost_minor: int | None = Field(default=None, ge=0)
    label: str | None = Field(default=None, max_length=255)


class _ProjectionBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: Literal["committed", "projection", "scratch"] = "scratch"
    source_projection_id: str | None = None
    expected_sale_price_minor: int | None = Field(default=None, ge=0)
    purchase_cost_minor: int | None = Field(default=None, ge=0)
    label: str | None = Field(default=None, max_length=255)


def _ctx(claims: dict, session: AsyncSession, data: dict | None = None, query: dict | None = None) -> ServiceContext:
    return ServiceContext(
        incoming_data=data or {},
        query_params=query or {},
        identity=claims,
        session=session,
    )


async def _run(function, claims: dict, session: AsyncSession, *, data: dict | None = None, query: dict | None = None):
    outcome = await run_service(function, _ctx(claims, session, data, query))
    return build_err(outcome.error) if not outcome.success else build_ok(outcome.data)


async def _run_budget_status(claims: dict, session: AsyncSession, task_client_id: str):
    worker_view = claims.get("role_name") in {WORKER, SELLER}
    function = get_task_budget_status_worker if worker_view else get_task_budget_status
    outcome = await run_service(
        function,
        _ctx(claims, session, data={"task_client_id": task_client_id}),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(
        serialize_task_budget_status(outcome.data, include_monetary=not worker_view)
    )


@router.post("/cost-groups")
async def route_create_production_cost_group(
    body: _CreateGroupBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(create_production_cost_group, claims, session, data=body.model_dump())


@router.get("/cost-groups")
async def route_list_production_cost_groups(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await _run(list_production_cost_groups, claims, session, query={"limit": limit, "offset": offset})


@router.patch("/cost-groups/{client_id}")
async def route_update_production_cost_group(
    client_id: str,
    body: _UpdateGroupBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(update_production_cost_group, claims, session, data={"client_id": client_id, **body.model_dump()})


@router.delete("/cost-groups/{client_id}")
async def route_delete_production_cost_group(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_production_cost_group, claims, session, data={"client_id": client_id})


@router.post("/cost-groups/{client_id}/sections")
async def route_add_section_to_cost_group(
    client_id: str,
    body: _SectionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(add_section_to_cost_group, claims, session, data={"production_cost_group_id": client_id, **body.model_dump()})


@router.delete("/cost-groups/{client_id}/sections/{working_section_client_id}")
async def route_remove_section_from_cost_group(
    client_id: str,
    working_section_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(remove_section_from_cost_group, claims, session, data={"production_cost_group_id": client_id, "working_section_id": working_section_client_id})


@router.post("/cost-groups/{client_id}/basis-versions")
async def route_create_production_cost_basis_version(
    client_id: str,
    body: _BasisVersionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    data = {"production_cost_group_id": client_id, **body.model_dump()}
    return await _run(create_production_cost_basis_version, claims, session, data=data)


@router.get("/cost-groups/{client_id}/basis-versions")
async def route_list_production_cost_basis_versions(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await _run(list_production_cost_basis_versions, claims, session, data={"production_cost_group_id": client_id}, query={"limit": limit, "offset": offset})


@router.delete("/basis-versions/{client_id}")
async def route_delete_production_cost_basis_version(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_production_cost_basis_version, claims, session, data={"client_id": client_id})


@router.post("/cost-model-versions")
async def route_create_cost_model_version(
    body: _CostModelVersionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(create_cost_model_version, claims, session, data=body.model_dump())


@router.get("/cost-model-versions")
async def route_list_cost_model_versions(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await _run(list_cost_model_versions, claims, session, query={"limit": limit, "offset": offset})


@router.delete("/cost-model-versions/{client_id}")
async def route_delete_cost_model_version(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_cost_model_version, claims, session, data={"client_id": client_id})


@router.get("/configuration-status")
async def route_get_economics_configuration_status(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_economics_configuration_status, claims, session)


@router.put("/items/{item_client_id}/valuation")
async def route_set_item_valuation(
    item_client_id: str,
    body: _ItemValuationBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        set_item_valuation,
        claims,
        session,
        data={"item_client_id": item_client_id, **body.model_dump()},
    )


@router.get("/items/{item_client_id}/valuations")
async def route_get_item_valuation_history(
    item_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        get_item_valuation_history,
        claims,
        session,
        data={"item_client_id": item_client_id},
    )


@router.delete("/items/{item_client_id}/valuation")
async def route_delete_item_valuation(
    item_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        delete_item_valuation,
        claims,
        session,
        data={"item_client_id": item_client_id},
    )


@router.post("/tasks/{task_client_id}/evaluations/commit")
async def route_commit_item_cost_evaluation(
    task_client_id: str,
    body: _CommitEvaluationBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        commit_item_cost_evaluation,
        claims,
        session,
        data={"task_client_id": task_client_id, **body.model_dump(exclude_unset=True)},
    )


@router.get("/tasks/{task_client_id}/evaluations")
async def route_list_task_evaluations(
    task_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_task_evaluations,
        claims,
        session,
        data={"task_client_id": task_client_id},
    )


@router.get("/tasks/{task_client_id}/budget-status", response_model=None)
async def route_get_task_budget_status(
    task_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run_budget_status(claims, session, task_client_id)


@router.post("/tasks/{task_client_id}/projections")
async def route_create_item_cost_projection(
    task_client_id: str,
    body: _ProjectionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        create_item_cost_projection,
        claims,
        session,
        data={"task_client_id": task_client_id, **body.model_dump(exclude_unset=True)},
    )


@router.delete("/projections/{client_id}")
async def route_delete_item_cost_projection(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_item_cost_projection, claims, session, data={"client_id": client_id})


@router.post("/projections/{client_id}/promote")
async def route_promote_item_cost_projection(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(promote_item_cost_projection, claims, session, data={"client_id": client_id})


@router.get("/items/{item_client_id}/economics")
async def route_get_item_lifetime_economics(
    item_client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await _run(
        get_item_lifetime_economics,
        claims,
        session,
        data={"item_client_id": item_client_id},
        query={"limit": limit, "offset": offset},
    )


# Route ownership is explicit so the all-role budget endpoint cannot silently
# inherit the manager-only table when this router grows.
_ALL_ROLE_ROUTES = frozenset({"/tasks/{task_client_id}/budget-status"})
_MANAGER_ONLY_ROUTES = frozenset(
    route.path for route in router.routes if route.path not in _ALL_ROLE_ROUTES
)
_ROUTES = _MANAGER_ONLY_ROUTES | _ALL_ROLE_ROUTES
