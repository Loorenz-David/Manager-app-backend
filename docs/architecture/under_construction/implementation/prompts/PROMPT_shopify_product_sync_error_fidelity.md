# Codex Prompt — Shopify userErrors fidelity (standalone improvement)

This is **not** part of the pre-order delivery. It improves every existing Shopify code path and
can be run at any time, in any order.

## Load first, in this order

1. **`backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`** — governs how this plan
   moves through its lifecycle. Follow its execution protocol, output format
   (`skills/_shared/output_format.md`) and quality gate (`skills/_shared/quality_gate.md`).
2. **`backend/docs/architecture/under_construction/implementation/prompts/GUARDRAILS.md`**
3. **`backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_error_fidelity_20260727.md`**
   — your plan. It is self-contained.

## Task

Every Shopify mutation in the codebase funnels through `raise_for_graphql_user_errors`
(`services/infra/shopify/graphql_client.py:233-251`), which discards every message and raises one
opaque `graphql_user_errors` code. Operators learn *that* Shopify rejected something, never *what*.

Retain the field paths, safe messages and typed codes on the raised exception.

## The hard constraint

**This must be invisible to every existing caller.**

- `ShopifyGraphQLUserErrorsError` is a **subclass** of `ShopifyGraphQLNonRetryableError`, so both
  `except ShopifyGraphQLError` and `except ShopifyGraphQLNonRetryableError` still match.
- Default `error_code` stays `"graphql_user_errors"`.
- `_product_sync_orchestrator.py:140-143` and `_inventory_sync.py:150-156` behave identically.

**Do not modify any call site.** Consuming the new detail is a follow-up.

## Security

Copy only `field`, `message` (truncated to 300 chars) and `code`. **Never** retain the raw response
body or the request variables — the variables can carry customer PII. Assert this in a test.

Note: `code` exists only on typed errors (`InventorySetQuantitiesUserError`,
`CustomerSetUserError`). The plain `UserError` from `inventoryItemUpdate` / `inventoryActivate` has
**no** `code` field in `2026-01` — emit `None`.

## Scope boundary

- **Modify:** `app/beyo_manager/errors/external_service.py`,
  `app/beyo_manager/services/infra/shopify/graphql_client.py`
- **Extend:** `app/tests/unit/services/infra/shopify/test_graphql_client.py`
- Nothing else.

## Done signal

```
pytest app/tests/unit/services/infra/shopify/test_graphql_client.py -v
pytest app/tests -k shopify
pytest app/tests
```

The **full suite** is the real gate — this function sits on every Shopify mutation path.

## Lifecycle (per the skill)

1. Set the plan's `Status` to `implemented`, update `Last updated at`.
2. Write a summary to `backend/docs/architecture/implemented_summaries/`, trace-linked to this plan.
3. Report in the skill's output format: lifecycle state, next transition, document paths touched.

This ticket is self-contained, so it may proceed to `summarized` → `archived` on its own once the
summary is written.

## Report explicitly

- Confirmation that no call site was modified.
- The exact normalised shape produced for a plain `UserError` versus a typed one.
