# SUMMARY_PLAN_shopify_product_sync_error_fidelity_20260727

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_product_sync_error_fidelity_20260727`
- Status: `implemented`
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T19:27:27Z`
- Source plan:
  `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_error_fidelity_20260727.md`

## What was implemented

- Added `ShopifyGraphQLUserErrorsError` as a subclass of
  `ShopifyGraphQLNonRetryableError`.
- Preserved the generic exception message, `retryable = False`, and default
  `error_code = "graphql_user_errors"`.
- Added an optional `error_code` override to
  `raise_for_graphql_user_errors`.
- Normalized mutation `userErrors` into an immutable tuple containing only
  `field`, a message truncated to 300 characters, and `code`.
- Retained no raw response body, request variables, extensions, or other
  provider fields.

## Exact normalized shapes

Plain Shopify `UserError`:

```python
{
    "field": ["inventoryItem", "tracked"],
    "message": "Inventory item cannot be updated.",
    "code": None,
}
```

Typed Shopify user error:

```python
{
    "field": ["quantities", "0", "quantity"],
    "message": "<safe Shopify message, truncated to 300 characters>",
    "code": "INVALID_QUANTITY",
}
```

## Compatibility and security evidence

- The raised object remains an instance of `ShopifyGraphQLError` and
  `ShopifyGraphQLNonRetryableError`.
- Existing default classification and error code are unchanged.
- Empty and `None` user-error collections still return without raising.
- No call site was modified. Existing callers in `product_sync_client.py` and
  `webhook_subscription_client.py` continue to call the helper unchanged.
- Tests inject raw-response and request-variable secrets into source entries
  and verify neither appears in retained exception detail.

## Files changed

- `app/beyo_manager/errors/external_service.py`
- `app/beyo_manager/services/infra/shopify/graphql_client.py`
- `app/tests/unit/services/infra/shopify/test_graphql_client.py`
- `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_error_fidelity_20260727.md`
- `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_product_sync_error_fidelity_20260727.md`

## Validation evidence

- Focused GraphQL client suite: **14 passed**.
- Scoped Ruff check: **passed**.
- `git diff --check`: **passed**.
- Shopify-filtered suite: **371 passed, 8 failed, 720 deselected**.
- Full suite: **1069 passed, 30 failed, 2 warnings**.

## Known validation debt

- The required Shopify-filtered and full suites are not green due to existing
  dirty-worktree and persistent-test-state failures outside this plan's strict
  three-file code scope.
- The Shopify failures include four product-sync characterisation fixtures
  missing a newly required `inventory_mode`, two legacy dimension assertions,
  one product-processing result-shape mismatch, and one repeated fixed-ID
  collision.
- No failing test exercises the new exception subclass, normalization, or
  sanitization behavior.

## Lifecycle transition

- Current state: `implemented`
- Next transition: `summarized` after the full-suite gate is green, then
  `archived`
- Archive: not performed because the real validation gate is red
