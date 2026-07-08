from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import ShopifyOAuthStateStatusEnum
from beyo_manager.domain.shopify.shop_domains import normalize_shop_domain
from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_oauth_state import ShopifyOAuthState
from beyo_manager.services.commands.shopify._callback_errors import ShopifyOAuthCallbackError
from beyo_manager.services.commands.shopify._linking import link_or_update_shopify_shop_record
from beyo_manager.services.commands.shopify._redirect import build_shopify_oauth_redirect_url, validate_redirect_after_success_key
from beyo_manager.services.commands.shopify._webhook_sync import record_webhook_sync_pending
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.hmac_verifier import is_valid_shopify_oauth_callback_hmac
from beyo_manager.services.infra.shopify.oauth_client import exchange_oauth_code_for_offline_token

logger = logging.getLogger(__name__)


class HandleShopifyOAuthCallbackRequest(BaseModel):
    shop: str
    state: str
    hmac: str
    code: str | None = None
    error: str | None = None
    raw_query_string: str

    @field_validator("shop", "state", "hmac", "raw_query_string")
    @classmethod
    def _required_strings_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank.")
        return value


def parse_handle_shopify_oauth_callback_request(data: dict) -> HandleShopifyOAuthCallbackRequest:
    try:
        return HandleShopifyOAuthCallbackRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def extract_shop_domain_for_redirect(raw_shop_domain: str | None) -> str | None:
    if not raw_shop_domain:
        return None
    try:
        return normalize_shop_domain(raw_shop_domain)
    except ValidationError:
        return None


def build_callback_redirect_payload(
    *,
    success: bool,
    shop_domain: str | None,
    error_code: str | None,
    redirect_key: str | None = None,
) -> dict:
    return {
        "redirect_url": build_shopify_oauth_redirect_url(
            success=success,
            shop_domain=shop_domain,
            error_code=error_code,
            redirect_key=redirect_key,
        ),
        "success": success,
        "shop_domain": shop_domain,
        "error_code": error_code,
    }


async def handle_shopify_oauth_callback(ctx: ServiceContext) -> dict:
    request = parse_handle_shopify_oauth_callback_request(ctx.incoming_data)
    if not is_valid_shopify_oauth_callback_hmac(request.raw_query_string):
        raise ShopifyOAuthCallbackError(
            "Invalid Shopify OAuth signature.",
            error_code="invalid_signature",
        )

    shop_domain = normalize_shop_domain(request.shop)
    now = datetime.now(timezone.utc)

    try:
        async with maybe_begin(ctx.session):
            oauth_state = (
                await ctx.session.execute(
                    select(ShopifyOAuthState)
                    .where(ShopifyOAuthState.state == request.state)
                    .with_for_update()
                )
            ).scalar_one_or_none()

            if oauth_state is None:
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state was not found.",
                    error_code="invalid_state",
                    shop_domain=shop_domain,
                )

            redirect_key = validate_redirect_after_success_key(oauth_state.redirect_after_success)
            if oauth_state.shop_domain != shop_domain:
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state does not match the requested shop.",
                    error_code="state_shop_mismatch",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if oauth_state.status != ShopifyOAuthStateStatusEnum.PENDING or oauth_state.consumed_at is not None:
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state has already been consumed.",
                    error_code="state_already_consumed",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if oauth_state.expires_at <= now:
                oauth_state.status = ShopifyOAuthStateStatusEnum.EXPIRED
                await ctx.session.flush()
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state has expired.",
                    error_code="state_expired",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if request.error:
                oauth_state.status = ShopifyOAuthStateStatusEnum.CONSUMED
                oauth_state.consumed_at = now
                await ctx.session.flush()
                raise ShopifyOAuthCallbackError(
                    "Shopify authorization was denied.",
                    error_code="access_denied",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if not request.code:
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth callback is missing a code parameter.",
                    error_code="missing_code",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )

            token_result = await exchange_oauth_code_for_offline_token(
                shop_domain=oauth_state.shop_domain,
                code=request.code,
            )
            integration = await link_or_update_shopify_shop_record(
                ctx.session,
                workspace_id=oauth_state.workspace_id,
                user_id=oauth_state.user_id,
                shop_domain=oauth_state.shop_domain,
                access_token=token_result.access_token,
                requested_scopes=tuple(oauth_state.requested_scopes or ()),
                granted_scopes=token_result.granted_scopes,
                api_version=settings.shopify_api_version,
            )

            await record_webhook_sync_pending(
                ctx.session,
                workspace_id=oauth_state.workspace_id,
                user_id=oauth_state.user_id,
                shop_integration_id=integration.client_id,
                shop_domain=integration.shop_domain,
            )

            oauth_state.status = ShopifyOAuthStateStatusEnum.CONSUMED
            oauth_state.consumed_at = now
            await ctx.session.flush()

    except ExternalServiceError as exc:
        logger.warning("Shopify OAuth callback failed during token exchange | shop_domain=%s", shop_domain)
        raise ShopifyOAuthCallbackError(
            str(exc),
            error_code="token_exchange_failed",
            shop_domain=shop_domain,
            redirect_key="default",
        ) from exc

    logger.info("Shopify OAuth callback linked shop | shop_domain=%s", shop_domain)
    return build_callback_redirect_payload(
        success=True,
        shop_domain=shop_domain,
        error_code=None,
        redirect_key=oauth_state.redirect_after_success if "oauth_state" in locals() else "default",
    )
