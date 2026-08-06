# HANDOFF_TO_FRONTEND_list_working_sections_endpoint_20260801

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_list_working_sections_endpoint_20260801`
- Created at (UTC): `2026-08-01T00:00:00Z`
- Owner agent: `claude-opus-5`
- Route: `backend/app/beyo_manager/routers/api_v1/working_sections.py`
- Query service: `backend/app/beyo_manager/services/queries/working_sections/list_working_sections.py`
- Serializer: `backend/app/beyo_manager/domain/working_sections/serializers.py` → `serialize_working_section_full`

> **STATUS: already implemented and live.** This is reference documentation for an existing
> endpoint, not a change notice. Nothing here requires a migration on your side.

## 1. Endpoint

```
GET /api/v1/working-sections
```

Returns every non-deleted working section in the caller's workspace, with its dependencies, item
categories, supported issue types, and assigned members inlined. Paginated.

**Authentication:** required. `Authorization: Bearer <jwt>`.
The workspace is taken from the token — there is no workspace query param and you cannot read
another workspace's sections.

**Allowed roles:** `admin`, `manager`, `worker`, `seller`.

## 2. Query parameters

| Param | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `limit` | int | `50` | `<= 200` | Values above 200 are rejected by FastAPI with a `422`, not silently clamped. |
| `offset` | int | `0` | `>= 0` | Plain offset pagination over the section list. |

Both are optional. `GET /api/v1/working-sections` alone is valid and returns the first 50.

## 3. Response envelope

Every response from this API is wrapped. Success:

```json
{ "ok": true, "warnings": [], "data": { ... } }
```

Failure:

```json
{ "ok": false, "error": "Human-readable message." }
```

Note the asymmetry: **`warnings` exists only on success, `error` only on failure.** Read
`data` only after checking `ok === true`. `warnings` is always present on success and is
always `[]` for this endpoint today — treat it as `string[]` and ignore it.

## 4. `data` shape

```
data: {
  working_sections: WorkingSectionFull[]
  working_sections_pagination: { has_more: boolean, limit: number, offset: number }
}
```

### `WorkingSectionFull`

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `client_id` | `string` | no | Stable id, prefix `wsec_`. Use as the React key and for all subsequent calls. |
| `name` | `string` | no | Unique per workspace among non-deleted sections. |
| `image` | `string \| null` | **yes** | Opaque string stored at create/edit time (CDN/S3 URL). Pass through; do not parse. |
| `order_list` | `number \| null` | **yes** | Manual sort position. `null` means unpositioned and is sorted last by the backend. |
| `allows_batch_working` | `boolean` | no | Never null — DB default `false`. |
| `allows_shopify_product_modifications` | `boolean` | no | Never null — DB default `false`. |
| `dependencies` | `{ client_id, name }[]` | no | Possibly empty. Prerequisite sections that must run before this one. `client_id` is another section's id (`wsec_`). |
| `item_categories` | `{ client_id, name, major_category }[]` | no | Possibly empty. `client_id` prefix `itc_`. |
| `supported_issue_types` | `{ client_id, name }[]` | no | Possibly empty. `client_id` prefix `ist_`. |
| `members` | `{ client_id, username, profile_picture }[]` | no | Possibly empty. Users with an **active** membership. `client_id` prefix `usr_`. |

The four array fields are **always present** — an empty relation is `[]`, never `null` and never
omitted. Safe to `.map()` without a guard.

### Nested object fields

`dependencies[]`
| Field | Type | Nullable |
|---|---|---|
| `client_id` | `string` (`wsec_…`) | no |
| `name` | `string` | no |

`item_categories[]`
| Field | Type | Nullable |
|---|---|---|
| `client_id` | `string` (`itc_…`) | no |
| `name` | `string` | no |
| `major_category` | `"wood" \| "seat"` | no |

`major_category` is a closed backend enum (`ItemMajorCategoryEnum`). Only those two values exist
today, but treat an unknown value as a non-crashing fallback rather than an exhaustive switch —
new members can be added backend-side without a contract change.

`supported_issue_types[]`
| Field | Type | Nullable |
|---|---|---|
| `client_id` | `string` (`ist_…`) | no |
| `name` | `string` | no |

`members[]`
| Field | Type | Nullable |
|---|---|---|
| `client_id` | `string` (`usr_…`) | no |
| `username` | `string` | no |
| `profile_picture` | `string \| null` | **yes** — render an initials avatar fallback |

### `working_sections_pagination`

| Field | Type | Notes |
|---|---|---|
| `has_more` | `boolean` | `true` if at least one more section exists past this page. |
| `limit` | `number` | The **effective** limit actually applied, not necessarily what you sent. |
| `offset` | `number` | Echoes the offset used. |

There is **no total count.** Build "load more" off `has_more`; you cannot render "page 3 of 7"
without extra calls.

## 5. Response examples

### 5.1 Populated (the normal case)

`GET /api/v1/working-sections?limit=50&offset=0` → `200`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "working_sections": [
      {
        "client_id": "wsec_01HQ8ZP3K2SANDING",
        "name": "Sanding",
        "image": "https://cdn.beyo.app/sections/sanding.webp",
        "order_list": 1,
        "allows_batch_working": true,
        "allows_shopify_product_modifications": false,
        "dependencies": [
          { "client_id": "wsec_01HQ8ZP3K0CUTTING", "name": "Cutting" }
        ],
        "item_categories": [
          { "client_id": "itc_01HQ8ZQ1AALEGS",     "name": "Chair Legs", "major_category": "wood" },
          { "client_id": "itc_01HQ8ZQ1BBCUSHION",  "name": "Cushions",   "major_category": "seat" }
        ],
        "supported_issue_types": [
          { "client_id": "ist_01HQ8ZR5CRACK", "name": "Crack" },
          { "client_id": "ist_01HQ8ZR6DENT",  "name": "Dent" }
        ],
        "members": [
          {
            "client_id": "usr_01HQ8ZS9ANA",
            "username": "ana.p",
            "profile_picture": "https://cdn.beyo.app/users/ana.webp"
          },
          {
            "client_id": "usr_01HQ8ZSAMARC",
            "username": "marc.t",
            "profile_picture": null
          }
        ]
      },
      {
        "client_id": "wsec_01HQ8ZP3K3UPHOL",
        "name": "Upholstery",
        "image": null,
        "order_list": 2,
        "allows_batch_working": false,
        "allows_shopify_product_modifications": true,
        "dependencies": [
          { "client_id": "wsec_01HQ8ZP3K2SANDING", "name": "Sanding" }
        ],
        "item_categories": [
          { "client_id": "itc_01HQ8ZQ1BBCUSHION", "name": "Cushions", "major_category": "seat" }
        ],
        "supported_issue_types": [],
        "members": [
          {
            "client_id": "usr_01HQ8ZSAMARC",
            "username": "marc.t",
            "profile_picture": null
          }
        ]
      },
      {
        "client_id": "wsec_01HQ8ZP3K9QC",
        "name": "Quality Control",
        "image": null,
        "order_list": null,
        "allows_batch_working": false,
        "allows_shopify_product_modifications": false,
        "dependencies": [],
        "item_categories": [],
        "supported_issue_types": [],
        "members": []
      }
    ],
    "working_sections_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

The third entry is the minimal-but-valid case: no image, no manual order, every relation empty.
It is worth wiring your UI against it — it is a real state (a freshly created section looks
exactly like this).

### 5.2 Empty workspace

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "working_sections": [],
    "working_sections_pagination": { "has_more": false, "limit": 50, "offset": 0 }
  }
}
```

The pagination object is **still present** when the list is empty — the shape does not change.

### 5.3 More pages available

`GET /api/v1/working-sections?limit=2&offset=0` → `200`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "working_sections": [ { "...": "2 sections" } ],
    "working_sections_pagination": { "has_more": true, "limit": 2, "offset": 0 }
  }
}
```

Next page is `offset=2` with the same `limit`.

## 6. Ordering guarantees

**Sections** are ordered deterministically:

1. `order_list` ascending, **nulls last**
2. then `created_at` ascending

So manually positioned sections come first in their configured order, and unpositioned ones fall
to the end in creation order. Do not re-sort client-side unless you intend to override this.

**`members`** are ordered by `username` ascending.

**`dependencies`, `item_categories`, `supported_issue_types` have no ORDER BY** — the database is
free to return them in any order, and that order can change between identical requests. If you
display these lists, sort them client-side (by `name`) or your UI will appear to shuffle on
refetch.

## 7. Error cases

| Status | Body | Cause |
|---|---|---|
| `401` | `{"detail": "Invalid or expired token."}` | Missing/malformed/expired bearer token. |
| `401` | `{"detail": "Token has been revoked."}` | Token was logged out / blocklisted. |
| `403` | `{"detail": "Insufficient role permissions."}` | Role is not one of admin/manager/worker/seller. |
| `422` | FastAPI validation body | `limit > 200`, `offset < 0`, or non-integer values. |
| `500` | `{"ok": false, "error": "An unexpected internal error occurred."}` | Unhandled backend failure. Message is deliberately generic; details are server-side only. |

**Important:** `401`/`403`/`422` come from FastAPI's dependency layer and use `{"detail": "..."}`
— they do **not** carry `ok`/`error`. Only failures raised inside the service layer (`>= 400` via
`build_err`) use `{"ok": false, "error": "..."}`. Your error handler must read both shapes:

```ts
const message =
  body?.error ??
  (typeof body?.detail === "string" ? body.detail : null) ??
  "Something went wrong";
```

This endpoint is a pure read and raises no domain errors of its own, so in practice you will only
see the auth, validation, and generic-500 rows above.

## 8. Suggested TypeScript types

```ts
export type ItemMajorCategory = "wood" | "seat";

export interface WorkingSectionRef {
  client_id: string;
  name: string;
}

export interface WorkingSectionItemCategoryRef extends WorkingSectionRef {
  major_category: ItemMajorCategory;
}

export interface WorkingSectionMemberRef {
  client_id: string;
  username: string;
  profile_picture: string | null;
}

/** Shared by every working-section payload in the API. */
export interface WorkingSectionCompact {
  client_id: string;
  name: string;
  image: string | null;
  order_list: number | null;
  allows_batch_working: boolean;
  allows_shopify_product_modifications: boolean;
}

/** Returned by GET /api/v1/working-sections */
export interface WorkingSectionFull extends WorkingSectionCompact {
  dependencies: WorkingSectionRef[];
  item_categories: WorkingSectionItemCategoryRef[];
  supported_issue_types: WorkingSectionRef[];
  members: WorkingSectionMemberRef[];
}

export interface Pagination {
  has_more: boolean;
  limit: number;
  offset: number;
}

export interface ListWorkingSectionsData {
  working_sections: WorkingSectionFull[];
  working_sections_pagination: Pagination;
}

export type ApiResponse<T> =
  | { ok: true; warnings: string[]; data: T }
  | { ok: false; error: string };

export type ListWorkingSectionsResponse = ApiResponse<ListWorkingSectionsData>;
```

## 9. Do not confuse with `GET /api/v1/working-sections/me`

Both return a top-level `working_sections` array and share the six `WorkingSectionCompact` fields,
but they are **different objects** — do not reuse one type for both.

| | `GET /working-sections` | `GET /working-sections/me` |
|---|---|---|
| Scope | All sections in the workspace | Only sections the caller is an active member of |
| Roles | admin, manager, worker, seller | admin, manager, worker (**no seller**) |
| Extra fields | `dependencies`, `item_categories`, `supported_issue_types`, `members` | `task_steps_counts`, `active_ready` |
| Pagination | `working_sections_pagination` | none — returns everything |
| Ordering | `order_list` (nulls last), then `created_at` | `order_list` (nulls last), then `name` |
| Query params | `limit`, `offset` | `today_start` (ISO 8601) |

Extend `WorkingSectionCompact` for each rather than making the extra fields optional on one type —
optional fields would let you read `task_steps_counts` off a list response and get `undefined` at
runtime with no type error.

## 10. Frontend action required

1. Model `WorkingSectionFull` per §8 — in particular treat `image`, `order_list`, and
   `profile_picture` as nullable; they are the three fields that are `null` in real data.
2. Sort `dependencies` / `item_categories` / `supported_issue_types` client-side if you render
   them — the backend does not guarantee their order (§6).
3. Drive "load more" from `has_more`; there is no total count.
4. Handle both error body shapes (§7).

## 11. Validation notes

- Backend validation: endpoint is pre-existing and covered by the working-sections test suite; no
  code changed for this handoff.
- Suggested frontend validation: request with `?limit=1` and confirm `has_more: true` plus a
  single-element array, then confirm a section with no members/categories renders without a crash.

## 12. Trace links

- Route: `backend/app/beyo_manager/routers/api_v1/working_sections.py` — `list_working_sections_route`
- Service: `backend/app/beyo_manager/services/queries/working_sections/list_working_sections.py`
- Serializers: `backend/app/beyo_manager/domain/working_sections/serializers.py`,
  `backend/app/beyo_manager/domain/users/serializers.py` — `serialize_user_working_section_member`
- Envelope: `backend/app/beyo_manager/routers/http/response.py`
- Auth: `backend/app/beyo_manager/routers/utils/jwt_dep.py`
