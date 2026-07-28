# ARCHIVE_RECORD_PLAN_shopify_product_sync_duplicate_fix_20260727

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_shopify_product_sync_duplicate_fix_20260727`
- Archived at (UTC): `2026-07-27T00:00:00Z`
- Archive owner agent: `claude-opus-5`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_product_sync_duplicate_fix_20260727.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_product_sync_duplicate_fix_20260727.md`
- Prerequisite: `ARCHIVE_RECORD_PLAN_shopify_product_sync_characterisation_net_20260727.md`
- Discovered while planning: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_product_20260727.md` (R12)
- Debug chain: `—`

## Outcome classification

- Result: `completed_with_validation_followups`
- Acceptance criteria: stage machine and operation-tag reconciliation implemented; the
  characterisation net still passes with only the two permitted deltas.
  **The human diff-review gate specified by the plan has not been formally recorded**, and the
  added per-item latency was not measured against a real Shopify endpoint (validation used mocked
  I/O).

## The bug this closed

A silent duplicate-product hole in **live production** product sync, independent of pre-orders.
The SKU is written by `productVariantsBulkUpdate`, not by `productCreate` — so a lost
`productCreate` response left the retry's exact-SKU lookup finding nothing, and it created a
**second Shopify product** while the operator saw a successful sync.

Two mitigations, both shipped: `shopify_product_id` persisted and the stage advanced **before** the
variant call, and operation-tag reconciliation (`products(query: "tag:managerbeyo-sync-<id>")`)
running before the SKU lookup to catch the case where the create response itself was lost.

## Why it was extracted

It surfaced while planning the pre-order feature, but it stands entirely on its own — it was
already costing the merchant duplicate products. Keeping it inside the pre-order delivery would
have coupled a production bug fix to an unrelated feature's schedule. The pre-order plan explicitly
accepted the bug as pre-existing and out of its own scope.

## Outstanding

- The human diff-review gate. The change touches live product-sync behaviour; the plan required a
  reviewer to confirm the two characterisation deltas and the stage-commit boundaries.
- Real-endpoint latency for the extra tag query per sync item.

No intention plan exists for this delivery, so the skill's step 10 does not apply.
