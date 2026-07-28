# SUMMARY_PLAN_shopify_product_sync_duplicate_fix_20260727

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_product_sync_duplicate_fix_20260727`
- Status: `implemented`
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T19:23:25Z`
- Source plan:
  `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_duplicate_fix_20260727.md`

## What was implemented

- Added the per-item operation tag
  `managerbeyo-sync-<shopify_product_sync_item.client_id>` to every created
  Shopify product.
- Added an operation-tag product query before exact-SKU/barcode resolution.
  One tagged product is adopted through the update path; two tagged products
  fail with `ambiguous_operation_tag`.
- Split the product mutation from `productVariantsBulkUpdate` so the product
  and default variant IDs can be persisted before the SKU-writing mutation.
- Added the replay stages `queued`, `product_created`,
  `variant_configured`, and `inventory_set`, with pure stage ordering.
- Preserved exact-SKU ambiguity as `ambiguous_product_match`, non-retryable
  failures as persisted `FAILED` rows, and retryable Shopify GraphQL failures
  as propagated exceptions from the orchestrator.

## Characterisation deltas

The characterisation net passes with exactly two intended changes:

1. `find_product_by_operation_tag` runs before the existing SKU lookup.
2. `productCreate` inputs carry one additional operation tag.

All pre-existing product/update, variant, metafield, and additive-inventory
GraphQL documents and variables are otherwise unchanged.

## Stage commit boundaries introduced

1. `product_created`: commits `requested_operation`, Shopify product/default
   variant IDs, optional inventory/media IDs, and the stage before the first
   `productVariantsBulkUpdate` call.
2. `variant_configured`: commits the configured variant and inventory-item IDs
   before inventory work.
3. `inventory_set`: commits completion of the inventory stage before
   metafields and final success.

The existing initial `PROCESSING`, inventory-ledger, absolute-inventory, and
final success/failure commits were retained.

## Inventory and latency

- `app/beyo_manager/services/tasks/shopify/_inventory_sync.py` is
  byte-for-byte identical to `HEAD`; the existing
  `sync_inventory_adjustments` call and additive ledger behavior are
  unchanged.
- Each newly queued sync item now pays for one additional sequential, indexed
  Shopify tag-query round trip. Resume paths after `product_created` do not
  repeat it. No meaningful external latency in milliseconds was measured
  because validation uses mocked Shopify I/O; added wall-clock latency is the
  live shop's single GraphQL-query RTT.

## Files changed for this fix

- `app/beyo_manager/domain/shopify/enums.py`
- `app/beyo_manager/domain/shopify/product_sync_stages.py`
- `app/beyo_manager/models/tables/shopify/shopify_product_sync_item.py`
- `app/beyo_manager/services/infra/shopify/product_sync_client.py`
- `app/beyo_manager/services/tasks/shopify/_product_sync_orchestrator.py`
- `app/migrations/versions/2e351577bb18_add_stage_to_shopify_product_sync_items.py`
- `app/tests/unit/services/infra/shopify/test_product_sync_client.py`
- `app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`
- `app/tests/unit/services/tasks/shopify/test_product_sync_orchestrator.py`
- `app/tests/integration/services/tasks/shopify/test_shopify_worker_handlers_integration.py`
- `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_duplicate_fix_20260727.md`
- `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_product_sync_duplicate_fix_20260727.md`

## Validation evidence

- Characterisation test: **4 passed**.
- Product-sync orchestrator test: **13 passed**.
- Product-sync client plus orchestrator focused tests: **20 passed**.
- Shopify product-sync model/command/worker integration selection:
  **18 passed** after upgrading the test database to the new migration head.
- Alembic `upgrade head && downgrade -1 && upgrade head`: **passed**.
- Scoped Ruff check: **passed**.
- `git diff --check`: **passed**.
- Inventory implementation hash comparison against `HEAD`: **identical**.
- Full suite after the test schema update: **1064 passed, 31 failed,
  2 warnings**.
- Shopify-filtered suite: **366 passed, 3 failed, 720 deselected**.

## Known validation debt outside this fix

- The repository-wide suite remains red in unrelated working-section,
  upholstery, audit, auth/serialization/router, legacy dimension-migration,
  and metafield-preference tests already present in the dirty worktree.
- The Shopify-filtered failures are two pre-existing legacy-dimension
  expectations and one fixed-ID metafield-preference collision caused by
  repeated database-backed test runs.
- All tests exercising the duplicate fix, characterisation contract,
  migration, and product-sync worker path pass.

## Lifecycle transition

- Current state: `implemented`
- Next transition: human review gate, then `summarized`
- Archive: intentionally not performed
