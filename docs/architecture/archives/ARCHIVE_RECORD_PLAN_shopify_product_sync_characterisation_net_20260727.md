# ARCHIVE_RECORD_PLAN_shopify_product_sync_characterisation_net_20260727

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_shopify_product_sync_characterisation_net_20260727`
- Archived at (UTC): `2026-07-27T00:00:00Z`
- Archive owner agent: `claude-opus-5`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_product_sync_characterisation_net_20260727.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_product_sync_characterisation_net_20260727.md`
- Protects: `ARCHIVE_RECORD_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`,
  `ARCHIVE_RECORD_PLAN_shopify_product_sync_duplicate_fix_20260727.md`
- Debug chain: `—`

## Outcome classification

- Result: `completed`
- Acceptance criteria: `app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`
  captures the exact GraphQL documents and variables product sync emits, across four fixtures
  (create path, update path, metafields, multi-location additive inventory), and passed green
  against unmodified production code.

## Final notes

A prerequisite safety net with **no production code**. It exists because two subsequent pieces of
work — the pre-order minimum delivery and the duplicate-product fix — both modify
`_product_sync_orchestrator.py` and `product_sync_client.py`, which are in live production use.

It asserts full query strings and complete variables dicts rather than operation names or shapes,
and inlines its own copies of the mutation documents rather than importing them from the client,
which would have made the assertions tautological.

It was originally commit 1 of the duplicate-fix plan and was split out because it gates **two**
independent workstreams, and because "tell the agent to stop halfway through a plan" is a fragile
instruction to give an implementing agent.

During the Phase 1 review its fixtures were corrected to carry the `inventory_mode` and `stage`
columns, which are NOT NULL on the real model — a stand-in that omits them misrepresents what it
stands in for.

No intention plan exists for this delivery, so the skill's step 10 does not apply.
