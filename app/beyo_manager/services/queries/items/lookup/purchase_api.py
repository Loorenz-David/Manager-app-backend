from __future__ import annotations

import logging
from urllib.parse import quote

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.queries.items.lookup.base import ItemLookupHandler, ItemLookupResult

logger = logging.getLogger(__name__)

_PURCHASE_API_BASE = "https://api.beyovintage.se"
_EXTERNAL_SOURCE_NAME = "purchase_api"


async def _find_category_id_by_name(
    session: AsyncSession,
    workspace_id: str,
    name: str,
) -> str | None:
    result = await session.execute(
        select(ItemCategory.client_id).where(
            ItemCategory.workspace_id == workspace_id,
            func.lower(ItemCategory.name) == name.lower(),
            ItemCategory.is_deleted.is_(False),
        ).limit(1)
    )
    return result.scalar_one_or_none()


class PurchaseApiLookupHandler(ItemLookupHandler):
    async def lookup(
        self,
        article_number: str | None,
        sku: str | None,
        session: AsyncSession,
        workspace_id: str,
    ) -> ItemLookupResult | None:
        if not article_number:
            return None

        api_key = settings.beyo_vintage_api_key
        if not api_key:
            logger.warning("BEYO_VINTAGE_API_KEY is not set; skipping purchase API lookup")
            return None

        url = f"{_PURCHASE_API_BASE}/api/partner/items/{quote(article_number, safe='')}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
            response = await client.get(url, headers={"X-Partner-Key": api_key})
            if response.status_code == 404:
                return None
            if response.status_code in (401, 403):
                logger.error(
                    "Purchase API rejected the request (HTTP %s) — check BEYO_VINTAGE_API_KEY",
                    response.status_code,
                )
                return None
            if response.status_code == 400:
                logger.warning(
                    "Purchase API returned 400 for article_number=%r — invalid or unsupported format",
                    article_number,
                )
                return None
            if response.status_code == 503:
                logger.warning("Purchase API unavailable (503) — partner API not configured on remote server")
                return None
            response.raise_for_status()
            body = response.json()

        if not body.get("success"):
            logger.warning("Purchase API returned success=false for article_number=%r: %s", article_number, body.get("error"))
            return None

        data = body.get("data", {})

        subcategory = data.get("subcategory")
        item_category_id: str | None = None
        if subcategory:
            item_category_id = await _find_category_id_by_name(session, workspace_id, subcategory)

        raw_photo_urls: list[str] = data.get("photo_urls") or []
        images = [
            f"{_PURCHASE_API_BASE}{path}" if path.startswith("/") else path
            for path in raw_photo_urls
        ]

        return ItemLookupResult(
            article_number=data.get("article_number", article_number),
            sku=None,
            item_category_id=item_category_id,
            quantity=int(data.get("quantity") or 1),
            external_id=None,
            external_source=_EXTERNAL_SOURCE_NAME,
            images=images,
        )
