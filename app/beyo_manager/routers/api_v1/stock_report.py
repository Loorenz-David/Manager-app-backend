from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.delete_stock_task_assignments import (
    delete_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.queries.stock_report.get_stock_report_consistency import (
    get_stock_report_consistency,
)
from beyo_manager.services.queries.stock_report.preview_stock_task_assignment_match import (
    preview_stock_task_assignment_match,
)

router = APIRouter()


class _StockTaskAssignmentEntryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stock_report_item_id: str
    task_id: str
    item_id: str
    override_property_mismatch: bool = False


class _CreateStockTaskAssignmentsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[_StockTaskAssignmentEntryBody]


class _DeleteStockTaskAssignmentsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_ids: list[str]


class _PreviewStockTaskAssignmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str | None = None
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    properties: dict
    quantity: int


# The two structured assignment errors are rendered explicitly with their `code` and
# `details` (the `routers/api_v1/auth.py:120-130` precedent); everything else goes
# through `build_err`.
_STRUCTURED_ASSIGNMENT_ERRORS = (StockAssignmentRefused, StockAssignmentPropertyMismatch)


async def _run(service, claims: dict, session: AsyncSession, incoming_data: dict | None = None):
    outcome = await run_service(
        service,
        ServiceContext(identity=claims, incoming_data=incoming_data or {}, session=session),
    )
    if outcome.success:
        return build_ok(outcome.data)
    if isinstance(outcome.error, _STRUCTURED_ASSIGNMENT_ERRORS):
        return JSONResponse(
            content={
                "error": outcome.error.message,
                "ok": False,
                "code": outcome.error.code,
                "details": outcome.error.details,
            },
            status_code=outcome.error.http_status,
        )
    return build_err(outcome.error)


@router.get("/consistency")
async def route_get_stock_report_consistency(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_stock_report_consistency, claims, session)


@router.post("/repair")
async def route_repair_stock_report(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(repair_stock_report, claims, session)


@router.post("/assignments")
async def route_create_stock_task_assignments(
    body: _CreateStockTaskAssignmentsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        create_stock_task_assignments, claims, session, incoming_data=body.model_dump()
    )


@router.post("/assignments/delete")
async def route_delete_stock_task_assignments(
    body: _DeleteStockTaskAssignmentsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        delete_stock_task_assignments, claims, session, incoming_data=body.model_dump()
    )


@router.post("/items/{client_id}/match-preview")
async def route_preview_stock_task_assignment_match(
    client_id: str,
    body: _PreviewStockTaskAssignmentBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        preview_stock_task_assignment_match,
        claims,
        session,
        incoming_data={**body.model_dump(), "client_id": client_id},
    )
