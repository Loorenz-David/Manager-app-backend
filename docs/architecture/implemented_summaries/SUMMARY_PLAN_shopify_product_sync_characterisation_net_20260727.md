# SUMMARY_PLAN_shopify_product_sync_characterisation_net_20260727

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_product_sync_characterisation_net_20260727`
- Status: `implemented`
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T18:29:46Z`
- Source plan:
  `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_characterisation_net_20260727.md`

## What was implemented

- Added a production-code-free characterization net around
  `sync_one_product_sync_item`.
- Captured each emitted GraphQL operation name, full document with only trailing
  whitespace normalized, complete variables dictionary, and call order.
- Added four deterministic fixtures:
  - `create_path_case`: exact-SKU lookup with no match, `productCreate`, then the
    default variant `productVariantsBulkUpdate`.
  - `update_path_case`: exact-SKU lookup with one existing product,
    `productUpdate`, then `productVariantsBulkUpdate`.
  - `metafields_case`: create path followed by `metafieldsSet` for two entries,
    including the current hard-coded `custom` namespace.
  - `multi_location_additive_inventory_case`: create path, shop-location
    ownership query, two inventory-state queries, then one batched
    `inventoryAdjustQuantities` mutation using `name: "available"`.
- The create/update snapshots contain no media argument, and the inventory
  snapshot contains no `inventorySetQuantities` operation.
- No production code was modified.

## Files changed

- `app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`:
  added the four exact GraphQL characterization cases.
- `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_characterisation_net_20260727.md`:
  transitioned the plan from `approved` to `implemented` and recorded the
  update timestamp.
- `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_product_sync_characterisation_net_20260727.md`:
  recorded implementation and validation evidence.

## Contract adherence

- `backend/architecture/15_testing.md`: deterministic unit tests isolate every
  external Shopify call and perform no database or network I/O.
- `backend/architecture/50_testing_strategy.md`: fixtures have fixed IDs,
  values, responses, and ordering with no local-state dependency.
- `backend/architecture/19_integrations.md`: the tests patch the Shopify
  integration boundary rather than making real external requests.
- `backend/docs/architecture/under_construction/implementation/prompts/GUARDRAILS.md`:
  production code remains unchanged and the additive inventory behavior is
  characterized exactly as it exists.

## Validation evidence

- `.venv/bin/python -m pytest tests/unit/services/tasks/shopify/test_product_sync_characterisation.py -v`:
  **4 passed**.
- `.venv/bin/python -m ruff check tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`:
  **passed**.
- `.venv/bin/python -m py_compile tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`:
  **passed**.
- `git diff --check`: **passed**.
- `.venv/bin/python -m pytest tests -k shopify`: **333 passed, 10 failed,
  716 deselected** after enabling access to the local test PostgreSQL instance.
- The same suite with the new file explicitly ignored still failed:
  **328 passed, 11 failed, 716 deselected**. The additional failure was a
  persisted fixed `client_id` collision on the repeated database-backed run.

## Anything that looked wrong but was not changed

- The required pre-existing Shopify suite is not green. Two dimension-migration
  assertions receive an unexpected `extensions_quantity: "0"`, two product
  processing router assertions receive an unexpected
  `inventory_adjustments: []`, and six authorization assertions expect `403`
  for worker/seller roles but receive `200`. These are outside this plan's
  single-test-file implementation scope and were not changed.
- A repeat database-backed run also exposed test-state leakage: the
  client-supplied-metafield-preference-ID integration test collided with the
  fixed ID left by the previous run.
- The existing product-sync normalizer defaults an omitted product status to
  `DRAFT`, while the standing Shopify guardrail says product status is
  `UNLISTED`. This characterization uses explicit `UNLISTED` fixtures and does
  not change the normalizer.
- No definite new defect was found inside
  `_product_sync_orchestrator.py`; its current call sequencing was preserved
  exactly.

## Known gaps or deferred items

- The plan cannot validly transition from `implemented` to `summarized` or
  `archived` until `pytest tests -k shopify` is green, because that command is
  an explicit done signal and guardrail.
- The unrelated failing tests and their production contracts require a
  separate scoped correction or reconciliation.

## Lifecycle transition

- Current state: `implemented`
- Next state: `summarized` after the required Shopify suite is green, then
  `archived`
- Archive target plan:
  `backend/docs/architecture/archives/implementation/PLAN_shopify_product_sync_characterisation_net_20260727.md`
