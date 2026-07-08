from __future__ import annotations

import hashlib
import hmac
from urllib.parse import parse_qsl

from beyo_manager.config import settings
from beyo_manager.errors.validation import ValidationError


def is_valid_shopify_oauth_callback_hmac(raw_query_string: str) -> bool:
    secret = settings.shopify_client_secret
    if not secret:
        raise ValidationError("SHOPIFY_CLIENT_SECRET is not configured.")

    pairs = parse_qsl(raw_query_string, keep_blank_values=True)
    provided_hmac = next((value for key, value in pairs if key == "hmac"), "")
    if not provided_hmac:
        return False

    signed_pairs = [(key, value) for key, value in pairs if key not in {"hmac", "signature"}]
    message = "&".join(f"{key}={value}" for key, value in sorted(signed_pairs))
    computed = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, provided_hmac)
