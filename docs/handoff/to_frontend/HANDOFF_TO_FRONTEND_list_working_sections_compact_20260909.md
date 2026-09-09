# HANDOFF_TO_FRONTEND_list_working_sections_compact_20260909

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_list_working_sections_compact_20260909`
- Created at (UTC): `2026-09-09T00:00:00Z`
- Owner agent: `claude-opus-5`
- Route: `backend/app/beyo_manager/routers/api_v1/working_sections.py` — `list_working_sections_route`
- Query service: `backend/app/beyo_manager/services/queries/working_sections/list_working_sections.py`
- Serializer: `backend/app/beyo_manager/domain/working_sections/serializers.py` → `serialize_working_section_compact`
- This is an **addendum** to `HANDOFF_TO_FRONTEND_list_working_sections_endpoint_20260801.md`. It adds
  one optional query param and supersedes nothing. Every statement in the parent handoff still holds
  for the default response.

> **STATUS: additive, opt-in, backwards compatible.** If you send nothing new, nothing changes. The
> existing response is byte-for-byte what it was before this change.

## 1. What changed

`GET /api/v1/working-sections` accepts a new optional `compact` query param. When it is true the
endpoint returns each section with only its six own-column fields, dropping the four relation arrays
(`dependencies`, `item_categories`, `supported_issue_types`, `members`).

This is not only a smaller payload. The four relation arrays each cost their own database query, and
the compact branch returns before any of them run — **one query instead of five**. Use it for any
surface that needs a section list but never opens a section's configuration: pickers, filter
dropdowns, chips, name lookups by id.

## 2. Query parameters

| Param | Type | Default | Notes |
|---|---|---|---|
| `limit` | int | `50` | Unchanged. `<= 200`, else `422`. |
| `offset` | int | `0` | Unchanged. `>= 0`. |
| **`compact`** | **bool** | **`false`** | **New.** Omit it and you get the existing full response. |

### Sending `compact` correctly

FastAPI parses this as a real boolean, not a string, and the accepted spellings are wider than you
might expect. Measured against this route's parser:

| You send | Result |
|---|---|
| `?compact=true`, `True`, `TRUE`, `1`, `yes`, `on`, `y`, `t` | compact response |
| `?compact=false`, `False`, `0`, `no`, `off` | full response |
| *param omitted entirely* | full response |
| `?compact` (bare flag, no `=`) | **`422`** — `"Input should be a valid boolean, unable to interpret input"` |
| `?compact=` (empty value) | **`422`** |
| `?compact=banana` | **`422`** |

Two traps worth wiring around:

1. **A bare `?compact` flag is a 422, not a truthy flag.** If you build query strings by appending
   flag names, or if a helper drops `=value` for booleans, you will get a validation error instead of
   a compact list. Always emit `compact=true`.
2. **Never send the param with an empty string.** A common pattern — `params.set("compact", state ??
   "")` — produces `?compact=` and fails with `422`. Omit the key instead when you do not want
   compact; the default already is `false`.

If the param is repeated (`?compact=true&compact=false`), the **last** occurrence wins.

## 3. Response shape when `compact=true`

The envelope, the `data` keys, and the pagination object are all identical. Only the objects inside
`working_sections` are narrower.

```
data: {
  working_sections: WorkingSectionCompact[]     // <- the only difference
  working_sections_pagination: { has_more: boolean, limit: number, offset: number }
}
```

### `WorkingSectionCompact`

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `client_id` | `string` | no | Stable id, prefix `wsec_`. React key, and the id for every follow-up call. |
| `name` | `string` | no | Unique per workspace among non-deleted sections. |
| `image` | `string \| null` | **yes** | Opaque string (CDN/S3 URL). Pass through; do not parse. |
| `order_list` | `number \| null` | **yes** | Manual sort position. `null` means unpositioned, sorted last by the backend. |
| `allows_batch_working` | `boolean` | no | Never null — DB default `false`. |
| `allows_shopify_product_modifications` | `boolean` | no | Never null — DB default `false`. |

**These six fields are exactly the fields the full response already carries.** `WorkingSectionFull`
is `WorkingSectionCompact` plus the four arrays — the shared fields are produced by the same
serializer, so a value never differs between the two modes. The compact object is the same one you
already receive nested inside the `GET /api/v1/users` list response, the working-section-steps
payload, and the reassigned-steps payload — this change only promotes it to a top-level list
element.

### What is absent, and how it is absent

`dependencies`, `item_categories`, `supported_issue_types` and `members` are **omitted keys**, not
empty arrays and not `null`.

This matters for how you type it. In the full response those four are guaranteed present and safe to
`.map()` without a guard (parent handoff §4). In the compact response `row.members` is `undefined`,
so `row.members.map(...)` throws. Model the two modes as **two distinct types** and pick by the flag
you sent — do not make the arrays optional on one shared type, or an unguarded `.map()` will
typecheck and then crash at runtime.

## 4. Response examples

### 4.1 `GET /api/v1/working-sections?compact=true` → `200`

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
        "allows_shopify_product_modifications": false
      },
      {
        "client_id": "wsec_01HQ8ZP3K3UPHOL",
        "name": "Upholstery",
        "image": null,
        "order_list": 2,
        "allows_batch_working": false,
        "allows_shopify_product_modifications": true
      },
      {
        "client_id": "wsec_01HQ8ZP3K9QC",
        "name": "Quality Control",
        "image": null,
        "order_list": null,
        "allows_batch_working": false,
        "allows_shopify_product_modifications": false
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

Same three sections as the parent handoff's §5.1 example, same order, four keys lighter each.

### 4.2 Empty workspace, `compact=true`

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

Identical to the full-mode empty response — the empty case never had relation arrays to drop, so the
two modes are indistinguishable here. Do not use "did the rows have `members`?" to detect which mode
a response came back in; track the flag you sent.

### 4.3 Pagination is unaffected

`GET /api/v1/working-sections?compact=true&limit=1&offset=0` → `200`

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "working_sections": [ { "client_id": "wsec_01HQ8ZP3K2SANDING", "...": "5 more fields" } ],
    "working_sections_pagination": { "has_more": true, "limit": 1, "offset": 0 }
  }
}
```

`has_more` is computed before serialization, from the same over-fetch-by-one, so it means exactly
what it means in full mode. `compact` and `limit`/`offset` compose freely.

## 5. Guarantees that do **not** change

- **Ordering.** Still `order_list` ascending nulls-last, then `created_at` ascending. Both modes run
  the same section query; the flag only chooses a serializer.
- **Scope.** Still every non-deleted section in the caller's workspace, taken from the token.
- **Roles.** Still `admin`, `manager`, `worker`, `seller`. `compact` grants nothing and hides nothing
  role-wise — it is a payload shape, not a permission.
- **Envelope.** Still `{ ok, warnings, data }` on success, `{ ok, error }` on service failures, and
  `{ detail }` on FastAPI auth/validation failures. Parent handoff §7 error table applies unchanged,
  with `?compact=<not-a-boolean>` joining `limit > 200` as a `422` cause.
- **Pagination semantics.** `has_more` / `limit` / `offset` mean what they meant; still no total count.

The client-side sorting advice in the parent handoff §6 only ever applied to the three relation
arrays. In compact mode there is nothing to sort — sections themselves are ordered by the backend.

## 6. Choosing a mode

| Use | Mode |
|---|---|
| Section admin/config screen, anything rendering members, categories, issue types or dependencies | full (omit `compact`) |
| Picker, `<select>`, filter chip row, autocomplete | `compact=true` |
| Resolving `wsec_` ids to names for display | `compact=true` |
| Section cards that show the image and the two capability flags | `compact=true` |

If a screen needs relations for *one* section, prefer `compact=true` for the list plus
`GET /api/v1/working-sections/{id}` for the opened one over fetching every relation for every
section up front.

Do not cache the two modes under the same key. A compact response written into a cache that a full
consumer reads will silently strip `members` from that consumer's view; that failure surfaces far
from its cause.

## 7. Suggested TypeScript types

`WorkingSectionCompact` is already defined in the parent handoff §8 and is unchanged — reuse it
rather than redeclaring. What is new is that it is now a **top-level list element**, not only a
nested object.

```ts
/** Already defined in the parent handoff §8 — shared by every working-section payload. */
export interface WorkingSectionCompact {
  client_id: string;
  name: string;
  image: string | null;
  order_list: number | null;
  allows_batch_working: boolean;
  allows_shopify_product_modifications: boolean;
}

/** GET /api/v1/working-sections           (compact omitted or false) */
export interface ListWorkingSectionsData {
  working_sections: WorkingSectionFull[];
  working_sections_pagination: Pagination;
}

/** GET /api/v1/working-sections?compact=true */
export interface ListWorkingSectionsCompactData {
  working_sections: WorkingSectionCompact[];
  working_sections_pagination: Pagination;
}

// Discriminate on the argument, so the return type is narrowed at the call site
// and `row.members` is a compile error on the compact path rather than a runtime crash.
export function listWorkingSections(
  opts: { compact: true; limit?: number; offset?: number },
): Promise<ApiResponse<ListWorkingSectionsCompactData>>;
export function listWorkingSections(
  opts?: { compact?: false; limit?: number; offset?: number },
): Promise<ApiResponse<ListWorkingSectionsData>>;
export function listWorkingSections(opts: {
  compact?: boolean;
  limit?: number;
  offset?: number;
} = {}) {
  const params = new URLSearchParams();
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.offset !== undefined) params.set("offset", String(opts.offset));
  // Only ever set it to the literal "true"; omit otherwise. Never "" and never a bare key.
  if (opts.compact) params.set("compact", "true");
  return request(`/api/v1/working-sections?${params}`);
}
```

## 8. Frontend action required

1. **Nothing, if you do not want it.** Existing calls are unaffected; this is opt-in.
2. Add `compact=true` to list calls that never read the four relation arrays (§6) — each one drops
   four database queries per request.
3. Type the compact result as `WorkingSectionCompact[]` and keep it distinct from
   `WorkingSectionFull[]` (§3). The four arrays are *absent*, so an optional-field shared type would
   let `.map()` typecheck and crash.
4. Emit the literal `compact=true`; never a bare `?compact` and never `?compact=` (§2) — both are
   `422`.
5. Key any client cache by mode as well as by `limit`/`offset` (§6).

## 9. Validation notes

- Backend validation: 4 new integration tests (9 cases) in
  `backend/app/tests/integration/services/queries/working_sections/test_list_working_sections_compact_integration.py`.
  They pin default-is-full, the compact key set **exactly** (`set(row) == COMPACT_KEYS`, so a future
  field leaking into the compact shape fails the suite), pagination under `limit=1`, non-`"true"`
  values staying full, and the `"True"` casing the router actually forwards.
- The tests were mutation-checked, not merely run green: forcing the flag off killed 2 of them,
  forcing it on killed 7.
- Working-sections query suite plus the serializer unit tests: 66 passed, 1 skipped (a pre-existing
  measurement-run skip, unrelated).
- Full suite: **3,060 passed, 24 failed, 1 skipped**. The 24 failures are the pre-existing baseline,
  not this change — the failing set is **byte-for-byte identical** to the same suite run on a clean
  tree (this change's two source files reverted to `HEAD` and the new test file moved aside, same
  fixed-order command both times, diffed). Several of the baseline failures sit in working-sections
  files, so this was checked rather than assumed.
- The `compact` spelling table in §2 was measured against a live FastAPI route, not assumed.
- Suggested frontend validation: request `?compact=true&limit=1`, confirm exactly six keys per row
  and `has_more: true`; then request the same page without the flag and confirm the six shared values
  are identical between the two responses.

## 10. Trace links

- Parent handoff: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_list_working_sections_endpoint_20260801.md`
- Route: `backend/app/beyo_manager/routers/api_v1/working_sections.py` — `list_working_sections_route`
- Service: `backend/app/beyo_manager/services/queries/working_sections/list_working_sections.py`
- Serializer: `backend/app/beyo_manager/domain/working_sections/serializers.py` — `serialize_working_section_compact`
- `compact` param precedent (same parsing convention): `GET /api/v1/users` —
  `backend/app/beyo_manager/services/queries/users/list_users.py`
- Envelope: `backend/app/beyo_manager/routers/http/response.py`
