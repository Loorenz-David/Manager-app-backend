"""QUERY: Suggest the next house SKU for an item category on a given day."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.sku_prefixes import (
    SKU_DATE_CODE_PATTERN,
    format_suggested_sku,
    next_sku_sequence,
    sku_prefix_for_category,
    sku_sequence_pattern,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.context import ServiceContext


async def _list_skus_for_day(
    session: AsyncSession, workspace_id: str, prefix: str, date_code: str
) -> list[str]:
    rows = await session.scalars(
        select(Item.sku).where(
            Item.workspace_id == workspace_id,
            Item.is_deleted.is_(False),
            Item.sku.isnot(None),
            Item.sku.regexp_match(sku_sequence_pattern(prefix, date_code), flags="i"),
        )
    )
    return [sku for sku in rows if sku]


async def suggest_item_sku(ctx: ServiceContext) -> dict:
    """Read-only: nothing is reserved. Two users racing on the same SKU get the
    existing duplicate-SKU conflict when the Shopify form saves."""
    item_category_id = (ctx.query_params.get("item_category_id") or "").strip()
    date_code = (ctx.query_params.get("date_code") or "").strip()
    if not item_category_id:
        raise ValidationError("item_category_id is required.")
    if not SKU_DATE_CODE_PATTERN.match(date_code):
        raise ValidationError("date_code must be six digits (DDMMYY).")

    category_name = await ctx.session.scalar(
        select(ItemCategory.name).where(
            ItemCategory.client_id == item_category_id,
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.is_deleted.is_(False),
        )
    )
    if category_name is None:
        raise NotFound("Item category not found.")

    prefix = sku_prefix_for_category(category_name)
    if prefix is None:
        return {"sku": None, "prefix": None, "sequence": None}

    existing = await _list_skus_for_day(ctx.session, ctx.workspace_id, prefix, date_code)
    sequence = next_sku_sequence(existing, prefix, date_code)
    return {
        "sku": format_suggested_sku(prefix, sequence, date_code),
        "prefix": prefix,
        "sequence": sequence,
    }
