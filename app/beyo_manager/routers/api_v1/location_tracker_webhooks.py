"""Router: /api/v1/location-tracker (Scanner-inbound stock webhooks).

Mounted at the same prefix as the existing `location_tracker.router` (H22 — that
router keeps its own mount and its own `/items/location` route; nothing collides).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.stock_report.process_items_processed import (
    process_items_processed,
)
from beyo_manager.services.commands.stock_report.process_stock_demand_deleted import (
    process_stock_demand_deleted,
)
from beyo_manager.services.commands.stock_report.receive_stock_demand_webhook import (
    receive_stock_demand_webhook,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.post("/webhooks/stock-demand")
async def stock_demand_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    outcome = await run_service(
        receive_stock_demand_webhook,
        ServiceContext(
            identity={},
            incoming_data={"raw_body": raw_body, "headers": dict(request.headers)},
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/webhooks/items-processed")
async def items_processed_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    outcome = await run_service(
        process_items_processed,
        ServiceContext(
            identity={},
            incoming_data={"raw_body": raw_body, "headers": dict(request.headers)},
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/webhooks/stock-demand-deleted")
async def stock_demand_deleted_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    outcome = await run_service(
        process_stock_demand_deleted,
        ServiceContext(
            identity={},
            incoming_data={"raw_body": raw_body, "headers": dict(request.headers)},
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
