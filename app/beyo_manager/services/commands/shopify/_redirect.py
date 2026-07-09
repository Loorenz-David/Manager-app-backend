from __future__ import annotations

import logging
from urllib.parse import urlencode, urlsplit, urlunsplit

from beyo_manager.config import settings
from beyo_manager.errors.validation import ValidationError

logger = logging.getLogger(__name__)

_DEFAULT_REDIRECT_KEY = "default"


def validate_redirect_after_success_key(raw_value: str | None) -> str:
    if raw_value in (None, "", _DEFAULT_REDIRECT_KEY):
        return _DEFAULT_REDIRECT_KEY
    raise ValidationError("redirect_after_success must be 'default' when provided.")


def build_shopify_oauth_redirect_url(
    *,
    success: bool,
    shop_domain: str | None = None,
    error_code: str | None = None,
    redirect_key: str | None = None,
) -> str:
    validate_redirect_after_success_key(redirect_key)

    base_url = settings.shopify_oauth_redirect_url
    if not base_url:
        raise ValidationError("SHOPIFY_OAUTH_REDIRECT_URL is not configured.")

    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValidationError("SHOPIFY_OAUTH_REDIRECT_URL must be an absolute http(s) URL.")

    query_items: list[tuple[str, str]] = [("success", "true" if success else "false")]
    if shop_domain:
        query_items.append(("shop_domain", shop_domain))
    if error_code:
        query_items.append(("error_code", error_code))

    redirect_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), ""))
    logger.debug(
        "Shopify OAuth frontend redirect built | success=%s shop_domain=%s error_code=%s redirect_url=%s",
        success,
        shop_domain,
        error_code,
        redirect_url,
    )
    return redirect_url
