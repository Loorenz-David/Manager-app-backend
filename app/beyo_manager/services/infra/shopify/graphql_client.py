from __future__ import annotations

import logging
import time
from collections.abc import Sequence

import httpx

from beyo_manager.config import settings
from beyo_manager.domain.shopify.shop_domains import normalize_shop_domain
from beyo_manager.errors.external_service import (
    ShopifyGraphQLError,
    ShopifyGraphQLNonRetryableError,
    ShopifyGraphQLRetryableError,
)
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field

logger = logging.getLogger(__name__)


def quote_shopify_search_term(value: str) -> str:
    """Escape and quote a value for use in a Shopify Admin GraphQL search query string
    (e.g. `sku:"value"`, `barcode:"value"`) — shared by every Shopify identity-lookup
    client so a single fix to the escaping rule covers every caller.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_shopify_admin_graphql_endpoint(shop_domain: str) -> str:
    normalized_shop_domain = normalize_shop_domain(shop_domain)
    return f"https://{normalized_shop_domain}/admin/api/{settings.shopify_api_version}/graphql.json"


async def execute_shopify_graphql(
    *,
    shop_domain: str,
    access_token_encrypted: str,
    query: str,
    variables: dict | None = None,
    operation_name: str,
) -> dict:
    normalized_shop_domain = normalize_shop_domain(shop_domain)
    url = build_shopify_admin_graphql_endpoint(normalized_shop_domain)
    payload = {
        "query": query,
        "variables": variables or {},
    }

    start = time.monotonic()
    try:
        # The migration CLI accepts raw Shopify tokens (for example shpat_,
        # shpca_, or shpua_), while normal application callers continue to
        # provide encrypted integration credentials.
        access_token = (
            access_token_encrypted
            if access_token_encrypted.startswith(("shpat_", "shpca_", "shpua_", "shppa_"))
            else decrypt_field(access_token_encrypted)
        )
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": access_token,
                },
            )
    except httpx.TimeoutException as exc:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=_elapsed_ms(start),
            reason="timeout",
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL request timed out.",
            error_code="timeout",
        ) from exc
    except httpx.ConnectError as exc:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=_elapsed_ms(start),
            reason="connection_error",
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL request failed to connect.",
            error_code="connection_error",
        ) from exc
    except httpx.HTTPError as exc:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=_elapsed_ms(start),
            reason="transport_error",
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL transport error.",
            error_code="transport_error",
        ) from exc

    latency_ms = _elapsed_ms(start)
    if response.status_code == 429:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="rate_limited",
            status_code=response.status_code,
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL request was rate limited.",
            error_code="rate_limited",
        )
    if response.status_code >= 500:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="server_error",
            status_code=response.status_code,
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL server error.",
            error_code="server_error",
        )
    if response.status_code in {401, 403}:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="auth_error",
            status_code=response.status_code,
        )
        raise ShopifyGraphQLNonRetryableError(
            "Shopify GraphQL authentication failed.",
            error_code="auth_error",
        )
    if response.status_code >= 400:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="validation_error",
            status_code=response.status_code,
        )
        raise ShopifyGraphQLNonRetryableError(
            "Shopify GraphQL request was rejected.",
            error_code="validation_error",
        )

    try:
        body = response.json()
    except ValueError as exc:
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="invalid_json",
            status_code=response.status_code,
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL returned invalid JSON.",
            error_code="invalid_json",
        ) from exc

    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, list) and errors:
        throttle_error = any(
            isinstance(error, dict)
            and (
                str((error.get("extensions") or {}).get("code") or "").upper() in {"THROTTLED", "RATE_LIMITED"}
                or "throttled" in str(error.get("message") or "").lower()
            )
            for error in errors
        )
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="throttled" if throttle_error else "graphql_errors",
            status_code=response.status_code,
        )
        if throttle_error:
            raise ShopifyGraphQLRetryableError(
                "Shopify GraphQL request was throttled.",
                error_code="throttled",
            )
        raise ShopifyGraphQLNonRetryableError(
            "Shopify GraphQL returned errors.",
            error_code="graphql_errors",
        )

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        _log_failure(
            operation_name=operation_name,
            shop_domain=normalized_shop_domain,
            latency_ms=latency_ms,
            reason="missing_data",
            status_code=response.status_code,
        )
        raise ShopifyGraphQLRetryableError(
            "Shopify GraphQL returned no data.",
            error_code="missing_data",
        )

    logger.info(
        "Shopify GraphQL request succeeded | operation=%s shop_domain=%s latency_ms=%s",
        operation_name,
        normalized_shop_domain,
        latency_ms,
    )
    return data


def raise_for_graphql_user_errors(
    *,
    user_errors: Sequence[dict] | None,
    operation_name: str,
    shop_domain: str,
) -> None:
    if not user_errors:
        return

    logger.warning(
        "Shopify GraphQL userErrors returned | operation=%s shop_domain=%s error_count=%s",
        operation_name,
        normalize_shop_domain(shop_domain),
        len(user_errors),
    )
    raise ShopifyGraphQLNonRetryableError(
        "Shopify GraphQL mutation returned user errors.",
        error_code="graphql_user_errors",
    )


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _log_failure(
    *,
    operation_name: str,
    shop_domain: str,
    latency_ms: int,
    reason: str,
    status_code: int | None = None,
) -> None:
    if status_code is None:
        logger.warning(
            "Shopify GraphQL request failed | operation=%s shop_domain=%s reason=%s latency_ms=%s",
            operation_name,
            shop_domain,
            reason,
            latency_ms,
        )
        return

    logger.warning(
        "Shopify GraphQL request failed | operation=%s shop_domain=%s status_code=%s reason=%s latency_ms=%s",
        operation_name,
        shop_domain,
        status_code,
        reason,
        latency_ms,
    )
