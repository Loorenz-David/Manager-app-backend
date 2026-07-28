# SUMMARY_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_preorder_phase_1_minimum_delivery_20260727`
- Status: `implemented`
- Owner agent: `codex`
- Created at (UTC): `2026-07-27T18:55:17Z`
- Source plan:
  `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
- Parent plan:
  `backend/docs/architecture/under_construction/implementation/PLAN_shopify_preorder_product_20260727.md`

## What was implemented

- Added unsigned public storage URLs with `STORAGE_PUBLIC_BASE_URL` support for
  local and S3 storage clients.
- Added optional Shopify product media to create/update while preserving the
  exact no-media GraphQL documents.
- Added `image_id`, `image_url`, and alt-text flow through the HTTP boundary,
  command request, normalized payload, worker-time resolver, and Shopify media
  result audit columns.
- Added command-time local-image validation for the 20 MB, 25 MP, and
  5000-pixel dimension limits.
- Added the `add`/`set` inventory discriminator and an idempotent absolute
  `inventorySetQuantities` path with shop-owned active-location validation,
  explicit `changeFromQuantity: null`, and `before_available` audit values.
- Added the subordinate pre-order product-sync enqueue inside `create_task`'s
  existing transaction, including task-type and role gates. Shopify GraphQL is
  executed only later by the worker.
- Added pre-order completion events and the additive migrations for one enum,
  three sync-item columns, and the pre-order integration event enum value.

## Contract and guardrail evidence

- `create_task` has no call or dependency on `execute_shopify_graphql`; an
  integration test also asserts zero Shopify HTTP calls during task creation.
- The characterization net proves a no-image, `add`-mode sync emits unchanged
  create, update, metafield, and additive inventory GraphQL.
- `inventory_mode` appears in no request or router body model. It is assigned
  only by the internal pre-order helper.
- `SHOPIFY_APP_SCOPES` is unchanged; no merchant reauthorization is required.
- The regression fixture keeps `custom.quantity = "6"` separate from absolute
  inventory quantity `2`, records `before_available = 5`, and preserves the
  caller's price string exactly.
- No merchant-specific literal was added under `domain/` or `services/infra/`.

## Validation evidence

- Required migration round-trip:
  `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`:
  **passed**. An additional two-revision downgrade/upgrade also passed.
- Storage, Shopify infrastructure, Shopify task, Shopify command, pre-order
  request, task integration, and focused router tests: **125 passed**.
- Product-sync characterization plus the absolute-inventory regression:
  **6 passed**.
- Scoped Ruff checks and `git diff --check`: **passed**.
- Full suite: **1054 passed, 31 failed, 2 warnings**. None of the failures
  exercise the new pre-order path. The failures are existing repository
  mismatches, including missing seeded reference data in integration tests,
  unrelated serializers/services, and six Shopify router role-policy
  assertions that conflict with the routes' current worker/seller policy.

## Known gaps and deferred verification

- The repository-wide suite is not green because of the 31 unrelated failures
  recorded above; this remains explicit validation debt rather than being
  broadened into this feature.
- A human must run the dev-store checklist before shipment: verify `UNLISTED`,
  exact SKU/price/metafields/image, selected-location availability, Zettle
  visibility, and storefront absence including search, collections, sitemap,
  and `resourcePublications`.
- The plan is intentionally not archived.

## Lifecycle transition

- Current state: `implemented`
- Next transition: human dev-store verification, then lifecycle review for
  `summarized` and eventual `archived`
- Archive target plan:
  `backend/docs/architecture/archives/implementation/PLAN_shopify_preorder_phase_1_minimum_delivery_20260727.md`
