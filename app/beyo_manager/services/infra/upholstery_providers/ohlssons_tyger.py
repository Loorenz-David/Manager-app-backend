import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.ohlssons_tyger.client import (
    fetch_ohlssons_tyger_detail_html,
    fetch_ohlssons_tyger_search_html,
)
from beyo_manager.services.infra.ohlssons_tyger.constants import (
    OHLSSONS_TYGER_BASE_URL,
    OHLSSONS_TYGER_ORIGIN,
)
from beyo_manager.services.infra.ohlssons_tyger.normalizer import (
    normalize_ohlssons_tyger_candidate,
)
from beyo_manager.services.infra.ohlssons_tyger.parser import (
    parse_ohlssons_tyger_detail,
    parse_ohlssons_tyger_listing_candidates,
)

logger = logging.getLogger(__name__)

_MAX_DETAIL_CONCURRENCY = 3


class OhlssonsTygerExternalUpholsteryProvider:
    async def search(self, q: str, limit: int) -> Sequence[dict[str, Any]]:
        try:
            listing_html = await fetch_ohlssons_tyger_search_html(q=q, limit=limit)
        except ExternalServiceError as exc:
            logger.warning("Ohlssons Tyger search failed for q=%r: %s", q, exc)
            return []

        listing_candidates = parse_ohlssons_tyger_listing_candidates(
            listing_html,
            OHLSSONS_TYGER_BASE_URL,
            limit=limit,
        )
        if not listing_candidates:
            return []

        semaphore = asyncio.Semaphore(_MAX_DETAIL_CONCURRENCY)

        async def _process(candidate: dict) -> dict | None:
            detail_url = candidate.get("detail_url", "")
            if not detail_url:
                return None

            try:
                async with semaphore:
                    detail_html = await fetch_ohlssons_tyger_detail_html(detail_url)
            except ExternalServiceError as exc:
                logger.warning("Ohlssons Tyger detail fetch failed for url=%r: %s", detail_url, exc)
                return None
            except Exception:
                logger.exception("Unexpected Ohlssons Tyger detail fetch failure for url=%r", detail_url)
                return None

            try:
                raw_detail = parse_ohlssons_tyger_detail(
                    detail_html,
                    detail_url,
                    OHLSSONS_TYGER_BASE_URL,
                    fallback_name=str(candidate.get("name", "")),
                    fallback_image=str(candidate.get("image_url", "")),
                )
                if raw_detail is None:
                    return None
                if raw_detail["code"] == detail_url.rstrip("/").rsplit("/", 1)[-1]:
                    logger.debug(
                        "Using Ohlssons Tyger URL slug as fallback product code: %s",
                        detail_url,
                    )
                return normalize_ohlssons_tyger_candidate(raw_detail)
            except Exception:
                logger.exception("Unexpected Ohlssons Tyger parse failure for url=%r", detail_url)
                return None

        normalized_candidates = await asyncio.gather(*[_process(candidate) for candidate in listing_candidates])

        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for candidate in normalized_candidates:
            if candidate is None:
                continue
            key = (OHLSSONS_TYGER_ORIGIN, str(candidate["code"]))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped
