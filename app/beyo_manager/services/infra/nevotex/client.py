import logging
from typing import Any

import httpx

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.nevotex.constants import NEVOTEX_SEARCH_URL
from beyo_manager.services.infra.nevotex.parser import parse_nevotex_search_results

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10.0

_HEADERS = {
    "Accept": "text/html, */*",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    "Referer": "https://nevotex.se/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
}


async def fetch_nevotex_raw_products(q: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "defaultpdpId": "null",
        "IsVariant": "false",
        "redirect": "false",
        "eq": q,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=_HEADERS) as client:
            response = await client.get(NEVOTEX_SEARCH_URL, params=params)
    except httpx.TimeoutException as exc:
        logger.warning("Nevotex search timed out for q=%r", q)
        raise ExternalServiceError("Nevotex search timed out.") from exc
    except httpx.RequestError as exc:
        logger.warning("Nevotex request error for q=%r: %s", q, exc)
        raise ExternalServiceError("Nevotex search request failed.") from exc

    if response.status_code != 200:
        logger.warning("Nevotex returned HTTP %s for q=%r", response.status_code, q)
        raise ExternalServiceError(
            f"Nevotex search returned unexpected status {response.status_code}."
        )

    html = response.text
    # A search with no hits still renders the results fragment, so "no product rows"
    # is a valid empty result. Only a response that is not markup at all is a defect.
    if "<" not in html:
        logger.warning("Nevotex returned a non-HTML response for q=%r", q)
        raise ExternalServiceError("Nevotex search returned an unexpected response shape.")

    return parse_nevotex_search_results(html, limit=limit)
