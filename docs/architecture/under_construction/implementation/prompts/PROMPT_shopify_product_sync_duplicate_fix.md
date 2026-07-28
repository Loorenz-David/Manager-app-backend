# Codex Prompt — Product-sync duplicate-product fix ⚠️ (standalone bug fix)

This is **not** part of the pre-order delivery. It fixes a bug that exists in production today and
can be run independently.

> ⚠️ You are modifying `_product_sync_orchestrator.py`, which is in live production use.
> A human reviews your diff before this ships.

## Load first, in this order

1. **`backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`** — governs how this plan
   moves through its lifecycle. Follow its execution protocol, output format
   (`skills/_shared/output_format.md`) and quality gate (`skills/_shared/quality_gate.md`).
2. **`backend/docs/architecture/under_construction/implementation/prompts/GUARDRAILS.md`** — the
   **regression rule** governs this work.
3. **`backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_duplicate_fix_20260727.md`**
   — your plan. It is self-contained.

## The bug

The SKU is written by `productVariantsBulkUpdate`, **not** by `productCreate`
(`_product_sync_orchestrator.py:100-113`). So if `productCreate` succeeds but the response is lost
— timeout, worker SIGKILL, network drop — the retry's exact-SKU lookup finds nothing and creates a
**second Shopify product**. Silently: the operator sees a successful sync.

## Prerequisite — stop if it is missing

`app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py` must already exist
and be green. It is delivered by its own plan
(`PLAN_shopify_product_sync_characterisation_net_20260727.md`).

**Do not write it inline, and do not proceed without it.** You are modifying live production code
and that snapshot is the only drift detector. If it is absent, stop and report.

## The constraint that decides whether you succeeded

The characterisation test must still pass afterwards, with **exactly two** intended deltas:

- created products carry one extra tag,
- a tag query runs before the SKU lookup.

**Do not edit that test to match new behaviour beyond those two.** If it fails otherwise, your
change is wrong — stop and report.

## Leave completely alone

- The inventory step. The additive `sync_inventory_adjustments` ledger path is untouched.
- The exception classification: non-retryable and ambiguity errors → `FAILED`;
  `ShopifyGraphQLRetryableError` **propagates** so the execution layer retries with backoff.
- The existing explicit `await session.commit()` calls — this runs in the worker via
  `task_db_session()`, **not** inside `maybe_begin`. They are correct. Do not convert them.

## Done signal

```
pytest app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py -v
pytest app/tests/unit/services/tasks/shopify/test_product_sync_orchestrator.py -v
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest app/tests
```

Run the **full** suite.

## Lifecycle (per the skill)

1. Set the plan's `Status` to `implemented`, update `Last updated at`.
2. Write a summary to `backend/docs/architecture/implemented_summaries/`, trace-linked to this plan.
3. Report in the skill's output format: lifecycle state, next transition, document paths touched.

**Then stop.** State that a human review gate is pending; do not archive.

## Report explicitly

- The two characterisation deltas, and confirmation there were no others.
- Every stage-commit boundary you introduced.
- Confirmation the inventory step is byte-for-byte unchanged.
- The added latency from one extra tag query per sync item.
