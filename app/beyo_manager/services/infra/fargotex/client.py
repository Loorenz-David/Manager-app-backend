import logging

import httpx

from beyo_manager.services.infra.fargotex.constants import (
    FARGOTEX_BASE_URL,
    FARGOTEX_UPHOLSTERY_CATEGORY_PATH,
)

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 20.0
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


async def fetch_fargotex_category_html(page: int = 1) -> str:
    if page <= 1:
        url = f"{FARGOTEX_BASE_URL}{FARGOTEX_UPHOLSTERY_CATEGORY_PATH}"
    else:
        url = f"{FARGOTEX_BASE_URL}{FARGOTEX_UPHOLSTERY_CATEGORY_PATH}page/{page}/"

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=_HEADERS) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
