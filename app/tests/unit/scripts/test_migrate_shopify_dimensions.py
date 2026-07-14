import csv
import json

import pytest
from typer.testing import CliRunner

from beyo_manager.domain.shopify.dimension_migration import ProductMigrationDecision
from scripts.backfill import migrate_shopify_dimensions


runner = CliRunner()


def test_cli_rejects_ambiguous_mode_before_running_async_work(monkeypatch) -> None:
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(migrate_shopify_dimensions.asyncio, "run", fail_if_called)
    result = runner.invoke(migrate_shopify_dimensions.app, [
        "--shop-domain", "shop.myshopify.com", "--access-token", "shpat_test", "--source-namespace", "legacy",
        "--source-height-key", "height", "--source-width-key", "width", "--source-depth-key", "depth",
        "--dry-run", "--execute",
    ])
    assert result.exit_code != 0
    assert not called


def test_cli_rejects_confirmation_mismatch_before_running_async_work(monkeypatch) -> None:
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(migrate_shopify_dimensions.asyncio, "run", fail_if_called)
    result = runner.invoke(migrate_shopify_dimensions.app, [
        "--shop-domain", "shop.myshopify.com", "--access-token", "shpat_test", "--source-namespace", "legacy",
        "--source-height-key", "height", "--source-width-key", "width", "--source-depth-key", "depth",
        "--execute", "--confirm-shop-domain", "other.myshopify.com",
    ])
    assert result.exit_code != 0
    assert not called


def test_write_reports_creates_dry_run_artifacts(tmp_path) -> None:
    decisions = [ProductMigrationDecision(
        product_gid="p1", title="Chair", handle="chair", sku="sku-1", status="proposed",
        field_actions={"height_dimension": "created"},
        proposed_values={"height_dimension": '{"value":100,"unit":"CENTIMETERS"}'},
        raw_values={"height": "100", "width": None, "depth": None},
    )]
    paths = migrate_shopify_dimensions.write_reports(
        decisions, report_directory=tmp_path, dry_run=True, timestamp="20260714T000000Z"
    )
    assert {path.name for path in paths.values()} == {
        "summary_20260714T000000Z.json", "products_20260714T000000Z.csv",
        "invalid_20260714T000000Z.csv", "proposed_mutations_20260714T000000Z.jsonl",
    }
    with paths["products"].open(newline="") as handle:
        assert next(csv.DictReader(handle))["product_gid"] == "p1"


def test_reports_expose_quantity_transition_fields_and_plural_mutation_key(tmp_path) -> None:
    decision = ProductMigrationDecision(
        product_gid="p1", title="Chair", handle="chair", sku=None, status="proposed",
        field_actions={"extensions_quantity": "created"},
        proposed_values={"extensions_quantity": "2"},
        reasons=("extensions_quantity_source:legacy_extension_quantity",),
        raw_values={"legacy_extension_quantity": "2", "existing_extensions_quantity": None},
    )
    paths = migrate_shopify_dimensions.write_reports(
        [decision], report_directory=tmp_path, dry_run=True, timestamp="20260714T000001Z"
    )
    with paths["products"].open(newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["legacy_extension_quantity"] == "2"
    assert row["proposed_extensions_quantity"] == "2"
    with paths["proposed_mutations"].open() as handle:
        mutation = json.loads(handle.readline())
    assert mutation["values"] == {"extensions_quantity": "2"}
    assert "extension_quantity" not in mutation["values"]


def test_cli_requires_access_token() -> None:
    result = runner.invoke(migrate_shopify_dimensions.app, [
        "--shop-domain", "shop.myshopify.com", "--source-namespace", "legacy",
        "--source-height-key", "height", "--source-width-key", "width", "--source-depth-key", "depth",
        "--dry-run",
    ])
    assert result.exit_code != 0
    assert "access-token" in result.output


def test_cli_reads_access_token_from_token_environment(monkeypatch) -> None:
    called = {}

    async def fake_run(**kwargs):
        called.update(kwargs)
        return 0

    monkeypatch.setattr(migrate_shopify_dimensions, "_run", fake_run)
    result = runner.invoke(migrate_shopify_dimensions.app, [
        "--shop-domain", "shop.myshopify.com", "--source-namespace", "legacy",
        "--source-height-key", "height", "--source-width-key", "width", "--source-depth-key", "depth",
        "--dry-run",
    ], env={"TOKEN": "  shpat_from_env  "})
    assert result.exit_code == 0
    assert called["access_token"] == "  shpat_from_env  "


def test_empty_access_token_is_rejected_before_database_or_integration_work(monkeypatch) -> None:
    import asyncio

    monkeypatch.setattr(migrate_shopify_dimensions, "init_db", lambda: (_ for _ in ()).throw(AssertionError("database used")), raising=False)
    with pytest.raises(ValueError, match="usable Shopify Admin API access token"):
        asyncio.run(migrate_shopify_dimensions._run(
            shop_domain="shop.myshopify.com", access_token=" \t ", source_namespace="legacy",
            source_keys={"height": "height", "width": "width", "depth": "depth"},
            target_namespace="custom", dry_run=True, execute=False, limit=1,
            overwrite_existing=False, strict_product=True, report_directory="/tmp/migration-tests",
            confirm_shop_domain=None, allow_partial_success=False,
        ))


def test_checkpoint_round_trip_preserves_decisions_without_token(tmp_path) -> None:
    decision = ProductMigrationDecision(
        product_gid="p1", title="Chair", handle="chair", sku=None, status="proposed",
        proposed_values={"height_dimension": '{"value":43,"unit":"CENTIMETERS"}'},
        raw_values={"legacy_dimensions": "Height: 43 cm"},
    )
    path = tmp_path / "checkpoint.json"
    checkpoint = {
        "version": 1, "signature": {"shop_domain": "shop.myshopify.com"},
        "phase": "scanning", "scan_cursor": "cursor-1",
        "decisions": [migrate_shopify_dimensions._decision_to_checkpoint(decision)],
    }
    migrate_shopify_dimensions._write_checkpoint(path, checkpoint)
    loaded = migrate_shopify_dimensions._load_checkpoint(path, checkpoint["signature"])
    restored = migrate_shopify_dimensions._decisions_from_checkpoint(loaded)
    assert restored[0].proposed_values == decision.proposed_values
    assert "access_token" not in path.read_text()
