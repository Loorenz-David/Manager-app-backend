from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.audit.list_audit_events import list_audit_events
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.get("")
async def list_audit_events_route(
    claims:             dict         = Depends(require_roles([ADMIN])),
    session:            AsyncSession = Depends(get_db),
    event:              str | None   = Query(None),
    actor_user_id:      str | None   = Query(None),
    resource_client_id: str | None   = Query(None),
    since:              str | None   = Query(None),
    until:              str | None   = Query(None),
    limit:              int          = Query(50, le=200),
):
    ctx = ServiceContext(
        incoming_data={
            "event":              event,
            "actor_user_id":      actor_user_id,
            "resource_client_id": resource_client_id,
            "since":              since,
            "until":              until,
            "limit":              limit,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_audit_events, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
