---
audience: frontend
subject: Stock Report — draft versions, scheduled activation, requested-quantity refresh (the complete contract)
date: 2026-09-27
status: CONTRACT, published before the backend is built. Build against it now; it is NOT live yet (§0.2).
extends: HANDOFF_TO_FRONTEND_stock_report_snapshots_v6_20260926.md (still CURRENT for what ships today; it moves to archived/, unedited, the day this contract goes live)
companion: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, unchanged)
source: backend plan update_stock_report/draft_versions_plan.md rev 3 + projections r0/r1
---

# Stock Report — draft versions

## 0. Which document is current

| Document | Status |
|---|---|
| **This file (v7)** | **CONTRACT, not yet live.** Every route, shape, identity and event the drafts capability will ship. The backend is built to it. On the day it ships, the backend's docs guard (`app/tests/unit/docs/test_stock_report_docs.py`) is pointed at this file and compares its §6 tables and §7–§8 names with the shipped code, field by field. |
| `HANDOFF_TO_FRONTEND_stock_report_snapshots_v6_20260926.md` | **CURRENT until then.** Describes what the server does today. Everything in v6 not restated here is unchanged by v7. |
| `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` | **CURRENT and RATIFIED.** Unchanged. |

## 0.0 What v7 changes, in one list

1. A version has a third state, **draft**: frozen like any version, invisible on the board, editable,
   deletable. A version's state is read from the new **`state`** field (`draft | active | closed`).
2. **`active_at` becomes nullable** on the version and on the item snapshot (null while draft). This is a
   **breaking nullability change** for any code that formats `active_at` unconditionally.
3. **`GET …/snapshots/versions` lists drafts too, first**, unless you send `state=` (§5.9).
4. Eight **new routes** (§5.13–5.20): read one version, activate, refresh requested, edit a version
   (title and schedule), delete a draft, and the three row edits **inside a version**.
5. Three routes gain an **optional body**, and calls without a body behave exactly as in v6:
   `POST …/snapshots/versions` (§5.8), `POST …/apply-priorities` (§5.10), and the new activate route.
6. `GET /items` gains **`version_id`** (§5.1): read any version's rows (a draft to prepare it, a closed one
   to browse history).
7. **`stock_report_item_snapshot:updated` now also fires for drafts**, and its `extra` gains
   **`quantity_requested`** (§7). **You must filter it by `extra.version_id`** (§0.1).
8. Four new version events: `stock_report_snapshot_version:activated`, `:refreshed`, `:updated`, `:deleted`.
9. **Completion can now go backwards, in one case only:** a refresh re-freezes what a version set out to do
   (§5.18). v6's "completion never goes backwards" still holds for everything else.
10. `snapshot_count` is **no longer fixed for life** (§6.7).

## 0.1 What you must change in the app, before drafts are used in production

These two are **required**. Today's socket code (`packages/stock-report/src/socket-events.ts`,
`applySnapshotUpdate`) finds the board row by `extra.stock_report_item_id` and never looks at `version_id`,
so a manager reordering a draft would repaint the live board on every connected screen.

1. **Apply `stock_report_item_snapshot:updated` only to views of `extra.version_id`.** The board shows the
   active version; a draft page shows its draft. An event for another version is ignored by that view.
2. **On `stock_report_snapshot_version:activated`, refetch the board, the active version, the versions list
   and the missing summary.** A version went live, and no per-row events accompany it (§5.17). On
   `:refreshed`, refetch every view of that version (§5.18).

Also:

3. Everywhere you render a version, handle `active_at: null` and `closed_at: null` together (a draft), and
   prefer `state` over deriving it from the two dates.
4. The versions screen now receives drafts. Filter with `state=` where you want only history.
5. Manual activation does **not** use the draft's stored refresh choice (§5.17). Send it in the body if you
   want it honoured.

## 0.2 Status and sequencing

- **Build against this now, as if it were already implemented.** Treat every shape, route name, identity and
  event here as the backend's truth, and finish your implementation against it. You never wait on the backend.
- **If the backend ends up differing, the change comes to you afterwards.** The backend ships a new dated
  handoff (**v8**) that lists exactly what differs from this file. You then align with v8 as a follow-up
  change. Nothing you built against v7 is wasted, and nothing in v7 changes under you. This file is never
  edited in place.
- **Not live until** v6 moves to `archived/` and this file's §0 row reads CURRENT in the next issued
  handoff index. Until then the server answers as v6.
- **One backend decision is still open, and it does not change any shape.** It covers which scheduled
  activation wins when two are due at the same time, or when a manager already published by hand
  (§5.21, last bullet). Handle `stock_report_snapshot_version:updated` by refetching the versions list, and
  either outcome renders correctly.

---

# Part A — routes

Envelopes, auth and the 422 request-validation shape are as in v6 and its archived predecessor (§1). All paths
are under `/api/v1/stock-report`. "404 version" means **404 `Stock report snapshot version not found.`**
for an absent or other-workspace version id.

## 5.1 `GET /items` — gains `version_id`

Roles: **admin, manager, worker, seller** (unchanged). All v6 parameters unchanged.

| Param | Meaning |
|---|---|
| `version_id` omitted | **unchanged:** the active version's rows. This is the board. Drafts never appear here. |
| `version_id=<srv_…>` | that version's rows, **in any state**: a draft (to prepare it) or a closed version (to browse history). `priority`, `include_zero_requested`, `missing_only`, the category filters, `limit`/`offset` and the ordering all apply exactly as on the board, scoped to that version. Absent/foreign → 404 version. With `live_stock=true` → **422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`**. |

- Each row's `snapshot` is **that version's** snapshot, never null on this read.
- Counters: an **open** snapshot (draft or active) shows the row's **live** `quantity_in_queue`,
  `quantity_in_progress` and `quantity_awaiting` beside its frozen `quantity_requested`, which is the draft page's
  guide. A closed snapshot shows its frozen copies.
- Rows deleted since (by a user or Scanner) are **not listed**, in any state. That matches `progress`, which
  excludes them, but it means the list can be shorter than `filtered_snapshot_count`.

## 5.2 / 5.3 / 5.7 `PATCH /items/{client_id}/priority | priority-order | missing-quantity` — unchanged on the wire

Same paths, bodies, roles, refusals and response as v6. They are now **the active-version shortcut** for
the §5.14–5.16 routes. One behaviour to know: a PATCH that arrives while a version is being activated waits,
then applies to the **newly active** version, exactly as it does today when a manager opens a version.

## 5.4 `DELETE /items/{client_id}` and the Scanner delete webhook — one addition

As v6, plus: the row is removed **from every draft** that holds it. Its draft snapshots are deleted, the
draft's priority group closes the gap, and that draft's `snapshot_count` drops by 1. No snapshot event is sent
for them (the row's `stock_report_item:deleted` covers it). If a draft page is open, refetch it on
`stock_report_item:deleted`.

## 5.8 `POST /snapshots/versions` — gains an optional body

Roles: **admin, manager** (unchanged). **No body → exactly v6** (a new active version).

```jsonc
{ "draft": false,                                   // bool, default false
  "title": null,                                    // string ≤ 200 or null; trimmed; "" or spaces → null
  "scheduled_activation_at": null,                  // draft only — ISO 8601 WITH offset ("…Z" or "…+02:00")
  "scheduled_activation_refreshes_requested": false // draft only — bool
}
```

- Unknown keys → 422 (request validation).
- `draft: false`: a new **active** version, as v6, with the title stored. Sending either schedule key at all
  (even `null` or `false`) with `draft: false` → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**. Omit them.
- `draft: true`: a **draft**. It freezes every live row's `quantity_requested` exactly as a new version does, but the
  active version is **not** closed and the board does not change. Many drafts may exist.
- `scheduled_activation_at` without an offset → 422 (request validation). At or before now →
  **422 `STOCK_REPORT_SCHEDULE_IN_THE_PAST`**.

Response (unchanged key): `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ } } }`.

Events: `draft: false` → `stock_report_snapshot_version:closed` (if one was open) then `:created`, as in v6.
`draft: true` → `:created` only, with `extra.state: "draft"`. (v6 code refetches the board on any `:created`;
for a draft that refetch is harmless but unnecessary. Check `extra.state`.)

## 5.9 `GET /snapshots/versions` — gains `state`

Roles: **admin, manager, worker, seller** (unchanged). Pagination and `priority` unchanged.

| Param | Meaning |
|---|---|
| `state` omitted | **every** version: drafts, the active one, closed ones |
| `state=draft` / `active` / `closed` | only that state (one value) |
| anything else | **422 `STOCK_REPORT_UNKNOWN_VERSION_STATE`** |

**Order:** drafts first (newest created first), then the active and closed versions by `active_at` newest
first. The exact key is `active_at DESC NULLS FIRST, created_at DESC, client_id DESC`.

Each row is §6.7 plus `filtered_snapshot_count` and `progress` (§6.8), as in v6. A **draft's `progress` is a
live preview**: the rows' live counters measured against the draft's frozen requested and missing.

## 5.10 `POST /snapshots/versions/{client_id}/apply-priorities` — target becomes selectable

Roles: **admin, manager** (unchanged). `{client_id}` is still the **source**. Body optional:

```jsonc
{ "target_version_id": null }   // null or omitted → the active version (v6); a draft's id → that draft
```

- The source may now be **closed, active or a draft**.
- The target must be open (the active version or a draft). A closed target → **422 `STOCK_REPORT_TARGET_VERSION_IS_CLOSED`**.
  Absent/foreign source or target → 404 version.
- Source is the active version and the target is omitted → **422 `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`**
  (the v6 refusal, kept). Any other source = target → **422 `STOCK_REPORT_SOURCE_IS_TARGET`**.
- Target omitted and no active version → **200 with `changed: 0`** (as in v6).
- The merge rule is unchanged from v6.

Response: `{ "data": { "changed": 4, "stock_report_items": [ /* §6.1, the changed rows, each with the TARGET version's snapshot */ ] } }`.
Events: one `stock_report_item_snapshot:updated` per changed snapshot, whose `extra.version_id` is the target.

## 5.13 `GET /snapshots/versions/{client_id}` — NEW

Roles: **admin, manager, worker, seller**. `?priority=` as on §5.9. Any state.

```jsonc
{ "data": { "stock_report_snapshot_version": { /* §6.7 */ "filtered_snapshot_count": 12, "progress": { /* §6.8 */ } } } }
```

Absent/foreign → 404 version. `GET /snapshots/versions/active` keeps its v6 meaning: it never returns a draft,
and it is 200 with `null` when there is no active version.

## 5.14 / 5.15 / 5.16 Row edits inside a version — NEW

The frontend is always inside one version: the versions page lists the cards, you open one, you edit its rows.
Each route takes the version in the path and the **row's** id as `{client_id}`.

| Route | Body (as the v6 twin) | Roles (as the v6 twin) |
|---|---|---|
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/priority` | `{"priority": "high"\|"medium"\|"low"\|null}` | **admin, manager, seller** |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/priority-order` | `{"priority_order": <strict int>}` | **admin, manager, seller** |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/missing-quantity` | `{"quantity_missing": <strict int>}` | **admin, manager, worker** |

- They work on **the active version and on drafts** (send the active version's id to edit the board this way).
- Version absent/foreign → 404 version. Version closed → **422 `STOCK_REPORT_VERSION_IS_CLOSED`**.
  Row absent, deleted or foreign → **404 `Stock report item not found.`** A live row with no snapshot in
  that version (created after the draft) → **404 `Stock report item not found.`**
- Groups are **per version**: a draft's `high` group is numbered 1..n independently of the board's.
  `STOCK_REPORT_ROW_HAS_NO_PRIORITY`, `STOCK_REPORT_TARGET_OUT_OF_RANGE` and
  `STOCK_REPORT_MISSING_EXCEEDS_CEILING` behave as in v6, within that version. On a draft the missing ceiling
  is `quantity_requested − (live in_queue + in_progress + awaiting)` (a draft has no resolved units).
- Setting the value already held → 200 no-op, no event.
- Response: `{ "data": { "stock_report_item": <§6.1 row, whose snapshot is THIS version's> } }`.
- Events: `stock_report_item_snapshot:updated` for the mover and each shifted neighbour, with `extra.version_id`.
- A draft's missing count is a **guide**. When a worker assigns an item on the board, only the **active**
  snapshot is clamped; a draft keeps its value until it is refreshed or activated, and both clamp it then.

## 5.17 `POST /snapshots/versions/{client_id}/activate` — NEW

Roles: **admin, manager**. Body optional: `{ "refresh_quantity_requested": false }` (bool, default `false`).

Publishes a draft as the board, in one transaction:

1. The current active version (if any) **closes** exactly as when a version is opened (counters frozen).
2. Rows Scanner created after the draft was made **join it** (unprioritised, missing 0).
3. `refresh_quantity_requested: true` → every snapshot's `quantity_requested` is re-frozen from the live rows now.
   `false` → the draft keeps what it froze. **Manual activation uses only the body; it ignores the draft's
   stored `scheduled_activation_refreshes_requested`.**
4. Each snapshot's `quantity_missing` is kept, but clamped to what is still uncovered now.
5. The draft becomes active: `state: "active"`, `active_at` set on it and on every snapshot. Its schedule is cleared.

- Not a draft (active or closed) → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**. Absent/foreign → 404 version.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 of the now-active version */ } } }`.
- Events: `stock_report_snapshot_version:closed` (the previous one, if any), then
  **`stock_report_snapshot_version:activated`**. **There are no per-row snapshot events.** Refetch (§0.1).

## 5.18 `POST /snapshots/versions/{client_id}/refresh-requested` — NEW

Roles: **admin, manager**. **No body.** Target: a draft **or the active version**.

Re-freezes `quantity_requested` from the live rows, adds rows created since, and clamps `quantity_missing`
to the new ceiling. It does not open a new version.

- Closed → **422 `STOCK_REPORT_VERSION_IS_CLOSED`**. Absent/foreign → 404 version.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ }, "changed": 3, "added": 1 } }`.
  `changed` counts snapshots whose requested changed; `added` counts rows that joined.
- Events: `stock_report_item_snapshot:updated` per snapshot whose requested or missing changed, then
  **`stock_report_snapshot_version:refreshed`**. Added rows have no event of their own; refetch the version's rows on `:refreshed`.
- **Completion can drop.** On the active version, a raised `quantity_requested` lowers `progress.quantity_target`'s
  coverage and can un-complete an item. This is the one exception to v6's "completion never goes backwards".

## 5.19 `PATCH /snapshots/versions/{client_id}` — NEW (title and schedule)

Roles: **admin, manager**. Body: any subset of

```jsonc
{ "title": "Upholstery push",                        // any state; null clears; trimmed, "" → null
  "scheduled_activation_at": "2026-10-05T06:00:00+02:00", // drafts only; null unschedules
  "scheduled_activation_refreshes_requested": true    // drafts only
}
```

- **An omitted key is left untouched. A key sent as `null` clears it.** `{}` → 200, nothing changes, no event.
  Unknown keys → 422 (request validation).
- Either schedule key sent (even as `null`) on an active or closed version → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**.
- `scheduled_activation_at` without an offset → 422 (request validation). At or before now →
  **422 `STOCK_REPORT_SCHEDULE_IN_THE_PAST`**.
- Setting only the refresh choice on an unscheduled draft simply stores it.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ } } }`.
- Event: `stock_report_snapshot_version:updated` when something changed.

## 5.20 `DELETE /snapshots/versions/{client_id}` — NEW (drafts only)

Roles: **admin, manager**. Hard delete: the draft and its snapshots are gone, and its schedule is cancelled.
The board is untouched.

- Not a draft → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**. Absent/foreign → 404 version.
- Response: `{ "data": { "client_id": "srv_…" } }`.
- Event: `stock_report_snapshot_version:deleted`.

## 5.21 Scheduled activation — behaviour (no route of its own)

- A draft with `scheduled_activation_at` activates itself **at or after** that time, through a background
  worker. **No latency is promised.** It is usually seconds later, but it can be much later if the backend's worker
  processes were down. **A late activation still happens** when they come back (owner ruling).
- It behaves as §5.17 with `refresh_quantity_requested` = the draft's stored
  `scheduled_activation_refreshes_requested`, **read at that moment**. Every edit you make to a scheduled draft
  before then is what gets published.
- Same events as §5.17; `:activated` carries `extra.scheduled: true`.
- Moving the date, clearing it, activating by hand or deleting the draft cancels the pending activation. A
  moved schedule **never** fires at the old time.
- **Overdue drafts:** a draft whose `scheduled_activation_at` is in the past has not been activated yet. The
  activation is either still being processed or it failed. Show it as overdue. A manager can activate it by hand.
- **Open backend decision:** when two scheduled drafts are due together, or a manager activated a newer board
  by hand after a draft's scheduled time, the rule for which one wins is not ratified yet. The candidate rule
  is: skip the older schedule, clear it, and emit `:updated` for it. No shape changes either way.

---

# 6. Payload shapes, field by field

The tables below are what the docs guard will compare with the shipped serializers when this file goes live.
§6.1–§6.5 are **unchanged from v6**. They are repeated here only because this file must be complete on its own.

## 6.1 Stock report row — `serialize_stock_report_item` — unchanged

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

Plus **`snapshot`**, a §6.6 object. It is `null` only on a `live_stock=true` read of a row with no active snapshot.
On a `version_id` read (§5.1) or a row-edit response (§5.14–5.16) it is **that version's** snapshot.

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

Active: `in_queue`, `in_progress`, `awaiting`. Terminal: `resolved`, `failed`, `resolved_early`.

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
| `active_at` | ISO 8601 string | yes | the snapshot belongs to a draft that has not been activated |
| `closed_at` | ISO 8601 string | yes | the snapshot is open: its version is a draft or the active one; set when its version closed or its row was deleted from the active version |
| `created_at` | ISO 8601 string | no | — |
| `updated_at` | ISO 8601 string | yes | no priority, order, missing or requested quantity has been written since creation |
| `updated_by_id` | string | yes | the last write was the automatic clamp, a Scanner-caused cascade, or there was none |

Counters: an **open** snapshot (draft or active) reports the row's live `quantity_in_queue` and
`quantity_in_progress`, and `quantity_awaiting` = live awaiting + `quantity_resolved`. A closed one reports its frozen
copies, as in v6. `quantity_resolved` is always 0 on a draft and restarts at 0 when a version is activated.
`quantity_requested` is frozen except when a refresh or an activation with refresh re-freezes it (§5.17, §5.18).

## 6.7 Version — `serialize_stock_report_snapshot_version`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `title` | string | yes | no title was given, or it was cleared |
| `active_at` | ISO 8601 string | yes | the version is a draft |
| `closed_at` | ISO 8601 string | yes | the version is a draft or the active one |
| `scheduled_activation_at` | ISO 8601 string | yes | the version has no pending schedule; always null once active or closed |
| `scheduled_activation_refreshes_requested` | boolean | no | — |
| `snapshot_count` | integer | no | — |
| `created_at` | ISO 8601 string | no | — |
| `created_by_id` | string | yes | column-nullable; every shipped path stamps the acting user |
| `closed_by_id` | string | yes | the version is a draft or still active, or was closed by a path with no user |

Plus **`state`** — one of `"draft"`, `"active"`, `"closed"`, **always present, never null**, on every version
payload (reads and command responses). It is computed rather than stored, which is why it sits outside the table.

The version reads (§5.9, §5.13, and `GET …/versions/active`) add `filtered_snapshot_count` and `progress`
beside these fields, exactly as in v6. The command responses (§5.8, §5.17, §5.18, §5.19) carry the fields above **without**
`progress`. Refetch a read if you need the numbers.

**`snapshot_count` is no longer fixed for life.** It counts the version's snapshots, deleted rows included, and:
- it **rises** when a refresh or an activation adds rows created since (§5.17 step 2, §5.18);
- on a **draft** it **falls** by 1 when a row is deleted (the snapshot is removed, §5.4). Active and closed
  versions keep counting deleted rows, as in v6.

**`state` is the field to read.** Derived from the dates it is `draft` = both null, `active` = `active_at` set and
`closed_at` null, `closed` = both set. `active_at` is when the version actually went live. For a scheduled
activation, that is when the worker ran it, not the scheduled time.

## 6.8 Version progress — unchanged shape

As v6. Two new cases:
- a **draft's** progress is a live preview: live counters against the draft's frozen requested and missing,
  `quantity_resolved` 0;
- after a **refresh**, `quantity_requested`, `quantity_target` and `items_completed` can go **down** (§5.18).

---

# 7. Events

Thirteen names, exhaustively:

| Event | `client_id` | `extra` |
|---|---|---|
| `stock_report_item:created` | the row | `{}` |
| `stock_report_item:updated` | the row | `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting` |
| `stock_report_item:deleted` | the row | `{}` |
| `stock_report_item_snapshot:updated` | **the snapshot** | `stock_report_item_id`, `version_id`, `priority`, `priority_order`, `quantity_missing`, `quantity_resolved`, **`quantity_requested`** (new) |
| `stock_report_snapshot_version:created` | the version | `snapshot_count`, **`state`**, **`title`** (new) |
| `stock_report_snapshot_version:closed` | the version | `snapshot_count` |
| `stock_report_snapshot_version:activated` | the version | `snapshot_count`, `title`, `refresh_quantity_requested`, `scheduled` |
| `stock_report_snapshot_version:refreshed` | the version | `snapshot_count`, `changed`, `added` |
| `stock_report_snapshot_version:updated` | the version | `title`, `scheduled_activation_at`, `scheduled_activation_refreshes_requested` |
| `stock_report_snapshot_version:deleted` | the version | `{}` |
| `stock_task_assignment:created` | the assignment | `stock_report_item_id`, `task_id`, `state` |
| `stock_task_assignment:state-changed` | the assignment | the same three |
| `stock_task_assignment:deleted` | the assignment | the same three |

**Which action emits what** (new or changed rows only; everything else as v6 §7):

| Action | Events |
|---|---|
| `POST /snapshots/versions`, `draft: false` | `…version:closed` (if one was open), `…version:created` |
| `POST /snapshots/versions`, `draft: true` | `…version:created` |
| the six row-edit routes (v6 shortcuts and §5.14–5.16) | `stock_report_item_snapshot:updated` for the mover and each shifted neighbour, `extra.version_id` = the edited version |
| `POST …/apply-priorities` | `stock_report_item_snapshot:updated` per changed snapshot of the **target** |
| `POST …/activate` (manual or scheduled) | `…version:closed` (previous, if any), `…version:activated` — **no snapshot events** |
| `POST …/refresh-requested` | `stock_report_item_snapshot:updated` per snapshot whose requested or missing changed, then `…version:refreshed` |
| `PATCH /snapshots/versions/{id}` | `…version:updated` (only if something changed) |
| `DELETE /snapshots/versions/{id}` | `…version:deleted` |
| `DELETE /items/{id}`, Scanner delete webhook | as v6; draft snapshots are removed silently under the row's `:deleted` |
| `POST /assignments` | as v6; the missing clamp touches the **active** snapshot only |

**Filtering rule (§0.1):** apply a `stock_report_item_snapshot:updated` to a view only if `extra.version_id` is
the version that view shows. Coalescing is as in v6.

# 8. Error identities, for triage

All 422, as the leading token of `error`. v6's list, unchanged:
`STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`, `STOCK_REPORT_ROW_HAS_NO_PRIORITY`, `STOCK_REPORT_TARGET_OUT_OF_RANGE`,
`STOCK_REPORT_NO_ACTIVE_SNAPSHOT`, `STOCK_REPORT_MISSING_EXCEEDS_CEILING`,
`STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`, `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`.

New in v7:

| Identity | When |
|---|---|
| `STOCK_REPORT_VERSION_NOT_DRAFT` | activate or delete a non-draft; schedule keys on a non-draft or with `draft: false` |
| `STOCK_REPORT_VERSION_IS_CLOSED` | a row edit (§5.14–5.16) or refresh (§5.18) on a closed version |
| `STOCK_REPORT_SCHEDULE_IN_THE_PAST` | `scheduled_activation_at` at or before now |
| `STOCK_REPORT_SOURCE_IS_TARGET` | apply-priorities with source = target (other than the v6 case) |
| `STOCK_REPORT_TARGET_VERSION_IS_CLOSED` | apply-priorities onto a closed version |
| `STOCK_REPORT_UNKNOWN_VERSION_STATE` | `state=` not one of `draft`, `active`, `closed` |
| `STOCK_REPORT_SCHEDULE_SUPERSEDED` | **never in an HTTP response.** The background worker's "this schedule was moved", listed so logs make sense |

404 messages: `Stock report snapshot version not found.` (any version id) and `Stock report item not found.` (row ids).

Error classes (never in a response body), unchanged from v6: `LocationTrackerWebhookAuthError` (401),
`StockDemandDeadlineExceeded` (503), `StockAssignmentRefused` (422, `stock_assignment_refused`),
`StockAssignmentPropertyMismatch` (409, `stock_assignment_property_mismatch`).

# 9. What is NOT built

- No "activated by" field on the version (the activating user is recorded in history, not on the wire).
- No undo of a draft deletion; no draft copy/duplicate route (create a new draft and apply-priorities from the old one).
- No lateness window for scheduled activations (late ones still happen, §5.21).
- No read of `stock_report_history_records` (as v6).
- Local development: scheduled activations fire only when the backend's scheduler, router and tasks-worker
  processes are running. `python run.py` alone does not start them.

# 10. If something here is wrong

Tell us. This file will never be edited in place. Any change, whether you found it or the backend
implementation forced it, is issued as a new dated handoff (v8) that lists only what differs from this one,
for you to align with after your v7 work is done.
