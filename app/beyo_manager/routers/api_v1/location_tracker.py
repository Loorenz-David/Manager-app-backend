"""Router: /api/v1/location-tracker"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.location_tracker.requests import PushItemLocationsRequest
from beyo_manager.services.commands.location_tracker.push_item_locations import push_item_locations
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.location_tracker.search_item_locations import search_item_locations
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.patch("/items/location")
async def route_push_item_locations(
    body: PushItemLocationsRequest,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(push_item_locations, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/items/location")
async def route_search_item_locations(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
    q: str = Query(..., max_length=200),
    item_identity: str | None = Query(None, max_length=100),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"q": q, "item_identity": item_identity},
        identity=claims,
        session=session,
    )
    outcome = await run_service(search_item_locations, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
