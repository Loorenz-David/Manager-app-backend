# HANDOFF_TO_FRONTEND_sku_templates_20260723

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_sku_templates_20260723`
- Created at (UTC): `2026-07-23T09:00:00Z`
- Owner agent: `claude`
- Status: **implemented**
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_sku_templates_20260723.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_sku_templates_20260723.md`

## TL;DR

New **SKU template** resource. Each workspace configures **one prefix per task type**. The frontend
reads the template for a task type to get the `prefix`, `separator`, `pad_width`, and a ready-to-use
`next_sku_preview` string (e.g. `PRE_ORDER-0001`), then either shows that preview on the item form or
calls the **atomic `reserve`** endpoint to lock in the next number so two users never build the same
SKU. `items.sku` stays a free string — the template just helps the user compose one.

- **Read the preview** (does NOT consume a number): `GET /api/v1/sku-templates/by-task-type/{task_type}`
- **Reserve the next number** (atomically increments the counter): `POST /api/v1/sku-templates/by-task-type/{task_type}/reserve`

## Response envelope

Every endpoint returns the standard envelope. Success:

```json
{ "data": <payload>, "ok": true, "warnings": [] }
```

Error:

```json
{ "error": "<message>", "ok": false }
```

> Note: unlike the pause-reasons endpoints, the single-object responses here put the object
> **directly** under `data` (there is no `{ "sku_template": {...} }` wrapper). The list endpoint is
> the only one with named keys (`sku_templates`, `sku_templates_pagination`).

## Auth (role split)

- **Read + reserve** (`GET` list, `GET` by-task-type, `POST .../reserve`): `ADMIN`, `MANAGER`, `WORKER`, `SELLER`.
- **Configure** (`POST` create, `PATCH` update): `ADMIN`, `MANAGER` only.

## Enums used in responses

The only enum in the payload is `task_type` (`TaskTypeEnum`). Values are always lowercase strings:

| `task_type` value | Meaning |
|---|---|
| `return` | Return task |
| `pre_order` | Pre-order task |
| `internal` | Internal task |

Only `pre_order` has a template by default (see Bootstrap defaults). The path param on the
`by-task-type` routes must be one of these exact values, otherwise FastAPI returns `422` before the
handler runs.

## The Sku Template object

Returned by create, update, get-by-task-type, and each item in the list. Flat shape:

```json
{
  "client_id": "skt_01J...",
  "workspace_id": "ws_01J...",
  "task_type": "pre_order",
  "prefix": "PRE_ORDER",
  "separator": "-",
  "pad_width": 4,
  "last_scalar": 0,
  "next_scalar": 1,
  "next_sku_preview": "PRE_ORDER-0001",
  "created_at": "2026-07-23T08:00:00+00:00",
  "created_by_id": "usr_01J...",
  "updated_at": null,
  "updated_by_id": null
}
```

Field reference:

| Field | Type | Notes |
|---|---|---|
| `client_id` | string | `skt_...` primary id; used in the `PATCH` path. |
| `workspace_id` | string | `ws_...`; scoping only. |
| `task_type` | enum string | `return` \| `pre_order` \| `internal`. |
| `prefix` | string | User-chosen. **Stored uppercased & trimmed** (server normalizes input). Max 32 chars. |
| `separator` | string | Joins prefix and number. Default `"-"`. Max 8 chars (may be empty `""`). |
| `pad_width` | int ≥ 0 | Zero-pad width of the number. `4` → `0007`. `0` → no padding. |
| `last_scalar` | int ≥ 0 | Highest number already **reserved**. Starts at `initial_scalar` (default `0`). |
| `next_scalar` | int | Computed = `last_scalar + 1`. The number a reserve would hand out next. |
| `next_sku_preview` | string | Computed = `prefix + separator + zeroPad(next_scalar, pad_width)`. Show this on the form. |
| `created_at` / `updated_at` | ISO-8601 string \| null | UTC, `+00:00` offset. |
| `created_by_id` / `updated_by_id` | string \| null | `usr_...`. |

> `next_scalar` and `next_sku_preview` are **derived** (read-only) — you never send them back.

## Endpoints

### `GET /api/v1/sku-templates?limit=50&offset=0`

Lists non-deleted templates for the workspace, ordered by `task_type`. Offset pagination.

```json
{
  "sku_templates": [ { /* Sku Template object */ } ],
  "sku_templates_pagination": { "has_more": false, "limit": 50, "offset": 0 }
}
```

`limit` 1–200 (default 50), `offset` ≥ 0 (default 0). In practice there are at most 3 rows (one per
task type), so pagination will effectively always return everything.

### `GET /api/v1/sku-templates/by-task-type/{task_type}`  ← primary read

Returns the single template for that task type as the flat object under `data`. **Read-only — does
not change the counter.** Use `data.next_sku_preview` to prefill the item form.

- `200` → the object.
- `404` → no template configured for that task type in this workspace.

### `POST /api/v1/sku-templates/by-task-type/{task_type}/reserve`  ← atomic reserve

Atomically increments `last_scalar` and returns the reserved number + formatted SKU. Call this the
moment the user commits to creating the item, so concurrent users get distinct consecutive numbers.
No request body.

```json
{
  "client_id": "skt_01J...",
  "task_type": "pre_order",
  "reserved_scalar": 7,
  "sku": "PRE_ORDER-0007"
}
```

- `200` → drop `data.sku` into the item's `sku` field.
- `404` → no template for that task type.

> Reserving `7` means the next reserve returns `8`, and `by-task-type` will then preview `...-0008`.
> The reserved number is consumed even if the user abandons the item form — gaps are expected and fine.

### `POST /api/v1/sku-templates`  (ADMIN/MANAGER)

Creates the template for a task type. Fails if one already exists for that `(workspace, task_type)`.

Request:

```json
{
  "task_type": "return",
  "prefix": "RET",
  "separator": "-",
  "pad_width": 4,
  "initial_scalar": 0
}
```

- `task_type` (required), `prefix` (required). `separator` (default `"-"`), `pad_width` (default `4`,
  ≥ 0), `initial_scalar` (default `0`, ≥ 0 — the counter's starting value; first reserve returns
  `initial_scalar + 1`).
- Returns the created object.
- `409` → a template already exists for that task type (use `PATCH` to edit it).
- `422` → validation (blank/oversized prefix, bad enum, negative numbers).

### `PATCH /api/v1/sku-templates/{client_id}`  (ADMIN/MANAGER)

Partial update of `prefix`, `separator`, `pad_width`, and/or `last_scalar`. Send only the fields you
change. Returns the updated object.

```json
{ "prefix": "PREORD", "pad_width": 5 }
```

- **`last_scalar` may only be raised, never lowered.** Lowering it below the current value would
  re-issue numbers already handed out and collide with existing item SKUs → `422`.
- `404` → unknown / cross-workspace / deleted `client_id`.
- `422` → validation, including the lower-`last_scalar` guard above.

## Realtime events

Emitted on the workspace room after the DB transaction commits. Payload carries `client_id` (+
`last_scalar` on reserve). Treat as a cache-invalidation signal and refetch the affected template /
list.

| Event | Payload data |
|---|---|
| `sku_template:created` | `{ "client_id": "skt_..." }` |
| `sku_template:updated` | `{ "client_id": "skt_..." }` |
| `sku_template:scalar-reserved` | `{ "client_id": "skt_...", "last_scalar": 7 }` |

> `scalar-reserved` fires on **every** reserve, so other clients' previews stay fresh. If you have a
> local optimistic counter, reconcile it from `last_scalar` in the payload.

## Bootstrap defaults

`POST /api/v1/bootstrap` idempotently seeds one default template and returns its task-type key under
`sku_templates_seeded`:

| task_type | prefix | separator | pad_width | first preview |
|---|---|---|---|---|
| `pre_order` | `PRE_ORDER` | `-` | `4` | `PRE_ORDER-0001` |

Re-running bootstrap never resets an advanced counter. `return` and `internal` have **no** template
until an admin creates one (their `by-task-type` read returns `404`).

## Suggested frontend flow (item form)

1. On opening the item form for a given task type, `GET .../by-task-type/{task_type}`.
   - `404` → no template; either hide the auto-SKU affordance or prompt an admin to configure one.
   - `200` → show `data.next_sku_preview` as a suggested SKU.
2. When the user confirms creating the item, `POST .../by-task-type/{task_type}/reserve` and write
   `data.sku` into the item's `sku` field before creating the item.
3. Because `sku` is still a free string, the user can override the reserved value; you don't have to
   use it.

## Error cases (quick reference)

| Status | When |
|---|---|
| `404` | No template for the task type / unknown `client_id` / cross-workspace. |
| `409` | Creating a second template for a task type that already has one. |
| `422` | Invalid body/enum, or trying to lower `last_scalar` on update. |
| `401` / `403` | Missing/invalid token, or role not permitted (config requires ADMIN/MANAGER). |

## Validation notes

- Backend validation run: focused SKU suite (unit domain + router, integration commands/queries incl.
  a concurrent-reserve test and the lower-`last_scalar` guard) — **10 passed**. Migration
  `upgrade`/`downgrade` round-trips cleanly.
- Suggested frontend validation: confirm the preview→reserve→item-create sequence writes the reserved
  `sku`, and that a `404` on `by-task-type` degrades gracefully for `return`/`internal`.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_sku_templates_20260723.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_sku_templates_20260723.md`
