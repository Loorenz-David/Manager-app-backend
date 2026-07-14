# SUMMARY_PLAN_shopify_dimension_migration_20260714

## Metadata

- Plan ID: `PLAN_shopify_dimension_migration_20260714`
- Summary status: `completed_with_validation_followups`
- Implemented at (UTC): `2026-07-14T12:12:11Z`
- Plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_dimension_migration_20260714.md`
- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_shopify_dimension_migration_20260714.md`

## Summary

Implemented a terminal-only Shopify dimension migration with a mandatory, reviewable dry-run path. Legacy height, width, and depth text is parsed with `Decimal` precision, normalized to centimeters, and inconsistent width extensions are rejected without guessing. Existing structured values are protected by default; overwriting and stale extension cleanup require `--overwrite-existing`.

The implementation includes target-definition preflight validation, paginated product reads, configurable-namespace `metafieldsSet` batching, indexed mutation-error correlation, bounded retry handling for retryable Shopify errors, verification reads after execution, and JSON/CSV/JSONL reports. The access-token decrypt boundary remains inside the existing GraphQL transport and no token, authorization header, or encryption key is logged or reported.

## Changes

- `app/beyo_manager/domain/shopify/dimension_migration.py`: pure parsing, serialization, target-protection decisions, and migration counters.
- `app/beyo_manager/services/infra/shopify/dimension_migration_client.py`: definition/product queries, batched set/delete mutations, retries, response mapping, and preflight type checks.
- `app/beyo_manager/services/queries/shopify/get_active_shopify_integration_by_domain.py`: active, non-deleted integration lookup by normalized shop domain.
- `app/scripts/backfill/migrate_shopify_dimensions.py`: Typer CLI with mutually exclusive `--dry-run`/`--execute`, confirmation guard, reports, and verification.
- `app/tests/unit/domain/shopify/test_dimension_migration.py`: parser and decision matrix.
- `app/tests/unit/services/infra/shopify/test_dimension_migration_client.py`: mutation payloads, error correlation, and retry behavior.
- `app/tests/unit/scripts/test_migrate_shopify_dimensions.py`: CLI safeguards and report artifacts.

## Validation

- `PYTHONPATH=. .venv/bin/pytest tests/unit/domain/shopify/test_dimension_migration.py tests/unit/services/infra/shopify/test_dimension_migration_client.py tests/unit/scripts/test_migrate_shopify_dimensions.py -q` — 27 passed.
- `app/.venv/bin/ruff check ...` — passed for all changed migration files.
- `app/.venv/bin/python -m compileall -q ...` — passed.

## Follow-ups before live execution

- Confirm the live source namespace/keys and run the prescribed `--dry-run --limit 100` against the intended shop.
- Review the generated reports and confirm the stale `extension_dimension` cleanup policy before any real `--execute --overwrite-existing` run.
- Live Shopify schema, credentials, mutation behavior, and post-execution verification were not exercised in this implementation run.
