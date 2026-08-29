"""Backfill purchase cost and item properties from the purchase app API, dry-run first.

Takes every item in the workspace that has an article_number, looks it up one
by one against the purchase app partner API (the same endpoint the frontend
lookup uses), and backfills two fields from that one response:

* ``purchase_cost`` — the returned purchase price, converted to SEK minor (öre)
  through the production transformation in
  `beyo_manager.services.queries.items.lookup.purchase_api`, multiplied by the
  quantity stored on the app item, and written as ``purchase_cost_minor``
  through `set_item_valuation` so versioning, audit, and preview semantics hold.
* ``properties`` — the purchase app's ``attributes`` list, projected into the
  canonical key→value snapshot by the same parser the lookup uses and written
  through `apply_properties_snapshot`, the single owner of the three snapshot
  columns, so the stored signature always describes the stored blob.

The two fields are decided and written independently: each gets its own plan,
its own drift check, and its own transaction, so a field that cannot be written
never costs the other one. Both are reported per item and counted separately.

Example::

    # from backend/app, dry run (default) against the workspace of a user
PYTHONPATH=. APP_ENV=development python -m scripts.purchase_api.backfill_from_purchase_api  --username david

    # write one item for real
    PYTHONPATH=. APP_ENV=development python -m scripts.purchase_api.backfill_from_purchase_api \
      --username david --article-number 12345 --execute
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from urllib.parse import quote

import httpx
import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.items.properties_signature import compute_properties_signature
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.commands.items._properties_snapshot import apply_properties_snapshot
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.lookup.purchase_api import (
    _PURCHASE_API_BASE,
    _normalize_purchase_price_to_sek_minor,
    has_attributes_payload,
    parse_purchase_api_attributes,
)

logger = logging.getLogger(__name__)
app = typer.Typer(add_completion=False, no_args_is_help=True)

FIELD_PURCHASE_COST = "purchase_cost"
FIELD_PROPERTIES = "properties"
BACKFILLED_FIELDS = (FIELD_PURCHASE_COST, FIELD_PROPERTIES)

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
    "unparsable_attributes",
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
class ItemSnapshot:
    """Everything the decisions read off the app item, so decide() stays pure."""

    client_id: str
    article_number: str
    quantity: int
    valuation: ItemValuation | None
    properties: dict | None
    established_properties_signature: str | None


@dataclass(frozen=True)
class FieldPlan:
    item_client_id: str
    article_number: str
    field_name: str
    action: str
    reason: str
    before: str
    after: str
    # For purchase_cost, the incoming_data for set_item_valuation; for properties,
    # the canonical snapshot blob handed to apply_properties_snapshot.
    payload: dict | None = None
    # What the row looked like when this plan was made, re-checked before writing:
    # the valuation triple for purchase_cost, the established signature for properties.
    expected_current: ValuationTriple | str | None = None


@dataclass
class _RunContext:
    identity: dict
    api_key: str
    items: list[Item]
    current_valuations: dict[str, ItemValuation]


@dataclass
class _Totals:
    updated: dict[str, int] = field(default_factory=dict)
    drifted: dict[str, int] = field(default_factory=dict)
    skipped: dict[tuple[str, str], int] = field(default_factory=dict)
    item_skipped: dict[str, int] = field(default_factory=dict)
    errors: int = 0
    attention: list[str] = field(default_factory=list)


def _bump(counter: dict, key) -> None:
    counter[key] = counter.get(key, 0) + 1


@app.command("backfill-from-purchase-api")
def main(
    username: Annotated[str, typer.Option("--username", help="App user whose workspace to backfill.")],
    workspace_id: Annotated[str | None, typer.Option("--workspace-id", help="Disambiguate when the user has several active workspaces.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute", help="Dry run (default) reports decisions without writing.")] = True,
    article_numbers: Annotated[list[str] | None, typer.Option("--article-number", help="Only these article numbers (repeatable).")] = None,
    limit: Annotated[int | None, typer.Option("--limit", min=1, help="Process at most N items.")] = None,
    log_level: Annotated[str, typer.Option("--log-level")] = "WARNING",
) -> None:
    """Backfill item purchase cost and properties from the purchase app API, through the proper services."""
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
            f"source={_PURCHASE_API_BASE} items={len(run_ctx.items)} "
            f"fields={','.join(BACKFILLED_FIELDS)}"
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
        planned_updates: dict[str, int] = {}
        for plan in updates:
            _bump(planned_updates, plan.field_name)

        if dry_run:
            typer.echo(f"\nDry run: {len(updates)} update(s) would be written. Re-run with --execute to apply.")
        elif updates:
            await _apply_updates(run_ctx, updates, totals)
        else:
            typer.echo("\nNo updates to write.")

        _echo_summary(totals, dry_run=dry_run, planned_updates=planned_updates)
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


def format_properties(properties: dict | None) -> str:
    """A one-line rendering of a properties snapshot: its keys, truncated."""
    if not properties:
        return "—"
    keys = sorted(properties)
    shown = ", ".join(keys[:3])
    return shown if len(keys) <= 3 else f"{shown} +{len(keys) - 3}"


def _current_triple(valuation: ItemValuation | None) -> ValuationTriple | None:
    if valuation is None:
        return None
    return (
        valuation.expected_sale_price_minor,
        valuation.purchase_cost_minor,
        valuation.currency,
    )


def established_properties_signature(item: Item) -> str | None:
    """The signature apply_properties_snapshot will actually compare against.

    A signature with no snapshot timestamp is not an established profile — the
    helper writes straight through it — so neither planning nor the drift check
    may read it as a match.
    """
    return item.properties_signature if item.properties_snapshot_at is not None else None


def snapshot_item(item: Item, valuation: ItemValuation | None) -> ItemSnapshot:
    return ItemSnapshot(
        client_id=item.client_id,
        article_number=(item.article_number or "").strip(),
        quantity=item.quantity,
        valuation=valuation,
        properties=item.properties,
        established_properties_signature=established_properties_signature(item),
    )


def _format_before(item: ItemSnapshot, field_name: str) -> str:
    if field_name == FIELD_PURCHASE_COST:
        return format_minor(
            item.valuation.purchase_cost_minor if item.valuation else None,
            item.valuation.currency if item.valuation else None,
        )
    return format_properties(item.properties)


def _skip(item: ItemSnapshot, field_name: str, reason: str) -> FieldPlan:
    return FieldPlan(
        item_client_id=item.client_id,
        article_number=item.article_number,
        field_name=field_name,
        action=ACTION_SKIP,
        reason=reason,
        before=_format_before(item, field_name),
        after="—",
    )


def _blocking_reason(item: ItemSnapshot, lookup: Lookup) -> str | None:
    """A reason that stops every field for this item, not just one of them."""
    if lookup.status == "not_found":
        return "not_found"
    if lookup.status == "invalid":
        return "invalid_article_number"
    if lookup.status == "api_reported_failure":
        return "api_reported_failure"

    returned_article = str((lookup.data or {}).get("article_number") or "").strip()
    if returned_article and returned_article != item.article_number:
        return "article_number_mismatch"
    return None


def _decide_purchase_cost(item: ItemSnapshot, data: dict) -> FieldPlan:
    # The production transformation: purchase_price × currency rate → SEK minor.
    try:
        unit_price_sek_minor = _normalize_purchase_price_to_sek_minor(
            data.get("purchase_price"),
            data.get("currency"),
        )
    except ValueError:
        return _skip(item, FIELD_PURCHASE_COST, "unsupported_currency")
    if unit_price_sek_minor is None:
        return _skip(item, FIELD_PURCHASE_COST, "no_price")

    if item.quantity < 1:
        return _skip(item, FIELD_PURCHASE_COST, "non_positive_quantity")
    total_minor = unit_price_sek_minor * item.quantity

    currency = ItemCurrencyEnum.SWEDISH_KRONA
    if item.valuation is None:
        new_triple: ValuationTriple = (None, total_minor, currency)
    else:
        if item.valuation.currency is not currency:
            return _skip(item, FIELD_PURCHASE_COST, "currency_conflict")
        new_triple = (item.valuation.expected_sale_price_minor, total_minor, currency)
        if new_triple == _current_triple(item.valuation):
            return _skip(item, FIELD_PURCHASE_COST, "unchanged")

    expected_sale_price_minor, purchase_cost_minor, currency = new_triple
    base_reason = "first_valuation" if item.valuation is None else "purchase_cost_changed"
    quantity_note = (
        f" (unit {format_minor(unit_price_sek_minor, currency)} × {item.quantity})"
        if item.quantity > 1
        else ""
    )
    return FieldPlan(
        item_client_id=item.client_id,
        article_number=item.article_number,
        field_name=FIELD_PURCHASE_COST,
        action=ACTION_UPDATE,
        reason=base_reason + quantity_note,
        before=_format_before(item, FIELD_PURCHASE_COST),
        after=format_minor(purchase_cost_minor, currency),
        payload={
            "item_client_id": item.client_id,
            "expected_sale_price_minor": expected_sale_price_minor,
            "purchase_cost_minor": purchase_cost_minor,
            "currency": currency.value,
        },
        expected_current=_current_triple(item.valuation),
    )


def _decide_properties(item: ItemSnapshot, data: dict) -> FieldPlan:
    raw_attributes = data.get("attributes")
    properties = parse_purchase_api_attributes(raw_attributes)
    if not properties:
        # The parser warns and yields {} for anything it cannot read, so the case
        # worth a human's eyes is a payload that was there and still gave nothing.
        reason = "unparsable_attributes" if has_attributes_payload(raw_attributes) else "no_attributes"
        return _skip(item, FIELD_PROPERTIES, reason)

    # Mirror apply_properties_snapshot exactly: an incoming profile whose signature
    # equals the established one writes nothing at all, so properties_snapshot_at
    # keeps meaning "when this profile was established", not "when the backfill ran".
    if compute_properties_signature(properties) == item.established_properties_signature:
        return _skip(item, FIELD_PROPERTIES, "unchanged")

    return FieldPlan(
        item_client_id=item.client_id,
        article_number=item.article_number,
        field_name=FIELD_PROPERTIES,
        action=ACTION_UPDATE,
        reason="first_snapshot" if item.established_properties_signature is None else "profile_changed",
        before=_format_before(item, FIELD_PROPERTIES),
        after=format_properties(properties),
        payload=properties,
        expected_current=item.established_properties_signature,
    )


def decide(*, item: ItemSnapshot, lookup: Lookup) -> list[FieldPlan]:
    """Turn one item plus its purchase API lookup into one plan per backfilled field.

    Pure — no network, no database. Always returns a plan for every field, so a
    field that cannot be written still reports why.
    """
    blocked = _blocking_reason(item, lookup)
    if blocked is not None:
        return [_skip(item, field_name, blocked) for field_name in BACKFILLED_FIELDS]

    data = lookup.data or {}
    return [
        _decide_purchase_cost(item, data),
        _decide_properties(item, data),
    ]


async def _fetch_and_decide(run_ctx: _RunContext) -> tuple[list[FieldPlan], _Totals]:
    totals = _Totals()
    plans: list[FieldPlan] = []

    fetchable = [item for item in run_ctx.items if (item.article_number or "").strip()]
    for item in run_ctx.items:
        if not (item.article_number or "").strip():
            _bump(totals.item_skipped, "blank_article_number")
            _echo_row("(blank)", item.client_id, "—", "skip", "", "blank_article_number")

    typer.echo(f"Looking up {len(fetchable)} item(s) one by one against the purchase API…\n")

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
        for item in fetchable:
            article_number = (item.article_number or "").strip()
            lookup = await _lookup_article(client, run_ctx.api_key, article_number)

            if lookup.status == "error":
                totals.errors += 1
                totals.attention.append(f"{article_number}  {item.client_id}  purchase_api_error: {lookup.error}")
                _echo_row(article_number, item.client_id, "—", "ERROR", "", f"purchase_api_error: {lookup.error}")
                continue

            snapshot = snapshot_item(item, run_ctx.current_valuations.get(item.client_id))
            for plan in decide(item=snapshot, lookup=lookup):
                plans.append(plan)
                if plan.action == ACTION_UPDATE:
                    _echo_row(article_number, item.client_id, plan.field_name, "UPDATE",
                              f"{plan.before} → {plan.after}", plan.reason)
                    continue

                _bump(totals.skipped, (plan.field_name, plan.reason))
                _echo_row(article_number, item.client_id, plan.field_name, "skip", plan.before, plan.reason)
                if plan.reason in _ATTENTION_REASONS:
                    detail = f": {lookup.error}" if lookup.error else ""
                    totals.attention.append(
                        f"{article_number}  {item.client_id}  {plan.field_name}: {plan.reason}{detail}"
                    )

    return plans, totals


async def _apply_purchase_cost(session: AsyncSession, identity: dict, plan: FieldPlan) -> str:
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


async def _apply_properties(session: AsyncSession, identity: dict, plan: FieldPlan) -> str:
    item = await session.scalar(
        select(Item).where(
            Item.workspace_id == identity["workspace_id"],
            Item.client_id == plan.item_client_id,
            Item.is_deleted.is_(False),
        )
    )
    if item is None or established_properties_signature(item) != plan.expected_current:
        return APPLY_DRIFTED

    # apply_properties_snapshot is the single owner of the three snapshot columns —
    # the same helper the three creation endpoints use — so the blob, its derived
    # signature and the snapshot timestamp can never disagree. It returns False for
    # anything that is not a genuinely new profile, which after the drift check
    # above means the row moved under us.
    if not apply_properties_snapshot(item, plan.payload):
        return APPLY_DRIFTED
    item.updated_at = datetime.now(timezone.utc)
    item.updated_by_id = identity["user_id"]
    return APPLY_APPLIED


async def _apply_one(session: AsyncSession, identity: dict, plan: FieldPlan) -> str:
    # Own the transaction: the drift-check SELECT would otherwise start an
    # implicit one and demote maybe_begin inside the command to subordinate
    # mode, which never commits.
    async with session.begin():
        if plan.field_name == FIELD_PURCHASE_COST:
            return await _apply_purchase_cost(session, identity, plan)
        return await _apply_properties(session, identity, plan)


async def _apply_updates(run_ctx: _RunContext, updates: list[FieldPlan], totals: _Totals) -> None:
    typer.echo(f"\nWriting {len(updates)} update(s)…")
    async for session in get_db_session():
        for plan in updates:
            try:
                result = await _apply_one(session, run_ctx.identity, plan)
            except Exception as exc:  # keep going: one failed field must not poison the rest
                logger.exception("backfill apply failed | item=%s field=%s", plan.item_client_id, plan.field_name)
                totals.errors += 1
                totals.attention.append(
                    f"{plan.article_number}  {plan.item_client_id}  {plan.field_name}: write failed: {exc}"
                )
                _echo_row(plan.article_number, plan.item_client_id, plan.field_name, "ERROR", "",
                          f"write failed: {exc}")
                continue
            if result == APPLY_APPLIED:
                _bump(totals.updated, plan.field_name)
                _echo_row(plan.article_number, plan.item_client_id, plan.field_name, "WROTE",
                          f"{plan.before} → {plan.after}", plan.reason)
            else:
                _bump(totals.drifted, plan.field_name)
                totals.attention.append(
                    f"{plan.article_number}  {plan.item_client_id}  {plan.field_name}: "
                    "row changed since planning, skipped"
                )
                _echo_row(plan.article_number, plan.item_client_id, plan.field_name, "skip", plan.before, "drifted")
        return


def _echo_row(article_number: str, item_id: str, field_name: str, action: str, values: str, reason: str) -> None:
    typer.echo(f"  {article_number:<16} {item_id:<24} {field_name:<14} {action:<7} {values:<32} {reason}")


def _echo_summary(totals: _Totals, *, dry_run: bool, planned_updates: dict[str, int]) -> None:
    typer.echo("\n─── Summary ───")
    for field_name in BACKFILLED_FIELDS:
        typer.echo(f"  {field_name}")
        if dry_run:
            typer.echo(f"    would update : {planned_updates.get(field_name, 0)}")
        else:
            typer.echo(f"    written      : {totals.updated.get(field_name, 0)}")
            if totals.drifted.get(field_name):
                typer.echo(f"    drifted      : {totals.drifted[field_name]}")
        for (plan_field, reason) in sorted(totals.skipped):
            if plan_field == field_name:
                typer.echo(f"    skip {reason:<24}: {totals.skipped[(plan_field, reason)]}")
    for reason in sorted(totals.item_skipped):
        typer.echo(f"  item skip {reason:<20}: {totals.item_skipped[reason]}")
    if totals.errors:
        typer.echo(f"  errors         : {totals.errors}")
    if totals.attention:
        typer.echo("\nNeeds attention:")
        for line in totals.attention:
            typer.echo(f"  {line}")


if __name__ == "__main__":
    app()
