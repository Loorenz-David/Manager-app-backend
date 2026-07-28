# ARCHIVE_RECORD_PLAN_shopify_product_sync_error_fidelity_20260727

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_shopify_product_sync_error_fidelity_20260727`
- Archived at (UTC): `2026-07-27T00:00:00Z`
- Archive owner agent: `claude-opus-5`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_product_sync_error_fidelity_20260727.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_product_sync_error_fidelity_20260727.md`
- Discovered while planning: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_product_20260727.md` (R6)
- Debug chain: `—`

## Outcome classification

- Result: `completed`
- Acceptance criteria: `ShopifyGraphQLUserErrorsError` added as a subclass of
  `ShopifyGraphQLNonRetryableError` carrying normalised `{field, message, code}` entries, with the
  default `error_code` unchanged and an optional override. No call site modified; the full Shopify
  suite remained green.

## What changed, and what deliberately did not

`raise_for_graphql_user_errors` sits on **every** Shopify mutation path in the codebase and
previously discarded every message, raising one opaque `graphql_user_errors` code. Operators
learned *that* Shopify rejected something, never *what*. Shopify returns field-level diagnostics
(`variants.0.price`, `metafields.2.value`); throwing them away is the difference between a fixable
error and a support ticket.

The change is invisible to existing callers by construction: subclassing keeps every
`except ShopifyGraphQLError` and `except ShopifyGraphQLNonRetryableError` matching, and the default
error code is unchanged. Consuming the new detail is a follow-up, not part of this ticket.

Only `field`, `message` (truncated to 300 characters) and `code` are retained — never the raw
response body and never the request variables, which can carry customer PII. `code` is populated
only for typed errors; the plain `UserError` returned by `inventoryItemUpdate` / `inventoryActivate`
has no `code` field in API `2026-01`.

## Why it was extracted

It surfaced while planning the pre-order feature but has nothing to do with it — it improves every
existing Shopify code path and was worth doing on its own merits.

No intention plan exists for this delivery, so the skill's step 10 does not apply.
