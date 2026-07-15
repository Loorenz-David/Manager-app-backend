import logging
from urllib.parse import urlparse

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


def _validate_fargotex_product_url(url: str) -> str:
    value = url.strip()
    parsed = urlparse(value)
    base = urlparse(FARGOTEX_BASE_URL)
    path = parsed.path.rstrip("/")

    if (
        parsed.scheme != base.scheme
        or parsed.hostname != base.hostname
        or parsed.netloc != base.netloc
        or parsed.username
        or parsed.password
        or not path.startswith("/produkt/")
        or not path.removeprefix("/produkt/")
    ):
        raise ValueError("Invalid Fargotex product URL")

    return value


async def fetch_fargotex_category_html(page: int = 1) -> str:
    if page <= 1:
        url = f"{FARGOTEX_BASE_URL}{FARGOTEX_UPHOLSTERY_CATEGORY_PATH}"
    else:
        url = f"{FARGOTEX_BASE_URL}{FARGOTEX_UPHOLSTERY_CATEGORY_PATH}page/{page}/"

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=_HEADERS) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def fetch_fargotex_product_html(product_url: str) -> str:
    url = _validate_fargotex_product_url(product_url)

    async with httpx.AsyncClient(
        timeout=_TIMEOUT_SECONDS,
        headers=_HEADERS,
        follow_redirects=False,
    ) as client:
        response = await client.get(url)
        if 300 <= response.status_code < 400:
            raise httpx.HTTPStatusError(
                "Fargotex product page returned a redirect",
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        return response.text
