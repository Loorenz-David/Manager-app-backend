# INTENTION_shopify_product_sync_20260709

## Metadata

- Intention ID: `INTENTION_shopify_product_sync_20260709`
- Status: `active`
- Owner: `David`
- Created at (UTC): `2026-07-09T00:00:00Z`
- Last updated at (UTC): `2026-07-09T00:00:00Z`

## Goal

Let a workspace user submit one or more products/items to be created or updated in one or more connected Shopify shops in a single batched, background-processed call, with per-item/per-shop status tracking the frontend can follow to completion.

## Why this matters

Today the Shopify integration (`57_shopify_integration.md`) only manages the shop connection itself (OAuth link, webhook subscriptions) and one read-only lookup (`lookup_shopify_customers_by_product_identity`). There is no capability that actually writes commerce data into Shopify. Workspaces need to push their catalog (title, description, price, SKU/barcode, tags, category, metafields) into one or more linked Shopify shops without leaving ManagerBeyo, and without blocking the request on Shopify's API latency — product creation/update, image upload, and metafield sync can each take multiple seconds per item, and a workspace may submit many items at once.

## Success criteria

1. `POST /api/v1/integrations/shopify/products/process` accepts a batch of items (each with identity fields `sku`/`item_article_number`, target shop(s), and product fields) and returns a fast "queued" response — it never calls Shopify's API synchronously in the request path.
2. The actual create-or-update work runs on the existing `queue:shopify` worker (`workers/shopify_worker.py`), reusing the existing `ExecutionTask`/`execute_shopify_graphql` infrastructure — no new queue, no new worker process, no new HTTP client.
3. For each (item, shop) pair, the system looks up whether a matching Shopify product/variant already exists (by SKU, falling back to barcode) and creates or updates accordingly — never blindly creating a duplicate for an item that already exists in that shop.
4. Every (item, shop) operation has a durable, queryable status row (pending -> processing -> succeeded/failed) so the frontend can track a batch's progress without polling Shopify directly.
5. One item's or one shop's failure does not abort the rest of the batch — partial success is the normal case, not an error state.
6. No Shopify access token or other secret ever appears in a response, a DB-tracking row's readable fields, or a socket payload.
7. Only shops actually connected to the caller's workspace can ever be targeted — a caller cannot address an arbitrary shop domain or another workspace's shop.

## Scope boundary

- In scope:
  - Batched create-or-update of single-variant products (one SKU per item) across one or more connected shops.
  - Product-level fields (title, description, status, tags, category/productType), the item's single variant (SKU, barcode, price, weight), and metafields (default namespace).
  - A new DB table tracking per-(item, shop) sync status, a new Shopify task type/payload, a new worker handler, a new admin route, and one new integration-event type.
  - One socket event per completed batch summarizing succeeded/failed operations.
- Out of scope (this cycle):
  - Product images/media upload — explicitly deferred; core product create/update must not depend on image handling landing first.
  - Multi-variant products / product options (color, size, etc.) — the identity model here is one SKU per item, matching the existing `customer_lookup.py` identity semantics.
  - Shopify's structured category taxonomy (`TaxonomyCategory`) — category maps to the legacy `productType` string field only.
  - Deleting/archiving Shopify products.
  - Any change to OAuth, webhook intake, or webhook subscription sync.
- Non-goals:
  - A general-purpose Shopify product GraphQL abstraction beyond what this feature needs.
  - Building a generic "sync any ManagerBeyo domain entity to Shopify" framework — this operates on the request payload as given, not on an internal Item/Upholstery catalog.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_shopify_product_sync_20260709` | `backend/docs/architecture/under_construction/implementation/PLAN_shopify_product_sync_20260709.md` | `under_construction` | Full DB/domain/infra/command/task/router/socket implementation of this capability |

## Progress notes

- `2026-07-09`: Intention drafted from a detailed user-authored capability spec; implementation plan drafted in the same session after reading `57_shopify_integration.md` and the full existing Shopify router/worker/infra/domain/command/query code, the async-execution and router contracts, and the current Alembic migration head.

## Open questions

- Whether the already-added-but-unused `WorkingSection.allows_shopify_product_modifications` flag should gate this capability. See the linked plan's "Clarifications required" — recommendation is to leave it unused for this cycle (role-based gating only) pending confirmation.
- Exact Shopify Admin GraphQL mutation field names for the configured API version must be verified against the live schema before the mutation-writing implementation step — see the linked plan.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: Linked implementation plan is implemented and archived, and both open questions above are resolved.
