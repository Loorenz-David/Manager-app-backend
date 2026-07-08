from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator

from beyo_manager.config import settings
from beyo_manager.domain.shopify.enums import ShopifyOAuthStateStatusEnum
from beyo_manager.domain.shopify.scopes import parse_scope_config
from beyo_manager.domain.shopify.shop_domains import normalize_shop_domain
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.shopify.shopify_oauth_state import ShopifyOAuthState
from beyo_manager.services.commands.shopify._redirect import validate_redirect_after_success_key
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.oauth_client import build_shopify_install_url

logger = logging.getLogger(__name__)

_OAUTH_STATE_TTL = timedelta(minutes=10)


class CreateShopifyInstallUrlRequest(BaseModel):
    shop_domain: str
    redirect_after_success: str | None = None

    @field_validator("shop_domain")
    @classmethod
    def _shop_domain_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("shop_domain is required.")
        return value

    @field_validator("redirect_after_success")
    @classmethod
    def _redirect_key_must_be_valid(cls, value: str | None) -> str | None:
        validate_redirect_after_success_key(value)
        return value


def parse_create_shopify_install_url_request(data: dict) -> CreateShopifyInstallUrlRequest:
    try:
        return CreateShopifyInstallUrlRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


async def create_shopify_install_url(ctx: ServiceContext) -> dict:
    request = parse_create_shopify_install_url_request(ctx.incoming_data)
    normalized_shop_domain = normalize_shop_domain(request.shop_domain)
    requested_scopes = parse_scope_config(settings.shopify_app_scopes)
    expires_at = datetime.now(timezone.utc) + _OAUTH_STATE_TTL
    state = secrets.token_urlsafe(32)

    oauth_state = ShopifyOAuthState(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        shop_domain=normalized_shop_domain,
        state=state,
        status=ShopifyOAuthStateStatusEnum.PENDING,
        requested_scopes=list(requested_scopes),
        redirect_after_success=validate_redirect_after_success_key(request.redirect_after_success),
        expires_at=expires_at,
    )
    async with maybe_begin(ctx.session):
        ctx.session.add(oauth_state)
        await ctx.session.flush()

    install_url = build_shopify_install_url(
        shop_domain=normalized_shop_domain,
        state=state,
        requested_scopes=requested_scopes,
    )
    logger.info(
        "Shopify install URL created | workspace=%s user=%s shop_domain=%s",
        ctx.workspace_id,
        ctx.user_id,
        normalized_shop_domain,
    )
    return {
        "install_url": install_url,
        "shop_domain": normalized_shop_domain,
        "expires_at": expires_at.isoformat(),
    }
