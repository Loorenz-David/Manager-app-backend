from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictInt
from sqlalchemy.ext.asyncio import AsyncSession
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from beyo_manager.services.commands.stock_report.apply_stock_report_snapshot_version_priorities import (
    apply_stock_report_snapshot_version_priorities,
)
from beyo_manager.services.commands.stock_report.create_stock_report_snapshot_version import (
    create_stock_report_snapshot_version,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.delete_stock_task_assignments import (
    delete_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.commands.stock_report.delete_stock_report_item import (
    delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority import (
    set_stock_report_item_priority,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority_order import (
    set_stock_report_item_priority_order,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_snapshot_missing_quantity import (
    set_stock_report_item_snapshot_missing_quantity,
)
from beyo_manager.services.queries.stock_report.get_stock_report_active_snapshot_version import (
    get_stock_report_active_snapshot_version,
)
from beyo_manager.services.queries.stock_report.get_stock_report_consistency import (
    get_stock_report_consistency,
)
from beyo_manager.services.queries.stock_report.get_stock_report_missing_summary import (
    get_stock_report_missing_summary,
)
from beyo_manager.services.queries.stock_report.list_stock_report_items import (
    list_stock_report_items,
)
from beyo_manager.services.queries.stock_report.list_stock_report_snapshot_versions import (
    list_stock_report_snapshot_versions,
)
from beyo_manager.services.queries.stock_report.list_stock_task_assignments import (
    list_stock_task_assignments,
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


class _SetStockReportItemPriorityBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # No default: an omitted key is a 422 (plan 12 C1(m)); `null` is a legal value
    # and means "clear the priority".
    priority: StockReportPriorityEnum | None


class _SetStockReportItemPriorityOrderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Strict: pydantic's lax mode would coerce the string "2" to 2 (plan 12 C1(n)).
    priority_order: StrictInt


class _SetStockReportItemSnapshotMissingQuantityBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Strict for the same reason as `priority_order`: "3" must not become 3.
    quantity_missing: StrictInt


class _PreviewStockTaskAssignmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str | None = None
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str
    properties: dict
    quantity: int


# The two structured assignment errors are rendered explicitly with their `code` and
# `details` (the `routers/api_v1/auth.py:120-130` precedent); everything else goes
# through `build_err`.
_STRUCTURED_ASSIGNMENT_ERRORS = (StockAssignmentRefused, StockAssignmentPropertyMismatch)


async def _run(
    service,
    claims: dict,
    session: AsyncSession,
    incoming_data: dict | None = None,
    query_params: dict | None = None,
):
    outcome = await run_service(
        service,
        ServiceContext(
            identity=claims,
            incoming_data=incoming_data or {},
            query_params=query_params or {},
            session=session,
        ),
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


@router.get("/snapshots/versions")
async def route_list_stock_report_snapshot_versions(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(20, le=200),
    offset: int = Query(0, ge=0),
    # Same values and meaning as on `GET /items`; selects what `progress` sums.
    priority: str | None = None,
):
    return await _run(
        list_stock_report_snapshot_versions,
        claims,
        session,
        query_params={"limit": limit, "offset": offset, "priority": priority},
    )


@router.get("/snapshots/versions/active")
async def route_get_stock_report_active_snapshot_version(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    priority: str | None = None,
):
    # Static segment, declared before any `/snapshots/versions/{client_id}/…` route.
    return await _run(
        get_stock_report_active_snapshot_version,
        claims,
        session,
        query_params={"priority": priority},
    )


@router.post("/snapshots/versions")
async def route_create_stock_report_snapshot_version(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    # No body: a version is taken of every live row, there is nothing to choose.
    return await _run(create_stock_report_snapshot_version, claims, session)


@router.post("/snapshots/versions/{client_id}/apply-priorities")
async def route_apply_stock_report_snapshot_version_priorities(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        apply_stock_report_snapshot_version_priorities,
        claims,
        session,
        incoming_data={"client_id": client_id},
    )


@router.get("/snapshots/missing-summary")
async def route_get_stock_report_missing_summary(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_stock_report_missing_summary, claims, session)


@router.get("/items")
async def route_list_stock_report_items(
    priority: str | None = None,
    include_zero_requested: bool = False,
    item_major_categories: list[ItemMajorCategoryEnum] | None = Query(None),
    item_category_ids: list[str] | None = Query(None),
    live_stock: bool = False,
    missing_only: bool = False,
    # Paginated since 2026-09-26; default 20 by owner ruling. `ge=1`: a zero or
    # negative limit has no meaning, and a negative one reaches Postgres as an error.
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_stock_report_items,
        claims,
        session,
        query_params={
            "priority": priority,
            "include_zero_requested": include_zero_requested,
            "item_major_categories": item_major_categories,
            "item_category_ids": item_category_ids,
            "live_stock": live_stock,
            "missing_only": missing_only,
            "limit": limit,
            "offset": offset,
        },
    )


@router.patch("/items/{client_id}/missing-quantity")
async def route_set_stock_report_item_snapshot_missing_quantity(
    client_id: str,
    body: _SetStockReportItemSnapshotMissingQuantityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        set_stock_report_item_snapshot_missing_quantity,
        claims,
        session,
        incoming_data={**body.model_dump(), "client_id": client_id},
    )


@router.patch("/items/{client_id}/priority")
async def route_set_stock_report_item_priority(
    client_id: str,
    body: _SetStockReportItemPriorityBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    # `client_id` travels in the path (§9B ruling 1) and is injected exactly as the
    # shipped match-preview route does.
    return await _run(
        set_stock_report_item_priority,
        claims,
        session,
        incoming_data={**body.model_dump(), "client_id": client_id},
    )


@router.patch("/items/{client_id}/priority-order")
async def route_set_stock_report_item_priority_order(
    client_id: str,
    body: _SetStockReportItemPriorityOrderBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        set_stock_report_item_priority_order,
        claims,
        session,
        incoming_data={**body.model_dump(), "client_id": client_id},
    )


@router.delete("/items/{client_id}")
async def route_delete_stock_report_item(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    # DELETE takes no body (§9B ruling 1); `client_id` travels in the path.
    return await _run(
        delete_stock_report_item,
        claims,
        session,
        incoming_data={"client_id": client_id},
    )


@router.get("/items/{client_id}/assignments")
async def route_list_stock_task_assignments(
    client_id: str,
    include_resolved: bool = False,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_stock_task_assignments,
        claims,
        session,
        incoming_data={"client_id": client_id},
        query_params={"include_resolved": include_resolved},
    )
