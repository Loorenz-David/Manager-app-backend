from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.shopify.enqueue_or_record_shopify_webhook import (
    enqueue_or_record_shopify_webhook,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


@router.post("/webhooks")
async def shopify_webhooks_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    outcome = await run_service(
        enqueue_or_record_shopify_webhook,
        ServiceContext(
            identity={},
            incoming_data={
                "raw_body": raw_body,
                "hmac_header": request.headers.get("X-Shopify-Hmac-Sha256"),
                "topic": request.headers.get("X-Shopify-Topic"),
                "shop_domain": request.headers.get("X-Shopify-Shop-Domain"),
                "webhook_id": request.headers.get("X-Shopify-Webhook-Id"),
            },
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
