---
audience: frontend
subject: Stock Report — the snapshot layer with draft versions, scheduled activation and manual requested quantity (the complete contract, in one file)
date: 2026-09-28
status: CURRENT. The server ships this contract. Build against this file.
supersedes: v6 (HANDOFF_TO_FRONTEND_stock_report_snapshots_v6_20260926.md) and the four draft-version contracts v7, v8, v9, v10 — all moved to archived/, unedited
companion: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, unchanged, not superseded)
---

# Stock Report — the snapshot layer and draft versions

## 0. Which document is current

| Document | Status |
|---|---|
| **This file (v11)** | **CURRENT.** Every route, shape, identity and event below is read out of shipping code. `app/tests/unit/docs/test_stock_report_docs.py` compares the §6 tables with the shipped serializers field by field, and the §7–§8 names with the code, in both directions. |
| `HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md` | **CURRENT and RATIFIED.** Unchanged. |
| `archived/…_snapshots_v10_20260928.md`, `…_v9_20260928.md`, `…_v8_20260927.md`, `…_v7_20260927.md` | **HISTORICAL.** The four draft-version contracts you built against (v7 complete, v8–v10 differences). This file is the four merged. |
| `archived/…_snapshots_v6_20260926.md` | **HISTORICAL.** The snapshot layer as it shipped before drafts. Everything in it that is still true is restated here. |
| `archived/HANDOFF_TO_FRONTEND_stock_report_api_20260922.md` | **HISTORICAL.** Its §1 (envelopes), §2 (auth), §4 (assignments, consistency, repair, match-preview) and the Scanner webhooks are unchanged in substance and are not repeated here. |

Section numbers are v7's (which kept v6's), so a reference in your code to "§5.17" or "§6.6" still points at the
same thing. §5.11, §5.12, §5.22 and §5.23 are restated from v6, v6, v8/v9 and v10.

## 0.0 What v11 is, and the four points where the shipped backend settled a delta

v11 is v7 + v8 + v9 + v10 applied in order, over v6. It adds no route, no field and no event. Where a later
delta replaced an earlier one, only the later text is here. Four points differ from what one of the deltas
said, because building the backend settled them:

1. **The documented default create body with `draft: false` is accepted** (§5.8). v7 §5.8 and v9 §5.8 said that
   sending either schedule key "at all (even `null` / `false`)" with `draft: false` is a 422. The shipped rule is
   narrower: a **schedule** is refused — a `scheduled_activation_at` date, or
   `scheduled_activation_keeps_active_missing: true`. The keys at their defaults (`null`, `false`) with
   `draft: false` create an active version, 200. The PATCH route (§5.19) is unchanged: there, either schedule
   key sent on an activated version is a 422 whatever its value.
2. **A row deleted while it is in a draft** (§5.4): v7 said "no snapshot event is sent for them". Exactly: the
   removed draft snapshot gets no event. But if it held a priority, the **neighbours** that shift up in that
   draft's group each emit `stock_report_item_snapshot:updated` with the draft's `version_id`, as on the board.
3. **`PATCH /snapshots/versions/{client_id}` with no body** behaves as `{}`: 200, nothing changes, no event (§5.19).
4. **`STOCK_REPORT_SCHEDULE_SUPERSEDED`** is the log token of **every** skipped scheduled activation (moved,
   hand-published, later plan due — §5.21), not only "this schedule was moved" as v7 §8 put it. It is still
   never in an HTTP response.

## 0.1 What you must change in the app

The first two are **required before drafts are used in production** (§0.2). Today's socket code
(`packages/stock-report/src/socket-events.ts`, `applySnapshotUpdate`) finds the board row by
`extra.stock_report_item_id` and never looks at `version_id`, so a manager reordering a draft would repaint the
live board on every connected screen.

1. **Apply `stock_report_item_snapshot:updated` only to views of `extra.version_id`.** The board shows the active
   version; a draft page shows its draft. An event for another version is ignored by that view — except rule 10.
2. **On `stock_report_snapshot_version:activated`, refetch the board, the active version, the versions list, the
   missing summary and every open draft page.** A version went live, no per-row events accompany it (§5.17), and
   every draft now borrows its missing counts from the **new** active version. On `:refreshed`, refetch every view
   of that version (§5.18).
3. Everywhere you render a version, handle `active_at: null` and `closed_at: null` together (a draft), and read
   `state` rather than deriving it from the two dates.
4. The versions screen receives drafts. Use `state=` where you want only history (§5.9).
5. **A draft page refetches on `stock_report_item:created`.** The new row is already in every draft; no snapshot
   event announces it (§5.4).
6. **When you patch a row from a snapshot event instead of refetching**, compute the requested value in force with
   `quantity_requested_manual ?? quantity_requested_scanner ?? <the row's live quantity_requested>`. The reads do
   this for you (§6.6); only the event carries the raw parts.
7. **A draft's numbers move on their own**: its requested quantities, its row list and its `progress` follow
   Scanner live. Treat `stock_report_item:updated` and `:created` as draft-page signals too.
8. **Read `quantity_missing` as the number to show on a draft row.** It already contains the borrowed value. Label
   it with `quantity_missing_source` (`own` = typed on this draft, `active` = borrowed from the board, `none` = no
   board value, shows 0). Show `active_quantity_missing` beside it only if you want the board's number visible
   after the user typed their own.
9. **The activate action opens a drawer** with one choice: keep the board's missing counts on the rows this draft
   did not type, or reset them to 0. Pre-fill it from the draft's `scheduled_activation_keeps_active_missing`;
   send the user's choice as the body. **A manual activation uses only the body**; the stored flag is what a
   *scheduled* activation uses.
10. **A draft's missing counts follow the board.** When the board's missing changes, every draft row that borrows
    shows the new number. Treat `stock_report_item_snapshot:updated` for the **active** version as a draft-page
    signal as well, or refetch the draft page when you refetch the board.
11. **The history page sends `state=active,closed`** (§5.9): one call.
12. **The hub's Drafts badge reads `GET /snapshots/versions/draft-count`** (§5.23) and refetches it on
    `stock_report_snapshot_version:created`, `:activated` and `:deleted`.

## 0.2 Status

- **Live.** The server answers as this file says.
- **The production gate stands:** drafts and schedules are not used in production until your app ships rules 1
  and 2 of §0.1. Until then a draft edit would repaint the board, and an activation would leave stale screens.
- Nothing is open on the backend side.

## 0.3 The model in one page

- **A version is `draft`, `active` or `closed`** (`state` on every version payload). At most one is active. Many
  drafts may exist. A draft becomes active by activation (by hand, §5.17, or on schedule, §5.21); the active
  version becomes closed when another one goes live. A draft can be deleted (§5.20); an activated version never is.
- **A version holds one snapshot per row.** The snapshot carries the row's `priority`, `priority_order`,
  `quantity_missing` and its requested quantity **for that version**. The row itself (`stock_report_items`) is
  Scanner's live mirror and carries none of the three.
- **A draft is live.** Its rows are the live rows (a row Scanner creates joins every draft at once; a deleted row
  leaves every draft). Its requested quantities are the rows' live values unless a user typed one by hand. Its
  missing counts are the board's unless the draft typed its own. What a draft owns: priorities and their order,
  typed missing counts, manual requested values, a title, an optional schedule.
- **Activation freezes.** The moment a draft goes live, each snapshot's Scanner value is frozen from the live row
  (`quantity_requested_scanner`), manual values are kept, the missing counts settle (typed, else kept from the
  closing board or reset to 0 — the drawer), and from then on the version behaves as v6's active version did.
- **Completion never goes backwards, with two exceptions.** Scanner resolving units never lowers a snapshot's
  `quantity_awaiting` or its version's progress (`quantity_resolved`, §6.6). Only a refresh of the active version
  (§5.18) or a manual requested change on it (§5.22) can lower `quantity_target` coverage or `items_completed`.

---

# Part A — routes

All paths are under `/api/v1/stock-report`. Envelopes, auth and the 422 request-validation shape are as in the
archived API handoff (§0). "404 version" means **404 `Stock report snapshot version not found.`** for an absent or
other-workspace version id; "404 row" means **404 `Stock report item not found.`**

| Method | Path | Roles | § |
|---|---|---|---|
| `GET` | `/items` | admin, manager, worker, seller | 5.1 |
| `PATCH` | `/items/{client_id}/priority` | admin, manager, seller | 5.2 |
| `PATCH` | `/items/{client_id}/priority-order` | admin, manager, seller | 5.3 |
| `DELETE` | `/items/{client_id}` | admin, manager | 5.4 |
| `PATCH` | `/items/{client_id}/missing-quantity` | admin, manager, worker | 5.7 |
| `POST` | `/snapshots/versions` | admin, manager | 5.8 |
| `GET` | `/snapshots/versions` | admin, manager, worker, seller | 5.9 |
| `POST` | `/snapshots/versions/{client_id}/apply-priorities` | admin, manager | 5.10 |
| `GET` | `/snapshots/missing-summary` | admin, manager, worker, seller | 5.11 |
| `GET` | `/snapshots/versions/active` | admin, manager, worker, seller | 5.12 |
| `GET` | `/snapshots/versions/{client_id}` | admin, manager, worker, seller | 5.13 |
| `PATCH` | `/snapshots/versions/{version_id}/items/{client_id}/priority` | admin, manager, seller | 5.14 |
| `PATCH` | `/snapshots/versions/{version_id}/items/{client_id}/priority-order` | admin, manager, seller | 5.15 |
| `PATCH` | `/snapshots/versions/{version_id}/items/{client_id}/missing-quantity` | admin, manager, worker | 5.16 |
| `POST` | `/snapshots/versions/{client_id}/activate` | admin, manager | 5.17 |
| `POST` | `/snapshots/versions/{client_id}/refresh-requested` | admin, manager | 5.18 |
| `PATCH` | `/snapshots/versions/{client_id}` | admin, manager | 5.19 |
| `DELETE` | `/snapshots/versions/{client_id}` | admin, manager | 5.20 |
| `PATCH` | `/snapshots/versions/{version_id}/items/{client_id}/requested-quantity` | admin, manager, seller | 5.22 |
| `GET` | `/snapshots/versions/draft-count` | admin, manager, worker, seller | 5.23 |

Unchanged and not repeated (archived API handoff §4, and match-preview v2): `POST /assignments`,
`POST /assignments/delete`, `GET /items/{client_id}/assignments`, `POST /items/{client_id}/match-preview`,
`GET /consistency`, `POST /repair`. One addition to `GET /consistency` for admin tooling: a divergence `kind` is
one of `counter_in_queue`, `counter_in_progress`, `counter_awaiting`, `signature`, `order_density`,
`missing_over_ceiling`, `snapshot_version_state_mismatch`, `draft_membership_mismatch`,
`schedule_scheduler_mismatch`, `goal_total`, `task_flag`. Of the draft-era kinds,
`snapshot_version_state_mismatch` names a snapshot in `client_id`, and `draft_membership_mismatch` and
`schedule_scheduler_mismatch` name a version.

## 5.1 `GET /items`

Roles: **admin, manager, worker, seller**. **Paginated:** `?limit=` (default **20**, min 1, max 200) and
`?offset=` (default 0); out-of-range values → 422 (request validation).

| Param | Meaning |
|---|---|
| `version_id` omitted | **the board**: the active version's rows. Drafts never appear here. A row without an active snapshot is absent. |
| `version_id=<srv_…>` | that version's rows, **in any state** — a draft to prepare it, a closed version to browse history. Every other parameter applies exactly as on the board, scoped to that version. Absent/foreign → 404 version. With `live_stock=true` → **422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`**. |
| `priority` | filters the **snapshot's** priority. **Omitted or empty = the snapshots whose priority is null** (the Unset bucket), ordered by the row's `created_at, client_id`. `priority=all` = every snapshot of the version, prioritised first in board order, then unprioritised by `created_at, client_id`; it must be the only token. A list (`high,low`) = those groups, `high` before `medium` before `low`, then `priority_order`. An unknown token, or `all` with another → **422 `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER`**. |
| `include_zero_requested=true` | by default a snapshot whose **outstanding** count is zero or less is hidden: `quantity_requested − quantity_missing <= 0`, both the values in force (§6.6). This shows it. It has no effect under `missing_only`. |
| `missing_only=true` | **every** snapshot with `quantity_missing > 0` (the value in force), including those whose every unit is missing — the buyer's list. On a draft that is the effective missing: a borrowing row whose board twin has missing > 0 **is listed**; a row the draft typed `0` for is not; a row with nothing typed and no board value is not. |
| `item_major_categories`, `item_category_ids` | repeated params, combined with AND. |
| `live_stock=true` | the **mirror read**: every live row, with `snapshot` = its **active** snapshot or `null`; `include_zero_requested` applies to the row's own `quantity_requested`. Ordered by `created_at, client_id`. With `priority`, `missing_only` or `version_id` → **422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT`**. |

```jsonc
{ "data": {
    "stock_report_items": [ /* §6.1, each with a "snapshot" object */ ],
    "stock_report_items_pagination": { "has_more": true, "limit": 20, "offset": 0 }
}, "ok": true, "warnings": [] }
```

- **Filters apply before paging**; `has_more` is about the filtered set. Every order ends in the row's
  `client_id`, so pages never overlap while the board is still. If rows move between two page requests, re-read
  from `offset=0`. There is no total count. `priority_order` is a position in the whole group, not in the page.
- Each row's `snapshot` is **that version's** snapshot (never null except on `live_stock=true`).
- Counters: an **open** snapshot (draft or active) shows the row's **live** `quantity_in_queue`,
  `quantity_in_progress` and `quantity_awaiting` (the latter plus `quantity_resolved`, §6.6); a closed snapshot
  shows its frozen copies.
- Rows deleted since (by a user or by Scanner) are **not listed**, in any state. That matches `progress`, which
  excludes them, so the list can be shorter than `filtered_snapshot_count`.

## 5.2 / 5.3 `PATCH /items/{client_id}/priority | priority-order` — the board shortcuts

Bodies: `{"priority": "high"|"medium"|"low"|null}` (key required) and `{"priority_order": <strict int>}`. Roles:
**admin, manager, seller**. They act on the row's snapshot in the **active** version; they are the shortcut form
of §5.14 / §5.15 on the active version's id. Response `{ "data": { "stock_report_item": <§6.1 row> } }` — read the
new position from `snapshot`. Setting the value already held → 200 no-op, no event.

The shortcut and the versioned route on the active version's id run the same command, write the same thing and
emit the same events. They differ only when the row or the version is not where the call expects:

| Case | Shortcut `PATCH /items/{id}/…` | Versioned `PATCH /snapshots/versions/{active}/items/{id}/…` |
|---|---|---|
| no active version, or the row has no snapshot in it | **422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`** | 404 row |
| an activation lands between your read and your PATCH | applies to the **newly** active version, 200 | the id you sent is now closed → **422 `STOCK_REPORT_VERSION_IS_CLOSED`** |

Use the shortcuts for the board and the versioned routes for a draft. Refusals inside the group:
**422 `STOCK_REPORT_ROW_HAS_NO_PRIORITY`** (ordering an unprioritised snapshot) and
**422 `STOCK_REPORT_TARGET_OUT_OF_RANGE`** (`priority_order` outside `1..n`). Absent, deleted or foreign row → 404 row.

## 5.4 Rows appearing and disappearing — `DELETE /items/{client_id}`, the Scanner webhooks

**Deletion** (`DELETE /items/{client_id}`, roles **admin, manager**, or Scanner's delete webhook) — per open
snapshot of the row:

- the **active** snapshot is **closed** with the row and keeps its last position; its neighbours in the board's
  priority group shift up and each emits `stock_report_item_snapshot:updated`. The version stays open.
- each **draft** snapshot is **removed**, and that draft's `snapshot_count` drops by 1. The removed snapshot gets
  no event of its own (the row's `stock_report_item:deleted` covers it). If it held a priority, the neighbours
  that shift up **in that draft's group** each emit `stock_report_item_snapshot:updated` with the draft's
  `version_id`.

A later demand for the same identity creates a new row, with no snapshot in the active version until the next
activation or refresh.

**Creation** — Scanner's demand webhook is the **only** code path that creates a row, and every row it creates
emits `stock_report_item:created` (the coalescer never drops a `:created`). The new row **joins every draft** at
once: unprioritised, no typed missing (it borrows), no manual requested value; each draft's `snapshot_count` rises
by 1. It does **not** join the active version (§5.18 adds it there). No snapshot event: refetch draft pages and the
versions list on `stock_report_item:created`. A webhook call that only updates quantities emits
`stock_report_item:updated` for the changed rows and nothing for unchanged ones. A row created in a call that then
fails (Scanner's deadline, 503) is rolled back with its event.

## 5.7 `PATCH /items/{client_id}/missing-quantity` — the board shortcut

Roles: **admin, manager, worker** (not seller). `client_id` is the **row's** id. Body
`{"quantity_missing": <strict int>}` — the key is required, the string `"3"` is a 422, it is an **absolute value**,
never a delta, and `null` is refused here (only §5.16 accepts `null`, on a draft).

Rule: `0 <= quantity_missing <= ceiling`, where `ceiling = max(0, quantity_requested − (quantity_in_queue +
quantity_in_progress + quantity_awaiting))` over the active snapshot's wire values (§6.6: the requested value in
force, and awaiting including the units Scanner already resolved). Above it → **422
`STOCK_REPORT_MISSING_EXCEEDS_CEILING`**, and the sentence names the ceiling. Same value → 200 no-op, no event. No
active snapshot → **422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`**. Absent, deleted or foreign row → 404 row.

Response `{ "data": { "stock_report_item": <row> } }`. Event: one `stock_report_item_snapshot:updated`.

**The automatic half.** When an assignment is **created** on a row (`POST /assignments`), the uncovered remainder
shrinks; if the **active** snapshot's `quantity_missing` is now above the new ceiling it is clamped down to it and
a `stock_report_item_snapshot:updated` is emitted in the same burst. A draft's missing count is a guide and is not
clamped then; activation clamps it (§5.17).

## 5.8 `POST /snapshots/versions` — open a version, or create a draft

Roles: **admin, manager**. Body **optional**; **no body → a new active version** (v6's behaviour).

```jsonc
{ "draft": false,                                     // bool, default false
  "title": null,                                      // string or null
  "scheduled_activation_at": null,                    // draft only — ISO 8601 WITH offset
  "scheduled_activation_keeps_active_missing": false  // draft only — bool, default false
}
```

- Unknown keys → 422 (request validation). `draft` and the flag are strict booleans.
- **`title`**: trimmed **first**, then capped: a trimmed length above 200 → 422 (request validation), never
  truncated. `""` or spaces → `null`. The same rule on §5.19.
- **`draft: false`** (or no body): a new **active** version. Every live row (zero-requested rows included) gets one
  snapshot, its `quantity_requested` frozen as the Scanner value, `priority: null`, **`quantity_missing: 0`** — the
  closing board's missing is not carried over on this path (only activation, §5.17, has that choice). The
  previously active version closes in the same transaction, its counters frozen as they stood. Two managers opening
  at once serialize; the second closes the first's version. An empty workspace still gets a version
  (`snapshot_count: 0`). **A schedule with `draft: false` → 422 `STOCK_REPORT_VERSION_NOT_DRAFT`**: a
  `scheduled_activation_at` date, or the flag `true`. The keys at their defaults (`null`, `false`) are accepted
  (§0.0 point 1).
- **`draft: true`**: a **draft** holding one snapshot per live row — no priorities, nothing typed, no manual
  values. It freezes nothing (a draft is live, §0.3). The active version is **not** closed and the board does not
  change.
- **`scheduled_activation_at`**: without an offset → 422 (request validation); at or before now → **422
  `STOCK_REPORT_SCHEDULE_IN_THE_PAST`**. Send any offset; it is stored and echoed in UTC (§6.7). The draft will
  activate itself at or after that time (§5.21).
- **The flag without a date** (`draft: true`, no `scheduled_activation_at`, flag `true`): stored, shown on the
  version, used if a date is set later. No refusal.

Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ } } }`.

Events: `draft: false` → `stock_report_snapshot_version:closed` (if one was open) then `:created` with
`extra.state: "active"`; **refetch the board** — every row's snapshot is new and priorities are null again.
`draft: true` → `:created` only, with `extra.state: "draft"`; the board is untouched.

## 5.9 `GET /snapshots/versions`

Roles: **admin, manager, worker, seller**. `?limit=` (default **20**, max 200) and `?offset=` (default 0).

| Param | Meaning |
|---|---|
| `state` omitted or empty | **every** version: drafts, the active one, closed ones |
| `state=draft` / `active` / `closed` | only that state |
| `state=active,closed` (any comma list of the three) | those states; tokens trimmed, empty tokens ignored, repeats folded |
| any other token, `all` included, alone or in a list | **422 `STOCK_REPORT_UNKNOWN_VERSION_STATE`** |
| `priority` | selects what each row's `progress` sums and `filtered_snapshot_count` counts — exactly the §5.1 parser and meaning (omitted = null-priority snapshots, `all`, or a list). It does **not** filter the version rows. |

**Order:** `active_at DESC NULLS FIRST, created_at DESC, client_id DESC` — drafts first (newest created first),
then the active version, then closed versions newest first. With `state=active,closed` the active version is first.

```jsonc
{ "data": {
    "stock_report_snapshot_versions": [
      { /* §6.7 */ "state": "draft", "active_at": null, "filtered_snapshot_count": 12, "progress": { /* §6.8 */ } },
      { /* §6.7 */ "state": "active", "closed_at": null, "filtered_snapshot_count": 12, "progress": { /* §6.8 */ } },
      { /* §6.7 */ "state": "closed", "closed_at": "2026-09-20T09:00:00+00:00", "filtered_snapshot_count": 9, "progress": { /* §6.8, frozen */ } }
    ],
    "stock_report_snapshot_versions_pagination": { "has_more": false, "limit": 20, "offset": 0 }
}, "ok": true, "warnings": [] }
```

Every row carries `filtered_snapshot_count` and `progress` (§6.7, §6.8), from the same engine as §5.12 and §5.13.
A closed version's progress is frozen; the active one's moves live; a draft's is a fully live preview.

## 5.10 `POST /snapshots/versions/{client_id}/apply-priorities`

Roles: **admin, manager**. `{client_id}` is the **source**. Body optional:

```jsonc
{ "target_version_id": null }   // null or omitted → the active version; a draft's id → that draft
```

Copies the source's `priority` / `priority_order` onto the target: a row present in both takes the source's
priority; a row absent from the source **keeps its current** priority; each group is renumbered densely with the
source's members first (in source order) and the kept members after (in their current order). **Only priorities
move** — the source's manual requested values are not copied.

- The source may be **closed, active or a draft**. The target must be open (the active version or a draft); a
  closed target → **422 `STOCK_REPORT_TARGET_VERSION_IS_CLOSED`**. Absent/foreign source or target → 404 version.
- Source is the active version and the target is omitted → **422 `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`**. Any
  other source = target → **422 `STOCK_REPORT_SOURCE_IS_TARGET`**.
- Target omitted and no active version → **200 with `changed: 0`**.

Response: `{ "data": { "changed": 4, "stock_report_items": [ /* §6.1, the changed rows, each with the TARGET version's snapshot */ ] } }`.
Events: one `stock_report_item_snapshot:updated` per changed snapshot, `extra.version_id` = the target.

## 5.11 `GET /snapshots/missing-summary`

Roles: **admin, manager, worker, seller**. No parameters.

```jsonc
{ "data": { "quantity_missing_total": 7, "items_with_missing": 3 }, "ok": true, "warnings": [] }
```

Both over the **active** snapshots. The list behind the counter is `GET /items?missing_only=true`.

## 5.12 `GET /snapshots/versions/active`

Roles: **admin, manager, worker, seller**. One parameter, `?priority=`, as on §5.9.

```jsonc
{ "data": { "stock_report_snapshot_version": { /* §6.7 */ "state": "active", "filtered_snapshot_count": 12, "progress": { /* §6.8 */ } } },
  "ok": true, "warnings": [] }
```

It never returns a draft. With **no active version** it is a **200** with `{ "stock_report_snapshot_version": null }`
— the board's normal empty state, not an error.

## 5.13 `GET /snapshots/versions/{client_id}`

Roles: **admin, manager, worker, seller**. `?priority=` as on §5.9. Any state.

```jsonc
{ "data": { "stock_report_snapshot_version": { /* §6.7 */ "filtered_snapshot_count": 12, "progress": { /* §6.8 */ } } } }
```

Absent/foreign → 404 version. The literal segments `active` and `draft-count` are declared first and are never
read as a version id.

## 5.14 / 5.15 / 5.16 Row edits inside a version

The version in the path, the **row's** id as `{client_id}`. They work on **the active version and on drafts**.

| Route | Body | Roles |
|---|---|---|
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/priority` | `{"priority": "high"\|"medium"\|"low"\|null}` | **admin, manager, seller** |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/priority-order` | `{"priority_order": <strict int>}` | **admin, manager, seller** |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/missing-quantity` | `{"quantity_missing": <strict int ≥ 0> \| null}` | **admin, manager, worker** |

- Version absent/foreign → 404 version. Version closed → **422 `STOCK_REPORT_VERSION_IS_CLOSED`**. Row absent,
  deleted or foreign, or a live row with no snapshot in that version → 404 row.
- Groups are **per version**: a draft's `high` group is numbered 1..n independently of the board's.
  `STOCK_REPORT_ROW_HAS_NO_PRIORITY` and `STOCK_REPORT_TARGET_OUT_OF_RANGE` behave as on the board, within that
  version.
- **Missing** (§5.16):
  - a number **types** the version's own value; on a draft `quantity_missing_source` becomes `"own"` and the row
    stops following the board;
  - `null` **clears** a draft's typed value: the row borrows the board's again (`"active"`, or `"none"` → 0);
    `null` on the **active** version → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`** (an active row always has its own
    number);
  - the ceiling is `<requested in force> − (live in_queue + in_progress + awaiting)`, and on the active version the
    awaiting includes `quantity_resolved` (§5.7). Above it → **422 `STOCK_REPORT_MISSING_EXCEEDS_CEILING`**.
    Negative, non-integer or a missing key → 422 (request validation).
- Setting the value already stored (including `null` on a draft row with nothing typed) → 200 no-op, no event.
- Response: `{ "data": { "stock_report_item": <§6.1 row, whose snapshot is THIS version's> } }`.
- Events: `stock_report_item_snapshot:updated` for the mover and each shifted neighbour, `extra.version_id` = the
  edited version. Edits on a draft write no history; edits on the active version write history as v6.

## 5.17 `POST /snapshots/versions/{client_id}/activate`

Roles: **admin, manager**. Body optional:

```jsonc
{ "keep_active_missing": false }   // bool, default false
```

No body and `{}` → the default (reset). Unknown keys → 422 (v7's `{"refresh_quantity_requested": …}` is a 422);
a non-boolean → 422.

Publishes a draft as the board, in one transaction:

1. The current active version (if any) **closes** exactly as when a version is opened (counters frozen).
2. Any live row the draft somehow lacks joins it (a safety net; with live membership it adds nothing).
3. **Every snapshot freezes its Scanner value from the live row now** (`quantity_requested_scanner`). Manual
   requested values are **kept** and stay in force.
4. **Every snapshot settles its missing:** the draft's typed value where there is one; otherwise, with
   `keep_active_missing: true`, the closing board's value for that row (0 if the row was not on it); with `false`,
   0. Then each is clamped to what the live counters leave uncovered.
5. The draft becomes active: `state: "active"`, `active_at` set on it and every snapshot (the moment it went live),
   its schedule cleared and any pending scheduled activation cancelled.

- **A manual activation uses only the body.** The draft's stored `scheduled_activation_keeps_active_missing` is for
  scheduled activations (§5.21); pre-fill the drawer from it.
- Not a draft (active or closed) → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**. Absent/foreign → 404 version.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 of the now-active version, no progress */ } } }`.
- Events: `stock_report_snapshot_version:closed` (the previous one, if any), then
  **`stock_report_snapshot_version:activated`** (`extra`: `snapshot_count`, `title`, `scheduled: false`,
  `keep_active_missing`). **No per-row snapshot events** — refetch (§0.1 rule 2).
- History: one priority record per prioritised row (not on the wire).

## 5.18 `POST /snapshots/versions/{client_id}/refresh-requested` — the active version only

Roles: **admin, manager**. Body optional:

```jsonc
{ "keep_manual_requested": true }   // bool, default true
```

Re-freezes every snapshot's Scanner value from the live rows, adds the rows created since activation, and clamps
`quantity_missing` to the new ceiling. It does not open a new version.

- **Target: the active version only.** A draft has nothing to refresh (it is live); a draft or a closed version →
  **422 `STOCK_REPORT_VERSION_NOT_ACTIVE`**. Absent/foreign → 404 version. Unknown keys or a non-boolean → 422.
- `keep_manual_requested: true` → manual values stay in force; the refreshed Scanner value sits underneath and a
  later revert (§5.22) lands on it. `false` → every manual value is cleared and the refreshed Scanner value takes
  over.
- Added rows join unprioritised, missing 0, stamped with the version's own `active_at`; `snapshot_count` rises.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ }, "changed": 3, "added": 1 } }`. `changed`
  counts snapshots whose **requested value in force** changed (an overridden row whose Scanner value moved is not
  counted); `added` counts rows that joined.
- Events: `stock_report_item_snapshot:updated` per snapshot whose Scanner value, manual value or missing changed,
  then **`stock_report_snapshot_version:refreshed`** (`extra`: `snapshot_count`, `changed`, `added`,
  `keep_manual_requested`). Added rows have no event of their own: refetch the version's rows on `:refreshed`.
- **Completion can drop** (§0.3): a raised requested lowers the coverage of `quantity_target` and can un-complete an
  item.

## 5.19 `PATCH /snapshots/versions/{client_id}` — title and schedule

Roles: **admin, manager**. Body: any subset of

```jsonc
{ "title": "Upholstery push",                             // any state; null clears; the §5.8 rule
  "scheduled_activation_at": "2026-10-05T06:00:00+02:00",  // drafts only; null unschedules
  "scheduled_activation_keeps_active_missing": true }      // drafts only
```

- **An omitted key is left untouched. A key sent as `null` clears it.** `{}` or no body → 200, nothing changes, no
  event. Unknown keys → 422 (request validation); the flag is a strict boolean (`null` → 422).
- Either schedule key **sent**, whatever its value (`null` included), on an active or closed version → **422
  `STOCK_REPORT_VERSION_NOT_DRAFT`**. `title` works in every state.
- `scheduled_activation_at` without an offset → 422 (request validation); at or before now → **422
  `STOCK_REPORT_SCHEDULE_IN_THE_PAST`**. Stored and echoed in UTC.
- Setting or moving the date replaces the pending activation (the old time never fires); clearing it cancels the
  pending activation; changing only the flag stores it and leaves the pending activation as it is (the flag is read
  when the activation runs). Setting only the flag on an unscheduled draft simply stores it.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ } } }`.
- Event: `stock_report_snapshot_version:updated` (`extra`: `title`, `scheduled_activation_at`,
  `scheduled_activation_keeps_active_missing`, as they now stand) — **only when something changed**. Re-sending
  the stored values is not a change.

## 5.20 `DELETE /snapshots/versions/{client_id}` — drafts only

Roles: **admin, manager**. No body. Hard delete: the draft and its snapshots are gone, its pending scheduled
activation is cancelled, the board is untouched.

- Not a draft → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**. Absent/foreign → 404 version.
- Response: `{ "data": { "client_id": "srv_…" } }`.
- Event: `stock_report_snapshot_version:deleted`, pushed **before the HTTP response returns** (§7). A client inside
  the deleted draft may see the event first and a 404 on its next read, or the 404 first if its read was already in
  flight.

## 5.21 Scheduled activation — behaviour (no route of its own)

- A draft with `scheduled_activation_at` activates itself **at or after** that time, through the backend's
  background workers. **No latency is promised**: usually seconds later, much later if the worker processes were
  down. **A late activation still happens** when they come back.
- It behaves as §5.17 with `keep_active_missing` = the draft's stored `scheduled_activation_keeps_active_missing`,
  **read at that moment**, and it is recorded as the act of the user who set the schedule. Every edit made to a
  scheduled draft before then — priorities, missing, manual requested, the flag — is what gets published, over the
  live Scanner values of that moment.
- Same events as §5.17; `:activated` carries `extra.scheduled: true`.
- Moving the date, clearing it, activating by hand or deleting the draft cancels the pending activation. **A moved
  schedule never fires at the old time.**
- **Skipped when superseded.** When the time comes, the activation does not run if:
  - **a board went live after this draft's scheduled time** (by hand, or another draft's activation): that board
    stands;
  - **another draft is also due and was scheduled later**: the later plan wins, in either processing order;
  - **two drafts are scheduled for exactly the same time and both are due**: the draft **created later** wins.

  The skipped draft **stays a draft**, its `scheduled_activation_at` becomes `null`, and
  `stock_report_snapshot_version:updated` is emitted for it. Every case is deterministic.
- **Overdue drafts:** a draft whose `scheduled_activation_at` is in the past has not been activated yet. The
  activation is still being processed, or it failed. Show it as overdue; a manager can activate it by hand.
- Local development: scheduled activations fire only when the backend's `delayed-scheduler`, `task-router` and
  `tasks-worker` processes run. `python run.py` alone does not start them.

## 5.22 `PATCH /snapshots/versions/{version_id}/items/{client_id}/requested-quantity`

Roles: **admin, manager, seller**. The version in the path, the **row's** id as `{client_id}`. Works on a **draft
and on the active version**. There is no board-shortcut path for it: send the active version's id.

```jsonc
{ "quantity_requested": 7 }      // strict integer ≥ 0 — set (pin) the manual value
{ "quantity_requested": null }   // revert
```

- The key is **required**: `{}` → 422, `-1` → 422, `"3"` → 422 (request validation). `null` → 200 (a revert).
- A number sets the manual value: `snapshot.quantity_requested` becomes it and `quantity_requested_source` becomes
  `"manual"`. **Typing the value already shown pins it**: a row with no manual value that shows `10` (Scanner's
  number) and receives `10` stores 10 as a manual value, emits an event, and **stays at 10** when Scanner later asks
  for 14.
- `null` **reverts**: on a draft the row's live Scanner value is in force again; on the active version the frozen
  Scanner value (`quantity_requested_scanner`) is.
- No-ops (200, no event): the same manual value again; `null` on a row with no manual value.
- Version absent/foreign → 404 version. Version closed → **422 `STOCK_REPORT_VERSION_IS_CLOSED`**. Row absent,
  deleted or foreign, or without a snapshot in that version → 404 row.
- **On the active version**, lowering the requested below what is covered clamps that snapshot's
  `quantity_missing` at once, and `progress` moves — the second exception to "completion never goes backwards"
  (§0.3). A history record is written. On a draft nothing is clamped and no history is written.
- Response: `{ "data": { "stock_report_item": <§6.1 row, whose snapshot is THIS version's> } }`.
- Event: one `stock_report_item_snapshot:updated` for the snapshot (the clamp's change folded into it), with
  `extra.version_id`.

## 5.23 `GET /snapshots/versions/draft-count`

Roles: **admin, manager, worker, seller**. No parameters, no body.

```jsonc
{ "data": { "draft_count": 2 } }
```

The workspace's versions whose `state` is `draft`; `0` when there are none. One count, no rows, no progress —
cheap enough to refetch on every version event. It has no event of its own: refetch on
`stock_report_snapshot_version:created`, `:activated` and `:deleted`, the three that change it.

---

# 6. Payload shapes, field by field

Each nullability table below is **checked by a test** against the shipped serializer it names: every field, and
every nullability claim with the condition that produces the null. Computed fields are listed **below** each table,
in a second table, because no stored column backs them. `item_category` is flattened with a dot; in JSON it is a
nested object. Every ISO 8601 string in this contract is echoed **in UTC with an explicit `+00:00`**, e.g.
`2026-10-05T04:00:00+00:00` — never `Z`, never the offset it was sent with.

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

Plus **`snapshot`**, a §6.6 object: `null` only on a `live_stock=true` read of a row with no active snapshot. On a
`version_id` read (§5.1) or a row-edit response (§5.14–§5.16, §5.22) it is **that version's** snapshot.

The row's `quantity_requested` is **Scanner's live number**; the number the board works against is
`snapshot.quantity_requested`. **There are no `priority` / `priority_order` keys on the row.**

```jsonc
{ "client_id": "sri_…",
  "item_category": { "client_id": "cat_…", "name": "Dining Chairs", "major_category": "seat", "image_url": null },
  "properties": { "wood_group": ["teak"] },
  "properties_signature": "…",
  "quantity_requested": 7, "quantity_in_queue": 2, "quantity_in_progress": 1, "quantity_awaiting": 0,
  "created_at": "…", "updated_at": null, "created_by_id": null, "updated_by_id": null,
  "snapshot": { "client_id": "srs_…", "version_id": "srv_…", "stock_report_item_id": "sri_…",
                "quantity_requested": 6, "quantity_requested_scanner": 5, "quantity_requested_source": "manual",
                "quantity_in_queue": 2, "quantity_in_progress": 1, "quantity_awaiting": 0,
                "quantity_missing": 1, "quantity_missing_source": "own", "active_quantity_missing": 1,
                "quantity_resolved": 0, "priority": "high", "priority_order": 3,
                "active_at": "…", "closed_at": null, "created_at": "…", "updated_at": "…", "updated_by_id": "usr_…" } }
```

## 6.6 Item snapshot — `serialize_stock_report_item_snapshot`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `version_id` | string | no | — |
| `stock_report_item_id` | string | no | — |
| `quantity_in_queue` | integer | no | — |
| `quantity_in_progress` | integer | no | — |
| `quantity_awaiting` | integer | no | — |
| `quantity_resolved` | integer | no | — |
| `priority` | `"high"`, `"medium"`, `"low"` | yes | the snapshot is unprioritised and sits in no group |
| `priority_order` | integer | yes | the snapshot has no priority, so it holds no position (the two are always both null or both set) |
| `active_at` | ISO 8601 string | yes | the snapshot belongs to a draft that has not been activated |
| `closed_at` | ISO 8601 string | yes | the snapshot is open: its version is a draft or the active one; set when its version closed or its row was deleted from the active version |
| `created_at` | ISO 8601 string | no | — |
| `updated_at` | ISO 8601 string | yes | no priority, order, missing or requested quantity has been written since creation |
| `updated_by_id` | string | yes | the last write was the automatic clamp, a Scanner-caused cascade, or there was none |

Computed fields (always present):

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `quantity_requested` | integer | no | **the value in force**: the manual value if set; else the frozen Scanner value on an active or closed snapshot; else (draft) the row's live value |
| `quantity_requested_scanner` | integer | no | **what Scanner says or said**: on a draft the row's live value (equal to the row's `quantity_requested`); once active, the value frozen at activation or at the last refresh |
| `quantity_requested_source` | `"scanner"` \| `"manual"` | no | which of the two is in force |
| `quantity_missing` | integer | no | **the number in force**: on an active or closed snapshot its own value; on a **draft** the typed value if there is one, else the active version's value for this row, else 0 |
| `quantity_missing_source` | `"own"` \| `"active"` \| `"none"` | no | `own` = the version's own number (always on active/closed; on a draft, typed); `active` = borrowed from the active version; `none` = draft, nothing typed, no board value (reads 0) |
| `active_quantity_missing` | integer | yes | the same row's `quantity_missing` on the **current active version**; `null` when there is no active version or the row has no snapshot in it. On the active version's own snapshot it equals `quantity_missing`. Present on every read, in every state |

- **Counters:** an **open** snapshot (draft or active) reports the row's **live** `quantity_in_queue` and
  `quantity_in_progress`; a closed one reports its frozen copies. `quantity_awaiting` = (live awaiting, or the
  frozen one once closed) **+ `quantity_resolved`**.
- **`quantity_awaiting` never goes down because Scanner processed a shelf.** When Scanner resolves an assignment
  the row's awaiting drops, but the **active** snapshot remembers the units in `quantity_resolved`, so
  `snapshot.quantity_awaiting >= row.quantity_awaiting`. It does go down when an assignment moves back out of
  awaiting, is deleted, or fails. `quantity_resolved` only rises within a version, is always 0 on a draft, and
  starts at 0 when a version is activated.
- **The outstanding count** a worker cares about is `quantity_requested − quantity_missing − (in_queue +
  in_progress + awaiting)`, never below 0, over the values in force.
- `quantity_requested` on a **draft** is live; on an **active** version it is frozen at activation and changes only
  by a refresh (§5.18) or a manual value (§5.22). When Scanner posts a new number for a draft row that holds a manual
  value, the next read shows `quantity_requested_scanner` = the new live value and `quantity_requested` = the manual
  one. On the active version `quantity_requested_scanner` does not move with `stock_report_item:updated`.

## 6.7 Version — `serialize_stock_report_snapshot_version`

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `client_id` | string | no | — |
| `title` | string | yes | no title was given, or it was cleared |
| `active_at` | ISO 8601 string | yes | the version is a draft |
| `closed_at` | ISO 8601 string | yes | the version is a draft or the active one |
| `scheduled_activation_at` | ISO 8601 string | yes | the version has no pending schedule; always null once active or closed, and after a skipped scheduled activation |
| `scheduled_activation_keeps_active_missing` | boolean | no | — |
| `snapshot_count` | integer | no | — |
| `created_at` | ISO 8601 string | no | — |
| `created_by_id` | string | yes | column-nullable; every shipped path stamps the acting user |
| `closed_by_id` | string | yes | the version is a draft or still active, or was closed by a path with no user |

Computed fields:

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `state` | `"draft"` \| `"active"` \| `"closed"` | no | on **every** version payload, reads and command responses. `draft` = both dates null, `active` = `active_at` set and `closed_at` null, `closed` = both set. Read it rather than deriving it |
| `filtered_snapshot_count` | integer | no | **reads only** (§5.9, §5.12, §5.13): the version's snapshots the request's `priority` selects, deleted rows included; equals `snapshot_count` under `priority=all` |
| `progress` | object | no | **reads only**: §6.8 |

The command responses (§5.8, §5.17, §5.18, §5.19) carry the version **without** `filtered_snapshot_count` and
`progress`; refetch a read if you need the numbers.

- `active_at` is when the version actually went live: for a scheduled activation, when the worker ran it, not the
  scheduled time.
- `scheduled_activation_keeps_active_missing` is present in every state; it only matters on a draft with a schedule.
- **`snapshot_count` counts the version's snapshots, deleted rows included**, and is not fixed for life: it rises
  when a refresh (§5.18) or an activation's safety net adds rows, and on a **draft** it rises when Scanner creates a
  row and falls when a row is deleted (§5.4). Active and closed versions keep counting deleted rows.

## 6.8 Version progress — `progress` on the version reads

Over the version's snapshots **that the `priority` query parameter selects** (omitted → null priority, `all` →
every snapshot, a list → those groups) and whose row has not been deleted since. Every key is a non-negative
integer and is always present; the four `by_priority` keys are always present too, zeros included, and the
top-level totals are their sum.

```jsonc
"progress": {
  "items_total": 3,          // selected snapshots counted
  "items_completed": 1,      // of those, how many have awaiting >= target
  "quantity_requested": 21,  // Σ requested in force
  "quantity_missing": 2,     // Σ missing in force
  "quantity_target": 19,     // Σ max(0, requested − missing)   ← the denominator
  "quantity_in_queue": 3,    // Σ in_queue   (live while open, frozen once closed)
  "quantity_in_progress": 1, // Σ in_progress
  "quantity_awaiting": 9,    // Σ the §6.6 wire awaiting (includes resolved)
  "quantity_resolved": 4,    // Σ quantity_resolved (already inside quantity_awaiting)
  "quantity_completed": 9,   // Σ min(target_i, awaiting_i)      ← the numerator
  "by_priority": {
    "high":   { /* the same ten keys, for the high group */ },
    "medium": { /* … */ },
    "low":    { /* … */ },
    "unset":  { /* … the null-priority snapshots */ }
  }
}
```

- **The bar is `quantity_completed / quantity_target`.** A zero target means the filter selected nothing with work
  to do; render that state rather than dividing.
- `quantity_completed` is capped **per item**, so an over-assigned row cannot cover another row's shortfall.
- A **closed** version's numbers are frozen at the moment it closed; the **active** version's move live; a
  **draft's** is a fully live preview — live counters against the live (or manual) requested and the effective
  missing (typed, else borrowed), `quantity_resolved` 0 — and it moves whenever Scanner posts or the board's missing
  changes.
- The same `priority` filter applies to a draft's progress as to the active version's, so a draft card's bars and
  the hub card's are computed alike.
- Resolution by Scanner never lowers `quantity_awaiting` or `quantity_completed`. A refresh (§5.18) or a manual
  requested change on the active version (§5.22) can lower `quantity_target` coverage and `items_completed`.

## 6.2 Assignment — `serialize_stock_task_assignment` — unchanged

Fourteen keys: the twelve below plus `item` (§6.3) and `task` (§6.4), each an object and each always present.

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

Active: `in_queue`, `in_progress`, `awaiting`. Terminal: `resolved`, `failed`, `resolved_early`. Semantics as in
the archived API handoff.

---

# 7. Events

Thirteen names, exhaustively:

| Event | `client_id` | `extra` |
|---|---|---|
| `stock_report_item:created` | the row | `{}` |
| `stock_report_item:updated` | the row | `quantity_requested`, `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting` |
| `stock_report_item:deleted` | the row | `{}` |
| `stock_report_item_snapshot:updated` | **the snapshot** | `stock_report_item_id`, `version_id`, `priority`, `priority_order`, `quantity_missing`, `quantity_resolved`, `quantity_requested_scanner`, `quantity_requested_manual` |
| `stock_report_snapshot_version:created` | the version | `snapshot_count`, `state`, `title` |
| `stock_report_snapshot_version:closed` | the version | `snapshot_count` |
| `stock_report_snapshot_version:activated` | the version | `snapshot_count`, `title`, `scheduled`, `keep_active_missing` |
| `stock_report_snapshot_version:refreshed` | the version | `snapshot_count`, `changed`, `added`, `keep_manual_requested` |
| `stock_report_snapshot_version:updated` | the version | `title`, `scheduled_activation_at`, `scheduled_activation_keeps_active_missing` |
| `stock_report_snapshot_version:deleted` | the version | `{}` |
| `stock_task_assignment:created` | the assignment | `stock_report_item_id`, `task_id`, `state` |
| `stock_task_assignment:state-changed` | the assignment | the same three |
| `stock_task_assignment:deleted` | the assignment | the same three |

**`stock_report_item_snapshot:updated` carries all eight `extra` keys on every emission**, on every path (the six
row-edit routes, §5.22, apply-priorities, the refresh, the clamps, repair, Scanner processing, cascades). A key is
never omitted; a value can be `null`: `priority` / `priority_order` on an unprioritised row, `quantity_missing` on a
draft row that borrows (the **stored** value — the read's `quantity_missing` is the value in force),
`quantity_requested_scanner` on a draft, `quantity_requested_manual` when there is none. The event carries the
**stored** parts, not the values in force: apply §0.1 rules 6 and 8, or refetch.

**Every write to an active row's `quantity_missing` emits it** — a §5.7 / §5.16 mark, the clamp when an assignment
is created, the clamp after a §5.22 change on the active version, the refresh's clamp, a repair — so a borrowing
draft row can follow the board from that event alone. **The one silent path is activation** (§5.17): the new
board's values arrive with `:activated`, on which you refetch.

**Which action emits what:**

| Action | Events |
|---|---|
| `POST /assignments` | `stock_task_assignment:created`, maybe `stock_report_item:updated`, maybe `stock_report_item_snapshot:updated` (the clamp, **active** snapshot only) |
| `POST /assignments/delete` | `stock_task_assignment:deleted`, maybe `stock_report_item:updated` |
| the six row-edit routes (§5.2, §5.3, §5.7, §5.14–§5.16) | `stock_report_item_snapshot:updated` for the mover and each shifted neighbour, `extra.version_id` = the edited version |
| `PATCH …/requested-quantity` (§5.22) | one `stock_report_item_snapshot:updated`, `extra.version_id` = the edited version |
| `POST /snapshots/versions`, `draft: false` or no body | `…version:closed` (if one was open), `…version:created` (`state: "active"`) |
| `POST /snapshots/versions`, `draft: true` | `…version:created` (`state: "draft"`) |
| `POST …/apply-priorities` | `stock_report_item_snapshot:updated` per changed snapshot of the **target** |
| `POST …/activate`, and a scheduled activation | `…version:closed` (previous, if any), `…version:activated` — **no snapshot events** |
| a skipped scheduled activation (§5.21) | `…version:updated` for the skipped draft (`scheduled_activation_at: null`); a schedule moved or cleared before its old time emits nothing |
| `POST …/refresh-requested` | `stock_report_item_snapshot:updated` per changed snapshot, then `…version:refreshed` |
| `PATCH /snapshots/versions/{id}` | `…version:updated`, only if something changed |
| `DELETE /snapshots/versions/{id}` | `…version:deleted` |
| `POST /repair` | `stock_report_item:updated` and/or `stock_report_item_snapshot:updated` for what it changed |
| `DELETE /items/{id}`, Scanner delete webhook | `stock_report_item:deleted`, one `stock_task_assignment:deleted` per assignment, `stock_report_item_snapshot:updated` per shifted neighbour — on the board and in each draft (§5.4) |
| Scanner demand webhook | `stock_report_item:created` / `stock_report_item:updated` — never assignment or snapshot events; a created row is already in every draft |
| Scanner items-processed | `stock_task_assignment:state-changed`, maybe `stock_report_item:updated`, and one `stock_report_item_snapshot:updated` per row with an **active** snapshot (its `quantity_resolved` rose) |
| the reads, match-preview, `GET /consistency` | nothing |

- **Filtering rule** (§0.1 rule 1): apply a `stock_report_item_snapshot:updated` to a view only if
  `extra.version_id` is the version that view shows (and rule 10 for borrowing draft rows).
- **Coalescing:** within one request events are coalesced to the net change per entity — a row or snapshot gets at
  most one `:updated`, a deleted row gets only its `:deleted`, and a snapshot whose row is deleted in that request
  gets nothing. **The items-processed webhook does not de-duplicate** — keep handlers idempotent.
- **Timing:** every event is pushed to the socket **before the HTTP response returns** (after the transaction
  commits). A client may see the event before its own response.

# 8. Error identities and classes, for triage

Message identities, the leading token of `error`, all **422**:

| Identity | When |
|---|---|
| `STOCK_REPORT_UNKNOWN_PRIORITY_FILTER` | a `priority` token that is not `high`, `medium`, `low` or `all`, or `all` with another token |
| `STOCK_REPORT_ROW_HAS_NO_PRIORITY` | ordering a snapshot that has no priority |
| `STOCK_REPORT_TARGET_OUT_OF_RANGE` | `priority_order` outside `1..n` for that group |
| `STOCK_REPORT_NO_ACTIVE_SNAPSHOT` | a board shortcut (§5.2, §5.3, §5.7) with no active version or no snapshot of the row in it |
| `STOCK_REPORT_MISSING_EXCEEDS_CEILING` | `quantity_missing` above what the requested in force leaves uncovered |
| `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT` | `priority`, `missing_only` or `version_id` with `live_stock=true` |
| `STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE` | apply-priorities from the active version with the target omitted |
| `STOCK_REPORT_SOURCE_IS_TARGET` | apply-priorities with source = target (every other case) |
| `STOCK_REPORT_TARGET_VERSION_IS_CLOSED` | apply-priorities onto a closed version |
| `STOCK_REPORT_VERSION_IS_CLOSED` | a versioned row edit (§5.14–§5.16, §5.22) on a closed version |
| `STOCK_REPORT_VERSION_NOT_DRAFT` | activate or delete a non-draft; a schedule with `draft: false` (§5.8); a schedule key on the PATCH of an activated version (§5.19); `null` missing on the active version (§5.16) |
| `STOCK_REPORT_VERSION_NOT_ACTIVE` | refresh (§5.18) of a draft or a closed version |
| `STOCK_REPORT_SCHEDULE_IN_THE_PAST` | `scheduled_activation_at` at or before now |
| `STOCK_REPORT_UNKNOWN_VERSION_STATE` | a `state=` token that is not `draft`, `active` or `closed`, alone or in a list |
| `STOCK_REPORT_SCHEDULE_SUPERSEDED` | **never in an HTTP response**: the background worker's log token for a skipped scheduled activation (§5.21), listed so logs make sense |

404 messages: `Stock report snapshot version not found.` (any version id) and `Stock report item not found.`
(row ids).

Error classes (never in a response body under these names): `LocationTrackerWebhookAuthError` (401),
`StockDemandDeadlineExceeded` (503), `StockAssignmentRefused` (422, `code: "stock_assignment_refused"`),
`StockAssignmentPropertyMismatch` (409, `code: "stock_assignment_property_mismatch"`).

# 9. What is NOT built

- No "activated by" field on the version: the activating user (for a scheduled activation, the user who set the
  schedule) is recorded in history, which has no read.
- No undo of a draft deletion; no draft copy route (create a draft and apply-priorities from the old one).
- No lateness window for scheduled activations (late ones still happen, §5.21).
- No per-row keep-or-reset at activation: the drawer's choice is one flag for every untyped row; type a value on the
  rows you want to pin.
- No bulk routes for manual requested values or missing counts (one row per call).
- No copy of manual requested values through apply-priorities.
- No `total` in either pagination object; the draft-count read (§5.23) is the badge's source, and there is no count
  read for other states.
- No read of `stock_report_history_records`, no local row creation (only Scanner creates rows).

# 10. If something here is wrong

Tell us; it is a defect on our side. This file is never edited in place: a change comes as a new dated file, and
this one moves to `archived/`.
