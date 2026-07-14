# HANDOFF_TO_FRONTEND_shopify_metafield_preferences_20260713

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_shopify_metafield_preferences_20260713`
- Created at (UTC): `2026-07-13T12:00:00Z`
- Last updated at (UTC): `2026-07-13T10:46:00Z`
- Owner agent: `Claude`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_delete_capability_20260713.md`
- Source summaries: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_metafield_preferences_20260713.md`, `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_metafield_preferences_delete_capability_20260713.md`
- Router file documented: `app/beyo_manager/routers/api_v1/shopify.py`
- Base conventions (response envelope, roles, error-shape distinctions, no-secret guarantee) inherited from: `HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md` — read that doc's "Overview" section first if this is your first Shopify-router integration; this doc only documents what's specific to the two routes below.

## Backend delivery context

- What backend implemented: create, read/search, and delete capabilities for Shopify product-metafield preferences, scoped per Shopify shop integration and workspace.
- API or contract changes: the DELETE route was added; the existing create/query response contracts are unchanged.
- Feature flags/toggles: none.

## Frontend action required

1. Wire the metafield-selection step of the Shopify product-creation form to batch every shop's selected metafields for the current category into **one** `POST` call (Route 1) — not one call per shop.
2. Wire the metafield search/typeahead UI to `GET` (Route 2) with `q=` as the user types; wire category preload to the same route with `item_category_ids=`. Both can be combined in one call.
3. Always source `shop_integration_id` values from the shop list route (documented in the base Shopify handoff) — never construct or submit a raw `shop_domain` to either route below.
4. Handle `unavailable_definition_ids` explicitly in the UI (see "Known limitations" below) — don't drop it silently.
5. When users remove saved selections, send their preference-row `client_id`s to Route 3 in one batch; do not send Shopify definition GIDs or shop domains.

## Overview

### Base path

`/api/v1/integrations/shopify` — same JWT-protected prefix as every other Shopify admin route.

### Roles

Both routes require one of: `admin`, `manager`, `seller`, `worker` — the same four roles gating `products/process` and `customers/by-product-identity`.

### Response envelope (restated from the base handoff doc)

- Success (200): `{ "data": ..., "ok": true, "warnings": [] }` — always read the payload from `data`.
- Domain-level failure: `{ "error": "...", "ok": false }`, status code varies per error type (table below).
- Role/JWT failure (401/403): FastAPI's own shape, no `ok` field — `{ "detail": "..." }`.
- Malformed request body (wrong JSON types, missing required fields): FastAPI's own 422 shape, `{ "detail": [{"loc": [...], "msg": "...", "type": "..."}] }` — **different from a domain-level 422** (see each route's error table; both are 422 but the payload shape differs, and which one you get depends on *which* validation rule failed).

---

## Route 1 — Create metafield preferences (batch, multi-shop)

`POST /api/v1/integrations/shopify/metafield-preferences`

### Purpose

Persists which Shopify product metafield definitions were selected for one internal item category — across one or more shops in a single call. Shopify remains the source of truth for the definition's own characteristics (name, type, validations, etc.); this endpoint never stores those, only the relationship (which definition, for which category, in which shop, in what display order).

### Request body

```json
{
  "item_category_id": "icat_001",
  "preferences": [
    {
      "shop_integration_id": "shpint_shop_a",
      "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/111",
      "sequence_order": 0
    },
    {
      "shop_integration_id": "shpint_shop_b",
      "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/987",
      "sequence_order": 0
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `item_category_id` | string | One internal item category, shared by every entry in `preferences[]`. Must belong to the authenticated workspace. |
| `preferences` | array, **min 1 entry** | One entry per shop-specific metafield selection. |
| `preferences[].shop_integration_id` | string | A `client_id` from the shop list route — never a raw domain. |
| `preferences[].shopify_metafield_definition_id` | string | Shopify GraphQL global ID; must match `gid://shopify/MetafieldDefinition/...`. |
| `preferences[].sequence_order` | integer, **≥ 0** | Display order within this category+shop group. |

**A request may select several different metafield definitions for the same shop** — expected and allowed (e.g. the user picking three metafields for one category on one shop). What's rejected is an *exact* repeat of `(shop_integration_id, shopify_metafield_definition_id)` within the same array.

### What the backend does with this

1. Validates `item_category_id` belongs to the workspace (checked once, shared across all selections).
2. Validates every referenced `shop_integration_id` belongs to the workspace, is active, and is not deleted.
3. For every selection, confirms `shopify_metafield_definition_id` actually exists **in that specific shop** — a definition ID is checked only against its own selection's shop, never against another selection's shop, even if two selections reference the same-looking GID string.
4. **The whole request is atomic.** If any single selection fails validation — wrong shop, bad/foreign definition, Shopify unreachable for even one shop — **nothing is saved**, not even the other, individually-valid selections in the same request. There is no partial-success mode.
5. Saving is **idempotent per selection**. Submitting the same `(shop_integration_id, shopify_metafield_definition_id)` pair again for the same category updates its `sequence_order` if it changed; it never creates a duplicate row, and it re-enables/restores it if it had somehow been disabled or removed.

### Response — success (200)

```json
{
  "data": [
    {
      "client_id": "shpmfp_01ARZ3NDEKTSV4RRFFQ69G5FAV",
      "item_category_id": "icat_001",
      "shop_integration_id": "shpint_shop_a",
      "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/111",
      "name": "Height",
      "namespace": "custom",
      "key": "height",
      "description": null,
      "type": "dimension",
      "validations": [],
      "sequence_order": 0,
      "is_enabled": true,
      "created_at": "2026-07-13T08:30:00+00:00",
      "updated_at": null,
      "created_by": {
        "client_id": "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "username": "jane",
        "profile_picture": null
      }
    }
  ],
  "ok": true,
  "warnings": []
}
```

`data` is a **plain array**, not wrapped in an object key — exactly one object per `preferences[]` entry, **in the same order the entries were submitted**, even when shops are interleaved in the request. `name`/`namespace`/`key`/`description`/`type`/`validations` are the *current* Shopify-side characteristics, fetched live at save time — the backend does not persist them, so a later read (Route 2) may show different values if the definition changed in Shopify Admin in the meantime.

### Errors

| Condition | Status | Response shape |
|---|---|---|
| Malformed body (wrong field types, missing required fields), empty `preferences` array, or `sequence_order < 0` | **422** | FastAPI's own shape — `{"detail": [...]}` (these are all enforced by the request body's own field constraints, before the route's code runs) |
| Malformed `shopify_metafield_definition_id` (not a `gid://shopify/MetafieldDefinition/...` string), or a duplicate `(shop_integration_id, shopify_metafield_definition_id)` pair in the payload | **422** | Domain shape — `{"error": "...", "ok": false}` (these checks happen one layer deeper, inside the command itself — do not assume every 422 on this route has the FastAPI `detail` shape) |
| `item_category_id` not found / not in this workspace | 404 | `{"error": "Item category not found.", "ok": false}` |
| A `shop_integration_id` not found / not in this workspace / soft-deleted | 404 | `{"error": "Shopify shop integration not found.", "ok": false}` |
| A `shop_integration_id` found but not active, or has no usable Shopify access token | 422 | `{"error": "Shopify shop integration is not active.", "ok": false}` / `{"error": "Shopify shop integration has no usable access token.", "ok": false}` |
| A `shopify_metafield_definition_id` doesn't resolve in Shopify for its own shop, isn't a metafield definition, or isn't owned by products | 404 | `{"error": "Shopify metafield definition not found.", "ok": false}` — deliberately doesn't distinguish which of the three; don't parse the message to tell them apart |
| Shopify's API unreachable/erroring while validating any one selection | 502 | `{"error": "...", "ok": false}` |
| Role not in `admin`/`manager`/`seller`/`worker` | 403 | `{"detail": "..."}` |
| Missing/invalid/expired JWT | 401 | `{"detail": "..."}` |

Any failure in this table means the **entire request failed** — no preferences were saved for any shop in the batch, even ones that individually would have succeeded.

---

## Route 2 — Query saved preferences and search live definitions (multi-shop, grouped)

`GET /api/v1/integrations/shopify/metafield-preferences`

### Purpose

One endpoint, two independent capabilities, both run **per shop** and combinable in a single call:

- **Preference hydration** — "what metafields did we already save for this category (per shop), and what are their current Shopify characteristics right now?"
- **Definition search** — "let the user search this shop's product metafield definitions by visible name, to pick a new one to save."

### Query parameters

| Param | Required | Type | Notes |
|---|---|---|---|
| `shop_integration_ids` | **always** | comma-separated string | One or more `client_id`s from the shop list route. |
| `item_category_ids` | one of these two, or both | comma-separated string | Triggers preference hydration. |
| `q` | one of these two, or both | string | Triggers live definition search. Case-insensitive **substring match against the Shopify `name` field only** — never matches on `namespace` or `key`. |
| `only_my_preferences` | no | `"true"` / `"false"` | Restricts preference hydration (never search) to preferences the *current* user created. Default `false`. |

```
GET /api/v1/integrations/shopify/metafield-preferences?shop_integration_ids=shpint_shop_a,shpint_shop_b&item_category_ids=icat_001&q=height&only_my_preferences=true
```

`shop_integration_ids` alone is not enough — at least one of `item_category_ids` or `q` must also be present, or the request is rejected (see error table).

### What the backend does with this

For **each** requested shop, independently:
- If `item_category_ids` is present: loads this shop's saved, enabled preferences for those categories, then hydrates them with *current* Shopify data in one batched call scoped to only this shop's own saved definition IDs and only this shop's own domain/token.
- If `q` is present: searches this shop's product metafield definitions by visible name, returning up to `SEARCH_RESULTS_LIMIT` (currently 20) matches — **per shop**, independently. A definition ID or search result is never looked up using another shop's credentials, and search limits are never shared across shops — a 3-shop request can return up to 3× the per-shop limit in total.

### Response — success (200)

```json
{
  "data": {
    "shops": [
      {
        "shop_integration_id": "shpint_shop_a",
        "shop_domain": "shop-a.myshopify.com",
        "item_categories": [
          {
            "item_category_id": "icat_001",
            "metafield_preferences": [
              {
                "client_id": "shpmfp_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "item_category_id": "icat_001",
                "shop_integration_id": "shpint_shop_a",
                "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/111",
                "name": "Height",
                "namespace": "custom",
                "key": "height",
                "description": null,
                "type": "dimension",
                "validations": [],
                "sequence_order": 0,
                "is_enabled": true,
                "created_at": "2026-07-13T08:30:00+00:00",
                "updated_at": null,
                "created_by": { "client_id": "usr_...", "username": "jane", "profile_picture": null }
              }
            ]
          }
        ],
        "unavailable_definition_ids": [],
        "search_results": [
          {
            "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/222",
            "name": "Seat height",
            "namespace": "custom",
            "key": "seat_height",
            "description": null,
            "type": "dimension",
            "validations": []
          }
        ]
      },
      {
        "shop_integration_id": "shpint_shop_b",
        "shop_domain": "shop-b.myshopify.com",
        "item_categories": [],
        "unavailable_definition_ids": [],
        "search_results": []
      }
    ]
  },
  "ok": true,
  "warnings": []
}
```

`shops[]` preserves the exact order `shop_integration_ids` was submitted in — never database order, never alphabetical.

If `item_category_ids` wasn't supplied, every shop's `item_categories` is `[]` (not omitted). If `q` wasn't supplied, every shop's `search_results` is `[]`. Both keys are always present with a stable shape regardless of which flow actually ran — no need to check for key existence before reading them.

### Two similar-looking but distinct object shapes — do not treat as interchangeable

| | `item_categories[].metafield_preferences[]` entries | `search_results[]` entries |
|---|---|---|
| Represents | An already-saved preference, hydrated with live Shopify data | A raw Shopify definition the user hasn't saved yet |
| Has `client_id` (the preference row's own ID)? | Yes | **No** |
| Has `item_category_id`, `sequence_order`, `is_enabled`, `created_at`/`updated_at`, `created_by`? | Yes | **No** |
| Has `shopify_metafield_definition_id`, `name`, `namespace`, `key`, `description`, `type`, `validations`? | Yes | Yes |

### `unavailable_definition_ids`

A saved preference can reference a Shopify metafield definition that was later deleted/changed in Shopify Admin. When Shopify no longer resolves it (or it's no longer product-owned), its `shopify_metafield_definition_id` string appears in **that shop's** `unavailable_definition_ids` array **instead of** appearing under `metafield_preferences[]`. The backend does **not** delete or disable the underlying saved preference when this happens — the row still exists, just currently unhydrated. Treat this as "this saved selection needs the user's attention" (e.g. a "no longer available in Shopify" chip) rather than silently dropping it or treating it as if it were never saved.

### Errors

| Condition | Status | `error` message |
|---|---|---|
| `shop_integration_ids` missing/empty, or both `item_category_ids` and `q` missing/empty | 422 | `"Provide shop_integration_ids and at least one of item_category_ids or q."` |
| Any requested `shop_integration_id` not found / not in this workspace / soft-deleted | 404 | `"Shopify shop integration not found."` |
| Any requested `shop_integration_id` found but not active, or has no usable access token *and* work is actually needed for it (search requested for it, or it has matching saved preferences) | 422 | `"Shopify shop integration is not active."` / `"Shopify shop integration has no usable access token."` |
| Any requested `item_category_id` not found / not in this workspace (only checked when `item_category_ids` is supplied) | 404 | `"Item category not found."` |
| Shopify unreachable/erroring for **any one** requested shop's hydration or search call | 502 | `{"error": "...", "ok": false}` |
| Role/auth failures | 403 / 401 | Same as Route 1 |

There is no FastAPI-body-validation distinction on this route — it's a `GET` with no request body, so every validation failure listed above is domain-shape (`{"error": ..., "ok": false}`).

Same all-or-nothing rule as Route 1: if any requested shop is invalid, or Shopify fails for any one shop, the **entire** request fails — there is never a response with some `shops[]` entries present and others missing.

---

## Route 3 — Delete metafield preferences (batch, local soft delete)

`DELETE /api/v1/integrations/shopify/metafield-preferences`

### Purpose

Soft-deletes explicitly selected preference rows from the authenticated workspace. This is a local operation only: it does not call Shopify and does not delete the underlying Shopify metafield definition.

### Request body

```json
{
  "client_ids": [
    "shpmfp_01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "shpmfp_01ARZ3NDEKTSV4RRFFQ69G5FAW"
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `client_ids` | array of strings, **min 1 entry** | Preference-row `client_id`s returned in Route 1 or Route 2. Duplicate IDs are accepted and deduplicated by the backend. |

Do not send `shopify_metafield_definition_id`, `shop_integration_id`, or `shop_domain` to identify records for deletion. The delete address is the preference row's own `client_id`.

### What the backend does with this

1. Resolves every requested ID within the authenticated workspace and only among non-deleted rows.
2. If every ID is valid, sets `is_deleted=true`, `deleted_at` to the deletion timestamp, and `deleted_by_id` to the current user.
3. The operation is **all-or-nothing**. If one ID is missing, belongs to another workspace, or is already soft-deleted, no rows are changed.
4. The operation never calls Shopify and does not emit a Shopify integration event.

### Response — success (200)

```json
{
  "data": {},
  "ok": true,
  "warnings": []
}
```

### Errors

| Condition | Status | Response shape |
|---|---|---|
| Missing/empty `client_ids`, or wrong body field type | **422** | FastAPI's own shape — `{"detail": [...]}` |
| Any ID not found in the workspace, belonging to another workspace, or already soft-deleted | 404 | `{"error": "Shopify metafield preference(s) not found: ...", "ok": false}` |
| Role not in `admin`/`manager`/`seller`/`worker` | 403 | `{"detail": "..."}` |
| Missing/invalid/expired JWT | 401 | `{"detail": "..."}` |

The delete operation is workspace-wide for the four allowed roles; it is not restricted to preferences created by the requesting user.

### Restore behavior

There is no separate undo endpoint. Re-submit the same selection through Route 1 using the same category, shop integration, and Shopify definition GID. The existing create command restores the soft-deleted row and preserves its original preference `client_id` rather than creating a duplicate.

---

## Known limitations / edge cases to design around

- **No pagination on `search_results`.** Each shop's search is capped at a fixed per-shop limit (20 today); there is no `has_more` flag or cursor to page further. If "load more" is needed later, that requires a backend change — don't try to work around it client-side by re-querying with a different `q`.
- **`only_my_preferences` never affects `search_results`**, only `metafield_preferences[]`. Don't apply it as a client-side filter on search results.
- **Current Shopify characteristics (`name`, `type`, `validations`, etc.) can change between the Route 1 response and a later Route 2 read.** Don't cache them long-term as if static — Route 2 is always the source of truth for "current."
- **Live-Shopify-store verification of some fine-grained schema behavior is still pending** on the backend side (the exact `MetafieldOwnerType` enum value has been confirmed against Shopify's documented schema, but a real dev-store round-trip and real cross-shop-GID-rejection test have not been run yet). This doesn't change any shape documented here — flagging only in case unexpected Shopify-side error text surfaces during integration testing against a real store.

## Suggested frontend build order

1. When a category and one-or-more shops are selected in the product-creation form, call Route 2 with `item_category_ids` to preload existing preferences per shop.
2. Add the metafield search/typeahead UI, calling Route 2 with `q=` as the user types — debounce client-side; the backend does not debounce or rate-limit for you.
3. On save, batch every shop's selected metafields for the category into **one** Route 1 call — never one call per shop.
4. Render `unavailable_definition_ids` distinctly from normally-hydrated preferences (see above).
5. On removal, optimistically remove the selected preference rows from the UI, then call Route 3 with their `client_id`s. If the batch fails, restore the affected UI selections because the backend applies no partial deletion.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_20260713.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_metafield_preferences_20260713.md`
- Delete-capability plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_delete_capability_20260713.md`
- Delete-capability summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_metafield_preferences_delete_capability_20260713.md`
- Base conventions this doc inherits from: `HANDOFF_TO_FRONTEND_shopify_integration_routes_20260709.md`
- Test-coverage correction plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_test_coverage_correction_20260713.md`
