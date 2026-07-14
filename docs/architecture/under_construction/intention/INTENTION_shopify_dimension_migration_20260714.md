# INTENTION_shopify_dimension_migration_20260714

## Metadata

- Intention ID: `INTENTION_shopify_dimension_migration_20260714`
- Status: `active`
- Owner: `David`
- Created at (UTC): `2026-07-14T00:00:00Z`
- Last updated at (UTC): `2026-07-14T12:12:11Z`

## Goal

 Migrate legacy free-text Shopify product dimension metafields (`height`, `width`, `depth`) into the new structured metafields (`height_dimension`, `width_dimension`, `depth_dimension`, `extensions_quantity`, `extension_dimension`), while reading the legacy `extension_quantity` source, all normalized to centimeters, via a manually-run standalone script — without ever writing to Shopify until a dry run has been reviewed.

## Why this matters

The store's ~5,000 products carry dimension data as inconsistent legacy text metafields (e.g. `100cm + 50cm + 50cm` encoding a base width plus one or more equal extensions). The new structured `dimension`/`number_integer` metafield definitions already exist in Shopify but are not populated. A one-off, carefully validated migration is needed to backfill them safely, without guessing on ambiguous data and without touching products until the output has been reviewed by a human.

## Success criteria

1. A dry run against the first 100 products (deterministic ordering) produces logs and reports showing exactly what would be written, with zero Shopify mutations performed.
2. Every legacy value is either migrated to a validated, correctly-typed structured metafield in centimeters, or is explicitly reported as invalid/ambiguous/inconsistent/needing manual review — never guessed.
3. A real execution (`--execute`) only proceeds after target metafield definitions are confirmed to exist with the expected types, and never silently overwrites existing non-empty target values unless `--overwrite-existing` is passed.
4. Post-execution verification re-queries Shopify and only counts a product as migrated once the written values are confirmed to match what was proposed.
5. The script is never exposed via an API endpoint, background worker, or scheduled task — terminal-only, manual execution.

## Scope boundary

- In scope: standalone script under `app/scripts/`, a pure parsing/decision domain module, a Shopify infra client for the migration's specific GraphQL needs, CSV/JSONL/JSON reports, dry-run and execute modes, target-definition preflight validation, verification phase, automated unit tests.
- Out of scope (for this intention): deleting legacy source metafields or their definitions, altering Shopify themes, updating ManagerBeyo frontend forms, any new HTTP endpoint, recurring/scheduled migrations.
- Non-goals: interpreting the fully expanded total width as the base width; averaging/summing/guessing inconsistent extension values; silently overwriting existing target data.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_shopify_dimension_migration_20260714` | `backend/docs/architecture/archives/implementation/PLAN_shopify_dimension_migration_20260714.md` | `archived` | Full implementation of the migration script: parsing rules, GraphQL query/mutation strategy, reports, idempotency, verification, tests |

## Progress notes

- 2026-07-14: Intention captured from user-supplied specification; paired implementation plan drafted after inspecting existing Shopify infra (`graphql_client.py`, `product_sync_client.py`, `metafield_definition_client.py`, `shopify_shop_integration.py`, `field_encryption.py`, `app/scripts/backfill/cleanup_expired_uploads.py`).
- 2026-07-14: Implementation completed and archived. Unit tests cover the parser, decision engine, Shopify adapter, retries, CLI safeguards, and reports. Live Shopify execution and operator review remain required before the intention can transition to `achieved`.

## Open questions

- Real source namespace/keys for legacy `height`/`width`/`depth` in the live store — impact if unresolved: dry run would target the wrong metafields or find nothing.
- Whether target metafield definitions currently have Shopify-side min/max `validations` configured — impact if unresolved: local pre-validation against limits would be skipped, relying solely on Shopify's own mutation-time rejection.
- Default stale `extension_dimension` cleanup policy (explicit delete vs. report-only) — impact if unresolved: risk of either silently losing data or leaving stale values that don't match the new parsed state.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: all success criteria met (migration executed, verified, and reports reviewed)
