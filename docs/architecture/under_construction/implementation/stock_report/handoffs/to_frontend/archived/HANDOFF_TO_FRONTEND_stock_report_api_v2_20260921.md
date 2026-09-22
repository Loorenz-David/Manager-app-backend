---
audience: frontend
subject: Stock Report — the complete API contract (v2)
date: 2026-09-21
status: CURRENT. This is the document to build against.
supersedes: HANDOFF_TO_FRONTEND_stock_report_api_20260921.md (moved to archived/)
companion: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, still current, NOT superseded)
---

# Stock Report — the complete API contract

## 0. Which document is current

| Document | Status |
|---|---|
| **This file** | **CURRENT.** Every route, every shape. Build against this. |
| `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` | **CURRENT and RATIFIED.** Still the authority for match-preview's *semantics* — why it behaves as it does. This file gives that endpoint's exact shape; that file explains its reasoning. Neither supersedes the other. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_api_20260921.md` | **HISTORICAL.** Superseded by this file. Do not build against it. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_match_preview_20260921.md` | **HISTORICAL** (v1 preview design intent). |

## 1. How much to trust each line — read this once, it governs everything below

Every endpoint carries one of two tags.

| Tag | Meaning |
|---|---|
| **VERIFIED** | Read directly out of the shipping code, field by field, on 2026-09-21. Exact. |
| **SPECIFIED** | Not built yet. The shape is pinned by a **criterion row** in the build plan. |

**What SPECIFIED guarantees, precisely.** In this backend's process, a phase's criterion rows *are*
its contract: an independent reviewer fails the phase if the code does not match its row, and the
phase cannot be approved until it does. So for a SPECIFIED route:

> **Build against it. If the backend ships something different, that is a backend defect and it
> gets fixed — it is not a contract change you absorb.**

That is the strongest honest guarantee available for code that does not exist yet. It is not the
same as VERIFIED, and this document will never blur the two.

**Six of the thirteen routes are SPECIFIED.** They are the last batch of work, running now.

## 2. The response envelope — the most important section in this document

**There are three different response shapes, and they are not interchangeable.** Getting this
wrong is the most likely source of wasted frontend time.

### 2.1 Success — always this

```jsonc
{ "data": { /* the endpoint's payload */ }, "ok": true, "warnings": [] }
```

HTTP 200. `warnings` is always present and, on every route in this document, always `[]`.
**The payload is nested under `data`.**

### 2.2 Domain errors — this

```jsonc
{ "error": "Human-readable message.", "ok": false }
```

HTTP status varies by error (404, 422, 401, 503, 500). **No `data` key, no `warnings` key.**

Two endpoints add two more keys for two specific errors — see §2.4.

### 2.3 Auth failures and malformed request bodies — **NOT the envelope**

```jsonc
{ "detail": "Insufficient role permissions." }
```

HTTP 401 or 403. This is FastAPI's own shape. **There is no `ok` field.** A client that reads
`response.ok` here gets `undefined`, not `false`.

The same applies to **body-shape validation failures** (a missing required field, a wrong type, an
unexpected extra key). Those are caught at the route boundary by FastAPI and come back as:

```jsonc
{ "detail": [ { "type": "extra_forbidden", "loc": ["body", "entries", 0, "typo"], "msg": "Extra inputs are not permitted" } ] }
```

HTTP 422, `detail` is an **array**. Note this is a different 422 from §2.2's `{"error", "ok"}` 422.

**Practical rule for your error handler:** branch on the presence of `ok` first. If `ok` is absent,
you have a `detail` response — auth or body-shape. If `ok` is `false`, you have a domain error.

### 2.4 The two structured errors — only on `POST /assignments`

These two, and only these two, carry `code` and `details`:

```jsonc
{ "error": "…", "ok": false, "code": "stock_assignment_refused", "details": [ … ] }
```

Full treatment in §4.3.

## 3. Auth

All `/api/v1/stock-report/*` routes take a **bearer JWT**. Roles: `admin`, `manager`, `worker`,
`seller`. Each route's list is given below; a role outside it gets **403 `{"detail": "Insufficient
role permissions."}`**.

Token problems give **401 `{"detail": …}`** with one of: `"Invalid or expired token."`,
`"Token has been revoked."`, `"Auth blocklist unavailable."`.

The three `/api/v1/location-tracker/webhooks/*` routes are **Scanner-facing, not browser-facing**.
They take no JWT and no role — they authenticate with an `x-api-key` header. They are documented
here for completeness; **your app does not call them.**

---

# Part A — Available now (VERIFIED)

## 4.1 `GET /api/v1/stock-report/consistency` — VERIFIED

Roles: **admin, manager**. No request body.

```jsonc
{ "data": {
    "workspace_id": "ws_…",
    "checked_at": "2026-09-21T18:00:00+00:00",   // ISO 8601
    "divergences": [
      { "kind": "counter_in_queue", "client_id": "sri_…", "field": "quantity_in_queue",
        "stored": 3, "expected": 2 }
    ]
}, "ok": true, "warnings": [] }
```

`kind` is one of: `counter_in_queue`, `counter_in_progress`, `counter_awaiting`, `signature`,
`priority_order_nullness`, `order_density`, `goal_total`, `task_flag`. Sorted by
`(kind, client_id, field)`.

**Trap:** `stored`/`expected` are untyped and vary by `kind` — integers for counters, `str|null`
for `signature`, `int|null` for `priority_order`, and for **`task_flag` they are the *strings*
`"true"` / `"false"`, not booleans.** Do not write a shared renderer that assumes one type.

This is admin tooling. An empty `divergences` array is the healthy state.

## 4.2 `POST /api/v1/stock-report/repair` — VERIFIED

Roles: **admin, manager**. No request body.

```jsonc
{ "data": {
    "repaired":     [ { "kind": "…", "client_id": "…", "field": "…", "stored": …, "expected": … } ],
    "not_repaired": [ { /* same five keys */ } ]
}, "ok": true, "warnings": [] }
```

Both arrays hold the same five-key shape as §4.1's divergences.

**`not_repaired` only ever contains `kind: "signature"`** — repair never attempts a
`properties_signature` mismatch. Neither array is re-sorted; do not rely on their order.

**Trap:** if repair fails to fix a non-signature divergence, the backend raises an internal error
and you get a **generic 500 `{"error": "An unexpected internal error occurred.", "ok": false}`**.
The real cause is server-side only. Treat a 500 here as "repair incomplete, escalate", not as a
transport glitch.

## 4.3 `POST /api/v1/stock-report/assignments` — VERIFIED

Roles: **admin, manager, worker**. (Not seller.)

### Request

```jsonc
{ "entries": [
    { "stock_report_item_id": "sri_…",     // required
      "task_id": "tsk_…",                  // required
      "item_id": "itm_…",                  // required
      "override_property_mismatch": false  // optional, defaults false
    }
] }
```

Unknown keys are **rejected** (`extra="forbid"`) — §2.3 shape.

**`entries: []` behaves unusually and you should know why.** An empty array passes the route-level
check and is rejected one layer deeper, so you get the **§2.2 shape** (`{"error", "ok": false}`,
422) rather than the §2.3 shape. Same status, different body. Don't send an empty array.

### Success

```jsonc
{ "data": { "stock_task_assignments": [ /* see §6 for the 14-key shape */ ] },
  "ok": true, "warnings": [] }
```

Ordered by **ascending `item_id`** — not the order you submitted.

### The two structured errors

**`stock_assignment_refused` — HTTP 422.** The whole batch is refused; **nothing is written.**

```jsonc
{ "error": "…", "ok": false, "code": "stock_assignment_refused",
  "details": [ { "index": 0, "reason": "item_already_assigned" } ] }
```

`index` is the position in *your* `entries` array. `reason` is one of **eleven**:
`duplicate_item_in_batch`, `duplicate_task_in_batch`, `stock_report_item_not_found`,
`task_not_found`, `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`,
`task_failed_or_cancelled`, `item_already_assigned`, `item_has_no_category`, `category_mismatch`.

**`stock_assignment_property_mismatch` — HTTP 409.** Also refuses the whole batch.

```jsonc
{ "error": "…", "ok": false, "code": "stock_assignment_property_mismatch",
  "details": [ { "index": 0, "stock_report_item_id": "…", "task_id": "…", "item_id": "…",
                 "failures": [ { "key": "wood_group", "reason": "value_not_accepted" } ] } ] }
```

`reason` ∈ `missing_on_item`, `value_not_accepted`, `no_group_for_value`,
`criterion_not_understood`.

**This is the retry contract:** a 409 is recoverable. Show the failures, and if the user accepts,
resend the *same* batch with `override_property_mismatch: true` on the offending entries. A **422
refusal is not overridable** — the user must change something.

## 4.4 `POST /api/v1/stock-report/assignments/delete` — VERIFIED

Roles: **admin, manager, worker**.

Request: `{ "client_ids": ["sta_…", …] }`. Same empty-array behaviour as §4.3.

```jsonc
{ "data": { "deleted_client_ids": ["sta_…"] }, "ok": true, "warnings": [] }
```

De-duplicated and sorted.

**Whole-batch refusal:** if *any* id is absent, foreign, already soft-deleted, or is deleted
concurrently, nothing is deleted and you get **404** (§2.2 shape) with a message naming every
missing id: `"Stock task assignment(s) not found: sta_a, sta_b"`. There is no partial success.

## 4.5 `POST /api/v1/stock-report/items/{client_id}/match-preview` — VERIFIED

Roles: **admin, manager, worker**. Semantics: see the companion v2 preview handoff.

### Request

```jsonc
{ "task_id": null,             // optional; null = "creating the task in this same form"
  "article_number": "ABC-123", // optional; identifies an EXISTING item
  "sku": null,                 // alternative to article_number — never both
  "item_category_id": "cat_…", // REQUIRED
  "properties": { "wood_group": "teak" },  // REQUIRED
  "quantity": 4 }              // REQUIRED
```

`item_category_id` is **required**. An Item cannot validly exist without a category, so the
preview requires one too.

Sending both `article_number` and `sku` → **422**, §2.2 shape,
`"article_number and sku are alternatives, not both"`.

### Response

```jsonc
{ "data": {
  "can_proceed": true,
  "override_required": false,
  "refusal_reason": null,
  "property_failures": [ { "key": "wood_group", "reason": "value_not_accepted" } ],
  "matched_item_client_id": null,
  "values_source": "supplied",         // "stored" | "supplied"
  "checks": [ { "check": "stock_report_item_not_found", "result": "pass", "advisory": false } ]
}, "ok": true, "warnings": [] }
```

**`checks` always has exactly 9 entries, always in this order:**

1. `stock_report_item_not_found` 2. `task_not_found` 3. `item_not_found`
4. `item_not_task_primary` 5. `already_processed_by_scanner` 6. `task_failed_or_cancelled`
7. `item_already_assigned` 8. `item_has_no_category` 9. `category_mismatch`

`result` ∈ `pass`, `fail`, `pass_by_construction`, `not_evaluated`.

### Three traps in this response. Please read them.

**(a) `refusal_reason` can be non-null while `can_proceed` is `true`.** `item_already_assigned` is
**advisory** — it is the only advisory check. It reports `fail` and appears as `refusal_reason`,
but it does not block. **Never treat a non-null `refusal_reason` as proof the action cannot
proceed. Branch on `can_proceed`.** `advisory: true` appears on that entry regardless of its
result value.

**(b) `override_required` is independent of `can_proceed` and of `checks`.** It is purely "did the
property matcher find a mismatch". You can have `can_proceed: false` with
`override_required: false`, and vice versa. They answer different questions.

**(c) Stored values win.** If `article_number` or `sku` resolves to a live item, the preview
evaluates that item's **stored** category, properties and quantity and ignores what you sent;
`values_source` reads `"stored"`. What you send is used **only** when no item resolves. This is
deliberate — it is what stops the preview saying "yes" where `create` would say "no".

### Which checks are evaluated, by case

| You sent | Result |
|---|---|
| a resolving `article_number`/`sku` **and** a `task_id` | all 9 are really evaluated |
| a resolving item, **no** `task_id` | `task_not_found`, `task_failed_or_cancelled`, `item_not_task_primary`, `already_processed_by_scanner` → `pass_by_construction`; other 5 real |
| **no** resolving item, **with** `task_id` | `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`, `item_already_assigned` → `not_evaluated`; other 5 real — **including both category checks, against what you sent** |
| **no** resolving item, **no** `task_id` | `item_not_found`, `item_already_assigned` → `not_evaluated`; `item_not_task_primary`, `already_processed_by_scanner`, `task_failed_or_cancelled`, `task_not_found` → `pass_by_construction`; only `stock_report_item_not_found`, `item_has_no_category`, `category_mismatch` real |

**404** (§2.2) if `{client_id}` is not a live stock-report row in your workspace.

## 4.6 The three Scanner webhooks — VERIFIED, and not yours to call

`POST /api/v1/location-tracker/webhooks/stock-demand` and `…/items-processed` are live;
`…/stock-demand-deleted` is **not built yet** (phase 13A). They take an `x-api-key` header, no JWT,
no role. Scanner calls them. They are listed so you can recognise their side effects in the event
stream — see §7.

---

# Part B — Coming in the current batch (SPECIFIED)

Shapes pinned by criterion rows. Build against them; a divergence is a backend defect.

## 5.1 `GET /api/v1/stock-report/items?priority=high,medium,low` — SPECIFIED (phase 12)

Roles: **admin, manager, worker, seller**.

`priority` is an optional comma-separated query param; each token must be `high`, `medium` or
`low`. **Omitted or empty means rows whose priority is NULL**, ordered by `created_at, client_id` —
it does *not* mean "all rows". An unknown token → **422**, `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`.

```jsonc
{ "data": { "stock_report_items": [ /* §6 row shape */ ] }, "ok": true, "warnings": [] }
```

**There is no pagination**, by an explicit product decision. No page/cursor key exists in the
request or the response.

## 5.2 `PATCH /api/v1/stock-report/items/{client_id}/priority` — SPECIFIED (phase 12)

Roles: **admin, manager, seller**. (Not worker.)

Request: `{ "priority": "high" | "medium" | "low" | null }` — **the key is required and has no
default; omitting it is a 422.** `null` is a legal value and means "clear the priority".

Response: `{ "data": { "stock_report_item": { /* §6 */ } }, "ok": true, "warnings": [] }`.

Setting the priority it already has is a **200 no-op** — the row comes back unchanged, with no
write and no event. Absent, soft-deleted or foreign `client_id` → **404**.

## 5.3 `PATCH /api/v1/stock-report/items/{client_id}/priority-order` — SPECIFIED (phase 12)

Roles: **admin, manager, seller**.

Request: `{ "priority_order": 2 }` — a **strict integer**. The string `"2"` is a **422**, not
coerced.

Response: same single-row shape as §5.2. `priority_order` is **1-based** within the row's priority
group.

Refusals, both 422 (§2.2 shape):
- `STOCK_REPORT_ROW_HAS_NO_PRIORITY` — the row's priority is null, so it has no group to order in.
- `STOCK_REPORT_TARGET_OUT_OF_RANGE` — the target is outside `1..n` for that group.

Moving to the position it already holds is a **200 no-op**.

## 5.4 `DELETE /api/v1/stock-report/items/{client_id}` — SPECIFIED (phase 13)

Roles: **admin, manager only.** (Not worker, not seller — narrower than every other route.)

**No request body at all.**

```jsonc
{ "data": { "client_id": "sri_…" }, "ok": true, "warnings": [] }
```

**404** `"Stock report item not found."` if absent, deleted or foreign.

**This cascades.** Deleting a row deletes its assignments too, and unsets the affected tasks'
stock-assignment flag. Expect a burst of events (§7). Confirm destructively in the UI.

## 5.5 `GET /api/v1/stock-report/items/{client_id}/assignments` — SPECIFIED (phase 13)

Roles: **admin, manager, worker, seller**.

```jsonc
{ "data": { "stock_task_assignments": [ /* §6, the 14-key shape */ ] }, "ok": true, "warnings": [] }
```

**404** if the row is absent, deleted or foreign — *not* an empty array.

## 5.6 `POST /api/v1/location-tracker/webhooks/stock-demand-deleted` — SPECIFIED (phase 13A)

Scanner-facing, `x-api-key`. **Not yours to call.** Its effect matters to you: when Scanner drops a
demand rule, the matching row **and all its assignments are deleted**, in every state — including
assignments a worker is actively holding. Users re-add by hand; there is no undo. Expect the same
event burst as §5.4.

---

# 6. Payload shapes

## 6.1 Stock report row — SPECIFIED (phase 12)

```jsonc
{ "client_id": "sri_…",
  "item_category": { "client_id": "cat_…", "name": "Sofa",
                     "major_category": "…", "image_url": "https://… | null" },
  "properties": { "wood_group": "teak" },   // stored, normalized
  "properties_signature": "…",
  "quantity_requested": 5, "quantity_in_queue": 2,
  "quantity_in_progress": 1, "quantity_awaiting": 0,
  "priority": "high | medium | low | null",
  "priority_order": 3,                      // int | null
  "created_at": "…", "updated_at": "…",     // ISO UTC
  "created_by_id": "usr_… | null", "updated_by_id": "usr_… | null" }
```

**`item_category.image_url` is `string | null` and is always present** — when the category has no
image the key is there with value `null`, never omitted. It was added on 2026-09-21 specifically
for you.

There is no `item_type` key and no pagination key.

## 6.2 Assignment — VERIFIED (14 keys)

```jsonc
{ "client_id": "sta_…",
  "state": "in_queue | in_progress | awaiting | resolved | failed | resolved_early",
  "stock_report_item_id": "sri_…", "task_id": "tsk_…", "item_id": "itm_…",
  "quantity": 2,
  "property_mismatch_overridden": false,
  "credited_history_record_id": "… | null",
  "created_at": "…", "created_by_id": "… | null",
  "updated_at": "…", "updated_by_id": "… | null",
  "item": { /* 6.3 */ }, "task": { /* 6.4 */ } }
```

**Assignment states.** Active: `in_queue`, `in_progress`, `awaiting`. Terminal: `resolved`,
`failed`, `resolved_early`.

**`resolved_early` means the physical item was processed by Scanner while the assignment was still
`in_queue` or `in_progress`** — i.e. finished ahead of the board's expectation. It is a success
state, not an error. `resolved` means it completed from `awaiting`, the expected path.

## 6.3 Item (compact) — VERIFIED (7 keys)

`client_id`, `article_number`, `sku`, `quantity`, `item_category_snapshot`,
`item_major_category_snapshot`, `item_images` (array).

## 6.4 Task (compact) — VERIFIED (12 keys)

`client_id`, `task_type`, `priority`, `state`, `title`, `return_source`, `ready_by_at`,
`return_method`, `created_at`, `updated_at`, `closed_at`, `completed_at`.

`return_source`, `ready_by_at`, `return_method` and the four timestamps are nullable.

---

# 7. Events — VERIFIED

Six names, exhaustively:

| Event | `extra` |
|---|---|
| `stock_report_item:created` | `{}` |
| `stock_report_item:updated` | `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`, `priority`, `priority_order` |
| `stock_report_item:deleted` | `{}` |
| `stock_task_assignment:created` | `stock_report_item_id`, `task_id`, `state` |
| `stock_task_assignment:state-changed` | same three |
| `stock_task_assignment:deleted` | same three |

`state` carries any of the six assignment states.

**Which action emits what:**

| Action | Events |
|---|---|
| `POST /assignments` | `stock_task_assignment:created`, maybe `stock_report_item:updated` |
| `POST /assignments/delete` | `stock_task_assignment:deleted`, maybe `stock_report_item:updated` |
| `POST /repair` | `stock_report_item:updated` only |
| `DELETE /items/{id}` (5.4) | `stock_report_item:deleted` plus assignment deletions |
| Scanner demand webhook | `stock_report_item:created` / `:updated` — never assignment events |
| Scanner items-processed | `stock_task_assignment:state-changed`, maybe `stock_report_item:updated` |
| `GET /consistency`, match-preview | nothing (read-only) |

**One inconsistency worth knowing.** Most mutating endpoints de-duplicate their events, so you get
at most one `:updated` per row per request. **The items-processed webhook does not** — it can emit
several events for the same entity in one request. Make your handlers idempotent; don't assume one
event per entity per action.

# 8. What is NOT built — do not design against it

- **No pagination anywhere**, by decision.
- **No history read endpoint.** History records are written; nothing exposes them.
- **No local row creation.** Rows are created by Scanner's demand webhook only.
- **`is_stock_assignment` is not surfaced** on the task read shape.
- **No "forgotten items" view.**
- No batch match-preview — it is one row per call. If you need batch, say so before it ships;
  retrofitting is a new endpoint version, not a free change.

# 9. If something here is wrong

For a **VERIFIED** line: that is a documentation defect — tell us and we correct this file.

For a **SPECIFIED** line that ships differently: that is a **backend defect**. Tell us and it gets
fixed. Do not work around it silently.

This file will be re-verified against the shipping code when the last phase lands, and re-issued if
anything moved. It will never be edited in place — a new dated file will supersede it, and this one
will move to `archived/`.
