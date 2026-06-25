import logging
from typing import Any

import httpx

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.nevotex.constants import NEVOTEX_SEARCH_URL

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10.0

_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    "Referer": "https://nevotex.se/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
}


async def fetch_nevotex_raw_products(q: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "ID": "9403",
        "instasearch": "1",
        "feed": "true",
        "pagesize": str(limit),
        "Search": q,
        "feedType": "productsOnly",
        "redirect": "false",
        "DoNotShowVariantsAsSingleProducts": "False",
        "Template": "SearchProductsTemplate",
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

    try:
        containers = response.json()
    except ValueError as exc:
        logger.warning("Nevotex returned invalid JSON for q=%r", q)
        raise ExternalServiceError("Nevotex search returned a non-JSON response.") from exc

    if not isinstance(containers, list):
        logger.warning("Nevotex response is not a list for q=%r", q)
        raise ExternalServiceError("Nevotex search returned an unexpected response shape.")

    raw_products: list[dict[str, Any]] = []
    for container in containers:
        if not isinstance(container, dict):
            continue
        products = container.get("Product")
        if not isinstance(products, list):
            continue
        raw_products.extend(product for product in products if isinstance(product, dict))

    return raw_products
