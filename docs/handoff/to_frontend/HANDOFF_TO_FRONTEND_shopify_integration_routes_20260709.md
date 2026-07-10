# HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709`
- Created at (UTC): `2026-07-09T19:00:00Z`
- Owner agent: `Claude`
- Source plan (master): `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Source plans (children, all archived): `PLAN_shopify_foundation_schema_config_20260707.md`, `PLAN_shopify_oauth_linking_20260707.md`, `PLAN_shopify_webhook_registry_sync_20260707.md`, `PLAN_shopify_webhook_intake_execution_20260708.md`, `PLAN_shopify_worker_execution_20260708.md`, `PLAN_shopify_admin_routes_serializers_20260709.md`, `PLAN_shopify_webhook_history_records_20260709.md`, `PLAN_shopify_deployment_validation_20260709.md`, `PLAN_shopify_customer_lookup_by_product_identity_20260709.md`, `PLAN_shopify_customer_lookup_corrections_20260709.md`
- Source summaries: `backend/docs/architecture/implemented_summaries/SUMMARY_shopify_admin_routes_serializers_20260709.md`, `SUMMARY_shopify_webhook_history_records_20260709.md`, `SUMMARY_shopify_deployment_validation_20260709.md`, `SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709.md`, `SUMMARY_PLAN_shopify_customer_lookup_corrections_20260709.md`
- Router files documented: `app/beyo_manager/routers/api_v1/shopify.py`, `app/beyo_manager/routers/api_v1/shopify_webhooks.py`

## Backend delivery context

- What backend implemented: The full Shopify integration backend — OAuth install/link flow, webhook registry sync, webhook intake + async processing via a dedicated worker/queue, admin routes for managing linked shops, and a webhook/event history endpoint. All 7 phases are implemented, tested, and deployed (systemd worker registered in `deploy.yml`).
- API or contract changes: This is the first frontend-facing documentation of these routes — nothing existed here before. All routes below are new.
- Feature flags/toggles: None. The routes are always registered; whether Shopify actually functions depends on whether the backend operator has configured the 10 Shopify/encryption env vars (see "Operational prerequisites" below). If they are unset, `install-url` and OAuth will fail at runtime, but the routes themselves are always reachable and return normal error responses (not 404s).

## Overview — read this before wiring anything up

### Base paths

- Admin/management routes (JWT-protected): prefix `/api/v1/integrations/shopify`.
- Inbound Shopify-facing routes (no ManagerBeyo JWT — called by Shopify itself, not the frontend): prefix `/api/v1/shopify`. The frontend does not call these directly; they're documented here for completeness only.

### Response envelope

Every route that goes through `run_service` (i.e. every route except role/JWT rejections and the OAuth callback's redirect) returns one of two shapes:

**Success** (HTTP 200):
```json
{ "data": { ... }, "ok": true, "warnings": [] }
```
The frontend should read the actual payload from `data`, never from the top level.

**Domain-level failure** (HTTP status varies — see each route's error table):
```json
{ "error": "Human-readable message.", "ok": false }
```

**Auth failure (401/403)** — these come from FastAPI's JWT dependency, not `run_service`, so the shape is different — no `ok` field at all:
```json
{ "detail": "Insufficient role permissions." }
```
`401` = missing/invalid/expired/revoked JWT. `403` = valid JWT, wrong role.

**Request-shape validation failure (422, before any route code runs)** — if the JSON body doesn't even match the route's Pydantic model (e.g. `shop_domain` sent as a number instead of a string), FastAPI's own validation kicks in before `run_service`, returning its default `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` shape. This is different from a domain-level 422 (see above) where the body's JSON *shape* was fine but a business rule failed (e.g. blank `shop_domain`) — those go through `run_service` and use the `{"error": ..., "ok": false}` shape instead. In practice: malformed JSON types → FastAPI shape; empty-string/business-rule failures → domain shape. Treat both as "422 = fix your request" but don't assume one specific body shape when parsing 422s defensively.

### Roles

Role values (JWT `role_name` claim): `admin`, `manager`, `worker`, `seller`. Every admin/management route below requires either `admin`+`manager`, or `admin` only — see each route.

### Response field conventions

- All timestamps are ISO-8601 strings (`datetime.isoformat()`), or `null` if not set — never omitted.
- `shop_domain` is always the normalized form (lowercase, `.myshopify.com` suffix), regardless of what the frontend submits.
- No route response ever includes `access_token_encrypted`, raw OAuth codes, HMAC signatures, or raw webhook payloads. See "No-secret guarantee" at the end of this document.

### Operational prerequisites (informational — not frontend's responsibility, but explains failure modes)

`SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, `SHOPIFY_APP_SCOPES`, `SHOPIFY_REDIRECT_URI`, `SHOPIFY_API_VERSION`, `SHOPIFY_WEBHOOK_BASE_URL`, `SHOPIFY_WEBHOOK_SECRET`, `SHOPIFY_OAUTH_REDIRECT_URL`, `FIELD_ENCRYPTION_KEY` must be set on the backend for the flow to work end-to-end. None of these gate whether the routes exist — they gate whether Shopify's own APIs accept the requests the backend sends them.

---

## Route 1 — Create Shopify install URL

`POST /api/v1/integrations/shopify/install-url`

Starts the OAuth install/link flow for a new (or re-authorizing) Shopify shop. The frontend should redirect the user's browser to the returned `install_url`.

- **Auth:** JWT required. Roles: `admin`, `manager`.

**Request body:**
```json
{
  "shop_domain": "my-shop.myshopify.com",
  "redirect_after_success": null
}
```
- `shop_domain` (string, required): any reasonable form of the shop's domain; the backend normalizes it (lowercases, ensures `.myshopify.com`). Blank/whitespace-only is rejected.
- `redirect_after_success` (string, optional): **must currently be `null`, omitted, or the literal string `"default"`.** Any other value is rejected — there is no support yet for custom post-OAuth redirect targets beyond the one configured value (`SHOPIFY_OAUTH_REDIRECT_URL`).

**Success response `data`:**
```json
{
  "install_url": "https://my-shop.myshopify.com/admin/oauth/authorize?client_id=...&scope=...&redirect_uri=...&state=...",
  "shop_domain": "my-shop.myshopify.com",
  "expires_at": "2026-07-09T19:10:00+00:00"
}
```
`expires_at` is when the underlying OAuth state expires (10 minutes from creation) — if the user doesn't complete the Shopify consent screen by then, they'll need to request a new install URL.

**Errors:**
| Status | Body | Cause |
|---|---|---|
| 422 | `{"error": "shop_domain: shop_domain is required.", "ok": false}` | Blank `shop_domain` |
| 422 | `{"error": "redirect_after_success: redirect_after_success must be 'default' when provided.", "ok": false}` | Anything other than `null`/`"default"` |
| 401/403 | FastAPI `detail` shape | Missing/invalid JWT or wrong role |

---

## Route 2 — List linked shops

`GET /api/v1/integrations/shopify/shops`

- **Auth:** JWT required. Roles: `admin`, `manager`. Workspace-scoped (only shows shops linked to the caller's workspace).

**Query params:**
- `limit` (optional, default `50`, min `0`, max `200`)
- `offset` (optional, default `0`)

**Success response `data`:**
```json
{
  "shops": [
    {
      "client_id": "shpint_01ABC...",
      "workspace_id": "ws_...",
      "shop_domain": "my-shop.myshopify.com",
      "shop_name": null,
      "provider": "shopify",
      "status": "active",
      "access_token_expires_at": null,
      "granted_scopes": ["read_orders", "read_products"],
      "requested_scopes": ["read_orders", "read_products"],
      "api_version": "2026-01",
      "installed_at": "2026-07-01T10:00:00+00:00",
      "uninstalled_at": null,
      "last_connected_at": "2026-07-01T10:00:00+00:00",
      "last_health_check_at": null,
      "last_health_check_status": null,
      "last_error_code": null,
      "last_error_message": null,
      "scopes_status": "up_to_date",
      "webhooks_status": "synced",
      "created_by": {
        "client_id": "usr_...",
        "username": "alice",
        "profile_picture": null
      },
      "updated_by": {
        "client_id": "usr_...",
        "username": "alice",
        "profile_picture": null
      },
      "created_at": "2026-07-01T10:00:00+00:00",
      "updated_at": "2026-07-01T10:00:00+00:00",
      "is_deleted": false
    }
  ],
  "shops_pagination": { "limit": 50, "offset": 0, "has_more": false }
}
```

**Field notes:**
- `status`: one of `pending_install`, `active`, `needs_reauth`, `scopes_outdated`, `webhooks_outdated`, `disabled`, `uninstalled`, `error`.
- `scopes_status`: `"outdated"` if `status` is `scopes_outdated`/`needs_reauth`, else `"up_to_date"`. Use this (not `status`) to decide whether to show a "reauthorize" call-to-action.
- `created_by` / `updated_by`: compact user references with exactly `client_id`, `username`, and `profile_picture`, or `null` when the provenance user is unknown.
- `webhooks_status`: `"has_failures"` (any subscription failed — show a warning), `"needs_sync"` (an enabled/scope-covered topic isn't installed/active yet — show a "sync webhooks" action), or `"synced"`.
- No `access_token_encrypted` field exists in this shape — it is never serialized.

**Errors:** 401/403 only (no request-shape validation on this route).

---

## Route 3 — Get one shop's detail

`GET /api/v1/integrations/shopify/shops/{shop_integration_id}`

- **Auth:** JWT required. Roles: `admin`, `manager`. Workspace-scoped.

**Success response `data`:**
```json
{
  "shop_integration": { /* same shape as one item in Route 2's "shops" array */ },
  "webhook_subscription_summary": {
    "total": 5, "active": 4, "failed": 0, "pending": 1, "disabled": 0, "removed": 0
  },
  "webhook_subscriptions": [
    {
      "client_id": "shpwsub_...",
      "workspace_id": "ws_...",
      "shop_integration_id": "shpint_...",
      "topic": "orders/create",
      "callback_url": "https://api.managerbeyo.com/api/v1/shopify/webhooks",
      "remote_subscription_id": "gid://shopify/WebhookSubscription/123",
      "payload_format": "json",
      "required_scopes": ["read_orders"],
      "status": "active",
      "installed_at": "2026-07-01T10:00:05+00:00",
      "last_verified_at": "2026-07-01T10:00:05+00:00",
      "last_install_attempt_at": "2026-07-01T10:00:05+00:00",
      "last_error_code": null,
      "last_error_message": null,
      "created_at": "2026-07-01T10:00:05+00:00",
      "updated_at": "2026-07-01T10:00:05+00:00"
    }
  ]
}
```
`webhook_subscriptions[].status`: one of `pending`, `active`, `failed`, `disabled`, `removed`.

**Errors:**
| Status | Cause |
|---|---|
| 404 `{"error": "Shopify shop integration not found.", "ok": false}` | Wrong ID, wrong workspace, or soft-deleted |
| 401/403 | Auth |

---

## Route 4 — Create a reauthorize URL for an existing shop

`POST /api/v1/integrations/shopify/shops/{shop_integration_id}/reauthorize-url`

Same purpose as install-url, but for a shop that's already linked and needs re-consent (e.g. `scopes_status: "outdated"`). No request body — the shop's existing `shop_domain` is looked up server-side.

- **Auth:** JWT required. Roles: `admin`, `manager`. Workspace-scoped.

**Success response `data`:** identical shape to Route 1 (`install_url`, `shop_domain`, `expires_at`).

**Errors:**
| Status | Cause |
|---|---|
| 404 `{"error": "Shopify shop integration not found.", "ok": false}` | Wrong ID, wrong workspace, or soft-deleted |
| 401/403 | Auth |

---

## Route 5 — Disconnect a shop

`DELETE /api/v1/integrations/shopify/shops/{shop_integration_id}`

Disables the integration (does **not** hard-delete the row — it stays visible in the shop list with `status: "disabled"`), clears the stored access token, and enqueues a background task to remove the shop's webhook subscriptions from Shopify's side.

- **Auth:** JWT required. Role: `admin` **only** (manager cannot disconnect).

**Success response `data`:**
```json
{
  "shop_integration_id": "shpint_...",
  "shop_domain": "my-shop.myshopify.com",
  "status": "disabled",
  "uninstalled_at": "2026-07-09T19:05:00+00:00",
  "remove_webhooks_task_id": "task_shopify_..."
}
```
The frontend should treat this as terminal for that shop card — re-showing it requires the user to go through install-url again (it will create a fresh, distinct row if the domain is re-linked later, since the old row keeps its `disabled` history).

**Errors:**
| Status | Cause |
|---|---|
| 404 `{"error": "Shopify shop integration not found.", "ok": false}` | Wrong ID, wrong workspace, or already soft-deleted |
| 401/403 | Auth (including a `manager` token — this route is admin-only) |

---

## Route 6 — Manually re-sync webhooks for one shop

`POST /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/sync`

Enqueues an async task that reconciles the shop's Shopify webhook subscriptions against the desired registry (installs missing/enabled topics, does not remove anything). Use this as the action behind a `webhooks_status: "needs_sync"` or `"has_failures"` call-to-action.

- **Auth:** JWT required. Role: `admin` **only**.

**Success response `data`:**
```json
{
  "shop_integration_id": "shpint_...",
  "shop_domain": "my-shop.myshopify.com",
  "sync_status": "pending",
  "sync_webhooks_task_id": "task_shopify_..."
}
```
This is fire-and-forget from the frontend's perspective — there's no synchronous "sync complete" response. Poll Route 2/3 afterward (webhook subscription statuses update once the worker finishes) or poll Route 7 (webhook history) to see the resulting `webhook_sync` event.

**Errors:** same 404/401/403 pattern as Route 5.

---

## Route 7 — Webhook + event history for one shop

`GET /api/v1/integrations/shopify/shops/{shop_integration_id}/webhooks/history`

A merged, newest-first feed of webhook deliveries (`ShopifyWebhookIntake` rows) and Shopify-lifecycle events (`ShopifyIntegrationEvent` rows, filtered to webhook-relevant types only — see below) for one shop. Good for an activity/audit log panel on a shop's detail page.

- **Auth:** JWT required. Roles: `admin`, `manager`. Workspace-scoped.

**Query params:**
- `limit` (optional, default `10`, min `1`, max `200`)
- `offset` (optional, default `0`)

**Success response `data`:**
```json
{
  "webhook_history_records": [
    {
      "record_type": "webhook_intake",
      "client_id": "shpwhi_...",
      "shop_integration_id": "shpint_...",
      "shop_domain": "my-shop.myshopify.com",
      "topic": "orders/create",
      "webhook_id": "wh_abc123",
      "status": "processed",
      "retryable": true,
      "attempts": 1,
      "received_at": "2026-07-09T18:00:00+00:00",
      "processing_started_at": "2026-07-09T18:00:01+00:00",
      "processed_at": "2026-07-09T18:00:02+00:00",
      "last_error": null,
      "created_at": "2026-07-09T18:00:00+00:00",
      "updated_at": "2026-07-09T18:00:02+00:00"
    },
    {
      "record_type": "integration_event",
      "client_id": "shpevt_...",
      "shop_integration_id": "shpint_...",
      "event_type": "webhook_sync",
      "severity": "info",
      "message": "Manual Shopify webhook sync requested.",
      "metadata_json": { "action": "manual_sync", "shop_domain": "my-shop.myshopify.com" },
      "created_by": {
        "client_id": "usr_...",
        "username": "alice",
        "profile_picture": null
      },
      "created_at": "2026-07-09T17:55:00+00:00"
    }
  ],
  "webhook_history_records_pagination": { "has_more": false, "limit": 10, "offset": 0 }
}
```

**Important — this is a merged, heterogeneous array.** Every item has `record_type` as a discriminator: `"webhook_intake"` or `"integration_event"`. The frontend must branch on this field — the two record types have different field sets (see below) and there is no shared superset schema.

- `webhook_intake` fields: `topic`, `webhook_id`, `status` (`received`/`processing`/`processed`/`failed`/`ignored`), `retryable`, `attempts`, `received_at`, `processing_started_at`, `processed_at`, `last_error`.
- `integration_event` fields: `event_type` (only `webhook_sync`, `webhook_received`, `webhook_processed`, or `disconnect` ever appear here — OAuth-lifecycle events like `install`/`reauthorize` are deliberately excluded from this feed), `severity` (`info`/`warning`/`error`), `message`, `metadata_json` (safe subset only — see "No-secret guarantee" below; can be `null`), `created_by` (compact user reference with `client_id`, `username`, `profile_picture`, or `null` for system-generated events like inbound webhook receipt).
- Neither record type ever includes `raw_payload`.

**Errors:**
| Status | Cause |
|---|---|
| 404 `{"error": "Shopify shop integration not found.", "ok": false}` | Wrong ID, wrong workspace, or soft-deleted |
| 401/403 | Auth |

---

## Route 8 — Manually re-sync webhooks for every eligible shop in the workspace

`POST /api/v1/integrations/shopify/webhooks/sync`

Same as Route 6, but fans out to every shop in the caller's workspace that's in a syncable status (active-like, not deleted). No path param, no body.

- **Auth:** JWT required. Role: `admin` **only**.

**Success response `data`:**
```json
{
  "enqueued_count": 2,
  "shops": [
    { "shop_integration_id": "shpint_1", "shop_domain": "shop-a.myshopify.com", "sync_webhooks_task_id": "task_shopify_1" },
    { "shop_integration_id": "shpint_2", "shop_domain": "shop-b.myshopify.com", "sync_webhooks_task_id": "task_shopify_2" }
  ]
}
```
If there are zero eligible shops, this still returns `200` with `enqueued_count: 0` and `shops: []` — not an error.

**Errors:** 401/403 only.

---

## Route 9 — Scope status

`GET /api/v1/integrations/shopify/scopes`

Reports whether each linked shop's granted OAuth scopes cover what the app currently requests. Use to power a "needs reauthorization" banner.

- **Auth:** JWT required. Roles: `admin`, `manager`. Workspace-scoped.

**Query params:**
- `shop_integration_id` (optional): if provided, scopes this to one shop; if omitted, returns every shop in the workspace.

**Success response `data`:**
```json
{
  "scope_statuses": [
    {
      "shop_integration_id": "shpint_...",
      "shop_domain": "my-shop.myshopify.com",
      "requested_scopes": ["read_orders", "read_products"],
      "granted_scopes": ["read_orders"],
      "missing_scopes": ["read_products"],
      "has_all_required_scopes": false,
      "shop_status": "outdated"
    }
  ]
}
```
`shop_status` here is `"outdated"` or `"up_to_date"` (same derivation as `scopes_status` in Route 2/3 — when `has_all_required_scopes` is `false`, prompt the user to hit Route 1/4's reauthorize flow).

**Errors:**
| Status | Cause |
|---|---|
| 404 `{"error": "Shopify shop integration not found.", "ok": false}` | `shop_integration_id` provided but not found/wrong workspace |
| 401/403 | Auth |

If no `shop_integration_id` is given and the workspace has zero shops, this returns `200` with `scope_statuses: []`.

---

## Route 10 — OAuth callback (Shopify-facing, not frontend-called)

`GET /api/v1/integrations/shopify/oauth/callback`

**The frontend never calls this directly.** Shopify's own OAuth consent screen redirects the merchant's browser here after Route 1/4's `install_url` is visited and approved. This route always responds with an HTTP `302` redirect to `SHOPIFY_OAUTH_REDIRECT_URL` (a ManagerBeyo **frontend** URL configured by the backend operator) — never with a JSON body.

**What the frontend needs to build:** a page at whatever path `SHOPIFY_OAUTH_REDIRECT_URL` points to, which reads these query params off its own URL and shows a result:

| Query param | Values | Meaning |
|---|---|---|
| `success` | `"true"` \| `"false"` | Whether the link succeeded |
| `shop_domain` | normalized shop domain, or absent | Which shop this was for (may be absent if the callback failed before the shop could be identified, e.g. invalid signature) |
| `error_code` | absent on success; one of `invalid_signature`, `invalid_state`, `state_shop_mismatch`, `state_already_consumed`, `state_expired`, `access_denied`, `missing_code`, `token_exchange_failed`, `oauth_callback_failed` on failure | Machine-readable reason, for showing a specific error message or a generic fallback |

No auth/no JWT applies to this route (Shopify calls it directly, unauthenticated by ManagerBeyo). It never returns a Shopify access token, HMAC value, or raw code to the frontend redirect — only these three safe status params.

---

## Route 11 — Inbound Shopify webhook delivery (Shopify-facing, not frontend-called)

`POST /api/v1/shopify/webhooks`

**The frontend never calls this.** This is where Shopify itself delivers webhook events (`orders/create`, `products/update`, etc.), verified via `X-Shopify-Hmac-Sha256` and persisted/enqueued for async processing. Documented here only so the frontend team knows it exists and is not part of any UI flow. Its response body is not meant for UI consumption (`outcome` field: `received`, `duplicate`, `ignored`, or `unknown_shop`).

---

## Route 12 — Customer lookup by product SKU/barcode

`POST /api/v1/integrations/shopify/customers/by-product-identity`

Given a product's SKU and/or barcode (`article_number`), searches every active Shopify shop integration in the caller's workspace for a matching order line item and returns normalized customer/address information for each match. This is the first Shopify route `seller` can call.

**Note on position:** in `routers/api_v1/shopify.py` this route is declared right after Route 9 (`/scopes`) and before Route 10 (`/oauth/callback`) — it is numbered 12 here only to avoid renumbering the already-documented Routes 10-11.

- **Auth:** JWT required. Roles: `admin`, `manager`, `seller`. Workspace-scoped.

**Request body:**
```json
{
  "sku": "ABC-123",
  "article_number": "0123456789012"
}
```

Both fields are optional strings, but at least one is required after trimming. When both are supplied, SKU is tried first for each eligible shop; barcode is used only as a fallback for that shop if the SKU path found no exact match.

**Success response `data`:**
```json
{
  "customer_matches": [
    {
      "shop_integration_id": "shpint_...",
      "shop_domain": "my-shop.myshopify.com",
      "match_type": "sku",
      "matched_value": "ABC-123",
      "order_id": "gid://shopify/Order/...",
      "order_name": "#1001",
      "customer_id": "gid://shopify/Customer/...",
      "display_name": "Jane Doe",
      "primary_phone_number": "+1234567890",
      "primary_email": "jane@example.com",
      "address": {
        "street_address": "123 Main St",
        "post_code": "12345",
        "coordinates": {
          "latitude": 59.1,
          "longitude": 18.2
        },
        "city": "Stockholm",
        "district": "Stockholm County"
      }
    }
  ],
  "failed_shops": [
    {
      "shop_integration_id": "shpint_...",
      "shop_domain": "other-shop.myshopify.com",
      "error_code": "missing_required_scope"
    },
    {
      "shop_integration_id": "shpint_...",
      "shop_domain": "tokenless-shop.myshopify.com",
      "error_code": "missing_access_token"
    }
  ]
}
```

`customer_matches` may be an empty array and still be a normal `200` response — that means no eligible shop found an exact match. `failed_shops` lists shops that could not be checked successfully (for example missing scope, missing token, or Shopify API failure), so a shop missing from `customer_matches` does not necessarily mean "no match"; it may mean "not checked." `display_name` is the best-known customer name for the match: the linked Shopify customer account name when present, otherwise a name derived from shipping/billing/default address data. Treat it as display text, not a verified identity field. Address and coordinate fields may be `null`; they are never omitted and never defaulted to `0`.

**Errors:**
| Status | Cause |
|---|---|
| 422 `{"error": "At least one of sku or article_number is required.", "ok": false}` | Both `sku` and `article_number` omitted or blank |
| 502 `{"error": "All Shopify shop lookups failed.", "ok": false}` | Every eligible shop with sufficient scope/token hit a Shopify API error and no matches were found anywhere |
| 401/403 | Auth |

No match anywhere (including zero active shops in the workspace) is a normal `200` with `customer_matches: []`, not an error.

---

## Route 13 — Create or update Shopify products (batched, async)

`POST /api/v1/integrations/shopify/products/process`

Accepts a batch of product items and creates-or-updates each one in one or more connected Shopify shops. This route never calls Shopify synchronously — it validates the request, persists a tracking row per (item, shop) pair, enqueues one background task, and returns immediately. Actual progress is reported later via the `shopify.products.synced` realtime event (see below), not in this route's response.

**Note on position:** in `routers/api_v1/shopify.py` this route is declared right after Route 12 (`/customers/by-product-identity`) — it is numbered 13 here only to avoid renumbering the already-documented routes above.


**Request body:**
```json
{
  "items": [
    {
      "client_id": "local-item-id-or-client-id",
      "target_shop_integration_ids": ["shpint_..."],
      "title": "Chair",
      "description": "A soft chair",
      "status": "draft",
      "tags": ["living", "sale"],
      "product_category": "Seating",
      "price": "199.00",
      "weight": { "value": 1.2, "unit": "kg" },
      "sku": "SKU-123",
      "item_article_number": "0123456789012",
      "metafields": { "origin": "warehouse-1" }
    }
  ]
}
```

- `items`: 1-200 entries per request.
- `client_id`: required, opaque to the backend — it is returned unchanged in the `shopify.products.synced` event so the frontend can map a result back to the item card/row that submitted it. It is **not** a ManagerBeyo `Item`/`Upholstery` id; this route does not read or write any internal catalog table.
- `target_shop_integration_ids`: optional. Omit it to target every `active` shop integration currently in the workspace. If provided, every id must belong to an `active` shop integration in the caller's workspace — an id that doesn't resolve (foreign workspace, wrong id, inactive shop) fails the **whole request** with `404`, not just that one item (this is a request-validation failure, not a per-item runtime failure).
- Identity: at least one of `sku`, `item_article_number`, or `article_number` is required per item. `sku` maps to the Shopify variant SKU; `item_article_number`/`article_number` both map to the Shopify variant barcode (same semantics as Route 12's identity fields).
- `status`: optional, defaults to `"draft"` if omitted.
- `weight.unit`: one of `kg`, `g`, `lb`, `oz`.
- `metafields`: a flat `{key: value}` object. All values are stored as Shopify metafields in a single fixed `custom` namespace with type `single_line_text_field` in this phase — no per-key namespace/type control yet.
- Product images are **not supported yet** — this route does not accept or process any image/media field in this phase.

**Success response `data`** (always `200`, returned immediately — no Shopify call has happened yet when this response is sent):
```json
{
  "queued": true,
  "task_id": "task_...",
  "sync_item_client_ids": ["shpsi_...", "shpsi_..."],
  "target_count": 2
}
```

`target_count` is the number of (item, shop) operations that were queued — it can be larger than `items.length` when an item targets multiple shops (or omits `target_shop_integration_ids` and fans out to every active shop).

**Errors:**
| Status | Cause |
|---|---|
| 422 | Missing identity (`sku`/`item_article_number`/`article_number` all blank), invalid `weight.unit`, empty `items`, more than 200 items, or `target_shop_integration_ids: []` explicitly provided as empty |
| 404 `{"error": "Shopify shop integration not found.", ...}` | An explicit `target_shop_integration_ids` entry does not resolve to an active shop in the caller's workspace |
| 422 | No active Shopify shop integrations exist at all in the caller's workspace |
| 401/403 | Auth |

### Realtime event: `shopify.products.synced`

Once the background worker finishes processing the whole batch (all items, all target shops), it emits exactly one socket event to the **workspace room** (not a per-user room — every connected admin/manager in the workspace receives it, matching how this is a shared, workspace-level operation):

```json
{
  "event": "shopify.products.synced",
  "data": {
    "task_id": "task_...",
    "succeeded": [
      {
        "frontend_client_id": "local-item-id-or-client-id",
        "shop_integration_id": "shpint_...",
        "sync_item_client_id": "shpsi_...",
        "requested_operation": "create",
        "shopify_product_id": "gid://shopify/Product/...",
        "shopify_variant_id": "gid://shopify/ProductVariant/..."
      }
    ],
    "failed": [
      {
        "frontend_client_id": "local-item-id-or-client-id",
        "shop_integration_id": "shpint_...",
        "sync_item_client_id": "shpsi_...",
        "requested_operation": "update",
        "error_code": "ambiguous_product_match",
        "error_message": "Multiple Shopify products matched the same identity."
      }
    ]
  }
}
```

- `frontend_client_id` is the same `client_id` the item was submitted with — use it to map each result back to its row/card.
- `requested_operation` is `"create"` or `"update"`, decided by the backend after looking up the item's identity in the target shop — the frontend never chooses this.
- One item targeting multiple shops produces one entry per (item, shop) pair in `succeeded`/`failed`, not one entry per item.
- A batch is normally a mix of `succeeded` and `failed` — one item/shop failing does not fail the others. There is no separate "batch failed" event; a fully-failed batch is just an event where `succeeded` is empty.
- Known `error_code` values: `ambiguous_product_match` (more than one existing Shopify product matched the same SKU/barcode — the backend never guesses which one to update), `missing_access_token`, `missing_shop_integration`, plus Shopify GraphQL error codes (`graphql_user_errors`, `rate_limited`, `timeout`, etc. — same taxonomy as every other Shopify GraphQL call in this integration).
- Never contains an access token or any other secret value.

### Known limitation

Live Shopify GraphQL schema/dev-shop verification for the exact `productCreate`/`productUpdate`/`productVariantsBulkUpdate`/`metafieldsSet` mutation field behavior at the configured `SHOPIFY_API_VERSION` has not been run yet — see `PLAN_shopify_product_sync_20260709.md`'s "Clarifications required" for details. The mutation names and top-level argument shapes are correct; only fine-grained, version-specific field behavior remains unverified against a live shop.

---

## No-secret guarantee

None of the 11 admin/OAuth-callback routes above (plus the `shopify.products.synced` realtime event) ever return: an access token (encrypted or decrypted), the Shopify client secret, the webhook secret, a raw OAuth `code`, a raw webhook/GraphQL payload, or an HMAC/signature value. Route 7's `metadata_json` additionally strips any key whose name contains `token`, `secret`, `hmac`, `signature`, `authorization`, `code`, `raw_payload`, `payload`, `raw_response`, or `provider_response` (case-insensitive) before it's serialized — if every key in an event's metadata happens to be unsafe, `metadata_json` will be `null` rather than an empty object.

## Suggested frontend build order

1. Shop list page → Route 2, with a "Connect a shop" button → Route 1 → redirect to `install_url`.
2. OAuth redirect landing page (Route 10's target) → reads `success`/`shop_domain`/`error_code`, then routes back into the shop list.
3. Shop detail page → Route 3 (shop + webhook subscription summary), with actions: "Reauthorize" (Route 4, shown when `scopes_status: "outdated"`), "Sync webhooks" (Route 6, shown when `webhooks_status` is `"needs_sync"`/`"has_failures"`), "Disconnect" (Route 5, admin-only — hide/disable for `manager` role).
4. Shop detail page's activity tab → Route 7, paginated, branching UI on `record_type`.
5. Optional workspace-level "Sync all shops" action → Route 8.
6. Optional workspace-level scope/health banner → Route 9 (call with no `shop_integration_id` to get every shop at once).
7. Optional shop-floor scan/lookup UI for staff → Route 12, using SKU and/or barcode to resolve the customer for a physical item.
8. Product catalog push UI (`admin`/`manager` only) → Route 13, submitting a batch and then listening for `shopify.products.synced` on the workspace room to update each item card's status from "queued" to "succeeded"/"failed".

## Validation notes

- Backend validation run (Phase 6/6.1/7): unit route/role-gating tests all pass (`tests/unit/test_shopify_router.py`); DB-backed integration coverage for the admin queries/commands and webhook-history query exists and has been run against a live database (see `SUMMARY_shopify_deployment_validation_20260709.md` for the one known, unrelated pre-existing test-isolation caveat — it does not affect route behavior, only the test suite's own data cleanup).
- Suggested frontend validation: exercise the golden path (install → OAuth redirect → shop appears `active` → sync webhooks → history shows the sync event) against a real or development Shopify store once `SHOPIFY_*` env vars are configured in the target environment; verify `manager`-role tokens are correctly blocked from Route 5/6/8 in the UI (hide the buttons, don't rely solely on the 403).

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_shopify_integration_master_20260707.md`
- Parent summaries: `SUMMARY_shopify_admin_routes_serializers_20260709.md`, `SUMMARY_shopify_webhook_history_records_20260709.md`, `SUMMARY_shopify_deployment_validation_20260709.md`, `SUMMARY_PLAN_shopify_customer_lookup_by_product_identity_20260709.md`, `SUMMARY_PLAN_shopify_customer_lookup_corrections_20260709.md`
- Related debug plan: none
