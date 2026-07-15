# SUMMARY_PLAN_shopify_inventory_increments_20260715

## Metadata

- Summary ID: `SUMMARY_PLAN_shopify_inventory_increments_20260715`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-15T06:39:10Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_inventory_increments_20260715.md`

## What was implemented

- Added request validation and per-shop normalization for positive, shop-tagged inventory increments. Zero values are dropped, negative values and malformed Shopify GIDs are rejected, and duplicate shop/location rows are rejected.
- Added additive persistence for Shopify inventory item IDs and per-item inventory outcomes.
- Added the durable `shopify_inventory_adjustments` ledger with a unique idempotency key on `(shop_integration_id, frontend_client_id, shopify_location_id)`, pending/applied/failed states, baseline reconciliation, and stable mutation idempotency keys.
- Added Shopify inventory infrastructure operations for live locations, inventory-item state, tracking enablement, inactive-location activation at zero, and batched additive adjustments.
- Wired product sync ordering so product and variant IDs are persisted before inventory processing, and inventory processing completes before metafields. Partial per-location results are serialized while the sync item uses the existing `FAILED` state for inventory failure.
- Added the workspace-scoped `GET /api/v1/integrations/shopify/locations` route with `ok`, `needs_reauth`, and `error` shop results, including inactive locations.
- Added the `read_locations` and `write_inventory` scope configuration and execution-time missing-scope handling.
- Added frontend Zod contracts, locations query/API hook, inventory location/quantity field, staged-form integration, per-shop submit splitting, and legacy draft compatibility for missing `inventoryAdjustments`.
- Updated the frontend handoff and the living Shopify architecture document.

## Resolved implementation decisions

- Shopify API version is pinned to `2026-01`; the implemented GraphQL inventory operations match that contract.
- Inventory idempotency uses the durable database ledger plus Shopify mutation idempotency keys and baseline reconciliation.
- Inventory outcomes remain item-level JSON plus structured worker errors; no new integration-event enum value was added.
- Partial inventory outcomes use the existing `FAILED` item state with per-location result entries.
- Inventory writes inherit the existing product-sync route roles: `ADMIN`, `MANAGER`, `SELLER`, and `WORKER`.

## Validation evidence

- Focused backend Shopify tests: `16 passed`.
- Broader Shopify unit slice: `166 passed, 2 failed`; the failures are existing dimension-migration expectations for `extensions_quantity: "0"` and are outside this change.
- Shopify schema integration tests: `8 passed`.
- Product-sync integration tests plus Shopify foundation constraints: `10 passed` before the additional ledger test; the foundation suite is now `8 passed` with the ledger uniqueness test included.
- Frontend Shopify tests: `33 files, 93 tests passed`.
- Frontend TypeScript check: passed.
- Ruff checks and Python compilation for changed backend code: passed.
- Alembic applied the new migration through head `c5d6e7f8a9b0`. The post-upgrade `alembic check` still reports pre-existing drift in `email_sync_states` and `workspace_roles`, unrelated to this migration.

## Known gaps or deferred items

- No live Shopify merchant mutation was performed in this implementation pass; GraphQL behavior is covered by mocked infra-client tests and the configured API version was verified during Phase 0.
- The broader unit-suite dimension failures remain for their existing owner to resolve.
- Existing unrelated worktree changes were preserved.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_shopify_inventory_increments_20260715.md`
