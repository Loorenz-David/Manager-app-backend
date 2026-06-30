import logging

import httpx

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.selfmade.constants import (
    SELFMADE_DEFAULT_HEADERS,
    SELFMADE_SEARCH_URL,
)

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(8.0, connect=4.0)


async def fetch_selfmade_search_html(q: str, page: int = 1) -> str:
    needle = q.strip()
    if not needle:
        return ""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=SELFMADE_DEFAULT_HEADERS) as client:
            response = await client.get(
                SELFMADE_SEARCH_URL,
                params={"search": needle, "p": str(page)},
            )
    except httpx.TimeoutException as exc:
        logger.warning("Selfmade request timed out for q=%r page=%s", needle, page)
        raise ExternalServiceError("Selfmade request timed out.") from exc
    except httpx.RequestError as exc:
        logger.warning("Selfmade request error for q=%r page=%s: %s", needle, page, exc)
        raise ExternalServiceError("Selfmade request failed.") from exc

    if response.status_code != 200:
        logger.warning(
            "Selfmade returned HTTP %s for q=%r page=%s",
            response.status_code,
            needle,
            page,
        )
        raise ExternalServiceError(f"Selfmade returned unexpected status {response.status_code}.")

    return response.text
