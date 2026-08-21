"""Field backfillers for the Shopify → app backfill orchestrator.

Each backfiller owns one app field sourced from Shopify. `decide` is pure —
it turns the item, its current valuation, and the fetched Shopify snapshot
into a `FieldPlan` without touching the network or the database. `apply`
re-verifies the plan against the live row and then writes through the proper
service so versioning, audit, and preview semantics hold.

Adding a new Shopify-sourced field = one new backfiller + one REGISTRY entry;
the orchestrator does not change.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.context import ServiceContext

ACTION_UPDATE = "update"
ACTION_SKIP = "skip"

APPLY_APPLIED = "applied"
APPLY_DRIFTED = "drifted"

SHOPIFY_TO_ITEM_CURRENCY: dict[str, ItemCurrencyEnum] = {
    "SEK": ItemCurrencyEnum.SWEDISH_KRONA,
    "DKK": ItemCurrencyEnum.DANISH_KRONA,
    "EUR": ItemCurrencyEnum.EURO,
}

_CURRENCY_DISPLAY: dict[ItemCurrencyEnum, str] = {
    ItemCurrencyEnum.SWEDISH_KRONA: "SEK",
    ItemCurrencyEnum.DANISH_KRONA: "DKK",
    ItemCurrencyEnum.EURO: "EUR",
}

ValuationTriple = tuple[int | None, int | None, ItemCurrencyEnum]


@dataclass(frozen=True)
class ShopifySnapshot:
    """What one item's Shopify lookup returned: exact barcode matches + shop currency."""

    variant_matches: list[dict]
    shop_currency_code: str | None


@dataclass(frozen=True)
class FieldPlan:
    field: str
    item_client_id: str
    article_number: str
    action: str
    reason: str
    before: str
    after: str
    payload: dict | None = None
    expected_current: ValuationTriple | None = None


class FieldBackfiller(Protocol):
    name: str

    def decide(
        self,
        *,
        item_client_id: str,
        article_number: str,
        current_valuation: ItemValuation | None,
        snapshot: ShopifySnapshot,
    ) -> FieldPlan: ...

    async def apply(self, session: AsyncSession, identity: dict, plan: FieldPlan) -> str: ...


def format_minor(amount_minor: int | None, currency: ItemCurrencyEnum | None) -> str:
    if amount_minor is None:
        return "—"
    display = _CURRENCY_DISPLAY.get(currency, "?") if currency else "?"
    return f"{Decimal(amount_minor) / 100:,.2f} {display}".replace(",", " ")


def _current_triple(valuation: ItemValuation | None) -> ValuationTriple | None:
    if valuation is None:
        return None
    return (
        valuation.expected_sale_price_minor,
        valuation.purchase_cost_minor,
        valuation.currency,
    )


class ExpectedSoldPriceBackfiller:
    """Shopify variant listing price → item valuation expected sale price."""

    name = "expected_sold_price"

    def decide(
        self,
        *,
        item_client_id: str,
        article_number: str,
        current_valuation: ItemValuation | None,
        snapshot: ShopifySnapshot,
    ) -> FieldPlan:
        def skip(reason: str) -> FieldPlan:
            return FieldPlan(
                field=self.name,
                item_client_id=item_client_id,
                article_number=article_number,
                action=ACTION_SKIP,
                reason=reason,
                before=format_minor(
                    current_valuation.expected_sale_price_minor if current_valuation else None,
                    current_valuation.currency if current_valuation else None,
                ),
                after="—",
            )

        matches = snapshot.variant_matches
        if not matches:
            return skip("not_found")

        # Several Shopify listings can share one article number (e.g. two copies
        # of the same piece). Duplicates are only ambiguous when they disagree
        # on the price — when every match quotes the same figure there is
        # nothing left to guess, so the backfill proceeds. A match that carries
        # no price counts as disagreement rather than agreement.
        distinct_prices = {_parse_price_minor(node.get("price")) for node in matches}
        if len(distinct_prices) > 1:
            return skip("ambiguous")

        price_minor = distinct_prices.pop()
        if price_minor is None:
            return skip("no_price")

        shop_currency = SHOPIFY_TO_ITEM_CURRENCY.get(snapshot.shop_currency_code or "")
        if shop_currency is None:
            return skip("unsupported_currency")

        if current_valuation is None:
            new_triple: ValuationTriple = (price_minor, None, shop_currency)
        else:
            if current_valuation.currency is not shop_currency:
                return skip("currency_conflict")
            new_triple = (price_minor, current_valuation.purchase_cost_minor, current_valuation.currency)
            if new_triple == _current_triple(current_valuation):
                return skip("unchanged")

        expected_sale_price_minor, purchase_cost_minor, currency = new_triple
        base_reason = "first_valuation" if current_valuation is None else "price_changed"
        agreeing_duplicates = f" ({len(matches)} listings agree)" if len(matches) > 1 else ""
        return FieldPlan(
            field=self.name,
            item_client_id=item_client_id,
            article_number=article_number,
            action=ACTION_UPDATE,
            reason=base_reason + agreeing_duplicates,
            before=format_minor(
                current_valuation.expected_sale_price_minor if current_valuation else None,
                current_valuation.currency if current_valuation else None,
            ),
            after=format_minor(expected_sale_price_minor, currency),
            payload={
                "item_client_id": item_client_id,
                "expected_sale_price_minor": expected_sale_price_minor,
                "purchase_cost_minor": purchase_cost_minor,
                "currency": currency.value,
            },
            expected_current=_current_triple(current_valuation),
        )

    async def apply(self, session: AsyncSession, identity: dict, plan: FieldPlan) -> str:
        # Own the transaction: the drift-check SELECT would otherwise start an
        # implicit one and demote maybe_begin inside the command to subordinate
        # mode, which never commits.
        async with session.begin():
            current = await session.scalar(
                select(ItemValuation).where(
                    ItemValuation.workspace_id == identity["workspace_id"],
                    ItemValuation.item_id == plan.item_client_id,
                    ItemValuation.superseded_at.is_(None),
                    ItemValuation.is_deleted.is_(False),
                )
            )
            if _current_triple(current) != plan.expected_current:
                return APPLY_DRIFTED
            ctx = ServiceContext(
                identity=identity,
                incoming_data=dict(plan.payload or {}),
                session=session,
            )
            await set_item_valuation(ctx)
        return APPLY_APPLIED


def _parse_price_minor(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        parsed = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None
    if parsed < 0:
        return None
    return int(parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN) * 100)


REGISTRY: dict[str, FieldBackfiller] = {
    ExpectedSoldPriceBackfiller.name: ExpectedSoldPriceBackfiller(),
}
