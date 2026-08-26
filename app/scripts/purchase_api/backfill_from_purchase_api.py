"""Backfill purchase cost from the purchase app API, dry-run first.

Takes every item in the workspace that has an article_number, looks it up one
by one against the purchase app partner API (the same endpoint the frontend
lookup uses), converts the returned purchase price to SEK minor (öre) through
the production transformation in
`beyo_manager.services.queries.items.lookup.purchase_api`, multiplies by the
quantity stored on the app item, and writes the total as
`purchase_cost_minor` through `set_item_valuation` so versioning, audit, and
preview semantics hold.

Example::

    # from backend/app, dry run (default) against the workspace of a user
    PYTHONPATH=. APP_ENV=development python -m scripts.purchase_api.backfill_from_purchase_api \
      --username david

    # write one item for real
    PYTHONPATH=. APP_ENV=development python -m scripts.purchase_api.backfill_from_purchase_api \
      --username david --article-number 12345 --execute
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Annotated
from urllib.parse import quote

import httpx
import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.lookup.purchase_api import (
    _PURCHASE_API_BASE,
    _normalize_purchase_price_to_sek_minor,
)

logger = logging.getLogger(__name__)
app = typer.Typer(add_completion=False, no_args_is_help=True)

FIELD_NAME = "purchase_cost"

ACTION_UPDATE = "update"
ACTION_SKIP = "skip"

APPLY_APPLIED = "applied"
APPLY_DRIFTED = "drifted"

# Skip reasons that deserve a line in the "Needs attention" list.
_ATTENTION_REASONS = (
    "unsupported_currency",
    "currency_conflict",
    "non_positive_quantity",
    "api_reported_failure",
    "article_number_mismatch",
)

_CURRENCY_DISPLAY: dict[ItemCurrencyEnum, str] = {
    ItemCurrencyEnum.SWEDISH_KRONA: "SEK",
    ItemCurrencyEnum.DANISH_KRONA: "DKK",
    ItemCurrencyEnum.EURO: "EUR",
}

ValuationTriple = tuple[int | None, int | None, ItemCurrencyEnum]


class FatalApiError(Exception):
    """The purchase API rejected the run itself (auth/config); every further call would fail."""


@dataclass(frozen=True)
class Lookup:
    """Outcome of one article-number lookup against the purchase API."""

    status: str  # "ok" | "not_found" | "invalid" | "api_reported_failure" | "error"
    data: dict | None = None
    error: str | None = None


@dataclass(frozen=True)
class FieldPlan:
    item_client_id: str
    article_number: str
    action: str
    reason: str
    before: str
    after: str
    payload: dict | None = None
    expected_current: ValuationTriple | None = None


@dataclass
class _RunContext:
    identity: dict
    api_key: str
    items: list[Item]
    current_valuations: dict[str, ItemValuation]


@dataclass
class _Totals:
    updated: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    drifted: int = 0
    errors: int = 0
    attention: list[str] = field(default_factory=list)


@app.command("backfill-from-purchase-api")
def main(
    username: Annotated[str, typer.Option("--username", help="App user whose workspace to backfill.")],
    workspace_id: Annotated[str | None, typer.Option("--workspace-id", help="Disambiguate when the user has several active workspaces.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute", help="Dry run (default) reports decisions without writing.")] = True,
    article_numbers: Annotated[list[str] | None, typer.Option("--article-number", help="Only these article numbers (repeatable).")] = None,
    limit: Annotated[int | None, typer.Option("--limit", min=1, help="Process at most N items.")] = None,
    log_level: Annotated[str, typer.Option("--log-level")] = "WARNING",
) -> None:
    """Backfill item purchase cost from the purchase app API, through the proper services."""
    exit_code = asyncio.run(
        _run(
            username=username,
            workspace_id=workspace_id,
            dry_run=dry_run,
            article_numbers=article_numbers or [],
            limit=limit,
            log_level=log_level,
        )
    )
    if exit_code:
        raise typer.Exit(exit_code)


async def _run(
    *,
    username: str,
    workspace_id: str | None,
    dry_run: bool,
    article_numbers: list[str],
    limit: int | None,
    log_level: str,
) -> int:
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.WARNING),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    await init_db()
    # The development engine runs with echo=True; keep script output readable.
    if log_level.upper() != "DEBUG":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    try:
        try:
            run_ctx = await _resolve_run_context(
                username=username,
                workspace_id=workspace_id,
                article_numbers=article_numbers,
                limit=limit,
            )
        except ValueError as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            return 1

        typer.echo(
            f"{'DRY RUN' if dry_run else 'EXECUTE'} | workspace={run_ctx.identity['workspace_id']} "
            f"source={_PURCHASE_API_BASE} items={len(run_ctx.items)} field={FIELD_NAME}"
        )
        if not run_ctx.items:
            typer.echo("Nothing to do: no items with an article_number matched the filters.")
            return 0

        try:
            plans, totals = await _fetch_and_decide(run_ctx)
        except FatalApiError as exc:
            typer.echo(f"\nERROR: {exc}", err=True)
            return 1

        updates = [plan for plan in plans if plan.action == ACTION_UPDATE]
        if dry_run:
            typer.echo(f"\nDry run: {len(updates)} update(s) would be written. Re-run with --execute to apply.")
        elif updates:
            await _apply_updates(run_ctx, updates, totals)
        else:
            typer.echo("\nNo updates to write.")

        _echo_summary(totals, dry_run=dry_run, planned_updates=len(updates))
        return 2 if totals.errors else 0
    finally:
        await close_db()


async def _resolve_run_context(
    *,
    username: str,
    workspace_id: str | None,
    article_numbers: list[str],
    limit: int | None,
) -> _RunContext:
    api_key = settings.beyo_vintage_api_key
    if not api_key:
        raise ValueError("BEYO_VINTAGE_API_KEY is not set; the purchase API cannot be queried.")

    async for session in get_db_session():
        user = await session.scalar(select(User).where(User.username == username))
        if user is None:
            raise ValueError(f"No user with username '{username}'.")

        memberships_query = select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user.client_id,
            WorkspaceMembership.is_active.is_(True),
        )
        if workspace_id is not None:
            memberships_query = memberships_query.where(WorkspaceMembership.workspace_id == workspace_id)
        memberships = (await session.execute(memberships_query)).scalars().all()
        if not memberships:
            raise ValueError(
                f"User '{username}' has no active workspace membership"
                + (f" in workspace '{workspace_id}'." if workspace_id else ".")
            )
        if len(memberships) > 1:
            options = ", ".join(m.workspace_id for m in memberships)
            raise ValueError(f"User '{username}' belongs to several workspaces ({options}); pass --workspace-id.")
        resolved_workspace_id = memberships[0].workspace_id

        items_query = select(Item).where(
            Item.workspace_id == resolved_workspace_id,
            Item.is_deleted.is_(False),
            Item.article_number.is_not(None),
        )
        if article_numbers:
            items_query = items_query.where(Item.article_number.in_(article_numbers))
        items_query = items_query.order_by(Item.article_number.asc())
        if limit is not None:
            items_query = items_query.limit(limit)
        items = (await session.execute(items_query)).scalars().all()

        current_valuations: dict[str, ItemValuation] = {}
        if items:
            valuation_rows = (
                await session.execute(
                    select(ItemValuation).where(
                        ItemValuation.workspace_id == resolved_workspace_id,
                        ItemValuation.item_id.in_([item.client_id for item in items]),
                        ItemValuation.superseded_at.is_(None),
                        ItemValuation.is_deleted.is_(False),
                    )
                )
            ).scalars().all()
            current_valuations = {row.item_id: row for row in valuation_rows}

        return _RunContext(
            identity={
                "workspace_id": resolved_workspace_id,
                "user_id": user.client_id,
                "username": user.username,
            },
            api_key=api_key,
            items=list(items),
            current_valuations=current_valuations,
        )
    raise RuntimeError("get_db_session() yielded no session.")


async def _lookup_article(client: httpx.AsyncClient, api_key: str, article_number: str) -> Lookup:
    """One purchase API lookup, mirroring the status handling of the production handler."""
    url = f"{_PURCHASE_API_BASE}/api/partner/items/{quote(article_number, safe='')}"
    try:
        response = await client.get(url, headers={"X-Partner-Key": api_key})
    except httpx.HTTPError as exc:
        return Lookup(status="error", error=f"{type(exc).__name__}: {exc}")

    if response.status_code == 404:
        return Lookup(status="not_found")
    if response.status_code in (401, 403):
        raise FatalApiError(
            f"Purchase API rejected the request (HTTP {response.status_code}) — check BEYO_VINTAGE_API_KEY."
        )
    if response.status_code == 503:
        raise FatalApiError("Purchase API unavailable (503) — partner API not configured on remote server.")
    if response.status_code == 400:
        return Lookup(status="invalid", error="invalid or unsupported article_number format")
    if response.status_code >= 400:
        return Lookup(status="error", error=f"HTTP {response.status_code}")

    body = response.json()
    if not body.get("success"):
        return Lookup(status="api_reported_failure", error=str(body.get("error")))
    return Lookup(status="ok", data=body.get("data") or {})


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


def decide(
    *,
    item_client_id: str,
    article_number: str,
    quantity: int,
    current_valuation: ItemValuation | None,
    lookup: Lookup,
) -> FieldPlan:
    """Turn one item + its purchase API lookup into a plan. Pure — no network, no database."""

    def skip(reason: str) -> FieldPlan:
        return FieldPlan(
            item_client_id=item_client_id,
            article_number=article_number,
            action=ACTION_SKIP,
            reason=reason,
            before=format_minor(
                current_valuation.purchase_cost_minor if current_valuation else None,
                current_valuation.currency if current_valuation else None,
            ),
            after="—",
        )

    if lookup.status == "not_found":
        return skip("not_found")
    if lookup.status == "invalid":
        return skip("invalid_article_number")
    if lookup.status == "api_reported_failure":
        return skip("api_reported_failure")

    data = lookup.data or {}
    returned_article = str(data.get("article_number") or "").strip()
    if returned_article and returned_article != article_number:
        return skip("article_number_mismatch")

    # The production transformation: purchase_price × currency rate → SEK minor.
    try:
        unit_price_sek_minor = _normalize_purchase_price_to_sek_minor(
            data.get("purchase_price"),
            data.get("currency"),
        )
    except ValueError:
        return skip("unsupported_currency")
    if unit_price_sek_minor is None:
        return skip("no_price")

    if quantity < 1:
        return skip("non_positive_quantity")
    total_minor = unit_price_sek_minor * quantity

    currency = ItemCurrencyEnum.SWEDISH_KRONA
    if current_valuation is None:
        new_triple: ValuationTriple = (None, total_minor, currency)
    else:
        if current_valuation.currency is not currency:
            return skip("currency_conflict")
        new_triple = (current_valuation.expected_sale_price_minor, total_minor, currency)
        if new_triple == _current_triple(current_valuation):
            return skip("unchanged")

    expected_sale_price_minor, purchase_cost_minor, currency = new_triple
    base_reason = "first_valuation" if current_valuation is None else "purchase_cost_changed"
    quantity_note = f" (unit {format_minor(unit_price_sek_minor, currency)} × {quantity})" if quantity > 1 else ""
    return FieldPlan(
        item_client_id=item_client_id,
        article_number=article_number,
        action=ACTION_UPDATE,
        reason=base_reason + quantity_note,
        before=format_minor(
            current_valuation.purchase_cost_minor if current_valuation else None,
            current_valuation.currency if current_valuation else None,
        ),
        after=format_minor(purchase_cost_minor, currency),
        payload={
            "item_client_id": item_client_id,
            "expected_sale_price_minor": expected_sale_price_minor,
            "purchase_cost_minor": purchase_cost_minor,
            "currency": currency.value,
        },
        expected_current=_current_triple(current_valuation),
    )


async def _fetch_and_decide(run_ctx: _RunContext) -> tuple[list[FieldPlan], _Totals]:
    totals = _Totals()
    plans: list[FieldPlan] = []

    fetchable = [item for item in run_ctx.items if (item.article_number or "").strip()]
    for item in run_ctx.items:
        if not (item.article_number or "").strip():
            totals.skipped["blank_article_number"] = totals.skipped.get("blank_article_number", 0) + 1
            _echo_row("(blank)", item.client_id, "skip", "", "blank_article_number")

    typer.echo(f"Looking up {len(fetchable)} item(s) one by one against the purchase API…\n")

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
        for item in fetchable:
            article_number = (item.article_number or "").strip()
            lookup = await _lookup_article(client, run_ctx.api_key, article_number)

            if lookup.status == "error":
                totals.errors += 1
                totals.attention.append(f"{article_number}  {item.client_id}  purchase_api_error: {lookup.error}")
                _echo_row(article_number, item.client_id, "ERROR", "", f"purchase_api_error: {lookup.error}")
                continue

            plan = decide(
                item_client_id=item.client_id,
                article_number=article_number,
                quantity=item.quantity,
                current_valuation=run_ctx.current_valuations.get(item.client_id),
                lookup=lookup,
            )
            plans.append(plan)
            if plan.action == ACTION_UPDATE:
                _echo_row(article_number, item.client_id, "UPDATE", f"{plan.before} → {plan.after}", plan.reason)
            else:
                totals.skipped[plan.reason] = totals.skipped.get(plan.reason, 0) + 1
                _echo_row(article_number, item.client_id, "skip", plan.before, plan.reason)
                if plan.reason in _ATTENTION_REASONS:
                    detail = f": {lookup.error}" if lookup.error else ""
                    totals.attention.append(f"{article_number}  {item.client_id}  {plan.reason}{detail}")

    return plans, totals


async def _apply_one(session: AsyncSession, identity: dict, plan: FieldPlan) -> str:
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


async def _apply_updates(run_ctx: _RunContext, updates: list[FieldPlan], totals: _Totals) -> None:
    typer.echo(f"\nWriting {len(updates)} update(s)…")
    async for session in get_db_session():
        for plan in updates:
            try:
                result = await _apply_one(session, run_ctx.identity, plan)
            except Exception as exc:  # keep going: one failed item must not poison the rest
                logger.exception("backfill apply failed | item=%s field=%s", plan.item_client_id, FIELD_NAME)
                totals.errors += 1
                totals.attention.append(f"{plan.article_number}  {plan.item_client_id}  write failed: {exc}")
                _echo_row(plan.article_number, plan.item_client_id, "ERROR", "", f"write failed: {exc}")
                continue
            if result == APPLY_APPLIED:
                totals.updated += 1
                _echo_row(plan.article_number, plan.item_client_id, "WROTE", f"{plan.before} → {plan.after}", plan.reason)
            else:
                totals.drifted += 1
                totals.attention.append(f"{plan.article_number}  {plan.item_client_id}  valuation changed since planning, skipped")
                _echo_row(plan.article_number, plan.item_client_id, "skip", plan.before, "drifted")
        return


def _echo_row(article_number: str, item_id: str, action: str, values: str, reason: str) -> None:
    typer.echo(f"  {article_number:<16} {item_id:<24} {action:<7} {values:<32} {reason}")


def _echo_summary(totals: _Totals, *, dry_run: bool, planned_updates: int) -> None:
    typer.echo("\n─── Summary ───")
    if dry_run:
        typer.echo(f"  would update : {planned_updates}")
    else:
        typer.echo(f"  written      : {totals.updated}")
        if totals.drifted:
            typer.echo(f"  drifted      : {totals.drifted}")
    for reason in sorted(totals.skipped):
        typer.echo(f"  skip {reason:<24}: {totals.skipped[reason]}")
    if totals.errors:
        typer.echo(f"  errors       : {totals.errors}")
    if totals.attention:
        typer.echo("\nNeeds attention:")
        for line in totals.attention:
            typer.echo(f"  {line}")


if __name__ == "__main__":
    app()
