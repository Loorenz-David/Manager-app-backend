"""QUERY: Lookup item by article_number across registered sources in parallel."""

from __future__ import annotations

import asyncio
import logging

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.lookup.base import ItemLookupResult
from beyo_manager.services.queries.items.lookup.internal_db import InternalDbLookupHandler
from beyo_manager.services.queries.items.lookup.purchase_api import PurchaseApiLookupHandler

logger = logging.getLogger(__name__)

_HANDLERS = [
    InternalDbLookupHandler(),
    PurchaseApiLookupHandler(),
]


def _serialize_result(result: ItemLookupResult) -> dict:
    return {
        "article_number": result.article_number,
        "sku": result.sku,
        "item_category_id": result.item_category_id,
        "quantity": result.quantity,
        "external_id": result.external_id,
        "external_source": result.external_source,
        "images": result.images,
    }


async def lookup_item_by_article_number(ctx: ServiceContext) -> dict:
    article_number = (ctx.query_params.get("article_number") or "").strip() or None
    sku = (ctx.query_params.get("sku") or "").strip() or None
    if not article_number and not sku:
        raise ValidationError("At least one of article_number or sku query parameters is required.")

    logger.info(
        "Looking up item by article_number=%r sku=%r across %d sources",
        article_number,
        sku,
        len(_HANDLERS),
    )

    raw_results = await asyncio.gather(
        *(handler.lookup(article_number, sku, ctx.session, ctx.workspace_id) for handler in _HANDLERS),
        return_exceptions=True,
    )

    items: list[dict] = []
    for handler, result in zip(_HANDLERS, raw_results):
        handler_name = handler.__class__.__name__
        if isinstance(result, Exception):
            logger.warning("Item lookup handler %s raised an exception: %s", handler_name, result, exc_info=result)
            continue
        if result is not None:
            serialized_result = _serialize_result(result)
            logger.info("Item lookup handler %s returned: %s", handler_name, serialized_result)
            items.append(serialized_result)
            continue
        logger.info("Item lookup handler %s returned no item", handler_name)

    return {"items": items}
