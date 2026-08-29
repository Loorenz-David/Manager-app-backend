from __future__ import annotations

import json
import logging
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.queries.items.lookup.base import (
    ItemLookupHandler,
    ItemLookupResult,
)

logger = logging.getLogger(__name__)

_PURCHASE_API_BASE = "https://api.beyovintage.se"
_EXTERNAL_SOURCE_NAME = "purchase_api"
_PURCHASE_PRICE_TO_SEK_RATE = {
    "DKK": Decimal("1.5"),
    "EUR": Decimal("11"),
    "SEK": Decimal("1"),
}


def _normalize_purchase_price_to_sek_minor(
    purchase_price: int | float | None,
    currency: str | None,
) -> int | None:
    if purchase_price is None:
        return None

    currency_code = (currency or "").strip().upper()
    try:
        rate = _PURCHASE_PRICE_TO_SEK_RATE[currency_code]
    except KeyError as exc:
        raise ValueError(
            f"Purchase API returned purchase_price with unsupported currency {currency_code!r}"
        ) from exc

    normalized_minor = Decimal(str(purchase_price)) * rate * 100
    return int(normalized_minor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def has_attributes_payload(raw: object) -> bool:
    """Did the purchase API send something under `attributes` that should yield properties?

    Lets a caller tell "this item has no attributes" apart from "this item has
    attributes we could not read" — the parser collapses both to an empty
    snapshot, but only the second is worth a human's attention.
    """
    if isinstance(raw, str):
        return raw.strip() not in ("", "[]")
    if isinstance(raw, list):
        return bool(raw)
    return raw is not None


def parse_purchase_api_attributes(raw: object) -> dict:
    r"""Project the purchase app's `attributes` payload into a canonical properties snapshot.

    The purchase API sends the attribute list JSON-encoded inside a string::

        "[{\"key\":\"wood_type\",\"label\":\"Type of Wood\",\"value\":\"Teak\"}]"

    which becomes ``{"wood_type": "Teak"}`` — an object keyed by attribute key,
    the shape `apply_properties_snapshot` stores and the creation endpoints
    accept. `label` is deliberately dropped: it is display text owned by the
    purchase app, and folding it into the blob would make a rename upstream
    change the item's signature and silently re-group its typical samples.

    Every failure degrades to an empty snapshot with a warning rather than
    raising. A malformed attributes blob must not cost the caller the rest of the
    lookup — price, images and category are still perfectly good — and an empty
    snapshot is inert on the write path, so it can never clear a stored profile.

    Entries are deduplicated by key keeping the first occurrence, and an entry
    with a blank key or no value is dropped: a blank value carries no profile
    information but would still change the signature.
    """
    if not has_attributes_payload(raw):
        return {}

    decoded = raw
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Purchase API sent attributes that are not valid JSON: %r", raw)
            return {}

    if not isinstance(decoded, list):
        logger.warning("Purchase API sent attributes that are not a list: %r", decoded)
        return {}

    properties: dict = {}
    for entry in decoded:
        if not isinstance(entry, dict):
            logger.warning("Skipping a non-object attributes entry: %r", entry)
            continue

        key = str(entry.get("key") or "").strip()
        if not key:
            logger.warning("Skipping an attributes entry with no key: %r", entry)
            continue
        if key in properties:
            logger.warning("Skipping a duplicate attributes key %r; keeping the first value", key)
            continue

        value = entry.get("value")
        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        properties[key] = value.strip() if isinstance(value, str) else value

    return properties


async def _find_category_id_by_name(
    session: AsyncSession,
    workspace_id: str,
    name: str,
) -> str | None:
    result = await session.execute(
        select(ItemCategory.client_id)
        .where(
            ItemCategory.workspace_id == workspace_id,
            func.lower(ItemCategory.name) == name.lower(),
            ItemCategory.is_deleted.is_(False),
        )
        .limit(1)
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
            logger.warning(
                "BEYO_VINTAGE_API_KEY is not set; skipping purchase API lookup"
            )
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
                logger.warning(
                    "Purchase API unavailable (503) — partner API not configured on remote server"
                )
                return None
            response.raise_for_status()
            body = response.json()

        if not body.get("success"):
            logger.warning(
                "Purchase API returned success=false for article_number=%r: %s",
                article_number,
                body.get("error"),
            )
            return None

        data = body.get("data", {})

        subcategory = data.get("subcategory")
        item_category_id: str | None = None
        if subcategory:
            item_category_id = await _find_category_id_by_name(
                session, workspace_id, subcategory
            )

        raw_photo_urls: list[str] = data.get("photo_urls") or []
        images = [
            f"{_PURCHASE_API_BASE}{path}" if path.startswith("/") else path
            for path in raw_photo_urls
        ]
        purchase_price_minor = _normalize_purchase_price_to_sek_minor(
            data.get("purchase_price"),
            data.get("currency"),
        )
        properties = parse_purchase_api_attributes(data.get("attributes"))

        return ItemLookupResult(
            article_number=data.get("article_number", article_number),
            sku=None,
            item_category_id=item_category_id,
            quantity=int(data.get("quantity") or 1),
            external_id=None,
            external_source=_EXTERNAL_SOURCE_NAME,
            images=images,
            purchase_price_minor=purchase_price_minor,
            properties=properties or None,
        )
