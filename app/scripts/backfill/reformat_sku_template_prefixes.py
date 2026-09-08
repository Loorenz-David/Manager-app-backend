"""One-off migration: reformat the PRE_ORDER and RETURN SKU template separators.

``format_sku`` builds a SKU as ``{prefix}{separator}{scalar}``. Today that
produces ``PRE_ORDER-1`` and ``RETURN-1``. This script moves both templates to
a space separator, and gives PRE_ORDER a hyphenated prefix, so newly generated
SKUs read ``PRE-ORDER 1`` and ``RETURN 1``. It then renames every existing,
non-deleted item whose SKU was generated from the old format, and — best
effort — corrects the SKU on the matching Shopify product variant.

The *current* prefix/separator on each ``sku_templates`` row is read live and
used to find old-format items, so the script adapts to whatever is actually
stored rather than assuming today's known values. A template already at the
target format is left untouched (and its items are skipped, since they were
already migrated).

Ordering makes a partial run safe to just re-run: Shopify is corrected first
(searching by the *old* SKU), and only committed to the database last, in one
transaction per template row. If Shopify was already renamed by an earlier,
interrupted attempt, searching by the old SKU simply finds nothing there and
the script proceeds straight to the database write.

Dry-run is the default and performs no writes — including no Shopify
mutations — but still searches Shopify so you can see what would happen.

Example (from ``backend/app``)::

    PYTHONPATH=. APP_ENV=development python -m scripts.backfill.reformat_sku_template_prefixes \\
      reformat-sku-template-prefixes --dry-run

    PYTHONPATH=. APP_ENV=development python -m scripts.backfill.reformat_sku_template_prefixes \\
      reformat-sku-template-prefixes --execute --actor-username david
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Annotated

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.external_service import ShopifyGraphQLError
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.infra.shopify.graphql_client import (
    execute_shopify_graphql,
    quote_shopify_search_term,
    raise_for_graphql_user_errors,
)
from beyo_manager.services.infra.shopify.product_sync_client import (
    BULK_UPDATE_VARIANT_MUTATION,
    FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
)

logger = logging.getLogger(__name__)
app = typer.Typer(add_completion=False, no_args_is_help=True)

_SYSTEM_ACTOR_LABEL = "sku-template-prefix-migration"
_SHOPIFY_SEARCH_FIRST = 5

# (prefix, separator) each PRE_ORDER/RETURN template should end up with.
TARGET_FORMATS: dict[TaskTypeEnum, tuple[str, str]] = {
    TaskTypeEnum.PRE_ORDER: ("PRE-ORDER", " "),
    TaskTypeEnum.RETURN: ("RETURN", " "),
}


@dataclass
class _Totals:
    templates_updated: int = 0
    templates_already_correct: int = 0
    items_renamed: int = 0
    items_skipped_collision: int = 0
    shopify_updated: int = 0
    shopify_not_found: int = 0
    shopify_errors: int = 0
    attention: list[str] = field(default_factory=list)


@app.command("reformat-sku-template-prefixes")
def main(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--execute", help="Report changes without writing (default)."),
    ] = True,
    actor_username: Annotated[
        str | None,
        typer.Option("--actor-username", help="App user recorded as the author of the change."),
    ] = None,
    workspace_id: Annotated[
        str | None,
        typer.Option("--workspace-id", help="Only this workspace (default: every workspace)."),
    ] = None,
    skip_shopify: Annotated[
        bool,
        typer.Option("--skip-shopify", help="Skip Shopify entirely; database-only run."),
    ] = False,
    log_level: Annotated[str, typer.Option("--log-level")] = "WARNING",
) -> None:
    """Reformat PRE_ORDER/RETURN SKU templates and every SKU generated from them."""
    exit_code = asyncio.run(
        _run(
            dry_run=dry_run,
            actor_username=actor_username,
            workspace_id=workspace_id,
            skip_shopify=skip_shopify,
            log_level=log_level,
        )
    )
    if exit_code:
        raise typer.Exit(exit_code)


async def _run(
    *,
    dry_run: bool,
    actor_username: str | None,
    workspace_id: str | None,
    skip_shopify: bool,
    log_level: str,
) -> int:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if log_level.upper() != "DEBUG":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    await init_db()
    try:
        async for session in get_db_session():
            actor_id, username_snapshot = await _resolve_actor(session, actor_username)

            rows_query = select(SkuTemplate).where(
                SkuTemplate.task_type.in_(list(TARGET_FORMATS)),
                SkuTemplate.is_deleted.is_(False),
            )
            if workspace_id is not None:
                rows_query = rows_query.where(SkuTemplate.workspace_id == workspace_id)
            rows = (await session.execute(rows_query.order_by(SkuTemplate.workspace_id.asc()))).scalars().all()

            if not rows:
                typer.echo("No matching PRE_ORDER/RETURN SKU templates found.")
                return 0

            totals = _Totals()
            for row in rows:
                await _process_template_row(
                    session,
                    row=row,
                    dry_run=dry_run,
                    skip_shopify=skip_shopify,
                    actor_id=actor_id,
                    username_snapshot=username_snapshot,
                    totals=totals,
                )

            _echo_summary(totals, dry_run=dry_run)
            return 2 if (totals.shopify_errors or totals.items_skipped_collision) else 0
        raise RuntimeError("get_db_session() yielded no session.")
    finally:
        await close_db()


async def _resolve_actor(session: AsyncSession, actor_username: str | None) -> tuple[str | None, str]:
    if actor_username is None:
        return None, _SYSTEM_ACTOR_LABEL
    user = await session.scalar(select(User).where(User.username == actor_username))
    if user is None:
        raise typer.BadParameter(f"No user with username '{actor_username}'.", param_hint="--actor-username")
    return user.client_id, user.username


async def _process_template_row(
    session: AsyncSession,
    *,
    row: SkuTemplate,
    dry_run: bool,
    skip_shopify: bool,
    actor_id: str | None,
    username_snapshot: str,
    totals: _Totals,
) -> None:
    old_prefix, old_separator = row.prefix, row.separator
    new_prefix, new_separator = TARGET_FORMATS[row.task_type]

    if (old_prefix, old_separator) == (new_prefix, new_separator):
        totals.templates_already_correct += 1
        typer.echo(
            "sku_template_already_correct | "
            f"workspace={row.workspace_id} task_type={row.task_type.value} "
            f"prefix={old_prefix!r} separator={old_separator!r}"
        )
        return

    candidates = await _find_old_format_items(
        session,
        workspace_id=row.workspace_id,
        old_prefix=old_prefix,
        old_separator=old_separator,
        new_prefix=new_prefix,
        new_separator=new_separator,
    )
    eligible = await _drop_collisions(session, row=row, candidates=candidates, totals=totals)

    if not skip_shopify:
        await _sync_shopify(
            session,
            row=row,
            eligible=eligible,
            dry_run=dry_run,
            totals=totals,
        )

    action = "would_update" if dry_run else "updated"
    typer.echo(
        f"sku_template_{action} | workspace={row.workspace_id} task_type={row.task_type.value} "
        f"prefix: {old_prefix!r} -> {new_prefix!r} separator: {old_separator!r} -> {new_separator!r} "
        f"items={len(eligible)}"
    )

    if dry_run:
        for item, new_sku in eligible:
            typer.echo(f"  [dry-run] item {item.client_id} sku: {item.sku!r} -> {new_sku!r}")
        return

    now = datetime.now(timezone.utc)
    for item, new_sku in eligible:
        old_sku = item.sku
        item.sku = new_sku
        item.updated_at = now
        item.updated_by_id = actor_id
        await _create_history_record_in_session(
            session=session,
            entity_type=HistoryRecordEntityTypeEnum.ITEM,
            entity_client_id=item.client_id,
            change_type=HistoryRecordChangeTypeEnum.UPDATED,
            description=(
                f"SKU reformatted from {old_sku} to {new_sku} "
                f"({row.task_type.value} separator migration)"
            ),
            field_name="sku",
            from_value={"sku": old_sku},
            to_value={"sku": new_sku},
            created_by_id=actor_id,
            username_snapshot=username_snapshot,
        )
        totals.items_renamed += 1

    row.prefix = new_prefix
    row.separator = new_separator
    row.updated_by_id = actor_id
    await session.commit()
    totals.templates_updated += 1


def _sql_like_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _find_old_format_items(
    session: AsyncSession,
    *,
    workspace_id: str,
    old_prefix: str,
    old_separator: str,
    new_prefix: str,
    new_separator: str,
) -> list[tuple[Item, str]]:
    like_pattern = _sql_like_escape(old_prefix) + _sql_like_escape(old_separator) + "%"
    stmt = (
        select(Item)
        .where(
            Item.workspace_id == workspace_id,
            Item.is_deleted.is_(False),
            Item.sku.isnot(None),
            Item.sku.like(like_pattern, escape="\\"),
        )
        .order_by(Item.sku.asc())
    )
    items = (await session.execute(stmt)).scalars().all()

    pattern = re.compile(r"^" + re.escape(old_prefix) + re.escape(old_separator) + r"(\d+)$")
    candidates: list[tuple[Item, str]] = []
    for item in items:
        match = pattern.fullmatch(item.sku)
        if match is None:
            continue
        candidates.append((item, f"{new_prefix}{new_separator}{match.group(1)}"))
    return candidates


async def _drop_collisions(
    session: AsyncSession,
    *,
    row: SkuTemplate,
    candidates: list[tuple[Item, str]],
    totals: _Totals,
) -> list[tuple[Item, str]]:
    if not candidates:
        return []

    renaming_ids = {item.client_id for item, _ in candidates}
    new_skus = [new_sku for _, new_sku in candidates]
    existing = (
        await session.execute(
            select(Item.client_id, Item.sku).where(
                Item.workspace_id == row.workspace_id,
                Item.is_deleted.is_(False),
                Item.sku.in_(new_skus),
            )
        )
    ).all()
    colliding_new_skus = {r.sku for r in existing if r.client_id not in renaming_ids}

    eligible: list[tuple[Item, str]] = []
    for item, new_sku in candidates:
        if new_sku in colliding_new_skus:
            totals.items_skipped_collision += 1
            message = (
                f"item {item.client_id} sku {item.sku!r} would collide with an existing "
                f"sku {new_sku!r}; skipped"
            )
            totals.attention.append(message)
            typer.echo(f"sku_rename_collision | workspace={row.workspace_id} {message}", err=True)
            continue
        eligible.append((item, new_sku))
    return eligible


async def _sync_shopify(
    session: AsyncSession,
    *,
    row: SkuTemplate,
    eligible: list[tuple[Item, str]],
    dry_run: bool,
    totals: _Totals,
) -> None:
    if not eligible:
        return

    integrations = (
        await session.execute(
            select(ShopifyShopIntegration).where(
                ShopifyShopIntegration.workspace_id == row.workspace_id,
                ShopifyShopIntegration.is_deleted.is_(False),
                ShopifyShopIntegration.status == ShopifyIntegrationStatusEnum.ACTIVE,
            )
        )
    ).scalars().all()
    if not integrations:
        typer.echo(f"shopify_no_active_integration | workspace={row.workspace_id}: skipping Shopify lookups")
        return

    for item, new_sku in eligible:
        old_sku = item.sku
        found = False
        for integration in integrations:
            try:
                data = await execute_shopify_graphql(
                    shop_domain=integration.shop_domain,
                    access_token_encrypted=integration.access_token_encrypted,
                    query=FIND_PRODUCT_VARIANTS_BY_IDENTITY_QUERY,
                    variables={
                        "searchQuery": f"sku:{quote_shopify_search_term(old_sku)}",
                        "first": _SHOPIFY_SEARCH_FIRST,
                    },
                    operation_name="reformat_sku_template_find_variant",
                )
            except ShopifyGraphQLError as exc:
                totals.shopify_errors += 1
                typer.echo(
                    f"shopify_search_error | shop={integration.shop_domain} old_sku={old_sku} error={exc}",
                    err=True,
                )
                continue

            edges = (data.get("productVariants") or {}).get("edges") or []
            nodes = [((edge or {}).get("node") or {}) for edge in edges]
            exact_matches = [node for node in nodes if _clean(node.get("sku")) == old_sku]
            if not exact_matches:
                continue

            found = True
            for node in exact_matches:
                variant_id = _clean(node.get("id"))
                product_id = _clean(((node.get("product") or {}).get("id")))
                if variant_id is None or product_id is None:
                    typer.echo(
                        f"shopify_variant_missing_ids | shop={integration.shop_domain} old_sku={old_sku}",
                        err=True,
                    )
                    continue

                action = "would_update" if dry_run else "updated"
                typer.echo(
                    f"shopify_variant_{action} | shop={integration.shop_domain} "
                    f"product={product_id} variant={variant_id} sku: {old_sku!r} -> {new_sku!r}"
                )
                if dry_run:
                    continue

                try:
                    result = await execute_shopify_graphql(
                        shop_domain=integration.shop_domain,
                        access_token_encrypted=integration.access_token_encrypted,
                        query=BULK_UPDATE_VARIANT_MUTATION,
                        variables={
                            "productId": product_id,
                            "variants": [{"id": variant_id, "inventoryItem": {"sku": new_sku}}],
                        },
                        operation_name="reformat_sku_template_update_variant",
                    )
                    raise_for_graphql_user_errors(
                        user_errors=(result.get("productVariantsBulkUpdate") or {}).get("userErrors"),
                        operation_name="reformat_sku_template_update_variant",
                        shop_domain=integration.shop_domain,
                    )
                except ShopifyGraphQLError as exc:
                    totals.shopify_errors += 1
                    typer.echo(
                        f"shopify_update_error | shop={integration.shop_domain} variant={variant_id} "
                        f"old_sku={old_sku} new_sku={new_sku} error={exc}",
                        err=True,
                    )
                    continue
                totals.shopify_updated += 1

        if not found:
            totals.shopify_not_found += 1
            typer.echo(f"shopify_not_found | old_sku={old_sku}: nothing to update in Shopify")


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _echo_summary(totals: _Totals, *, dry_run: bool) -> None:
    typer.echo(
        "\n"
        f"{'DRY RUN' if dry_run else 'EXECUTE'} summary | "
        f"templates_updated={totals.templates_updated} "
        f"templates_already_correct={totals.templates_already_correct} "
        f"items_renamed={totals.items_renamed} "
        f"items_skipped_collision={totals.items_skipped_collision} "
        f"shopify_updated={totals.shopify_updated} "
        f"shopify_not_found={totals.shopify_not_found} "
        f"shopify_errors={totals.shopify_errors}"
    )
    for message in totals.attention:
        typer.echo(f"  ATTENTION: {message}")


if __name__ == "__main__":
    app()
