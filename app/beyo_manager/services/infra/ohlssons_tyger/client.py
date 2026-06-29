import logging

import httpx

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.ohlssons_tyger.constants import (
    OHLSSONS_TYGER_BASE_URL,
    OHLSSONS_TYGER_SEARCH_PATH,
)

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 20.0
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}


async def _fetch_html(url: str, *, params: dict[str, str] | None = None) -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=_HEADERS) as client:
            response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        logger.warning("Ohlssons Tyger request timed out for url=%r", url)
        raise ExternalServiceError("Ohlssons Tyger request timed out.") from exc
    except httpx.RequestError as exc:
        logger.warning("Ohlssons Tyger request error for url=%r: %s", url, exc)
        raise ExternalServiceError("Ohlssons Tyger request failed.") from exc

    if response.status_code != 200:
        logger.warning("Ohlssons Tyger returned HTTP %s for url=%r", response.status_code, url)
        raise ExternalServiceError(
            f"Ohlssons Tyger returned unexpected status {response.status_code}."
        )

    return response.text


async def fetch_ohlssons_tyger_search_html(q: str, limit: int) -> str:
    del limit
    return await _fetch_html(
        f"{OHLSSONS_TYGER_BASE_URL}{OHLSSONS_TYGER_SEARCH_PATH}",
        params={"ecSearchText": q},
    )


async def fetch_ohlssons_tyger_detail_html(url: str) -> str:
    return await _fetch_html(url)
