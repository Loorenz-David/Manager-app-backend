from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.connecteam.enqueue_connecteam_time_activity_webhook import (
    enqueue_connecteam_time_activity_webhook,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.post("/webhooks/time-activity")
async def connecteam_time_activity_webhook_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    outcome = await run_service(
        enqueue_connecteam_time_activity_webhook,
        ServiceContext(
            identity={},
            incoming_data={"raw_body": raw_body, "headers": dict(request.headers)},
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)

