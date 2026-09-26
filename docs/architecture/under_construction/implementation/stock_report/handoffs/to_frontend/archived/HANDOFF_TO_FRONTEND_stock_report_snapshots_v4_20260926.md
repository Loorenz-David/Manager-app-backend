---
audience: frontend
subject: Stock Report — the snapshot layer, and the complete API contract as it now ships
date: 2026-09-26
status: CURRENT. This is the document to build against.
supersedes: HANDOFF_TO_FRONTEND_stock_report_snapshots_v3_20260926.md (moved to archived/, unedited)
companion: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, still current, NOT superseded)
---

# Stock Report — the snapshot layer

## 0. Which document is current

| Document | Status |
|---|---|
| **This file** | **CURRENT.** Every shape below is read out of shipping code, and `app/tests/unit/docs/test_stock_report_docs.py` compares the tables in §6 against the shipped serializers field by field. |
| `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` | **CURRENT and RATIFIED.** Match-preview semantics are unchanged. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_snapshots_v3_20260926.md` | **HISTORICAL.** The v3 you received. This file is v3 plus pagination on `GET /items` (§0.0, first entry); nothing else changed. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_snapshots_v2_20260926.md` | **HISTORICAL.** v2. v3 fixed `missing_only` (§0.0, second entry). |
| `archived/HANDOFF_TO_FRONTEND_stock_report_snapshots_20260926.md` | **HISTORICAL.** The first snapshots handoff. v2 added `priority=all` (§0.0, third entry). |
| `archived/HANDOFF_TO_FRONTEND_stock_report_api_20260922.md` | **HISTORICAL.** Superseded by the snapshots handoff. Its §1 (envelopes), §2 (auth), §4 (assignments, consistency, repair, match-preview) and §5.4–5.6 are unchanged in substance and are not repeated here; the parts that changed are below. |

## 0.0 What changed since the snapshots handoff you already have

Three changes, newest first. Nothing else moved.

### v4 — `GET /items` is paginated (breaking: the default page is 20 rows)

**Act on this one.** `GET /api/v1/stock-report/items` used to return every matching
row in one response. It now returns **at most 20** unless you ask for more, so a
screen that reads the whole board in one call will silently show only the first 20.

- **New query parameters:** `limit` (default **20**, minimum 1, maximum 200; `0`,
  a negative value or `201` → 422) and `offset` (default 0, not negative → 422).
- **New response key**, always present, including on an empty page:
  `"stock_report_items_pagination": { "has_more": <bool>, "limit": <int>, "offset": <int> }`.
  Ask for the next page with `offset = offset + limit` while `has_more` is `true`.
  It is the same shape as `GET …/snapshots/versions` (§5.9).
- **Filters apply before paging.** `priority`, `missing_only`, the category filters and
  `live_stock` narrow the set first; the pages walk that narrowed set in its usual
  order. `has_more` is about the filtered set.
- **Order is stable across pages.** Every read orders by a key that ends in the row's
  `client_id`, so pages never overlap or skip a row while the board is not changing.
  If rows are reordered or added between two page requests, re-read from `offset=0`
  — offset paging cannot follow a list that moves underneath it.
- `priority_order` is still a position **in the whole group**, not in the page: the
  `PATCH …/priority-order` target is unchanged by paging.
- There is no total count in the response. The missing counter keeps its own route
  (`GET …/snapshots/missing-summary`); a version's totals are in its `progress` (§6.8).

The updated description is the head of §5.1.

### v3 — `missing_only=true` now returns rows whose every unit is missing (fix)

**This is a bug fix to the buyer's list.** By default `GET /items` hides a snapshot
whose outstanding count, `quantity_requested − quantity_missing`, is zero or less.
That rule was also applied under `missing_only=true`, so a snapshot with **all** its
units missing (say 4 requested, 4 missing) was hidden from the one list meant to show
it, while `GET …/snapshots/missing-summary` still counted it.

- **Now:** `missing_only=true` returns **every** active snapshot with
  `quantity_missing > 0`, fully missing or not. The outstanding rule no longer applies
  to it, so `include_zero_requested` has no effect on it.
- **Consequence:** the list behind the missing-summary counter now always has as many
  rows as `items_with_missing`, when no other filter narrows it.
- The board read without `missing_only` is **unchanged**: fully missing snapshots stay
  hidden there unless `include_zero_requested=true`.
- If you worked around the bug by sending `include_zero_requested=true` together with
  `missing_only=true`, it still returns the same rows; you can drop it.

The updated descriptions are the `include_zero_requested` and `missing_only` rows of §5.1.

### v2 — `priority=all`

`GET /api/v1/stock-report/items` accepts
**`priority=all`**: every row on the board, prioritised and unprioritised together, in
one response. Before this there was no single value for that — omitting `priority`
returns only the unprioritised rows, and `priority=high,medium,low` only the
prioritised ones.

- **Order:** prioritised rows first, in board order (`high`, then `medium`, then `low`,
  each by `snapshot.priority_order`), then the unprioritised rows by the row's
  `created_at, client_id`. It is exactly `priority=high,medium,low` followed by the
  omitted-`priority` read.
- **`all` must be sent alone.** `priority=all,high` → **422
  `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`**. With `live_stock=true` it is refused like
  any other priority value (**422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`**) — a live
  read already returns every row.
- Every other filter (`include_zero_requested`, `missing_only`, the category filters)
  combines with it exactly as with a priority list.
- The response shape is unchanged (§6.1). Existing calls behave exactly as before.

The full, updated description is the `priority` row of §5.1.

## 0.1 What changed, in one paragraph

The stock report used to be one live board. It is now a **live mirror plus a snapshot
layer**. A manager opens a **version**; that freezes every live row's
`quantity_requested` into one **snapshot** per row and closes the previous version.
`priority` and `priority_order` **moved from the row to the snapshot** — every version
starts unprioritised, and a manager re-orders it or copies a previous version's order.
A snapshot carries `quantity_missing`: units the buyer still has to find, which lowers
what workers see as outstanding and is clamped automatically when someone assigns an
item. `GET /items` shows **only rows with an active snapshot**, unless `live_stock=true`.

**What you must change in the app:**

1. `row.priority` / `row.priority_order` no longer exist. Read `row.snapshot.priority`
   and `row.snapshot.priority_order`. The two `PATCH` ordering routes are **unchanged in
   path, body, roles and response key** — they now move the row's active snapshot.
2. `stock_report_item:updated` lost its two priority keys. Position changes arrive as
   **`stock_report_item_snapshot:updated`**, whose `client_id` is the **snapshot's** id
   and whose `extra.stock_report_item_id` names the row.
3. A row Scanner creates after the current version opened is **not on the board** (and
   not in `GET /items`) until the next version. Its `live_stock=true` listing carries
   `snapshot: null`.
4. Six new routes (§5). Nothing else moved.
5. **Completion never goes backwards** (added the same day, before this handoff was
   delivered): `snapshot.quantity_awaiting` keeps counting units Scanner has already
   processed (`snapshot.quantity_resolved`, §6.6), and a version carries a `progress`
   object (§6.8) on `GET …/snapshots/versions/active` (§5.12) and on every row of
   `GET …/snapshots/versions` (§5.9).

---

# Part A — the versioned board

## 5.1 `GET /api/v1/stock-report/items` — changed

Roles: **admin, manager, worker, seller**. **Paginated** (v4, §0.0): `?limit=`
(default **20**, min 1, max 200) and `?offset=` (default 0); out-of-range values → 422.

Query parameters, all optional:

| Param | Meaning |
|---|---|
| `priority=high,medium,low` | filters the **snapshot's** priority. **Omitted or empty means snapshots whose priority is NULL**, ordered by the row's `created_at, client_id` — not "all rows". **`priority=all`** (added, §0.0) means every active snapshot, prioritised first in board order then unprioritised by `created_at, client_id`; it must be the only token. Unknown token, or `all` combined with another → 422 `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`. |
| `include_zero_requested=true` | by default a snapshot with `quantity_requested − quantity_missing <= 0` is hidden — **outstanding**, not Scanner's live number. This shows it. The rule does not apply under `missing_only` (v3, §0.0). |
| `missing_only=true` | **every** active snapshot with `quantity_missing > 0`, including those whose every unit is missing — the buyer's list. The outstanding rule above does not apply here (fixed in v3, §0.0). |
| `item_major_categories`, `item_category_ids` | as before, repeated params, combined with AND. |
| `live_stock=true` | the **mirror read**: every live row, with `snapshot` attached when there is an active one and `null` otherwise; `include_zero_requested` applies to the row's own `quantity_requested`. Ordered by `created_at, client_id`. `priority` or `missing_only` together with it → 422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`. |

```jsonc
{ "data": {
    "stock_report_items": [ /* §6.1, each with a "snapshot" object */ ],
    "stock_report_items_pagination": { "has_more": true, "limit": 20, "offset": 0 }
}, "ok": true, "warnings": [] }
```

Ordering inside a priority filter is `high` before `medium` before `low`, then
`snapshot.priority_order` ascending.

## 5.2 `PATCH /items/{client_id}/priority` and 5.3 `PATCH /items/{client_id}/priority-order` — unchanged on the wire

Same paths, bodies (`{"priority": "high"|"medium"|"low"|null}` with the key required;
`{"priority_order": <strict int>}`), roles (**admin, manager, seller**), 200 no-ops and
404 boundary as before. They act on the row's **active snapshot**. One new refusal on
both: **422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`** when the row exists but has no active
snapshot (created since the last version). The response is still
`{ "data": { "stock_report_item": <row> } }` — read the new position from `snapshot`.

## 5.7 `PATCH /api/v1/stock-report/items/{client_id}/missing-quantity` — NEW

Roles: **admin, manager, worker**. (Not seller.) `client_id` is the **row's** id.

Request: `{ "quantity_missing": 3 }` — a **strict integer** (the string `"3"` is a 422),
the key is required, unknown keys are rejected (§1.3 shape). It is an **absolute
value**, never a delta.

Rule: `0 <= quantity_missing <= ceiling`, where `ceiling = max(0,
snapshot.quantity_requested − (quantity_in_queue + quantity_in_progress +
quantity_awaiting))` with `quantity_awaiting` the **snapshot's wire value** (§6.6: the
row's live awaiting plus the units Scanner already resolved) — what the frozen demand
still leaves uncovered. Above it → **422 `STOCK_REPORT_MISSING_EXCEEDS_CEILING`**, the sentence
names the ceiling. Setting the value it already holds is a **200 no-op** (no write, no
event). No active snapshot → 422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`. Absent, deleted or
foreign row → 404.

Response: `{ "data": { "stock_report_item": <row> } }`. Event: one
`stock_report_item_snapshot:updated`.

**The automatic half.** When an assignment is **created** on a row (`POST /assignments`),
the uncovered remainder shrinks; if `quantity_missing` is now above the new ceiling it is
clamped down to it, and a `stock_report_item_snapshot:updated` is emitted for it in the
same burst. Someone marked the units missing, a manager found one and assigned it: the
missing count follows. No other move (state sync, deletion, Scanner processing) touches
`quantity_missing`.

## 5.8 `POST /api/v1/stock-report/snapshots/versions` — NEW

Roles: **admin, manager**. **No body.**

Opens a new version: every live row (zero-requested rows included) gets one snapshot
with its current `quantity_requested` frozen, `priority: null`, `quantity_missing: 0`.
The previously active version, if any, is closed in the same transaction and its
snapshots freeze their counters as they stood at that moment. Two managers opening at
once serialize; the second closes the first's version.

```jsonc
{ "data": { "stock_report_snapshot_version": { /* §6.7 */ } }, "ok": true, "warnings": [] }
```

Events: `stock_report_snapshot_version:closed` (when one was open) then
`stock_report_snapshot_version:created`. **Refetch the board** on `:created` — every
row's snapshot is new, and priorities are all null again.

An empty workspace still gets a version, with `snapshot_count: 0`.

## 5.9 `GET /api/v1/stock-report/snapshots/versions` — NEW

Roles: **admin, manager, worker, seller**. `?limit=` (default **20**, max 200; 201 → 422)
and `?offset=` (default 0). Newest first (`active_at` descending).

```jsonc
{ "data": {
    "stock_report_snapshot_versions": [
      { /* §6.7 fields */ "client_id": "srv_…", "closed_at": null, "progress": { /* §6.8 */ } },
      { /* … */ "closed_at": "2026-09-20T09:00:00+00:00", "progress": { /* §6.8, frozen */ } }
    ],
    "stock_report_snapshot_versions_pagination": { "has_more": false, "limit": 20, "offset": 0 }
}, "ok": true, "warnings": [] }
```

The active version is the one whose `closed_at` is `null` — at most one. **Every row
carries `progress`** (§6.8) — the same object §5.12 returns for the active version, from
the same engine, so the history screen and the "current version" card render the same
numbers. A closed version's progress is frozen (its counters were copied at close).

## 5.10 `POST /api/v1/stock-report/snapshots/versions/{client_id}/apply-priorities` — NEW

Roles: **admin, manager**. **No body.** `client_id` is a **closed** version.

Copies that version's `priority` / `priority_order` onto the **active** version: a row
present in both takes the source's priority; a row absent from the source **keeps its
current** priority; each priority group is renumbered densely with the source's members
first (in source order) and the kept members after (in their current order). One
history record per changed row; one `stock_report_item_snapshot:updated` per changed
snapshot.

```jsonc
{ "data": { "changed": 4, "stock_report_items": [ /* §6.1, the changed rows only */ ] }, "ok": true, "warnings": [] }
```

Naming the active version → **422 `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`**. Absent or
foreign version → 404 `Stock report snapshot version not found.`

## 5.11 `GET /api/v1/stock-report/snapshots/missing-summary` — NEW

Roles: **admin, manager, worker, seller**. No parameters.

```jsonc
{ "data": { "quantity_missing_total": 7, "items_with_missing": 3 }, "ok": true, "warnings": [] }
```

Both over the **active** snapshots of the workspace. The list behind the counter is
`GET /items?missing_only=true`.

## 5.12 `GET /api/v1/stock-report/snapshots/versions/active` — NEW

Roles: **admin, manager, worker, seller**. No parameters.

```jsonc
{ "data": { "stock_report_snapshot_version": { /* §6.7 fields */ "closed_at": null, "progress": { /* §6.8 */ } } },
  "ok": true, "warnings": [] }
```

When the workspace has **no version yet** it is a **200** with
`{ "stock_report_snapshot_version": null }` — the board's normal empty state
(`GET /items` is empty then too), not an error.

## 5.4 `DELETE /items/{client_id}` and 5.6 the Scanner delete webhook — one addition

Unchanged, plus: the row's active snapshot is **closed** with it and keeps its last
position; its neighbours in the priority group shift and each emits
`stock_report_item_snapshot:updated`. The version stays open. A later demand for the
same identity creates a new row with **no snapshot** until the next version.

---

# 6. Payload shapes, field by field

Each table below is **checked by a test** against the shipped serializer it names:
every field, and every nullability claim, with the condition that produces the null.
`item_category` is flattened with a dot; in JSON it is a nested object.

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
| `created_at` | ISO 8601 string | no | — |
| `updated_at` | ISO 8601 string | yes | the row has not been written since it was created |
| `created_by_id` | string | yes | the row was created by Scanner's demand webhook, which records no user |
| `updated_by_id` | string | yes | the last write was Scanner's, which records no user |

Plus one key the table above does not list because it is an object, not a column:
**`snapshot`** — a §6.6 object, or **`null`** only on a `live_stock=true` read of a row
that has no active snapshot. On the default read it is never null.

`quantity_requested` here is **Scanner's live number**; the frozen one the board works
against is `snapshot.quantity_requested`. **There are no `priority` / `priority_order`
keys on the row.**

```jsonc
{ "client_id": "sri_…",
  "item_category": { "client_id": "cat_…", "name": "Dining Chairs", "major_category": "seat", "image_url": null },
  "properties": { "wood_group": ["teak"] },
  "properties_signature": "…",
  "quantity_requested": 7, "quantity_in_queue": 2, "quantity_in_progress": 1, "quantity_awaiting": 0,
  "created_at": "…", "updated_at": null, "created_by_id": null, "updated_by_id": null,
  "snapshot": { "client_id": "srs_…", "version_id": "srv_…", "stock_report_item_id": "sri_…",
                "quantity_requested": 5, "quantity_in_queue": 2, "quantity_in_progress": 1, "quantity_awaiting": 0,
                "quantity_missing": 1, "quantity_resolved": 0, "priority": "high", "priority_order": 3,
                "active_at": "…", "closed_at": null, "created_at": "…", "updated_at": "…", "updated_by_id": "usr_…" } }
```

## 6.6 Item snapshot — `serialize_stock_report_item_snapshot`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `version_id` | string | no | — |
| `stock_report_item_id` | string | no | — |
| `quantity_requested` | integer | no | — |
| `quantity_in_queue` | integer | no | — |
| `quantity_in_progress` | integer | no | — |
| `quantity_awaiting` | integer | no | — |
| `quantity_missing` | integer | no | — |
| `quantity_resolved` | integer | no | — |
| `priority` | `"high"`, `"medium"`, `"low"` | yes | the snapshot is unprioritised and sits in no group |
| `priority_order` | integer | yes | the snapshot has no priority, so it holds no position (the two are always both null or both set) |
| `active_at` | ISO 8601 string | no | — |
| `closed_at` | ISO 8601 string | yes | the snapshot is active; set when its version closed or its row was deleted |
| `created_at` | ISO 8601 string | no | — |
| `updated_at` | ISO 8601 string | yes | no priority, order or missing quantity has been written since creation |
| `updated_by_id` | string | yes | the last write was the automatic clamp, a Scanner-caused cascade, or there was none |

**`quantity_requested` is frozen.** `quantity_in_queue` and `quantity_in_progress` are
the **row's live values while the snapshot is active** and its own frozen copies once
`closed_at` is set — so on the board `snapshot.quantity_in_queue` always equals
`row.quantity_in_queue`.

**`quantity_awaiting` is different: it never goes down because Scanner processed a
shelf.** When Scanner resolves an assignment, the *row's* awaiting drops (those units
left the counters) but the snapshot remembers them in `quantity_resolved`, and
`snapshot.quantity_awaiting` = (row's live awaiting, or the frozen one once closed) **+
`quantity_resolved`**. So `snapshot.quantity_awaiting >= row.quantity_awaiting`, always,
and the difference is exactly `quantity_resolved`. It *does* go down when an assignment
is moved back out of awaiting into `in_queue` / `in_progress`, or deleted, or fails —
the same rule as the goal credit. `quantity_resolved` only ever rises within a version
and starts at 0 in a new one.

The outstanding count the worker cares about is `quantity_requested − quantity_missing
− (in_queue + in_progress + awaiting)`, never below 0 — and with the awaiting above it
decreases as Scanner processes items, as it should.

## 6.7 Version — `serialize_stock_report_snapshot_version`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `active_at` | ISO 8601 string | no | — |
| `closed_at` | ISO 8601 string | yes | the version is the active one |
| `snapshot_count` | integer | no | — |
| `created_at` | ISO 8601 string | no | — |
| `created_by_id` | string | yes | column-nullable; every shipped path stamps the acting user |
| `closed_by_id` | string | yes | the version is still active, or was closed by a path with no user |

The two version reads (§5.9, §5.12) add a **`progress`** key beside these fields. It is
computed, not a column, so it is described in §6.8 rather than in this table.

## 6.8 Version progress — computed, `progress` on §5.9 and §5.12

Over the version's snapshots **whose `priority` is set** (that is what the version "set
out to do") and whose row has not been deleted since (Scanner withdrew that goal).
Every key is a non-negative integer and is always present; the three `by_priority`
keys are always present too, zeros included.

```jsonc
"progress": {
  "items_total": 3,          // prioritised snapshots counted
  "items_completed": 1,      // of those, how many have awaiting >= target
  "quantity_requested": 21,  // Σ frozen requested
  "quantity_missing": 2,     // Σ quantity_missing
  "quantity_target": 19,     // Σ max(0, requested − missing)   ← the denominator
  "quantity_in_queue": 3,    // Σ in_queue   (live while active, frozen once closed)
  "quantity_in_progress": 1, // Σ in_progress
  "quantity_awaiting": 9,    // Σ the §6.6 wire awaiting (includes resolved)
  "quantity_resolved": 4,    // Σ quantity_resolved (already inside quantity_awaiting)
  "quantity_completed": 9,   // Σ min(target_i, awaiting_i)      ← the numerator
  "by_priority": {
    "high":   { /* the same ten keys, for the high group */ },
    "medium": { /* … */ },
    "low":    { /* … */ }
  }
}
```

- **The bar is `quantity_completed / quantity_target`.** A zero target means nothing
  has been prioritised yet; render that state rather than dividing.
- `quantity_completed` is capped **per item**, so an over-assigned row cannot cover
  another row's shortfall; `quantity_awaiting` is the raw sum if you want to show it.
- `quantity_in_queue + quantity_in_progress` is the work in flight that has not yet
  reached the shelf.
- A closed version's numbers are frozen at the moment it closed; the active version's
  move live. Resolution by Scanner never lowers `quantity_awaiting` or
  `quantity_completed` (§6.6).

## 6.2 Assignment — `serialize_stock_task_assignment` — unchanged

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

## 6.3 Item (compact) — `serialize_item_compact` — unchanged

Seven keys: the six below plus `item_images`, an array (possibly empty, never null).

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `article_number` | string | yes | the item carries no article number |
| `sku` | string | yes | the item carries no SKU |
| `quantity` | integer | no | — |
| `item_category_snapshot` | string | yes | no category snapshot was taken for this item |
| `item_major_category_snapshot` | string | yes | no category snapshot was taken for this item |

## 6.4 Task (compact) — `serialize_task_compact` — unchanged

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

## 6.5 The six assignment states — unchanged

Active: `in_queue`, `in_progress`, `awaiting`. Terminal: `resolved`, `failed`,
`resolved_early`. Semantics as in the superseded document.

---

# 7. Events

Nine names, exhaustively:

| Event | `client_id` | `extra` |
|---|---|---|
| `stock_report_item:created` | the row | `{}` |
| `stock_report_item:updated` | the row | `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting` — **no priority keys any more** |
| `stock_report_item:deleted` | the row | `{}` |
| `stock_report_item_snapshot:updated` | **the snapshot** | `stock_report_item_id`, `version_id`, `priority`, `priority_order`, `quantity_missing`, `quantity_resolved` |
| `stock_report_snapshot_version:created` | the version | `snapshot_count` |
| `stock_report_snapshot_version:closed` | the version | `snapshot_count` |
| `stock_task_assignment:created` | the assignment | `stock_report_item_id`, `task_id`, `state` |
| `stock_task_assignment:state-changed` | the assignment | the same three |
| `stock_task_assignment:deleted` | the assignment | the same three |

**Which action emits what:**

| Action | Events |
|---|---|
| `POST /assignments` | `stock_task_assignment:created`, maybe `stock_report_item:updated`, maybe `stock_report_item_snapshot:updated` (the clamp) |
| `POST /assignments/delete` | `stock_task_assignment:deleted`, maybe `stock_report_item:updated` |
| the two `PATCH` ordering routes | `stock_report_item_snapshot:updated` for the mover and each shifted neighbour |
| `PATCH …/missing-quantity` | one `stock_report_item_snapshot:updated` |
| `POST /snapshots/versions` | `stock_report_snapshot_version:closed` (if one was open), `stock_report_snapshot_version:created` |
| `POST …/apply-priorities` | `stock_report_item_snapshot:updated` per changed snapshot |
| `POST /repair` | `stock_report_item:updated` and/or `stock_report_item_snapshot:updated` for what it changed |
| `DELETE /items/{id}` | `stock_report_item:deleted`, one `stock_task_assignment:deleted` per assignment, `stock_report_item_snapshot:updated` per shifted neighbour |
| Scanner demand webhook | `stock_report_item:created` / `stock_report_item:updated` — never assignment or snapshot events |
| Scanner items-processed | `stock_task_assignment:state-changed`, maybe `stock_report_item:updated`, and one `stock_report_item_snapshot:updated` per row that has an active snapshot (its `quantity_resolved` rose — refresh `snapshot.quantity_awaiting` and the version progress from it) |
| Scanner delete webhook | the same burst as `DELETE /items/{id}`, once per deleted row |
| the read endpoints, match-preview, `GET /consistency` | nothing |

Within one request events are coalesced to the net change per entity: a row or
snapshot gets at most one `:updated`, a deleted row gets only its `:deleted`, and a
snapshot whose row is deleted in that request gets nothing. **The items-processed
webhook still does not de-duplicate** — keep handlers idempotent.

# 8. Backend error classes and identities, for triage

Classes (never in a response body): `LocationTrackerWebhookAuthError` (401),
`StockDemandDeadlineExceeded` (503), `StockAssignmentRefused` (422,
`stock_assignment_refused`), `StockAssignmentPropertyMismatch` (409,
`stock_assignment_property_mismatch`).

Message identities you can see, all 422, as the leading token of `error`:
`STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`, `STOCK_REPORT_ROW_HAS_NO_PRIORITY`,
`STOCK_REPORT_TARGET_OUT_OF_RANGE`, `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`,
`STOCK_REPORT_MISSING_EXCEEDS_CEILING`, `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`,
`STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`.

# 9. What is NOT built

- No backfill: after deploy there is **no version**. The board is empty until a manager
  opens the first one; the old row priorities were dropped, by decision.
- No scheduled activation (`active_at` always equals creation time).
- No read of a closed version's **snapshots** (the versions list carries the version
  row and its `progress`, not the per-row snapshots behind it). Ask if you need it; it
  is a small addition.
- No total count on `GET /items` (it pages with `has_more`), no read of
  `stock_report_history_records`, no local row creation — as before.

# 10. If something here is wrong

Tell us; it is a defect on our side and it gets fixed. This file will never be edited
in place: if anything changes, a new dated file supersedes it and this one moves to
`archived/`.
