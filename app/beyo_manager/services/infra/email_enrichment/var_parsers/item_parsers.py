from __future__ import annotations

from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext


def parse_item_article_number(ctx: EnrichmentContext) -> str:
    if ctx.item is None:
        return ""
    return ctx.item.article_number or ""


def parse_item_sku(ctx: EnrichmentContext) -> str:
    if ctx.item is None:
        return ""
    return ctx.item.sku or ""


def parse_item_category(ctx: EnrichmentContext) -> str:
    if ctx.item_category is None:
        return ""
    return ctx.item_category.name or ""

