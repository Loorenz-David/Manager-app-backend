from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.item_economics.configuration import resolve_item_economics_status
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.item_economics.serializers import serialize_item_economics_preview
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs, audit
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_item_valuation(ctx: ServiceContext) -> dict:
    async with maybe_begin(ctx.session):
        valuation_client_id = (
            ctx.incoming_data.get("valuation_client_id")
            or ctx.incoming_data.get("client_id")
        )
        statement = select(ItemValuation).where(ItemValuation.workspace_id == ctx.workspace_id)
        if valuation_client_id is not None:
            statement = statement.where(ItemValuation.client_id == valuation_client_id)
        else:
            statement = statement.where(
                ItemValuation.item_id == ctx.incoming_data.get("item_client_id"),
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
        valuation = await ctx.session.scalar(statement)
        if valuation is None or valuation.is_deleted:
            raise NotFound("Item valuation not found.")
        if valuation.superseded_at is not None:
            raise ValidationError(
                "ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE: superseded valuations cannot be deleted"
            )
        valuation.is_deleted = True
        valuation.deleted_at = datetime.now(timezone.utc)
        valuation.deleted_by_id = ctx.user_id
        await ctx.session.flush()
        await audit(ctx, "item_valuation.deleted", "item_valuation", valuation.client_id)
        item = await ctx.session.scalar(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == valuation.item_id,
                Item.is_deleted.is_(False),
            )
        )
        if item is None:
            status = EconomicsStatusEnum.ITEM_UNVALUED
        else:
            selection, terms = await _load_preview_inputs(ctx, item)
            status = resolve_item_economics_status(None, selection, terms)
    return {"preview": serialize_item_economics_preview(status)}
