"""Router: /api/v1/pricing (inbound, for the external pricing app).

Key-authenticated by `X-API-KEY` (the Scanner's shared inbound key — see
`services/infra/pricing_api/auth.py`), not by JWT. Read-only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_item_costs_by_sku import (
    get_item_costs_for_pricing_app,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.get("/item-costs")
async def route_get_item_costs(
    request: Request,
    sku: str = Query(..., min_length=1, max_length=128),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        identity={},
        incoming_data={"headers": request.headers, "sku": sku},
        session=session,
    )
    outcome = await run_service(get_item_costs_for_pricing_app, ctx)
    return build_err(outcome.error) if not outcome.success else build_ok(outcome.data)
