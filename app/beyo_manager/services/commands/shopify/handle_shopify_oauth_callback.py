from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import ShopifyOAuthStateStatusEnum
from beyo_manager.domain.shopify.shop_domains import normalize_shop_domain
from beyo_manager.errors.external_service import ExternalServiceError, ShopifyGraphQLError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_oauth_state import ShopifyOAuthState
from beyo_manager.services.commands.shopify._callback_errors import ShopifyOAuthCallbackError
from beyo_manager.services.commands.shopify._linking import link_or_update_shopify_shop_record
from beyo_manager.services.commands.shopify._redirect import build_shopify_oauth_redirect_url, validate_redirect_after_success_key
from beyo_manager.services.commands.shopify._webhook_sync import record_webhook_sync_pending
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.crypto.field_encryption import encrypt_field
from beyo_manager.services.infra.shopify.hmac_verifier import is_valid_shopify_oauth_callback_hmac
from beyo_manager.services.infra.shopify.oauth_client import exchange_oauth_code_for_offline_token
from beyo_manager.services.infra.shopify.shop_client import fetch_shopify_shop_name

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
    logger.info(
        "Shopify OAuth callback received | shop=%s state_prefix=%s has_code=%s has_error=%s",
        request.shop,
        request.state[:8],
        bool(request.code),
        bool(request.error),
    )
    logger.debug("Shopify OAuth callback raw query string | raw_query_string=%s", request.raw_query_string)

    hmac_valid = is_valid_shopify_oauth_callback_hmac(request.raw_query_string)
    logger.debug("Shopify OAuth callback HMAC check | shop=%s valid=%s", request.shop, hmac_valid)
    if not hmac_valid:
        logger.warning("Shopify OAuth callback rejected | shop=%s reason=invalid_signature", request.shop)
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
                logger.warning(
                    "Shopify OAuth callback rejected | shop_domain=%s reason=invalid_state state_prefix=%s",
                    shop_domain,
                    request.state[:8],
                )
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state was not found.",
                    error_code="invalid_state",
                    shop_domain=shop_domain,
                )

            logger.debug(
                "Shopify OAuth state loaded | shop_domain=%s status=%s expires_at=%s consumed_at=%s",
                oauth_state.shop_domain,
                oauth_state.status.value,
                oauth_state.expires_at.isoformat(),
                oauth_state.consumed_at.isoformat() if oauth_state.consumed_at else None,
            )

            redirect_key = validate_redirect_after_success_key(oauth_state.redirect_after_success)
            if oauth_state.shop_domain != shop_domain:
                logger.warning(
                    "Shopify OAuth callback rejected | reason=state_shop_mismatch "
                    "state_shop_domain=%s callback_shop_domain=%s",
                    oauth_state.shop_domain,
                    shop_domain,
                )
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state does not match the requested shop.",
                    error_code="state_shop_mismatch",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if oauth_state.status != ShopifyOAuthStateStatusEnum.PENDING or oauth_state.consumed_at is not None:
                logger.warning(
                    "Shopify OAuth callback rejected | shop_domain=%s reason=state_already_consumed status=%s",
                    oauth_state.shop_domain,
                    oauth_state.status.value,
                )
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state has already been consumed.",
                    error_code="state_already_consumed",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if oauth_state.expires_at <= now:
                logger.warning(
                    "Shopify OAuth callback rejected | shop_domain=%s reason=state_expired expires_at=%s now=%s",
                    oauth_state.shop_domain,
                    oauth_state.expires_at.isoformat(),
                    now.isoformat(),
                )
                oauth_state.status = ShopifyOAuthStateStatusEnum.EXPIRED
                await ctx.session.flush()
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth state has expired.",
                    error_code="state_expired",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )
            if request.error:
                logger.warning(
                    "Shopify OAuth callback rejected | shop_domain=%s reason=access_denied shopify_error=%s",
                    oauth_state.shop_domain,
                    request.error,
                )
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
                logger.warning(
                    "Shopify OAuth callback rejected | shop_domain=%s reason=missing_code",
                    oauth_state.shop_domain,
                )
                raise ShopifyOAuthCallbackError(
                    "Shopify OAuth callback is missing a code parameter.",
                    error_code="missing_code",
                    shop_domain=oauth_state.shop_domain,
                    redirect_key=redirect_key,
                )

            logger.debug(
                "Shopify OAuth callback validations passed, exchanging code | shop_domain=%s",
                oauth_state.shop_domain,
            )
            token_result = await exchange_oauth_code_for_offline_token(
                shop_domain=oauth_state.shop_domain,
                code=request.code,
            )
            logger.info(
                "Shopify OAuth token exchange succeeded | shop_domain=%s granted_scopes=%s",
                oauth_state.shop_domain,
                list(token_result.granted_scopes),
            )

            shop_name: str | None = None
            try:
                shop_name = await fetch_shopify_shop_name(
                    shop_domain=oauth_state.shop_domain,
                    access_token_encrypted=encrypt_field(token_result.access_token),
                )
                logger.info(
                    "Shopify shop name fetched | shop_domain=%s shop_name=%s",
                    oauth_state.shop_domain,
                    shop_name,
                )
            except ShopifyGraphQLError as exc:
                logger.warning(
                    "Shopify shop name fetch failed, continuing without it | shop_domain=%s "
                    "error_code=%s error=%s",
                    oauth_state.shop_domain,
                    exc.error_code,
                    exc,
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
                shop_name=shop_name,
            )
            logger.info(
                "Shopify shop integration linked/updated | shop_integration_id=%s shop_domain=%s status=%s",
                integration.client_id,
                integration.shop_domain,
                integration.status.value,
            )

            await record_webhook_sync_pending(
                ctx.session,
                workspace_id=oauth_state.workspace_id,
                user_id=oauth_state.user_id,
                shop_integration_id=integration.client_id,
                shop_domain=integration.shop_domain,
            )
            logger.debug(
                "Shopify post-OAuth webhook sync enqueued | shop_integration_id=%s",
                integration.client_id,
            )

            oauth_state.status = ShopifyOAuthStateStatusEnum.CONSUMED
            oauth_state.consumed_at = now
            await ctx.session.flush()

    except ExternalServiceError as exc:
        logger.warning(
            "Shopify OAuth callback failed during token exchange | shop_domain=%s error=%s",
            shop_domain,
            exc,
        )
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
