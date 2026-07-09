from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from urllib.parse import parse_qsl

from beyo_manager.config import settings
from beyo_manager.errors.validation import ValidationError

logger = logging.getLogger(__name__)


def is_valid_shopify_oauth_callback_hmac(raw_query_string: str) -> bool:
    secret = settings.shopify_client_secret
    if not secret:
        raise ValidationError("SHOPIFY_CLIENT_SECRET is not configured.")

    pairs = parse_qsl(raw_query_string, keep_blank_values=True)
    provided_hmac = next((value for key, value in pairs if key == "hmac"), "")
    if not provided_hmac:
        logger.debug("Shopify OAuth callback HMAC missing from query string.")
        return False

    signed_pairs = [(key, value) for key, value in pairs if key not in {"hmac", "signature"}]
    message = "&".join(f"{key}={value}" for key, value in sorted(signed_pairs))
    computed = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(computed, provided_hmac)
    logger.debug(
        "Shopify OAuth callback HMAC comparison | signed_message=%s computed=%s provided=%s valid=%s",
        message,
        computed,
        provided_hmac,
        valid,
    )
    return valid


def is_valid_shopify_webhook_hmac(raw_body: bytes, provided_hmac_header: str | None) -> bool:
    secret = settings.shopify_webhook_secret or settings.shopify_client_secret
    if not secret:
        raise ValidationError("SHOPIFY webhook secret is not configured.")

    provided_hmac = (provided_hmac_header or "").strip()
    if not provided_hmac:
        logger.debug("Shopify webhook HMAC header missing.")
        return False

    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode()
    valid = hmac.compare_digest(computed, provided_hmac)
    logger.debug(
        "Shopify webhook HMAC comparison | body_length=%d computed=%s provided=%s valid=%s",
        len(raw_body),
        computed,
        provided_hmac,
        valid,
    )
    return valid
