from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from beyo_manager.config import settings
from beyo_manager.domain.shopify.scopes import normalize_scopes
from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.errors.validation import ValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShopifyOAuthTokenExchangeResult:
    access_token: str
    granted_scopes: tuple[str, ...]


def build_shopify_install_url(
    *,
    shop_domain: str,
    state: str,
    requested_scopes: tuple[str, ...],
) -> str:
    if not settings.shopify_client_id:
        raise ValidationError("SHOPIFY_CLIENT_ID is not configured.")
    if not settings.shopify_redirect_uri:
        raise ValidationError("SHOPIFY_REDIRECT_URI is not configured.")

    query = urlencode(
        {
            "client_id": settings.shopify_client_id,
            "scope": ",".join(requested_scopes),
            "redirect_uri": settings.shopify_redirect_uri,
            "state": state,
        }
    )
    install_url = f"https://{shop_domain}/admin/oauth/authorize?{query}"
    logger.debug(
        "Shopify install URL built | shop_domain=%s client_id=%s redirect_uri=%s scope=%s "
        "state_prefix=%s install_url=%s",
        shop_domain,
        settings.shopify_client_id,
        settings.shopify_redirect_uri,
        ",".join(requested_scopes),
        state[:8],
        install_url,
    )
    return install_url


async def exchange_oauth_code_for_offline_token(
    *,
    shop_domain: str,
    code: str,
) -> ShopifyOAuthTokenExchangeResult:
    if not settings.shopify_client_id:
        raise ValidationError("SHOPIFY_CLIENT_ID is not configured.")
    if not settings.shopify_client_secret:
        raise ValidationError("SHOPIFY_CLIENT_SECRET is not configured.")

    url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {
        "client_id": settings.shopify_client_id,
        "client_secret": settings.shopify_client_secret,
        "code": code,
    }

    logger.debug(
        "Shopify OAuth token exchange starting | shop_domain=%s url=%s client_id=%s code_prefix=%s",
        shop_domain,
        url,
        settings.shopify_client_id,
        code[:8],
    )
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(url, json=payload)
    except httpx.TimeoutException as exc:
        logger.warning("Shopify OAuth token exchange timed out | shop_domain=%s", shop_domain)
        raise ExternalServiceError("Shopify OAuth token exchange timed out.") from exc
    except httpx.HTTPError as exc:
        logger.warning("Shopify OAuth token exchange transport failure | shop_domain=%s", shop_domain)
        raise ExternalServiceError("Shopify OAuth token exchange failed.") from exc

    elapsed_ms = int((time.monotonic() - start) * 1000)
    if response.status_code >= 400:
        logger.warning(
            "Shopify OAuth token exchange rejected | shop_domain=%s status_code=%s latency_ms=%s",
            shop_domain,
            response.status_code,
            elapsed_ms,
        )
        raise ExternalServiceError("Shopify OAuth token exchange failed.")

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning(
            "Shopify OAuth token exchange returned invalid JSON | shop_domain=%s latency_ms=%s",
            shop_domain,
            elapsed_ms,
        )
        raise ExternalServiceError("Shopify OAuth token exchange returned invalid JSON.") from exc

    access_token = payload.get("access_token")
    raw_scope = payload.get("scope", "")
    if not isinstance(access_token, str) or not access_token.strip():
        raise ExternalServiceError("Shopify OAuth token exchange returned no access token.")

    logger.info(
        "Shopify OAuth token exchange succeeded | shop_domain=%s latency_ms=%s",
        shop_domain,
        elapsed_ms,
    )
    return ShopifyOAuthTokenExchangeResult(
        access_token=access_token,
        granted_scopes=normalize_scopes(raw_scope.split(",")),
    )
