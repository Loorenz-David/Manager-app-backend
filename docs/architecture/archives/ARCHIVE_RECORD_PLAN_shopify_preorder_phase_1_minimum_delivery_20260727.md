# ARCHIVE_RECORD_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727`
- Archived at (UTC): `2026-07-27T00:00:00Z`
- Archive owner agent: `claude-opus-5`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
- Prerequisite: `ARCHIVE_RECORD_PLAN_shopify_product_sync_characterisation_net_20260727.md`
- Gates: `ARCHIVE_RECORD_PLAN_shopify_preorder_phase_0_dev_store_verification_20260727.md`
- Parent (still active): `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_product_20260727.md`
- Debug chain: `—`

## Outcome classification

- Result: `completed_with_validation_followups`
- Acceptance criteria: all five scope items implemented and unit/integration tested.
  **The dev-store verification has not been run** — acceptance criteria 4 and 6a
  (`UNLISTED`, absent from the storefront, `available` matching the selected quantity, visible in
  Zettle) require a real Shopify/Zettle environment.

## What was delivered

The pre-order feature as a **second entry point onto the existing `/products/process` pipeline**,
not a parallel one — the decisive scope decision of the whole delivery (parent plan R12/R13).

- `public_url(key)` on `StorageClient` plus `STORAGE_PUBLIC_BASE_URL`; the bucket was public but no
  application code composed an unsigned URL.
- Optional `media` on `productCreate`/`productUpdate`, implemented as **separate mutation
  documents** so the no-media path emits a byte-identical document to before — better than the plan
  anticipated, which expected a characterisation delta.
- Command-time image validation (20 MB / 25 MP / 5000 px) from data already on `images`.
- An `inventory_mode` discriminator (`add` | `set`) with an idempotent absolute
  `inventorySetQuantities` path: `@idempotent`, explicit `changeFromQuantity: null`, no
  `ignoreCompareQuantity`/`compareQuantity`, and `before_available` audit values.
- The trigger: `process_shopify_products` converted to `maybe_begin`, called from `create_task`
  behind task-type and role gates, with no Shopify I/O inside the task transaction.

Schema delta was **one enum and three columns** rather than the fourteen an earlier revision
proposed — the result of asking "what is the smallest delta?" instead of "what would a robust
system look like?".

## Post-implementation review corrections

Reviewed 2026-07-27 against a pristine-tree baseline; **no regressions** (31 pre-existing failures
before, 23 after; zero new). Three corrections applied during review:

- `inventory.quantities` split from the additive `inventory.adjustments`, so the payload shape is
  self-describing rather than inferable only from `inventory_mode`.
- `process_shopify_products` now returns `event_client_ids`, replacing a brittle lookup that
  queried `metadata_json` and depended on autoflush.
- Defensive `getattr` on `inventory_mode`/`stage` removed; the test stand-ins were corrected to
  carry the NOT NULL columns instead.

## Outstanding

The dev-store verification, which also carries **deferred Phase 0 gate 0.2** (storefront absence).
A leak there is a scope change — two new OAuth scopes plus merchant reauthorization — not a bug fix.

No intention plan exists for this delivery, so the skill's step 10 does not apply.
