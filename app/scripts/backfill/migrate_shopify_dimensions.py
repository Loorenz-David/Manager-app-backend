"""Manually-run Shopify dimension migration with dry-run-first safeguards.

Example::

    export DOMAIN="example.myshopify.com"
    export TOKEN="shpat_..."
    python scripts/backfill/migrate_shopify_dimensions.py migrate-shopify-dimensions \
      --shop-domain "$DOMAIN" --access-token "$TOKEN" \
      --source-namespace custom --source-height-key height \
      --source-width-key width --source-depth-key depth \
      --target-namespace custom --dry-run --limit 10
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer

from beyo_manager.domain.shopify.dimension_migration import (
    MigrationConfig,
    MigrationSummary,
    ProductMigrationDecision,
    ProductMigrationInput,
    build_product_migration,
)
from beyo_manager.domain.shopify.shop_domains import normalize_shop_domain
from beyo_manager.services.infra.shopify.dimension_migration_client import (
    TARGET_TYPES,
    delete_stale_extension_dimension_batch,
    fetch_target_metafield_definitions,
    iter_product_dimensions,
    set_dimension_metafields_batch,
    validate_target_metafield_definitions,
)

logger = logging.getLogger(__name__)
app = typer.Typer(add_completion=False, no_args_is_help=True)

TARGET_KEYS = {key: key for key in TARGET_TYPES}
REPORT_COLUMNS = (
    "product_gid", "title", "handle", "sku", "status", "action", "raw_height",
    "raw_width", "raw_depth", "legacy_dimensions", "parsed_legacy_dimensions", "malformed_legacy_lines",
    "legacy_extension_quantity", "existing_extensions_quantity",
    "proposed_extensions_quantity", "extensions_quantity_source", "quantity_source_conflict",
    "field_actions", "proposed_values", "reasons",
)


@app.command("migrate-shopify-dimensions")
def main(
    shop_domain: Annotated[str, typer.Option("--shop-domain", help="Shopify shop domain.")],
    access_token: Annotated[str, typer.Option("--access-token", envvar="TOKEN", help="Shopify Admin API access token.")],
    source_namespace: Annotated[str, typer.Option("--source-namespace")],
    source_height_key: Annotated[str, typer.Option("--source-height-key")],
    source_width_key: Annotated[str, typer.Option("--source-width-key")],
    source_depth_key: Annotated[str, typer.Option("--source-depth-key")],
    target_namespace: Annotated[str, typer.Option("--target-namespace")] = "custom",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Inspect without Shopify mutations.")] = False,
    execute: Annotated[bool, typer.Option("--execute", help="Write proposed values to Shopify.")] = False,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = None,
    overwrite_existing: Annotated[bool, typer.Option("--overwrite-existing")] = False,
    strict_product: Annotated[bool, typer.Option("--strict-product/--no-strict-product")] = True,
    report_directory: Annotated[str, typer.Option("--report-directory")] = "migration_reports/shopify_dimensions/",
    checkpoint_file: Annotated[str | None, typer.Option("--checkpoint-file", help="Checkpoint path for resumable runs.")] = None,
    resume: Annotated[bool, typer.Option("--resume", help="Resume from the checkpoint file.")] = False,
    confirm_shop_domain: Annotated[str | None, typer.Option("--confirm-shop-domain")] = None,
    allow_partial_success: Annotated[bool, typer.Option("--allow-partial-success")] = False,
    log_level: Annotated[str, typer.Option("--log-level")] = "INFO",
) -> None:
    """Migrate legacy Shopify product dimensions into structured metafields."""
    try:
        _validate_invocation(dry_run=dry_run, execute=execute, shop_domain=shop_domain, confirm_shop_domain=confirm_shop_domain)
        exit_code = asyncio.run(_run(
            shop_domain=shop_domain,
            access_token=access_token,
            source_namespace=source_namespace,
            source_keys={"height": source_height_key, "width": source_width_key, "depth": source_depth_key},
            target_namespace=target_namespace,
            dry_run=dry_run,
            execute=execute,
            limit=limit,
            overwrite_existing=overwrite_existing,
            strict_product=strict_product,
            report_directory=report_directory,
            checkpoint_file=checkpoint_file,
            resume=resume,
            confirm_shop_domain=confirm_shop_domain,
            allow_partial_success=allow_partial_success,
            log_level=log_level,
        ))
    except ValueError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(1) from exc
    if exit_code:
        raise typer.Exit(exit_code)


async def _run(
    *,
    shop_domain: str,
    access_token: str,
    source_namespace: str,
    source_keys: dict[str, str],
    target_namespace: str,
    dry_run: bool,
    execute: bool,
    limit: int | None,
    overwrite_existing: bool,
    strict_product: bool,
    report_directory: str | Path,
    confirm_shop_domain: str | None,
    allow_partial_success: bool,
    log_level: str = "INFO",
    checkpoint_file: str | Path | None = None,
    resume: bool = False,
) -> int:
    _configure_logging(log_level)
    _validate_invocation(dry_run=dry_run, execute=execute, shop_domain=shop_domain, confirm_shop_domain=confirm_shop_domain)
    access_token = access_token.strip()
    if not access_token:
        raise ValueError("--access-token must contain a usable Shopify Admin API access token.")

    normalized_domain = normalize_shop_domain(shop_domain)
    target_keys = dict(TARGET_KEYS)
    checkpoint_path = Path(checkpoint_file) if checkpoint_file else Path(report_directory) / "checkpoint.json"
    run_signature = {
        "shop_domain": normalized_domain, "source_namespace": source_namespace,
        "source_keys": source_keys, "target_namespace": target_namespace,
        "limit": limit, "overwrite_existing": overwrite_existing,
        "strict_product": strict_product, "mode": "execute" if execute else "dry_run",
    }
    checkpoint = _load_checkpoint(checkpoint_path, run_signature) if resume else {
        "version": 1, "signature": run_signature, "phase": "scanning",
        "scan_cursor": None, "decisions": [],
    }
    if not resume:
        _write_checkpoint(checkpoint_path, checkpoint)
    decisions = _decisions_from_checkpoint(checkpoint)
    logger.info("shopify_dimension_migration_start | shop_domain=%s mode=%s limit=%s", normalized_domain, "execute" if execute else "dry_run", limit if limit is not None else "all")
    mutation_errors: list[dict] = list(checkpoint.get("mutation_errors") or [])
    try:
        definitions = await fetch_target_metafield_definitions(
            shop_domain=normalized_domain,
            access_token_encrypted=access_token,
            target_namespace=target_namespace,
            target_keys=tuple(target_keys.values()),
        )
        definition_problems = validate_target_metafield_definitions(definitions)
        if definition_problems:
            raise ValueError("Target metafield preflight failed: " + ", ".join(definition_problems))
        limits = {
            key: ((definition or {}).get("validations", {}).get("min"), (definition or {}).get("validations", {}).get("max"))
            for key, definition in definitions.items()
        }
        config = MigrationConfig(overwrite_existing=overwrite_existing, strict_product=strict_product, target_limits=limits)
        typer.echo(f"Preflight passed for {normalized_domain}; processing products...")
        if checkpoint.get("phase") == "scanning":
            async def on_page_complete(cursor: str | None, processed: int) -> None:
                checkpoint.update({
                    "phase": "scanning", "scan_cursor": cursor,
                    "decisions": [_decision_to_checkpoint(d) for d in decisions],
                })
                _write_checkpoint(checkpoint_path, checkpoint)

            async for product in iter_product_dimensions(
                shop_domain=normalized_domain,
                access_token_encrypted=access_token,
                source_namespace=source_namespace,
                source_keys=source_keys,
                target_namespace=target_namespace,
                target_keys=target_keys,
                limit=limit,
                start_after=checkpoint.get("scan_cursor"),
                initial_yielded=len(decisions),
                on_page_complete=on_page_complete,
            ):
                decisions.append(build_product_migration(ProductMigrationInput(
                gid=product["gid"], title=product["title"], handle=product["handle"], sku=product["sku"],
                legacy_height=product["legacy"]["height"], legacy_width=product["legacy"]["width"],
                legacy_depth=product["legacy"]["depth"],
                legacy_dimensions=product["legacy"].get("dimensions"),
                legacy_extension_quantity=product["legacy"].get("extension_quantity"),
                existing_extensions_quantity=product["existing"].get("extensions_quantity"),
                existing_targets=product["existing"],
                ), config=config))
                decision = decisions[-1]
                logger.info(
                "legacy_dimensions_migration | product_gid=%s title=%s product_status=%s original=%r parsed=%s malformed=%s action=%s proposed=%s",
                decision.product_gid, decision.title, product.get("status"),
                decision.raw_values.get("legacy_dimensions"),
                decision.raw_values.get("parsed_legacy_dimensions"),
                decision.raw_values.get("malformed_legacy_lines"), decision.action,
                decision.proposed_values,
                )
                if decision.legacy_extension_quantity is not None:
                    logger.info(
                    "legacy_extension_quantity_detected | product_gid=%s title=%s legacy_quantity=%s width_quantity=%s existing_canonical=%s decision=%s",
                    decision.product_gid, decision.title, decision.legacy_extension_quantity,
                    decision.proposed_extensions_quantity, decision.existing_extensions_quantity,
                    decision.status,
                    )
                if decision.quantity_source_conflict:
                    logger.warning(
                    "quantity_sources_conflict | product_gid=%s title=%s legacy_quantity=%s width=%s existing_canonical=%s reason=conflicting_quantity_sources",
                    decision.product_gid, decision.title, decision.legacy_extension_quantity,
                    product["legacy"].get("width"), decision.existing_extensions_quantity,
                    )
                if len(decisions) % 50 == 0:
                    typer.echo(f"Processed {len(decisions)} products...")

            checkpoint.update({"phase": "scan_complete", "decisions": [_decision_to_checkpoint(d) for d in decisions]})
            _write_checkpoint(checkpoint_path, checkpoint)

        summary = summarize_decisions(decisions)
        if execute:
            set_mutations = [{"product_gid": d.product_gid, "key": key, "value": value} for d in decisions for key, value in d.proposed_values.items()]
            delete_mutations = [{"product_gid": d.product_gid, "key": key} for d in decisions for key in d.delete_keys]
            checkpoint["phase"] = "mutating"
            checkpoint.setdefault("mutation_stage", "set")
            checkpoint.setdefault("mutation_offset", 0)
            _write_checkpoint(checkpoint_path, checkpoint)

            async def on_set_batch_complete(offset: int) -> None:
                checkpoint.update({"mutation_stage": "set", "mutation_offset": offset, "mutation_errors": mutation_errors})
                _write_checkpoint(checkpoint_path, checkpoint)

            async def on_delete_batch_complete(offset: int) -> None:
                checkpoint.update({"mutation_stage": "delete", "mutation_offset": offset, "mutation_errors": mutation_errors})
                _write_checkpoint(checkpoint_path, checkpoint)

            if checkpoint.get("mutation_stage") == "set":
                set_start_offset = int(checkpoint.get("mutation_offset") or 0)
                mutation_errors.extend(await set_dimension_metafields_batch(
                    shop_domain=normalized_domain, access_token_encrypted=access_token,
                    target_namespace=target_namespace, mutations=set_mutations,
                    start_offset=set_start_offset, on_batch_complete=on_set_batch_complete,
                ))
                checkpoint.update({"mutation_stage": "delete", "mutation_offset": 0, "mutation_errors": mutation_errors})
                _write_checkpoint(checkpoint_path, checkpoint)
            delete_start_offset = int(checkpoint.get("mutation_offset") or 0)
            mutation_errors.extend(await delete_stale_extension_dimension_batch(
                shop_domain=normalized_domain, access_token_encrypted=access_token,
                target_namespace=target_namespace, mutations=delete_mutations,
                start_offset=delete_start_offset, on_batch_complete=on_delete_batch_complete,
            ))
            for mutation_error in mutation_errors:
                logger.error(
                    "shopify_dimension_mutation_error | product_gid=%s key=%s message=%s field=%s",
                    mutation_error.get("product_gid"), mutation_error.get("key"),
                    mutation_error.get("message"), mutation_error.get("field"),
                )
            summary.written = max(0, summary.proposed - len({error.get("product_gid") for error in mutation_errors}))
            await _verify(
                decisions=decisions, summary=summary, shop_domain=normalized_domain,
                access_token_encrypted=access_token, source_namespace=source_namespace,
                source_keys=source_keys, target_namespace=target_namespace,
                target_keys=target_keys, limit=limit, mutation_errors=mutation_errors,
            )
            checkpoint["phase"] = "completed"

        paths = write_reports(
            decisions, report_directory=report_directory, dry_run=dry_run, summary=summary,
            mutation_errors=mutation_errors,
            metadata={"shop_domain": normalized_domain, "mode": "execute" if execute else "dry_run"},
        )
        if not execute:
            checkpoint["phase"] = "completed"
        checkpoint["decisions"] = [_decision_to_checkpoint(d) for d in decisions]
        _write_checkpoint(checkpoint_path, checkpoint)
        typer.echo(f"Reports written under {Path(report_directory)} ({len(paths)} files).")
        logger.info("shopify_dimension_migration_end | shop_domain=%s products=%s proposed=%s invalid=%s", normalized_domain, len(decisions), summary.proposed, summary.invalid)
        if execute and mutation_errors and not allow_partial_success:
            return 1
        if execute and (summary.invalid or summary.conflicting_target) and not allow_partial_success:
            return 1
        return 0
    finally:
        pass


async def _verify(
    *,
    decisions: list[ProductMigrationDecision], summary: MigrationSummary,
    shop_domain: str, access_token_encrypted: str, source_namespace: str,
    source_keys: dict[str, str], target_namespace: str, target_keys: dict[str, str],
    limit: int | None, mutation_errors: list[dict],
) -> None:
    errors_by_product = {error.get("product_gid") for error in mutation_errors}
    decisions_by_gid = {decision.product_gid: decision for decision in decisions}
    async for product in iter_product_dimensions(
        shop_domain=shop_domain, access_token_encrypted=access_token_encrypted,
        source_namespace=source_namespace, source_keys=source_keys,
        target_namespace=target_namespace, target_keys=target_keys, limit=limit,
    ):
        decision = decisions_by_gid.get(product["gid"])
        if decision is None or decision.product_gid in errors_by_product:
            continue
        if not decision.proposed_values and not decision.delete_keys:
            continue
        matches = all(_same_metafield_value(product["existing"].get(key), value) for key, value in decision.proposed_values.items())
        matches = matches and all(not (product["existing"].get(key) or "").strip() for key in decision.delete_keys)
        if matches:
            summary.verified += 1
        else:
            summary.verification_failed += 1


def write_reports(
    decisions: list[ProductMigrationDecision], *, report_directory: str | Path,
    dry_run: bool, summary: MigrationSummary | None = None,
    mutation_errors: list[dict] | None = None, metadata: dict | None = None,
    timestamp: str | None = None,
) -> dict[str, Path]:
    directory = Path(report_directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = summary or summarize_decisions(decisions)
    output_paths: dict[str, Path] = {}
    summary_path = directory / f"summary_{stamp}.json"
    summary_path.write_text(json.dumps({**(metadata or {}), "counts": summary.as_dict(), "product_count": len(decisions)}, indent=2, default=str) + "\n", encoding="utf-8")
    output_paths["summary"] = summary_path
    products_path = directory / f"products_{stamp}.csv"
    _write_csv(products_path, REPORT_COLUMNS, [_decision_row(decision) for decision in decisions])
    output_paths["products"] = products_path
    invalid_path = directory / f"invalid_{stamp}.csv"
    _write_csv(invalid_path, REPORT_COLUMNS, [_decision_row(decision) for decision in decisions if decision.status == "invalid"])
    output_paths["invalid"] = invalid_path
    if dry_run:
        proposed_path = directory / f"proposed_mutations_{stamp}.jsonl"
        with proposed_path.open("w", encoding="utf-8") as handle:
            for decision in decisions:
                if decision.proposed_values or decision.delete_keys:
                    handle.write(json.dumps({
                        "product_gid": decision.product_gid,
                        "legacy_extension_quantity": decision.legacy_extension_quantity,
                        "existing_extensions_quantity": decision.existing_extensions_quantity,
                        "proposed_extensions_quantity": decision.proposed_extensions_quantity,
                        "extensions_quantity_source": decision.extensions_quantity_source,
                        "quantity_source_conflict": decision.quantity_source_conflict,
                        "values": decision.proposed_values,
                        "delete_keys": list(decision.delete_keys),
                    }, sort_keys=True) + "\n")
        output_paths["proposed_mutations"] = proposed_path
    else:
        errors_path = directory / f"mutation_errors_{stamp}.csv"
        _write_csv(errors_path, ("product_gid", "key", "message", "field"), mutation_errors or [])
        output_paths["mutation_errors"] = errors_path
    return output_paths


def summarize_decisions(decisions: list[ProductMigrationDecision]) -> MigrationSummary:
    summary = MigrationSummary()
    for decision in decisions:
        if decision.status == "proposed":
            summary.proposed += 1
        elif decision.status == "already_correct":
            summary.already_correct += 1
        elif decision.status == "no_legacy_value":
            summary.no_legacy_value += 1
        elif decision.status == "invalid":
            summary.invalid += 1
        elif decision.status == "conflicting_target":
            summary.conflicting_target += 1
        else:
            summary.skipped += 1
    return summary


def _decision_row(decision: ProductMigrationDecision) -> dict:
    return {
        "product_gid": decision.product_gid, "title": decision.title, "handle": decision.handle,
        "sku": decision.sku or "", "status": decision.status,
        "action": decision.action,
        "raw_height": decision.raw_values.get("height") or "", "raw_width": decision.raw_values.get("width") or "",
        "raw_depth": decision.raw_values.get("depth") or "",
        "legacy_dimensions": decision.raw_values.get("legacy_dimensions") or "",
        "parsed_legacy_dimensions": json.dumps(decision.raw_values.get("parsed_legacy_dimensions") or {}, default=str, sort_keys=True),
        "malformed_legacy_lines": json.dumps(decision.raw_values.get("malformed_legacy_lines") or [], default=str),
        "legacy_extension_quantity": decision.legacy_extension_quantity or "",
        "existing_extensions_quantity": decision.existing_extensions_quantity or "",
        "proposed_extensions_quantity": decision.proposed_extensions_quantity or "",
        "extensions_quantity_source": decision.extensions_quantity_source or "",
        "quantity_source_conflict": str(decision.quantity_source_conflict).lower(),
        "field_actions": json.dumps(decision.field_actions, sort_keys=True),
        "proposed_values": json.dumps(decision.proposed_values, sort_keys=True),
        "reasons": ";".join(decision.reasons),
    }


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)


def _same_metafield_value(existing: str | None, proposed: str) -> bool:
    if not existing:
        return False
    try:
        return json.loads(existing) == json.loads(proposed)
    except (TypeError, ValueError, json.JSONDecodeError):
        return existing.strip() == proposed.strip()


def _configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError("--log-level must be a valid Python logging level.")
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _validate_invocation(*, dry_run: bool, execute: bool, shop_domain: str, confirm_shop_domain: str | None) -> None:
    if dry_run == execute:
        raise ValueError("Exactly one of --dry-run or --execute is required.")
    if execute and confirm_shop_domain != shop_domain:
        raise ValueError("--confirm-shop-domain must exactly match --shop-domain for --execute.")


def _decision_to_checkpoint(decision: ProductMigrationDecision) -> dict:
    return {
        "product_gid": decision.product_gid,
        "title": decision.title,
        "handle": decision.handle,
        "sku": decision.sku,
        "status": decision.status,
        "field_actions": decision.field_actions,
        "proposed_values": decision.proposed_values,
        "delete_keys": list(decision.delete_keys),
        "reasons": list(decision.reasons),
        "raw_values": decision.raw_values,
    }


def _decisions_from_checkpoint(checkpoint: dict) -> list[ProductMigrationDecision]:
    decisions: list[ProductMigrationDecision] = []
    for item in checkpoint.get("decisions") or []:
        decisions.append(ProductMigrationDecision(
            product_gid=item["product_gid"], title=item.get("title", ""),
            handle=item.get("handle", ""), sku=item.get("sku"),
            status=item.get("status", "skipped"),
            field_actions=dict(item.get("field_actions") or {}),
            proposed_values=dict(item.get("proposed_values") or {}),
            delete_keys=tuple(item.get("delete_keys") or ()),
            reasons=tuple(item.get("reasons") or ()),
            raw_values=dict(item.get("raw_values") or {}),
        ))
    return decisions


def _load_checkpoint(path: Path, signature: dict) -> dict:
    if not path.exists():
        raise ValueError(f"Checkpoint file does not exist: {path}")
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Checkpoint file is not readable: {path}") from exc
    if checkpoint.get("signature") != signature:
        raise ValueError("Checkpoint settings do not match this migration invocation.")
    if checkpoint.get("phase") == "completed":
        raise ValueError("Checkpoint is already completed; omit --resume to start a new run.")
    return checkpoint


def _write_checkpoint(path: Path, checkpoint: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(checkpoint, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


if __name__ == "__main__":
    app()
