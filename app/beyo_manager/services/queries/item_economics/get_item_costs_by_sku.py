"""Item cost summary by SKU for the external pricing app.

A deliberately flat read: purchase cost, expected sale price, restoration cost
(actual labour spent, else the committed production budget) and "other costs"
(the cost-model terms this app subtracts from the sale price, minus the purchase
term). No new economics — every number is a stored value or comes from
`calculator.calculate_term_amount` over the same terms `_load_preview_inputs`
selects for the valuation preview.

Contract: `GET /api/v1/pricing/item-costs?sku=…` (routers/api_v1/pricing_api.py).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, text

from beyo_manager.domain.item_economics.calculator import calculate_term_amount
from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_result import ItemCostResult
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.pricing_api.auth import (
    refuse_pricing_api_auth,
    verify_pricing_api_request,
)

_ISO_CURRENCY = {
    ItemCurrencyEnum.SWEDISH_KRONA: "SEK",
    ItemCurrencyEnum.DANISH_KRONA: "DKK",
    ItemCurrencyEnum.EURO: "EUR",
}

RESTORATION_SOURCE_ACTUAL = "actual"
RESTORATION_SOURCE_PLANNED = "planned"


def _amount(minor: int) -> str:
    """Minor units → a two-decimal string. All three supported currencies have
    two minor digits."""
    return str((Decimal(minor) / Decimal(100)).quantize(Decimal("0.01")))


def _money(minor: int | None, updated_at: datetime | None, **extra) -> dict | None:
    if minor is None:
        return None
    return {
        "amount": _amount(minor),
        "updatedAt": updated_at.isoformat() if updated_at is not None else None,
        **extra,
    }


def _stamp(row) -> datetime:
    return getattr(row, "updated_at", None) or row.created_at


async def get_item_costs_for_pricing_app(ctx: ServiceContext) -> dict:
    """Authenticate the pricing app, then answer for its configured workspace.

    `ctx.incoming_data` carries `headers` (the request headers) and `sku`. Auth
    runs here, inside `run_service`, so its refusal renders like any other
    `DomainError`.
    """
    workspace_id = verify_pricing_api_request(ctx.incoming_data["headers"])
    exists = (
        await ctx.session.execute(
            text("SELECT 1 FROM workspaces WHERE client_id = :ws"),
            {"ws": workspace_id},
        )
    ).first()
    if exists is None:
        raise refuse_pricing_api_auth("workspace_not_found")
    scoped = replace(
        ctx,
        identity={"workspace_id": workspace_id},
        incoming_data={"sku": ctx.incoming_data.get("sku")},
    )
    return await get_item_costs_by_sku(scoped)


async def get_item_costs_by_sku(ctx: ServiceContext) -> dict:
    sku = (ctx.incoming_data.get("sku") or "").strip()
    if not sku:
        raise NotFound("Item not found.")
    item = await ctx.session.scalar(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.sku == sku,
            Item.is_deleted.is_(False),
        )
    )
    if item is None:
        raise NotFound("Item not found.")

    currencies: dict[str, ItemCurrencyEnum] = {}

    # ── valuation: purchase cost + expected sale price ──────────────────────
    valuation = await ctx.session.scalar(
        select(ItemValuation).where(
            ItemValuation.workspace_id == ctx.workspace_id,
            ItemValuation.item_id == item.client_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )
    purchase_cost = None
    expected_sale_price = None
    if valuation is not None:
        currencies["valuation"] = valuation.currency
        purchase_cost = _money(valuation.purchase_cost_minor, valuation.created_at)
        expected_sale_price = _money(valuation.expected_sale_price_minor, valuation.created_at)

    # ── restoration: actual spent, else the committed budget ────────────────
    # Same "current committed evaluation" predicates as get_item_lifetime_economics.
    evaluations = list(
        (
            await ctx.session.scalars(
                select(ItemCostEvaluation)
                .where(
                    ItemCostEvaluation.workspace_id == ctx.workspace_id,
                    ItemCostEvaluation.item_id == item.client_id,
                    ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
                    ItemCostEvaluation.superseded_at.is_(None),
                    ItemCostEvaluation.is_deleted.is_(False),
                )
                .order_by(
                    ItemCostEvaluation.committed_at.desc(),
                    ItemCostEvaluation.client_id.desc(),
                )
            )
        ).all()
    )
    restoration_cost = None
    if evaluations:
        by_task = {row.task_id: row for row in evaluations}
        results = list(
            (
                await ctx.session.scalars(
                    select(ItemCostResult).where(
                        ItemCostResult.workspace_id == ctx.workspace_id,
                        ItemCostResult.item_id == item.client_id,
                        ItemCostResult.task_id.in_(list(by_task)),
                    )
                )
            ).all()
        )
        if results:
            for result in results:
                currencies[f"evaluation:{result.task_id}"] = by_task[result.task_id].currency
            restoration_cost = _money(
                sum(result.consumed_cost_minor for result in results),
                max(result.computed_at for result in results),
                source=RESTORATION_SOURCE_ACTUAL,
            )
        else:
            latest = evaluations[0]
            currencies[f"evaluation:{latest.task_id}"] = latest.currency
            restoration_cost = _money(
                latest.production_budget_minor,
                latest.committed_at,
                source=RESTORATION_SOURCE_PLANNED,
            )

    # ── other costs: current cost-model terms, purchase term excluded ───────
    other_costs = None
    if valuation is not None and valuation.expected_sale_price_minor is not None:
        selection, terms = await _load_preview_inputs(ctx, item, now=ctx.now)
        model = selection.cost_model_version
        if model is not None:
            currencies["cost_model"] = model.currency  # type: ignore[attr-defined]
            counted = [
                term
                for term in terms
                if term.calculation_type is not CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST
            ]
            total = sum(
                calculate_term_amount(
                    term.calculation_type,
                    valuation.expected_sale_price_minor,
                    term.percent_value,
                    term.fixed_amount_minor,
                    valuation.purchase_cost_minor,
                )
                for term in counted
            )
            other_costs = _money(
                total,
                max([valuation.created_at, _stamp(model), *(_stamp(term) for term in counted)]),
            )

    distinct = set(currencies.values())
    if len(distinct) > 1:
        detail = ", ".join(f"{source}={value.value}" for source, value in sorted(currencies.items()))
        raise ConflictError(f"ITEM_COST_CURRENCY_MISMATCH: {detail}")

    return {
        "sku": item.sku,
        "currency": _ISO_CURRENCY[distinct.pop()] if distinct else None,
        "expectedSalePrice": expected_sale_price,
        "purchaseCost": purchase_cost,
        "restorationCost": restoration_cost,
        "otherCosts": other_costs,
    }
