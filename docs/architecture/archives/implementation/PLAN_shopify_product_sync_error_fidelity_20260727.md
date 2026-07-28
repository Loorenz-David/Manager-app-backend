# PLAN_shopify_product_sync_error_fidelity_20260727

## Metadata

- Plan ID: `PLAN_shopify_product_sync_error_fidelity_20260727`
- Status: `archived`
- Type: **standalone improvement** — independent of the pre-order delivery
- Related plan: `PLAN_shopify_preorder_product_20260727.md` (rev 8, research finding **R6**)
- Depends on: nothing
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T00:00:00Z`
- Last updated at (UTC): `2026-07-27T21:00:00Z`

## Why this exists on its own merits

Every Shopify mutation in the codebase funnels through `raise_for_graphql_user_errors`
(`services/infra/shopify/graphql_client.py:233-251`), which discards every message and raises one
opaque `graphql_user_errors` code. So a failed product sync — or a failed inventory adjustment,
or a failed webhook subscription — tells the operator *that* Shopify rejected something, never
*what*.

Shopify returns field-level diagnostics (`variants.0.price`, `metafields.2.value`). Throwing them
away is the difference between a fixable error and a support ticket.

This was surfaced while planning pre-orders but has nothing to do with them. It improves every
existing Shopify code path.

## Goal and intent

- Goal: retain `userErrors` field paths, safe messages and typed codes on the raised exception.
- Non-goals: no change to error classification (retryable vs non-retryable), no change to
  transport behaviour, and **no change to what any existing caller observes**.

## The hard constraint

**This change must be invisible to existing callers.**

- `ShopifyGraphQLUserErrorsError` is a **subclass** of `ShopifyGraphQLNonRetryableError`, so both
  `except ShopifyGraphQLError` and `except ShopifyGraphQLNonRetryableError` still match.
- The default `error_code` stays `"graphql_user_errors"`.
- `services/tasks/shopify/_product_sync_orchestrator.py:140-143` and
  `services/tasks/shopify/_inventory_sync.py:150-156` behave identically afterwards.

Do not modify any call site. Consuming the new detail is a follow-up.

## Security

Copy only `field`, `message` (truncated to 300 chars) and `code`. **Never** retain the raw
response body or the request variables — the variables can carry customer PII. Assert it in a test.

## Contracts to load

- `backend/architecture/05_errors.md` — typed domain errors, `http_status`.
- `backend/architecture/18_security.md` — no-secret serialization.
- `backend/architecture/19_integrations.md` — adapter boundary.

## Files

### Modify

| Path | Change |
|---|---|
| `app/beyo_manager/errors/external_service.py` | add `ShopifyGraphQLUserErrorsError(ShopifyGraphQLNonRetryableError)` carrying `user_errors: tuple[dict, ...]` |
| `app/beyo_manager/services/infra/shopify/graphql_client.py` | `raise_for_graphql_user_errors` raises the subclass; optional `error_code=` override |

## Implementation

```python
class ShopifyGraphQLUserErrorsError(ShopifyGraphQLNonRetryableError):
    def __init__(self, message="…", *, error_code="graphql_user_errors",
                 user_errors: tuple[dict, ...] = ()) -> None:
        super().__init__(message, error_code=error_code)
        self.user_errors = user_errors
```

Normalise each entry to `{"field": list[str] | None, "message": str[:300], "code": str | None}`.

- `field` is a list of strings in Shopify's payloads — keep as-is or `None`.
- `code` exists only on typed errors (`InventorySetQuantitiesUserError`, `CustomerSetUserError`).
  The plain `UserError` returned by `inventoryItemUpdate` / `inventoryActivate` has **no** `code`
  field in `2026-01` — emit `None`.

Add `error_code: str = "graphql_user_errors"` as a parameter so callers can attach specific codes
later. Keep the existing `logger.warning` and its fields.

## Test contract

`app/tests/unit/services/infra/shopify/test_graphql_client.py` (extend):

- the raised exception is an instance of `ShopifyGraphQLError`, `ShopifyGraphQLNonRetryableError`
  **and** the new class
- `error_code == "graphql_user_errors"` with no override; the override is honoured when passed
- `user_errors` retains `field` and `message` per entry
- `code` is `None` for a plain `UserError`, populated for a typed one
- a message over 300 chars is truncated
- `user_errors` contains **nothing** beyond `field` / `message` / `code`
- empty or `None` `user_errors` returns without raising

## Done signal

```
pytest app/tests/unit/services/infra/shopify/test_graphql_client.py -v
pytest app/tests -k shopify
pytest app/tests
```

The **full suite** is the real gate — this function sits on every Shopify mutation path.

## Risks and mitigations

- Risk: an existing `except` clause stops matching.
  Mitigation: subclassing, plus the full-suite gate.
- Risk: PII leaks into `user_errors`.
  Mitigation: only three fields are copied; asserted by test.

## Lifecycle transition

- Current state: `implemented`
- Next state: `summarized` → `archived` after the full-suite gate is green
- Transition owner: `codex`
