# Codex Prompt — Product-sync characterisation net

**This is the first Codex task in the Shopify pre-order delivery.** It is a safety net for the two
pieces of work that follow, and it changes no production code.

## Load first, in this order

1. **`backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`** — governs how this plan
   moves through its lifecycle. Follow its execution protocol, output format
   (`skills/_shared/output_format.md`) and quality gate (`skills/_shared/quality_gate.md`).
2. **`backend/docs/architecture/under_construction/implementation/prompts/GUARDRAILS.md`**
3. **`backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_characterisation_net_20260727.md`**
   — your plan. It is self-contained.

Do **not** read the parent plan `PLAN_shopify_preorder_product_20260727.md` — it is ~1300 lines of
research and backlog, and nothing in it is needed here.

## Task

Write one test file capturing the **exact** GraphQL documents and variables the existing Shopify
product sync emits **today**.

**No production code changes. Zero.** Only the new test file may be added.

If you find a bug while reading the orchestrator, write it down in your summary — do not fix it.

## Why this matters

Two upcoming pieces of work modify `_product_sync_orchestrator.py` and `product_sync_client.py`,
both in live production use:

- the pre-order minimum delivery (adds media and an inventory-mode branch),
- the duplicate-product fix (adds a stage machine and tag reconciliation).

This snapshot is the only thing that will catch silent behavioural drift in product sync while
those land. Make it tight: assert **full query strings and complete variables dicts**, not
operation names or shapes.

## Scope boundary

- **Add:** `app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py`
- **Modify:** nothing.

If you believe a production change is needed to make the test pass, **the test is wrong** — it
describes reality, not the target state. Stop and report.

## Done signal

```
pytest app/tests/unit/services/tasks/shopify/test_product_sync_characterisation.py -v
pytest app/tests -k shopify
```

Both green against **unmodified** production code.

## Lifecycle (per the skill)

1. Set the plan's `Status` to `implemented`, update `Last updated at`.
2. Write a summary to `backend/docs/architecture/implemented_summaries/`, trace-linked to this plan.
3. Report in the skill's output format: lifecycle state, next transition, document paths touched.

This plan is self-contained, so it may proceed to `summarized` → `archived` once the summary is
written.

## Report explicitly

- The four fixtures you captured and what each exercises.
- Anything that looked wrong but which you did not change.
