from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.calculator import (
    calculate_allowed_worker_minutes,
    calculate_production_budget,
    calculate_term_amounts,
)
from beyo_manager.domain.item_economics.configuration import (
    resolve_economics_selection,
    resolve_item_economics_status,
    resolve_major_category,
)
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.item_economics.serializers import (
    serialize_item_economics_preview,
    serialize_item_valuation,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.item_economics._common import audit, today_utc, translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import parse_item_valuation_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def _load_preview_inputs(ctx: ServiceContext, item: Item):
    groups = (
        await ctx.session.execute(
            select(ProductionCostGroup).where(
                ProductionCostGroup.workspace_id == ctx.workspace_id,
                ProductionCostGroup.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    basis_versions = (
        await ctx.session.execute(
            select(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
                ProductionCostBasisVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    cost_model_versions = (
        await ctx.session.execute(
            select(CostModelVersion).where(
                CostModelVersion.workspace_id == ctx.workspace_id,
                CostModelVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    selection = resolve_economics_selection(
        resolve_major_category(item.item_major_category_snapshot),
        groups,
        basis_versions,
        cost_model_versions,
        today_utc(),
    )
    terms = []
    if selection.cost_model_version is not None:
        terms = (
            await ctx.session.execute(
                select(CostModelTerm).where(
                    CostModelTerm.workspace_id == ctx.workspace_id,
                    CostModelTerm.cost_model_version_id == selection.cost_model_version.client_id,
                    CostModelTerm.is_deleted.is_(False),
                ).order_by(CostModelTerm.created_at.asc(), CostModelTerm.client_id.asc())
            )
        ).scalars().all()
    return selection, terms


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
        current = await ctx.session.scalar(
            select(ItemValuation).where(
                ItemValuation.workspace_id == ctx.workspace_id,
                ItemValuation.item_id == item.client_id,
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
        )
        old_client_id = current.client_id if current is not None else None
        close_result = await ctx.session.execute(
            update(ItemValuation)
            .where(
                ItemValuation.workspace_id == ctx.workspace_id,
                ItemValuation.item_id == item.client_id,
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
            .values(superseded_at=now)
        )

        valuation = ItemValuation(
            workspace_id=ctx.workspace_id,
            item_id=item.client_id,
            expected_sale_price_minor=request.expected_sale_price_minor,
            purchase_cost_minor=request.purchase_cost_minor,
            currency=request.currency,
            created_at=now,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(valuation)
        try:
            await ctx.session.flush()
        except IntegrityError as exc:
            translate_integrity_error(exc)
        if close_result.rowcount == 1 and old_client_id is not None:
            await ctx.session.execute(
                update(ItemValuation)
                .where(ItemValuation.client_id == old_client_id)
                .values(superseded_by_id=valuation.client_id)
            )
            await ctx.session.flush()

        selection, terms = await _load_preview_inputs(ctx, item)
        preview = _preview(valuation, selection, terms)
        await audit(ctx, "item_valuation.created", "item_valuation", valuation.client_id)
        response = {
            "item_valuation": serialize_item_valuation(valuation),
            "preview": preview,
        }
    return response
