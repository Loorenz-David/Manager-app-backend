# INTENTION_shopify_customer_lookup_by_product_identity_20260709

## Metadata

- Intention ID: `INTENTION_shopify_customer_lookup_by_product_identity_20260709`
- Status: `achieved`
- Owner: `David`
- Created at (UTC): `2026-07-09T00:00:00Z`
- Last updated at (UTC): `2026-07-09T11:50:47Z`

## Goal

Let a workspace user look up the customer(s) behind a physical product — identified by SKU and/or barcode (`article_number`) scanned or typed on the shop floor — across every Shopify shop connected to the workspace, without leaving ManagerBeyo.

## Why this matters

Field/seller staff handling a returned or misplaced item often only have the product's barcode or SKU, not an order number or customer name. Today there is no backend capability that turns "this SKU/barcode" into "this is the customer and address it shipped to" using the Shopify data ManagerBeyo already has OAuth access to. This is the first Shopify capability built on top of the existing OAuth/webhook integration (`57_shopify_integration.md`) that actually reads Shopify's commerce data (orders/products) rather than managing the integration itself — it establishes the pattern for future Shopify data-lookup features.

## Success criteria

1. `POST /api/v1/integrations/shopify/customers/by-product-identity` accepts `{"sku": "...", "article_number": "..."}` (either optional, at least one required) and returns normalized customer matches from every active Shopify shop integration in the caller's workspace.
2. SKU is preferred over barcode; barcode (`article_number`) is only used as a fallback per shop when SKU yields no match for that shop, or when only `article_number` was supplied.
3. Matching is exact (post-filtered in application code even though Shopify's search index may fuzzy-match), and every returned object identifies its source shop and whether it matched via `sku` or `barcode`.
4. One shop's Shopify API failure does not prevent other shops' results from being returned; only a total failure across every queried shop surfaces as an error to the caller.
5. No Shopify access token, raw GraphQL payload, or other secret ever appears in the response.
6. ADMIN, MANAGER, and SELLER can call the route; SELLER did not previously have access to any Shopify route and must be added to the router's imports.

## Scope boundary

- In scope:
  - One new query capability (read-only), one new router route, one new low-level Shopify GraphQL infra function, and one new domain normalization/matching module.
  - Adding `SELLER` to `routers/api_v1/shopify.py`'s role imports (first Shopify route any non-admin/manager role can call).
- Out of scope (this cycle):
  - Persisting or caching lookup results.
  - Background/async processing — this is a synchronous, request-time, bounded lookup.
  - Order status, fulfillment/shipping status, or order history beyond the single matched order.
  - Batch lookup of multiple product identities in one call.
  - Limiting the lookup to a single shop (always fans out to every active shop in the workspace, for now).
  - Any change to the OAuth, webhook intake, or webhook subscription sync flows.
- Non-goals:
  - Building a general-purpose Shopify Admin GraphQL abstraction layer — only the two queries this feature needs.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_shopify_customer_lookup_by_product_identity_20260709` | `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_by_product_identity_20260709.md` | `archived` (implemented) | Full router/query/infra/domain implementation of this lookup capability |
| `PLAN_shopify_customer_lookup_corrections_20260709` | `backend/docs/architecture/archives/implementation/PLAN_shopify_customer_lookup_corrections_20260709.md` | `archived` | Corrective follow-up: missing workspace-isolation integration test, a null-token per-shop-isolation fix, a router-test instruction fix, and the frontend handoff doc update — all found in a post-implementation review of the plan above |

## Progress notes

- `2026-07-09`: Intention drafted; implementation plan drafted in the same session after reading the existing Shopify integration code (`57_shopify_integration.md`, `routers/api_v1/shopify.py`, `services/queries/shopify/*`, `services/infra/shopify/*`, `domain/shopify/*`) directly.
- `2026-07-09`: `PLAN_shopify_customer_lookup_by_product_identity_20260709` implemented and archived (see its own summary). A post-implementation review then found four gaps: the plan's mandated Postgres-backed integration test for workspace isolation/soft-delete/active-status filtering was never written (only a fake-session unit test that bypasses the real SQL filter exists); a missing/blank `access_token_encrypted` on an `ACTIVE` shop could break per-shop failure isolation; a router test was patched in a way that contradicted the parent plan's own explicit instruction; and the frontend handoff doc was never updated with the new route, per `57_shopify_integration.md`'s explicit requirement. `PLAN_shopify_customer_lookup_corrections_20260709` was drafted the same day to close all four.
- `2026-07-09`: `PLAN_shopify_customer_lookup_corrections_20260709` implemented and archived. The corrective pass added the missing DB-backed workspace-isolation/soft-delete/active-status integration test, fixed the missing-access-token precondition so tokenless shops are skipped safely instead of queried, restored the router role-gating test structure to match the parent plan's original instruction, and updated the Shopify frontend handoff with the new lookup route contract.

## Open questions

- None blocking. Whether to eventually support single-shop-scoped lookup, batch identities, or order-status filtering is deferred to a future intention cycle if the frontend asks for it.

## Lifecycle transition

- Current status: `achieved`
- Next status: `—`
- Transition trigger: `Achieved` — both linked implementation plans are implemented and archived.
