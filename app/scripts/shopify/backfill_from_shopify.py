"""Backfill app fields from Shopify through the proper services, dry-run first.

Matches items to Shopify by article_number ↔ variant barcode (the product-sync
identity) using the workspace's active Shopify integration, then routes each
enabled field through its backfiller in scripts/shopify/fields.py — today only
`expected_sold_price` (variant listing price → set_item_valuation).

Example::

    # from backend/app, dry run (default) against the workspace of a user
    PYTHONPATH=. APP_ENV=development python -m scripts.shopify.backfill_from_shopify \
      --username david

    # write one item for real
    PYTHONPATH=. APP_ENV=development python -m scripts.shopify.backfill_from_shopify \
      --username david --article-number 12345 --execute
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Annotated

import typer
from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.infra.shopify.product_sync_client import (
    find_product_variant_pricing_by_barcode,
    find_product_variant_pricing_by_barcodes,
)
from beyo_manager.services.infra.shopify.shop_client import fetch_shopify_shop_currency
from scripts.shopify.fields import (
    ACTION_UPDATE,
    APPLY_APPLIED,
    REGISTRY,
    FieldPlan,
    ShopifySnapshot,
)

logger = logging.getLogger(__name__)
app = typer.Typer(add_completion=False, no_args_is_help=True)

_REQUIRED_SCOPES: tuple[str, ...] = ("read_products",)

# One search request covers this many barcodes; a failed batch degrades to
# per-barcode lookups rather than failing the whole run.
BARCODE_BATCH_SIZE = 100


@dataclass
class _BatchLookup:
    matches: dict[str, list[dict]]
    failures: dict[str, str]


@dataclass
class _RunContext:
    identity: dict
    shop_domain: str
    access_token_encrypted: str
    items: list[Item]
    current_valuations: dict[str, ItemValuation]


@dataclass
class _Totals:
    updated: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    drifted: int = 0
    errors: int = 0
    attention: list[str] = field(default_factory=list)


@app.command("backfill-from-shopify")
def main(
    username: Annotated[str, typer.Option("--username", help="App user whose workspace and Shopify integration to use.")],
    workspace_id: Annotated[str | None, typer.Option("--workspace-id", help="Disambiguate when the user has several active workspaces.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run/--execute", help="Dry run (default) reports decisions without writing.")] = True,
    fields_enabled: Annotated[list[str] | None, typer.Option("--field", help="Field backfiller to run (repeatable). Default: all registered.")] = None,
    article_numbers: Annotated[list[str] | None, typer.Option("--article-number", help="Only these article numbers (repeatable).")] = None,
    limit: Annotated[int | None, typer.Option("--limit", min=1, help="Process at most N items.")] = None,
    log_level: Annotated[str, typer.Option("--log-level")] = "WARNING",
) -> None:
    """Backfill app fields from Shopify for one workspace, through the proper services."""
    enabled = _resolve_fields(fields_enabled)
    exit_code = asyncio.run(
        _run(
            username=username,
            workspace_id=workspace_id,
            dry_run=dry_run,
            enabled_fields=enabled,
            article_numbers=article_numbers or [],
            limit=limit,
            log_level=log_level,
        )
    )
    if exit_code:
        raise typer.Exit(exit_code)


def _resolve_fields(requested: list[str] | None) -> list[str]:
    if not requested:
        return list(REGISTRY)
    unknown = [name for name in requested if name not in REGISTRY]
    if unknown:
        typer.echo(f"ERROR: unknown field(s): {', '.join(unknown)}. Registered: {', '.join(REGISTRY)}", err=True)
        raise typer.Exit(1)
    return requested


async def _run(
    *,
    username: str,
    workspace_id: str | None,
    dry_run: bool,
    enabled_fields: list[str],
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
            f"shop={run_ctx.shop_domain} items={len(run_ctx.items)} fields={', '.join(enabled_fields)}"
        )
        if not run_ctx.items:
            typer.echo("Nothing to do: no items with an article_number matched the filters.")
            return 0

        plans, totals = await _fetch_and_decide(run_ctx, enabled_fields)

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

        integrations = (
            await session.execute(
                select(ShopifyShopIntegration)
                .where(
                    ShopifyShopIntegration.workspace_id == resolved_workspace_id,
                    ShopifyShopIntegration.is_deleted.is_(False),
                    ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
                )
                .order_by(ShopifyShopIntegration.created_at.desc())
            )
        ).scalars().all()
        integration = next(
            (
                candidate
                for candidate in integrations
                if has_all_required_scopes(_REQUIRED_SCOPES, candidate.granted_scopes or ())
                and (candidate.access_token_encrypted or "").strip()
            ),
            None,
        )
        if integration is None:
            raise ValueError(
                f"No usable ACTIVE Shopify integration in workspace '{resolved_workspace_id}' "
                f"(needs scopes {list(_REQUIRED_SCOPES)} and an access token)."
            )

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
            shop_domain=integration.shop_domain,
            access_token_encrypted=integration.access_token_encrypted,
            items=list(items),
            current_valuations=current_valuations,
        )
    raise RuntimeError("get_db_session() yielded no session.")


def chunked(items: list[Item], size: int) -> list[list[Item]]:
    return [items[start:start + size] for start in range(0, len(items), size)]


def partition_by_article_number(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """Split items into those with a usable article number and those without."""
    usable: list[Item] = []
    blank: list[Item] = []
    for item in items:
        (usable if (item.article_number or "").strip() else blank).append(item)
    return usable, blank


async def _lookup_batch(run_ctx: _RunContext, batch: list[Item]) -> _BatchLookup:
    """Resolve one batch of barcodes, degrading to per-barcode lookups on failure."""
    barcodes = [(item.article_number or "").strip() for item in batch]
    try:
        return _BatchLookup(
            matches=await find_product_variant_pricing_by_barcodes(
                shop_domain=run_ctx.shop_domain,
                access_token_encrypted=run_ctx.access_token_encrypted,
                barcodes=barcodes,
            ),
            failures={},
        )
    except ExternalServiceError as exc:
        logger.warning("batched barcode lookup failed, falling back | size=%s error=%s", len(batch), exc)
        typer.echo(f"  batch lookup failed ({exc}); retrying {len(batch)} item(s) one by one…")

    matches: dict[str, list[dict]] = {}
    failures: dict[str, str] = {}
    for barcode in barcodes:
        try:
            matches[barcode] = await find_product_variant_pricing_by_barcode(
                shop_domain=run_ctx.shop_domain,
                access_token_encrypted=run_ctx.access_token_encrypted,
                barcode=barcode,
            )
        except ExternalServiceError as exc:
            failures[barcode] = str(exc)
    return _BatchLookup(matches=matches, failures=failures)


async def _fetch_and_decide(run_ctx: _RunContext, enabled_fields: list[str]) -> tuple[list[FieldPlan], _Totals]:
    totals = _Totals()
    plans: list[FieldPlan] = []

    shop_currency_code = await fetch_shopify_shop_currency(
        shop_domain=run_ctx.shop_domain,
        access_token_encrypted=run_ctx.access_token_encrypted,
    )
    typer.echo(f"Shop currency: {shop_currency_code or 'UNKNOWN'}")

    fetchable, blank = partition_by_article_number(run_ctx.items)
    for item in blank:
        totals.skipped["blank_article_number"] = totals.skipped.get("blank_article_number", 0) + 1
        _echo_row("(blank)", item.client_id, "-", "skip", "", "blank_article_number")

    batches = chunked(fetchable, BARCODE_BATCH_SIZE)
    typer.echo(f"Looking up {len(fetchable)} item(s) in {len(batches)} Shopify request(s)…\n")

    for batch_number, batch in enumerate(batches, start=1):
        if len(batches) > 1:
            typer.echo(f"  · batch {batch_number}/{len(batches)} ({len(batch)} items)")
        lookup = await _lookup_batch(run_ctx, batch)

        for item in batch:
            article_number = (item.article_number or "").strip()
            failure = lookup.failures.get(article_number)
            if failure is not None:
                totals.errors += 1
                totals.attention.append(f"{article_number}  {item.client_id}  shopify_error: {failure}")
                _echo_row(article_number, item.client_id, "-", "ERROR", "", f"shopify_error: {failure}")
                continue

            snapshot = ShopifySnapshot(
                variant_matches=lookup.matches.get(article_number, []),
                shop_currency_code=shop_currency_code,
            )
            for field_name in enabled_fields:
                plan = REGISTRY[field_name].decide(
                    item_client_id=item.client_id,
                    article_number=article_number,
                    current_valuation=run_ctx.current_valuations.get(item.client_id),
                    snapshot=snapshot,
                )
                plans.append(plan)
                if plan.action == ACTION_UPDATE:
                    _echo_row(article_number, item.client_id, plan.field, "UPDATE", f"{plan.before} → {plan.after}", plan.reason)
                else:
                    totals.skipped[plan.reason] = totals.skipped.get(plan.reason, 0) + 1
                    _echo_row(article_number, item.client_id, plan.field, "skip", plan.before, plan.reason)
                    if plan.reason in ("ambiguous", "currency_conflict", "unsupported_currency"):
                        totals.attention.append(f"{article_number}  {plan.item_client_id}  {plan.field}: {plan.reason}")

    return plans, totals


async def _apply_updates(run_ctx: _RunContext, updates: list[FieldPlan], totals: _Totals) -> None:
    typer.echo(f"\nWriting {len(updates)} update(s)…")
    async for session in get_db_session():
        for plan in updates:
            try:
                result = await REGISTRY[plan.field].apply(session, run_ctx.identity, plan)
            except Exception as exc:  # keep going: one failed item must not poison the rest
                logger.exception("backfill apply failed | item=%s field=%s", plan.item_client_id, plan.field)
                totals.errors += 1
                totals.attention.append(f"{plan.article_number}  {plan.item_client_id}  {plan.field}: write failed: {exc}")
                _echo_row(plan.article_number, plan.item_client_id, plan.field, "ERROR", "", f"write failed: {exc}")
                continue
            if result == APPLY_APPLIED:
                totals.updated += 1
                _echo_row(plan.article_number, plan.item_client_id, plan.field, "WROTE", f"{plan.before} → {plan.after}", plan.reason)
            else:
                totals.drifted += 1
                totals.attention.append(f"{plan.article_number}  {plan.item_client_id}  {plan.field}: valuation changed since planning, skipped")
                _echo_row(plan.article_number, plan.item_client_id, plan.field, "skip", plan.before, "drifted")
        return


def _echo_row(article_number: str, item_id: str, field_name: str, action: str, values: str, reason: str) -> None:
    typer.echo(f"  {article_number:<16} {item_id:<24} {field_name:<20} {action:<7} {values:<28} {reason}")


def _echo_summary(totals: _Totals, *, dry_run: bool, planned_updates: int) -> None:
    typer.echo("\n─── Summary ───")
    if dry_run:
        typer.echo(f"  would update : {planned_updates}")
    else:
        typer.echo(f"  written      : {totals.updated}")
        if totals.drifted:
            typer.echo(f"  drifted      : {totals.drifted}")
    for reason in sorted(totals.skipped):
        typer.echo(f"  skip {reason:<19}: {totals.skipped[reason]}")
    if totals.errors:
        typer.echo(f"  errors       : {totals.errors}")
    if totals.attention:
        typer.echo("\nNeeds attention:")
        for line in totals.attention:
            typer.echo(f"  {line}")


if __name__ == "__main__":
    app()
