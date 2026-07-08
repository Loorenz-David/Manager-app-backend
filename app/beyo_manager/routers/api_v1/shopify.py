from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.commands.shopify._callback_errors import ShopifyOAuthCallbackError
from beyo_manager.services.commands.shopify.handle_shopify_oauth_callback import (
    build_callback_redirect_payload,
    handle_shopify_oauth_callback,
)
from beyo_manager.services.commands.shopify.create_shopify_install_url import create_shopify_install_url
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


class ShopifyInstallUrlBody(BaseModel):
    shop_domain: str
    redirect_after_success: str | None = None


@router.post("/install-url")
async def create_shopify_install_url_route(
    body: ShopifyInstallUrlBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        create_shopify_install_url,
        ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/oauth/callback")
async def shopify_oauth_callback_route(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    incoming_data = dict(request.query_params)
    incoming_data["raw_query_string"] = request.url.query
    outcome = await run_service(
        handle_shopify_oauth_callback,
        ServiceContext(identity={}, incoming_data=incoming_data, session=session),
    )
    if outcome.success:
        return RedirectResponse(outcome.data["redirect_url"], status_code=302)

    if isinstance(outcome.error, ShopifyOAuthCallbackError):
        redirect_payload = build_callback_redirect_payload(
            success=False,
            shop_domain=outcome.error.shop_domain,
            error_code=outcome.error.error_code,
            redirect_key=outcome.error.redirect_key,
        )
        return RedirectResponse(redirect_payload["redirect_url"], status_code=302)

    try:
        redirect_payload = build_callback_redirect_payload(
            success=False,
            shop_domain=None,
            error_code="oauth_callback_failed",
            redirect_key="default",
        )
    except Exception:
        return build_err(outcome.error)
    return RedirectResponse(redirect_payload["redirect_url"], status_code=302)
