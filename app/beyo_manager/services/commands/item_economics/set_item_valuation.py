from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.item_economics.calculator import (
    calculate_allowed_worker_minutes,
    calculate_production_budget,
    calculate_term_amounts,
)
from beyo_manager.domain.item_economics.configuration import resolve_item_economics_status
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.item_economics.serializers import (
    serialize_item_economics_preview,
    serialize_item_valuation,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.item_economics._common import (
    _load_preview_inputs,
    audit,
    write_item_valuation_chain_in_session,
)
from beyo_manager.services.commands.item_economics.requests import parse_item_valuation_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

# The extracted preview loader remains the sole production call site for
# resolve_major_category(item.item_major_category_snapshot).


def _preview(
    valuation: ItemValuation,
    selection: object,
    terms: list[object],
) -> dict:
    status = resolve_item_economics_status(valuation, selection, terms)
    if status is not EconomicsStatusEnum.NOT_EVALUATED:
        return serialize_item_economics_preview(status)

    basis = selection.basis_version
    amounts = calculate_term_amounts(
        terms,
        valuation.expected_sale_price_minor,
        valuation.purchase_cost_minor,
    )
    budget = calculate_production_budget(valuation.expected_sale_price_minor, amounts)
    allowed = calculate_allowed_worker_minutes(budget, basis.cost_per_worker_minute_minor)
    return serialize_item_economics_preview(status, budget, allowed)


async def set_item_valuation(ctx: ServiceContext) -> dict:
    request = parse_item_valuation_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        item = await ctx.session.scalar(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id == (
                    ctx.incoming_data.get("item_client_id")
                    or ctx.incoming_data.get("item_id")
                ),
                Item.is_deleted.is_(False),
            )
        )
        if item is None:
            raise NotFound("Item not found.")

        now = datetime.now(timezone.utc)
        valuation = await write_item_valuation_chain_in_session(
            ctx.session,
            workspace_id=ctx.workspace_id,
            item_id=item.client_id,
            expected_sale_price_minor=request.expected_sale_price_minor,
            purchase_cost_minor=request.purchase_cost_minor,
            currency=request.currency,
            created_by_id=ctx.user_id,
            now=now,
        )

        selection, terms = await _load_preview_inputs(ctx, item)
        preview = _preview(valuation, selection, terms)
        await audit(ctx, "item_valuation.created", "item_valuation", valuation.client_id)
        response = {
            "item_valuation": serialize_item_valuation(valuation),
            "preview": preview,
        }
    return response
