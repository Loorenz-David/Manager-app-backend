from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.shopify.create_shopify_reauthorize_url import create_shopify_reauthorize_url
from beyo_manager.services.commands.shopify.disconnect_shopify_shop import disconnect_shopify_shop
from beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_for_shop import (
    enqueue_shopify_webhook_sync_for_shop,
)
from beyo_manager.services.commands.shopify.enqueue_shopify_webhook_sync_for_workspace import (
    enqueue_shopify_webhook_sync_for_workspace,
)
from beyo_manager.services.commands.shopify._callback_errors import ShopifyOAuthCallbackError
from beyo_manager.services.commands.shopify.handle_shopify_oauth_callback import (
    build_callback_redirect_payload,
    handle_shopify_oauth_callback,
)
from beyo_manager.services.commands.shopify.process_shopify_products import process_shopify_products
from beyo_manager.services.commands.shopify.create_shopify_metafield_preferences import (
    create_shopify_metafield_preferences,
)
from beyo_manager.services.commands.shopify.delete_shopify_metafield_preferences import (
    delete_shopify_metafield_preferences,
)
from beyo_manager.services.commands.shopify.update_shopify_metafield_preference_sequence_order import (
    update_shopify_metafield_preference_sequence_order,
)
from beyo_manager.services.commands.shopify.create_shopify_install_url import create_shopify_install_url
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.shopify.get_shopify_scope_status import get_shopify_scope_status
from beyo_manager.services.queries.shopify.get_shopify_shop_integration import get_shopify_shop_integration
from beyo_manager.services.queries.shopify.get_shopify_webhook_history_records import (
    get_shopify_webhook_history_records,
)
from beyo_manager.services.queries.shopify.list_shopify_shop_integrations import list_shopify_shop_integrations
from beyo_manager.services.queries.shopify.lookup_shopify_customers_by_product_identity import (
    lookup_shopify_customers_by_product_identity,
)
from beyo_manager.services.queries.shopify.get_shopify_metafield_preferences import get_shopify_metafield_preferences
from beyo_manager.services.run_service import run_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ShopifyInstallUrlBody(BaseModel):
    shop_domain: str
    redirect_after_success: str | None = None


class ShopifyShopIntegrationPathBody(BaseModel):
    shop_integration_id: str


class ShopifyMetafieldPreferencesDeleteBody(BaseModel):
    client_ids: list[str] = Field(min_length=1)


class ShopifyProductIdentityCustomerLookupBody(BaseModel):
    article_number: str | None = None
    sku: str | None = None


class ShopifyProductSyncWeightBody(BaseModel):
    value: float
    unit: str


class ShopifyProductSyncItemBody(BaseModel):
    client_id: str
    target_shop_integration_ids: list[str] | None = None
    title: str
    description: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    product_category: str | None = None
    price: str | None = None
    weight: ShopifyProductSyncWeightBody | None = None
    sku: str | None = None
    item_article_number: str | None = None
    article_number: str | None = None
    metafields: dict[str, object] = Field(default_factory=dict)


class ShopifyProcessProductsBody(BaseModel):
    items: list[ShopifyProductSyncItemBody]


class ShopifyMetafieldPreferenceSelectionBody(BaseModel):
    client_id: str | None = None
    shop_integration_id: str
    shopify_metafield_definition_id: str
    sequence_order: int = Field(ge=0)


class ShopifyMetafieldPreferencesCreateBody(BaseModel):
    item_category_id: str
    preferences: list[ShopifyMetafieldPreferenceSelectionBody] = Field(min_length=1)


class ShopifyMetafieldPreferenceSequenceOrderUpdateBody(BaseModel):
    sequence_order: int = Field(ge=0)


@router.post("/install-url")
async def create_shopify_install_url_route(
    body: ShopifyInstallUrlBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    logger.debug(
        "Shopify install-url route hit | shop_domain=%s redirect_after_success=%s",
        body.shop_domain,
        body.redirect_after_success,
    )
    outcome = await run_service(
        create_shopify_install_url,
        ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
    )
    if not outcome.success:
        logger.warning("Shopify install-url route failed | error=%s", outcome.error)
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/shops")
async def list_shopify_shops_route(
    request: Request,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        list_shopify_shop_integrations,
        ServiceContext(identity=claims, incoming_data={}, query_params=dict(request.query_params), session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/shops/{shop_integration_id}")
async def get_shopify_shop_route(
    shop_integration_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        get_shopify_shop_integration,
        ServiceContext(identity=claims, incoming_data={"shop_integration_id": shop_integration_id}, session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/shops/{shop_integration_id}/reauthorize-url")
async def create_shopify_reauthorize_url_route(
    shop_integration_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        create_shopify_reauthorize_url,
        ServiceContext(identity=claims, incoming_data={"shop_integration_id": shop_integration_id}, session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/shops/{shop_integration_id}")
async def disconnect_shopify_shop_route(
    shop_integration_id: str,
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        disconnect_shopify_shop,
        ServiceContext(identity=claims, incoming_data={"shop_integration_id": shop_integration_id}, session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/shops/{shop_integration_id}/webhooks/sync")
async def enqueue_shopify_webhook_sync_for_shop_route(
    shop_integration_id: str,
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        enqueue_shopify_webhook_sync_for_shop,
        ServiceContext(identity=claims, incoming_data={"shop_integration_id": shop_integration_id}, session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/shops/{shop_integration_id}/webhooks/history")
async def get_shopify_webhook_history_route(
    shop_integration_id: str,
    request: Request,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        get_shopify_webhook_history_records,
        ServiceContext(
            identity=claims,
            incoming_data={"shop_integration_id": shop_integration_id},
            query_params=dict(request.query_params),
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/webhooks/sync")
async def enqueue_shopify_webhook_sync_for_workspace_route(
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        enqueue_shopify_webhook_sync_for_workspace,
        ServiceContext(identity=claims, incoming_data={}, session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/scopes")
async def get_shopify_scopes_route(
    request: Request,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        get_shopify_scope_status,
        ServiceContext(identity=claims, incoming_data={}, query_params=dict(request.query_params), session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/customers/by-product-identity")
async def lookup_shopify_customers_by_product_identity_route(
    body: ShopifyProductIdentityCustomerLookupBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        lookup_shopify_customers_by_product_identity,
        ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/metafield-preferences")
async def create_shopify_metafield_preferences_route(
    body: ShopifyMetafieldPreferencesCreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        create_shopify_metafield_preferences,
        ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/metafield-preferences")
async def get_shopify_metafield_preferences_route(
    request: Request,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        get_shopify_metafield_preferences,
        ServiceContext(
            identity=claims,
            incoming_data={},
            query_params=dict(request.query_params),
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/metafield-preferences")
async def delete_shopify_metafield_preferences_route(
    body: ShopifyMetafieldPreferencesDeleteBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        delete_shopify_metafield_preferences,
        ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/metafield-preferences/{preference_client_id}")
async def update_shopify_metafield_preference_sequence_order_route(
    preference_client_id: str,
    body: ShopifyMetafieldPreferenceSequenceOrderUpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        update_shopify_metafield_preference_sequence_order,
        ServiceContext(
            identity=claims,
            incoming_data={
                "client_id": preference_client_id,
                **body.model_dump(),
            },
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/products/process")
async def process_shopify_products_route(
    body: ShopifyProcessProductsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        process_shopify_products,
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
    logger.debug(
        "Shopify OAuth callback route hit | path=%s query=%s",
        request.url.path,
        request.url.query,
    )
    outcome = await run_service(
        handle_shopify_oauth_callback,
        ServiceContext(identity={}, incoming_data=incoming_data, session=session),
    )
    if outcome.success:
        logger.info(
            "Shopify OAuth callback redirecting on success | redirect_url=%s",
            outcome.data["redirect_url"],
        )
        return RedirectResponse(outcome.data["redirect_url"], status_code=302)

    if isinstance(outcome.error, ShopifyOAuthCallbackError):
        redirect_payload = build_callback_redirect_payload(
            success=False,
            shop_domain=outcome.error.shop_domain,
            error_code=outcome.error.error_code,
            redirect_key=outcome.error.redirect_key,
        )
        logger.warning(
            "Shopify OAuth callback redirecting on failure | error_code=%s shop_domain=%s redirect_url=%s",
            outcome.error.error_code,
            outcome.error.shop_domain,
            redirect_payload["redirect_url"],
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
        logger.error(
            "Shopify OAuth callback failed with an unhandled error and could not build a redirect | error=%s",
            outcome.error,
        )
        return build_err(outcome.error)
    logger.error(
        "Shopify OAuth callback redirecting on unhandled error | error=%s redirect_url=%s",
        outcome.error,
        redirect_payload["redirect_url"],
    )
    return RedirectResponse(redirect_payload["redirect_url"], status_code=302)
