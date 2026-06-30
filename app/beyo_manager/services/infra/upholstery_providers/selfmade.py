import logging
from collections.abc import Sequence
from typing import Any

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.selfmade.client import fetch_selfmade_search_html
from beyo_manager.services.infra.selfmade.constants import (
    MAX_SELFMADE_PAGES,
    SELFMADE_ORIGIN,
)
from beyo_manager.services.infra.selfmade.normalizer import normalize_selfmade_candidates
from beyo_manager.services.infra.selfmade.parser import (
    has_next_selfmade_page,
    parse_selfmade_listing_candidates,
)

logger = logging.getLogger(__name__)


class SelfmadeExternalUpholsteryProvider:
    async def search(self, q: str, limit: int) -> Sequence[dict[str, Any]]:
        needle = q.strip()
        if not needle or limit <= 0:
            return []

        matches: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for page in range(1, MAX_SELFMADE_PAGES + 1):
            try:
                html = await fetch_selfmade_search_html(q=needle, page=page)
            except ExternalServiceError as exc:
                logger.warning("Selfmade search failed for q=%r page=%s: %s", needle, page, exc)
                break
            except Exception:
                logger.exception("Unexpected Selfmade search failure for q=%r page=%s", needle, page)
                break

            try:
                raw_candidates = parse_selfmade_listing_candidates(html)
                normalized_candidates = normalize_selfmade_candidates(raw_candidates)
            except Exception:
                logger.exception("Unexpected Selfmade parse failure for q=%r page=%s", needle, page)
                break

            for candidate in normalized_candidates:
                code = candidate.get("code")
                if not code or candidate.get("unit") != "m":
                    continue
                key = (SELFMADE_ORIGIN, str(code))
                if key in seen:
                    continue
                seen.add(key)
                matches.append(candidate)
                if len(matches) >= limit:
                    return matches[:limit]

            if len(matches) >= limit or not has_next_selfmade_page(html):
                break

        return matches[:limit]
