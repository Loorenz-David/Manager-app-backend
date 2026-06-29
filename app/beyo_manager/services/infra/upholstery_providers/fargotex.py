import asyncio
import logging
from collections.abc import Sequence
from typing import Any

import httpx

from beyo_manager.services.infra.fargotex.client import fetch_fargotex_category_html
from beyo_manager.services.infra.fargotex.constants import FARGOTEX_ORIGIN, MAX_FARGOTEX_PAGES
from beyo_manager.services.infra.fargotex.normalizer import normalize_fargotex_candidates
from beyo_manager.services.infra.fargotex.parser import (
    has_next_fargotex_page,
    parse_fargotex_listing_candidates,
)

logger = logging.getLogger(__name__)
_MAX_PAGE_CONCURRENCY = 3


def _matches_query(candidate: dict, q: str) -> bool:
    needle = q.strip().casefold()
    if not needle:
        return False
    haystack = " ".join(
        str(candidate.get(key) or "")
        for key in ("name", "code", "external_url")
    ).casefold()
    return needle in haystack


class FargotexExternalUpholsteryProvider:
    async def search(self, q: str, limit: int) -> Sequence[dict[str, Any]]:
        needle = q.strip()
        if not needle:
            return []

        matches: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        semaphore = asyncio.Semaphore(_MAX_PAGE_CONCURRENCY)

        async def _fetch_page(page: int) -> tuple[int, str | None]:
            try:
                async with semaphore:
                    html = await fetch_fargotex_category_html(page=page)
                return page, html
            except httpx.HTTPError as exc:
                logger.warning("Fargotex category fetch failed for page=%s: %s", page, exc)
                return page, None
            except Exception:
                logger.exception("Unexpected Fargotex category fetch failure for page=%s", page)
                return page, None

        page_results = await asyncio.gather(
            *[_fetch_page(page) for page in range(1, MAX_FARGOTEX_PAGES + 1)]
        )

        for page, html in sorted(page_results, key=lambda item: item[0]):
            if html is None:
                break
            try:
                raw_candidates = parse_fargotex_listing_candidates(html)
                normalized_candidates = normalize_fargotex_candidates(raw_candidates)
            except Exception:
                logger.exception("Unexpected Fargotex parse failure for page=%s", page)
                break

            for candidate in normalized_candidates:
                if not _matches_query(candidate, needle):
                    continue
                key = (FARGOTEX_ORIGIN, str(candidate["code"]))
                if key in seen:
                    continue
                seen.add(key)
                matches.append(candidate)
                if len(matches) >= limit:
                    return matches[:limit]

            if not has_next_fargotex_page(html):
                break

        return matches[:limit]
