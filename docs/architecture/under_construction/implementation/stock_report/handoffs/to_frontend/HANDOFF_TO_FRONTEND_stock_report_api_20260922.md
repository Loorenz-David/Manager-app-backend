---
audience: frontend
subject: Stock Report — the complete API contract, re-verified against shipped code
date: 2026-09-22
status: CURRENT. This is the document to build against.
supersedes: HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md (moved to archived/, unedited)
companion: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, still current, NOT superseded)
---

# Stock Report — the complete API contract

## 0. Which document is current

| Document | Status |
|---|---|
| **This file** | **CURRENT.** Every route, every shape, every one of them now read out of shipping code. Build against this. |
| `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` | **CURRENT and RATIFIED.** Still the authority for match-preview's *semantics* — why it behaves as it does. This file gives that endpoint's exact shape; that file explains its reasoning. Neither supersedes the other, and there is no v3 of it. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_api_v2_20260921.md` | **HISTORICAL.** Superseded by this file. Do not build against it. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_api_20260921.md` | **HISTORICAL.** |
| `archived/HANDOFF_TO_FRONTEND_stock_report_match_preview_20260921.md` | **HISTORICAL** (v1 preview design intent). |

## 0.1 What changed since the 2026-09-21 document, and why this file exists

The previous document tagged every line **VERIFIED** (read out of shipping code) or
**SPECIFIED** (pinned by a criterion row, not yet built), and promised it would be
re-verified when the last phase landed. That has now happened: the last batch shipped,
and every route in this document was read field by field against the code on
2026-09-22. **There is no SPECIFIED line left.**

Four things moved. Nothing here changes a shape you were told to build against
except the first, which was wrong in the old document:

1. **`properties` is list-valued, and the old example showed a bare string.** §6.1 of
   the superseded file showed `"properties": { "wood_group": "teak" }`. The stored,
   normalized form is **`{"wood_group": ["teak"]}`** — normalization lower-cases,
   trims, de-duplicates and sorts, and turns a single string into a one-element list.
   The code is right and the old document was wrong. If you wrote a renderer against
   the string form, that is the one thing to fix.
2. **The Scanner delete webhook is built** and its response shape is documented for
   the first time (§5.6). You still never call it; its effects reach you as events.
3. **The six routes that were SPECIFIED are now VERIFIED** — §5.1 to §5.6. Their
   shapes are unchanged from what you were promised.
4. **Nullability is now stated per field, and a test enforces it.** §6 carries a
   field table per payload shape, with the exact condition that produces each null.
   `app/tests/unit/docs/test_stock_report_docs.py` parses those tables and compares
   them against the shipped serializers, so this document cannot silently drift from
   the code again.

## 1. The response envelope — the most important section in this document

**There are three different response shapes, and they are not interchangeable.**

### 1.1 Success — always this

```jsonc
{ "data": { /* the endpoint's payload */ }, "ok": true, "warnings": [] }
```

HTTP 200. `warnings` is always present and, on every route in this document, always
`[]`. **The payload is nested under `data`.**

### 1.2 Domain errors — this

```jsonc
{ "error": "Human-readable message.", "ok": false }
```

HTTP status varies by error (404, 422, 401, 409, 503, 500). **No `data` key, no
`warnings` key.** Two errors on one endpoint add two more keys — §4.3.

### 1.3 Auth failures and malformed request bodies — **NOT the envelope**

```jsonc
{ "detail": "Insufficient role permissions." }
```

HTTP 401 or 403, FastAPI's own shape. **There is no `ok` field.** A client that reads
`response.ok` here gets `undefined`, not `false`.

The same applies to **body-shape validation failures** (a missing required field, a
wrong type, an unexpected extra key):

```jsonc
{ "detail": [ { "type": "extra_forbidden", "loc": ["body", "entries", 0, "typo"], "msg": "Extra inputs are not permitted" } ] }
```

HTTP 422, `detail` is an **array**. This is a different 422 from §1.2's.

**Practical rule for your error handler:** branch on the presence of `ok` first. If
`ok` is absent you have a `detail` response — auth or body-shape. If `ok` is `false`
you have a domain error.

## 2. Auth

All `/api/v1/stock-report/*` routes take a **bearer JWT**. Roles: `admin`, `manager`,
`worker`, `seller`. Each route's list is given below; a role outside it gets **403
`{"detail": "Insufficient role permissions."}`**.

Token problems give **401 `{"detail": …}`** with one of: `"Invalid or expired
token."`, `"Token has been revoked."`, `"Auth blocklist unavailable."`.

The three Scanner webhooks are **not browser-facing**. They take no JWT and no role —
they authenticate with an `x-api-key` header. They are documented here so you can
recognise their side effects in the event stream; **your app does not call them.**

---

# Part A — The board's own endpoints

## 4.1 `GET /api/v1/stock-report/consistency` — VERIFIED

Roles: **admin, manager**. No request body.

```jsonc
{ "data": {
    "workspace_id": "ws_…",
    "checked_at": "2026-09-22T18:00:00+00:00",   // ISO 8601
    "divergences": [
      { "kind": "counter_in_queue", "client_id": "sri_…", "field": "quantity_in_queue",
        "stored": 3, "expected": 2 }
    ]
}, "ok": true, "warnings": [] }
```

`kind` is one of: `counter_in_queue`, `counter_in_progress`, `counter_awaiting`,
`signature`, `priority_order_nullness`, `order_density`, `goal_total`, `task_flag`.
Sorted by `(kind, client_id, field)`.

**Trap:** `stored`/`expected` are untyped and vary by `kind` — integers for counters,
`str|null` for `signature`, `int|null` for `priority_order`, and for **`task_flag`
they are the *strings* `"true"` / `"false"`, not booleans.** Do not write a shared
renderer that assumes one type.

This is admin tooling. An empty `divergences` array is the healthy state.

## 4.2 `POST /api/v1/stock-report/repair` — VERIFIED

Roles: **admin, manager**. No request body.

```jsonc
{ "data": {
    "repaired":     [ { "kind": "…", "client_id": "…", "field": "…", "stored": …, "expected": … } ],
    "not_repaired": [ { /* same five keys */ } ]
}, "ok": true, "warnings": [] }
```

**`not_repaired` only ever contains `kind: "signature"`** — repair never attempts a
`properties_signature` mismatch. Neither array is re-sorted; do not rely on their
order.

**Trap:** if repair fails to fix a non-signature divergence you get a generic **500**
`{"error": "An unexpected internal error occurred.", "ok": false}`. Treat a 500 here
as "repair incomplete, escalate", not as a transport glitch.

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

Unknown keys are **rejected** (`extra="forbid"`) — §1.3 shape.

**`entries: []` behaves unusually.** An empty array passes the route-level check and
is rejected one layer deeper, so you get the **§1.2 shape** (422) rather than the §1.3
shape. Same status, different body. Don't send an empty array.

### Success

```jsonc
{ "data": { "stock_task_assignments": [ /* §6.2 */ ] }, "ok": true, "warnings": [] }
```

Ordered by **ascending `item_id`** — not the order you submitted.

### The two structured errors

**`StockAssignmentRefused` → `stock_assignment_refused`, HTTP 422.** The whole batch is
refused; **nothing is written.**

```jsonc
{ "error": "…", "ok": false, "code": "stock_assignment_refused",
  "details": [ { "index": 0, "reason": "item_already_assigned" } ] }
```

`index` is the position in *your* `entries` array. `reason` is one of **eleven**:
`duplicate_item_in_batch`, `duplicate_task_in_batch`, `stock_report_item_not_found`,
`task_not_found`, `item_not_found`, `item_not_task_primary`,
`already_processed_by_scanner`, `task_failed_or_cancelled`, `item_already_assigned`,
`item_has_no_category`, `category_mismatch`.

**`already_processed_by_scanner`, in product words:** the physical item has already
been through Scanner's repair flow, so there is nothing left for a worker to do on it.
Assigning it to a board row would promise work that is already finished.

**`StockAssignmentPropertyMismatch` → `stock_assignment_property_mismatch`, HTTP 409.**
Also refuses the whole batch.

```jsonc
{ "error": "…", "ok": false, "code": "stock_assignment_property_mismatch",
  "details": [ { "index": 0, "stock_report_item_id": "…", "task_id": "…", "item_id": "…",
                 "failures": [ { "key": "wood_group", "reason": "value_not_accepted" } ] } ] }
```

`reason` ∈ `missing_on_item`, `value_not_accepted`, `no_group_for_value`,
`criterion_not_understood`.

**This is the retry contract:** a 409 is recoverable. Show the failures, and if the
user accepts, resend the *same* batch with `override_property_mismatch: true` on the
offending entries. A **422 refusal is not overridable** — the user must change
something.

## 4.4 `POST /api/v1/stock-report/assignments/delete` — VERIFIED

Roles: **admin, manager, worker**. Request: `{ "client_ids": ["sta_…", …] }`. Same
empty-array behaviour as §4.3.

```jsonc
{ "data": { "deleted_client_ids": ["sta_…"] }, "ok": true, "warnings": [] }
```

De-duplicated and sorted.

**Whole-batch refusal:** if *any* id is absent, foreign, already soft-deleted, or is
deleted concurrently, nothing is deleted and you get **404** naming every missing id.
There is no partial success.

## 4.5 `POST /api/v1/stock-report/items/{client_id}/match-preview` — VERIFIED

Roles: **admin, manager, worker**. Semantics: the companion v2 preview handoff is the
source of truth and is unchanged.

### Request

```jsonc
{ "task_id": null,             // optional; null = "creating the task in this same form"
  "article_number": "ABC-123", // optional; identifies an EXISTING item
  "sku": null,                 // alternative to article_number — never both
  "item_category_id": "cat_…", // REQUIRED
  "properties": { "wood_group": ["teak"] },  // REQUIRED
  "quantity": 4 }              // REQUIRED
```

`item_category_id` is **required**. An Item cannot validly exist without a category,
so the preview is never more permissive than item creation.

Sending both `article_number` and `sku` → **422**, §1.2 shape.

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

**`pass_by_construction`** means the check cannot fail in this call because its
subject does not exist — you sent no `task_id`, so "the task is not failed or
cancelled" is true by construction, not by inspection. **`not_evaluated`** means the
opposite: the check could matter but nothing was available to run it against (no item
resolved, so "is this item already assigned" has no item to ask about). Neither is a
failure; neither is a pass you can rely on as evidence about a real object.

### Three traps in this response. Please read them.

**(a) `refusal_reason` can be non-null while `can_proceed` is `true`.**
`item_already_assigned` is **advisory** — the only advisory check. It reports `fail`
and appears as `refusal_reason`, but it does not block. **Branch on `can_proceed`.**

**(b) `override_required` is independent of `can_proceed` and of `checks`.** It is
purely "did the property matcher find a mismatch".

**(c) Stored values win.** If `article_number` or `sku` resolves to a live item, the
preview evaluates that item's **stored** category, properties and quantity and ignores
what you sent; `values_source` reads `"stored"`. What you send is used **only** when no
item resolves.

### Which checks are evaluated, by case

| You sent | Result |
|---|---|
| a resolving `article_number`/`sku` **and** a `task_id` | all 9 are really evaluated |
| a resolving item, **no** `task_id` | `task_not_found`, `task_failed_or_cancelled`, `item_not_task_primary`, `already_processed_by_scanner` → `pass_by_construction`; other 5 real |
| **no** resolving item, **with** `task_id` | `item_not_found`, `item_not_task_primary`, `already_processed_by_scanner`, `item_already_assigned` → `not_evaluated`; other 5 real — **including both category checks, against what you sent** |
| **no** resolving item, **no** `task_id` | `item_not_found`, `item_already_assigned` → `not_evaluated`; `item_not_task_primary`, `already_processed_by_scanner`, `task_failed_or_cancelled`, `task_not_found` → `pass_by_construction`; only `stock_report_item_not_found`, `item_has_no_category`, `category_mismatch` real |

**404** if `{client_id}` is not a live stock-report row in your workspace.

---

# Part B — The routes that were SPECIFIED, now verified

## 5.1 `GET /api/v1/stock-report/items?priority=high,medium,low` — VERIFIED

Roles: **admin, manager, worker, seller**.

`priority` is an optional comma-separated query param; each token must be `high`,
`medium` or `low`. **Omitted or empty means rows whose priority is NULL**, ordered by
`created_at, client_id` — it does *not* mean "all rows". An unknown token → **422**,
`STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`.

```jsonc
{ "data": { "stock_report_items": [ /* §6.1 */ ] }, "ok": true, "warnings": [] }
```

**There is no pagination**, by an explicit product decision. No page or cursor key
exists in the request or the response.

## 5.2 `PATCH /api/v1/stock-report/items/{client_id}/priority` — VERIFIED

Roles: **admin, manager, seller**. (Not worker.)

Request: `{ "priority": "high" | "medium" | "low" | null }` — **the key is required
and has no default; omitting it is a 422.** `null` is a legal value and means "clear
the priority".

Response: `{ "data": { "stock_report_item": { /* §6.1 */ } }, "ok": true, "warnings": [] }`.

Setting the priority it already has is a **200 no-op** — the row comes back unchanged,
with no write and no event. Absent, soft-deleted or foreign `client_id` → **404**.

## 5.3 `PATCH /api/v1/stock-report/items/{client_id}/priority-order` — VERIFIED

Roles: **admin, manager, seller**.

Request: `{ "priority_order": 2 }` — a **strict integer**. The string `"2"` is a
**422**, not coerced.

Response: the same single-row shape as §5.2. `priority_order` is **1-based** within the
row's priority group.

Refusals, both 422 (§1.2 shape):

- `STOCK_REPORT_ROW_HAS_NO_PRIORITY` — the row's priority is null, so it has no group
  to order within.
- `STOCK_REPORT_TARGET_OUT_OF_RANGE` — the target is outside `1..n` for that group.

Moving to the position it already holds is a **200 no-op**.

## 5.4 `DELETE /api/v1/stock-report/items/{client_id}` — VERIFIED

Roles: **admin, manager only.** (Not worker, not seller — narrower than every other
route.) **No request body at all.**

```jsonc
{ "data": { "client_id": "sri_…" }, "ok": true, "warnings": [] }
```

**404** `"Stock report item not found."` if absent, deleted or foreign.

**This cascades.** Deleting a row deletes its assignments too — in every state,
including ones a worker is actively holding — and unsets the affected tasks'
stock-assignment flag. Expect a burst of events (§7). Confirm destructively in the UI.

## 5.5 `GET /api/v1/stock-report/items/{client_id}/assignments` — VERIFIED

Roles: **admin, manager, worker, seller**.

```jsonc
{ "data": { "stock_task_assignments": [ /* §6.2 */ ] }, "ok": true, "warnings": [] }
```

Every non-deleted assignment of the row, in **all** states — `resolved` and
`resolved_early` included, because this list is the board's traceability surface.
Ordered by `created_at, client_id`.

**404** if the row is absent, deleted or foreign — *not* an empty array.

## 5.6 `POST /api/v1/location-tracker/webhooks/stock-demand-deleted` — VERIFIED

Scanner-facing, `x-api-key`. **Not yours to call.** Newly built; documented because
its effect reaches your users.

When Scanner drops a demand rule, the matching row **and all its assignments are
deleted**, in every state — including assignments a worker is actively holding. The
row's priority group closes its gap, the row keeps its own last position on its
deleted record, and the tasks themselves are untouched and keep running. **Users
re-add by hand; there is no undo.** A later demand for the same identity creates a
**new** row, never a revival of the deleted one — so a rule that comes back comes back
empty, with no history, no assignments and no priority.

Its response, for completeness:

```jsonc
{ "data": { "results": [
    { "itemCategory": "Dining Chairs", "properties": { "wood_group": ["teak"] },
      "outcome": "deleted" } ] }, "ok": true, "warnings": [] }
```

`outcome` ∈ `deleted`, `not_found`, `category_not_found`, one per entry in request
order. `itemCategory` and `properties` are echoed back exactly as Scanner sent them.

---

# 6. Payload shapes, field by field

Each table below is **checked by a test** against the shipped serializer it names:
every field, and every nullability claim, with the condition that produces the null.
A disagreement fails the suite.

`item_category` is flattened with a dot in the tables; in JSON it is a nested object.

## 6.1 Stock report row — `serialize_stock_report_item`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `item_category.client_id` | string | no | — |
| `item_category.name` | string | no | — |
| `item_category.major_category` | string | no | — |
| `item_category.image_url` | string | yes | the category has no image; the key is always present, never omitted |
| `properties` | object of string → array of string | no | — |
| `properties_signature` | string | no | — |
| `quantity_requested` | integer | no | — |
| `quantity_in_queue` | integer | no | — |
| `quantity_in_progress` | integer | no | — |
| `quantity_awaiting` | integer | no | — |
| `priority` | `"high"`, `"medium"`, `"low"` | yes | the row is unprioritised and sits in no group |
| `priority_order` | integer | yes | the row has no priority, so it holds no position |
| `created_at` | ISO 8601 string | no | — |
| `updated_at` | ISO 8601 string | yes | the row has not been written since it was created |
| `created_by_id` | string | yes | the row was created by Scanner's demand webhook, which records no user |
| `updated_by_id` | string | yes | the last write was Scanner's, which records no user |

```jsonc
{ "client_id": "sri_…",
  "item_category": { "client_id": "cat_…", "name": "Dining Chairs",
                     "major_category": "seat", "image_url": null },
  "properties": { "wood_group": ["teak"] },   // stored, NORMALIZED — see below
  "properties_signature": "…",
  "quantity_requested": 5, "quantity_in_queue": 2,
  "quantity_in_progress": 1, "quantity_awaiting": 0,
  "priority": "high", "priority_order": 3,
  "created_at": "…", "updated_at": null,
  "created_by_id": null, "updated_by_id": null }
```

**`properties` values are always arrays of strings.** Normalization lower-cases,
trims, de-duplicates and sorts each criterion's values, and a single string becomes a
one-element list: what Scanner sent as `"Teak"` is stored and returned as `["teak"]`.
*The previous version of this document showed `{"wood_group": "teak"}` in this example.
That was a documentation defect; the code was always list-valued.*

There is no `item_type` key and no pagination key.

## 6.2 Assignment — `serialize_stock_task_assignment`

Fourteen keys: the twelve below plus `item` (§6.3) and `task` (§6.4), each an object
and each always present.

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `state` | one of the six in §6.5 | no | — |
| `stock_report_item_id` | string | no | — |
| `task_id` | string | no | — |
| `item_id` | string | no | — |
| `quantity` | integer | no | — |
| `property_mismatch_overridden` | boolean | no | — |
| `credited_history_record_id` | string | yes | the assignment has never entered `awaiting` or `resolved_early`, so no goal record was ever credited |
| `created_at` | ISO 8601 string | no | — |
| `created_by_id` | string | yes | column-nullable; every shipped creation path stamps the acting user, so in practice it is present |
| `updated_at` | ISO 8601 string | yes | the assignment has not moved since it was created |
| `updated_by_id` | string | yes | the last move was made by Scanner or by the task-state sync, neither of which records a user |

## 6.3 Item (compact) — `serialize_item_compact`

Seven keys: the six below plus `item_images`, an array (possibly empty, never null).

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `article_number` | string | yes | the item carries no article number |
| `sku` | string | yes | the item carries no SKU |
| `quantity` | integer | no | — |
| `item_category_snapshot` | string | yes | no category snapshot was taken for this item |
| `item_major_category_snapshot` | string | yes | no category snapshot was taken for this item |

## 6.4 Task (compact) — `serialize_task_compact`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `task_type` | string | no | — |
| `priority` | string | no | — |
| `state` | string | no | — |
| `title` | string | yes | the task has no title |
| `return_source` | string | yes | the task records no return source |
| `ready_by_at` | ISO 8601 string | yes | the task has no ready-by date |
| `return_method` | string | yes | the task records no return method |
| `created_at` | ISO 8601 string | no | — |
| `updated_at` | ISO 8601 string | yes | the task has not been written since it was created |
| `closed_at` | ISO 8601 string | yes | the task is not closed |
| `completed_at` | ISO 8601 string | yes | the task is not completed |

## 6.5 The six assignment states

Active: `in_queue`, `in_progress`, `awaiting`. Terminal: `resolved`, `failed`,
`resolved_early`.

**`resolved_early` means the physical item was processed by Scanner while the
assignment was still `in_queue` or `in_progress`** — finished ahead of the board's
expectation, before anyone marked the task ready. Its units are already out of the
counters, the task is still running, and the assignment is kept as the trace of what
happened. It is a success state, not an error. `resolved` is the same success reached
the expected way, from `awaiting`.

---

# 7. Events — VERIFIED

Six names, exhaustively:

| Event | `extra` |
|---|---|
| `stock_report_item:created` | `{}` |
| `stock_report_item:updated` | `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`, `priority`, `priority_order` |
| `stock_report_item:deleted` | `{}` |
| `stock_task_assignment:created` | `stock_report_item_id`, `task_id`, `state` |
| `stock_task_assignment:state-changed` | the same three |
| `stock_task_assignment:deleted` | the same three |

`state` carries any of the six assignment states.

**Which action emits what:**

| Action | Events |
|---|---|
| `POST /assignments` | `stock_task_assignment:created`, maybe `stock_report_item:updated` |
| `POST /assignments/delete` | `stock_task_assignment:deleted`, maybe `stock_report_item:updated` |
| `POST /repair` | `stock_report_item:updated` only |
| `DELETE /items/{id}` (5.4) | `stock_report_item:deleted`, one `stock_task_assignment:deleted` per assignment, and `stock_report_item:updated` for each neighbour whose position shifted |
| Scanner demand webhook | `stock_report_item:created` / `stock_report_item:updated` — never assignment events |
| Scanner items-processed | `stock_task_assignment:state-changed`, maybe `stock_report_item:updated` |
| Scanner delete webhook (5.6) | the same burst as `DELETE /items/{id}`, once per deleted row |
| `GET /consistency`, match-preview, the two read endpoints | nothing |

**A deleted row never carries an `:updated`.** Within one request the events are
coalesced to the net change per entity, and a row that is created or deleted in that
request gets only its one lifecycle event — even though its counters moved several
times on the way.

**One inconsistency worth knowing.** Most mutating endpoints de-duplicate their
events, so you get at most one `:updated` per row per request. **The items-processed
webhook does not** — it can emit several events for the same entity in one request.
Make your handlers idempotent.

# 8. What is NOT built — do not design against it

- **No pagination anywhere**, by decision.
- **No history read endpoint.** History records are written; nothing exposes them.
- **No local row creation.** Rows are created by Scanner's demand webhook only.
- **`is_stock_assignment` is not surfaced** on the task read shape.
- **No "forgotten items" view** — there is no screen that lists items Scanner resolved
  early so someone can chase the step that was skipped. It was considered and deferred.
- No batch match-preview — it is one row per call.

# 9. Backend error classes, for triage conversations

You never see these names in a response; they are here so that a bug report and the
backend log say the same word.

| Class | HTTP | Code in the body |
|---|---|---|
| `LocationTrackerWebhookAuthError` | 401 | — (Scanner-facing only) |
| `StockDemandDeadlineExceeded` | 503 | — (Scanner-facing only) |
| `StockAssignmentRefused` | 422 | `stock_assignment_refused` |
| `StockAssignmentPropertyMismatch` | 409 | `stock_assignment_property_mismatch` |

Message identities you *can* see, all 422: `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`,
`STOCK_REPORT_ROW_HAS_NO_PRIORITY`, `STOCK_REPORT_TARGET_OUT_OF_RANGE`.

# 10. If something here is wrong

Tell us; it is a defect on our side and it gets fixed. This document is now covered by
a test that reads the shipped code, so the most likely remaining errors are in the
prose, not in the tables.

This file will never be edited in place. If anything changes, a new dated file
supersedes it and this one moves to `archived/`.
