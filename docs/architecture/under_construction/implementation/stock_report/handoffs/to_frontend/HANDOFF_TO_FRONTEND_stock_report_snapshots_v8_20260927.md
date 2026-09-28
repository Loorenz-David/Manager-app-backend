---
audience: frontend
subject: Stock Report — draft versions, second round: live drafts, manual requested quantity, active missing beside drafts (the differences from v7)
date: 2026-09-27
status: CONTRACT, published before the backend is built. Build against v7 + this file; neither is live yet (§0.2).
extends: HANDOFF_TO_FRONTEND_stock_report_snapshots_v7_20260927.md (CONTRACT, unedited; everything in v7 not restated here stands)
companion: HANDOFF_TO_FRONTEND_stock_report_snapshots_v6_20260926.md (CURRENT for what ships today); HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, unchanged)
source: backend plan update_stock_report/draft_versions_plan.md rev 5
---

# Stock Report — draft versions, v8: what differs from v7

v7 §10 promised that any change would come as a new dated file listing only what differs. This is
that file. It corrects v7 on **one idea** the owner reshaped after v7 went out: **a draft is not a
frozen copy. A draft is live.** Its rows' requested quantities are the live ones, new Scanner rows
join it at once, and what a draft holds of its own is priorities, missing counts and the manual
requested values a user typed. Only activation freezes anything.

Section numbers below are v7's. A section not listed here is unchanged.

## 0. Which document is current

| Document | Status |
|---|---|
| **This file (v8)** | **CONTRACT, not yet live.** Read it as a diff on v7. The docs guard is pointed at v7 + v8 on the day this ships. |
| `…_v7_20260927.md` | **CONTRACT, not yet live**, unedited. Where v8 restates a v7 section, v8 wins. |
| `…_v6_20260926.md` | **CURRENT until then.** What the server does today. |

## 0.0 What v8 changes, in one list

1. **A draft's `quantity_requested` is live**, not frozen (v7 §5.8, §5.1, §6.6, §6.8 said frozen). It
   is the row's live Scanner value until a user types a value by hand.
2. **A draft's row set is live**: a row Scanner creates joins **every draft** the moment it exists
   (v7 §5.17 step 2 and §5.18 said "rows created since join at activation / refresh"). That still
   holds for the **active** version, which is fixed at activation.
3. **Manual requested quantity**: a new route sets or reverts a row's `quantity_requested` by hand,
   on a draft **and on the active version** (§5.22). Three new fields on every snapshot say what the
   value is, what Scanner says, and which one is in force (§6.6).
4. **`active_quantity_missing`** on every snapshot: the same row's missing count on the **current
   active version**, so a planner sees today's situation while preparing a draft (§6.6).
5. **Activation has no body** and no refresh choice. It always freezes the live Scanner values of
   that moment and keeps manual values (§5.17). `scheduled_activation_refreshes_requested` is gone
   from every shape (§5.8, §5.19, §6.7, §7).
6. **Refresh is for the active version only** and gains a body: keep or replace the manual values
   (§5.18). Its refusal identity changes.
7. **The open decision of v7 §0.2 / §5.21 is ruled**: skip when superseded (§5.21).
8. "Completion can go backwards" has a **second** case: a manual requested change on the active
   version (§5.22).
9. `stock_report_item_snapshot:updated` `extra` carries **two** requested fields, the stored ones,
   not the effective value (§7). One rule tells you the effective value.

## 0.1 What you must change in the app — additions to v7 §0.1

v7 §0.1 items 1–4 and 6 stand. **Item 5 is void**: there is no refresh choice to send on activation.

7. **A draft page refetches on `stock_report_item:created`.** The new row is already in the draft;
   no snapshot event announces it.
8. **Compute the effective requested from a snapshot event** with one rule, when you patch a row
   from `stock_report_item_snapshot:updated` rather than refetching:
   `quantity_requested_manual ?? quantity_requested_scanner ?? <the row's live quantity_requested>`.
   The read payloads do this for you (§6.6); only the event carries the raw parts.
9. **A draft's numbers move on their own.** Its `quantity_requested`, its `progress` and its row list
   follow Scanner live. Treat `stock_report_item:updated` and `:created` as draft-page signals too.

## 0.2 Status and sequencing

As v7 §0.2. The one open backend decision named there is now ruled (§5.21). Nothing else is open.

---

# Part A — routes

## 5.1 `GET /items` — `version_id` (restated only where it changes)

- On a **draft**, each row's `snapshot.quantity_requested` is the **live** row value, or the manual
  value if one is set. It changes whenever Scanner posts for that row. (v7 said "frozen".)
- Every row's `snapshot` carries **`active_quantity_missing`** (§6.6), on every read, in every state.
- `include_zero_requested` and the outstanding rule use the **effective** requested value (the same
  number you see in `snapshot.quantity_requested`).

## 5.4 `DELETE /items/{client_id}` and the Scanner delete webhook

Unchanged from v7. Plus the mirror image for **creation**: when Scanner's demand webhook creates a
row, that row joins **every draft** at once (unprioritised, missing 0, no manual value). The active
version does not receive it (as v6). No snapshot event: refetch a draft page on
`stock_report_item:created`. Each draft's `snapshot_count` rises by 1.

## 5.8 `POST /snapshots/versions` — body shrinks

```jsonc
{ "draft": false,                    // bool, default false
  "title": null,                     // string ≤ 200 or null; trimmed; "" or spaces → null
  "scheduled_activation_at": null }  // draft only — ISO 8601 WITH offset
```

- `scheduled_activation_refreshes_requested` **no longer exists**. Sending it → 422 (request validation).
- `draft: true` **does not freeze anything**. It records which rows exist now (their membership),
  with priorities empty, missing 0, no manual values. Everything else about the draft is live.
- Everything else as v7.

## 5.9 `GET /snapshots/versions`

As v7, minus `scheduled_activation_refreshes_requested` on each row. A **draft's `progress` is fully
live**: live counters against the live (or manual) requested and the draft's missing. It moves when
Scanner posts.

## 5.10 `POST …/apply-priorities`

As v7. One precision: only priorities and their order are copied. **Manual requested values of the
source are not copied** (they belong to that version's own plan).

## 5.14 / 5.15 / 5.16 Row edits inside a version

As v7, with one precision on §5.16: the missing ceiling on a draft is
`<effective quantity_requested> − (live in_queue + in_progress + awaiting)`, where the effective
value is the live row value or the manual one. On the active version the ceiling also subtracts
`quantity_resolved`, as v6.

The "row created after the draft → 404" case of v7 is now practically gone (rows join drafts at
once). It remains for a row created after the **active** version was activated and not yet refreshed in.

## 5.17 `POST /snapshots/versions/{client_id}/activate` — no body

Roles: **admin, manager**. **No body.** A body → 422 (request validation).

Steps, replacing v7's list:

1. The current active version (if any) **closes** exactly as when a version is opened.
2. Any live row the draft somehow lacks joins it (a safety net; with live membership this adds nothing).
3. **Every snapshot freezes its Scanner value from the live row now** (`quantity_requested_scanner`).
   Manual values are **kept**: a row with a manual value keeps it as the effective requested.
4. Each snapshot's `quantity_missing` is kept, clamped to what the effective requested leaves uncovered.
5. The draft becomes active: `state: "active"`, `active_at` set on it and on every snapshot. Its
   schedule is cleared.

- Refusals and response as v7.
- Events: `stock_report_snapshot_version:closed` (the previous one, if any), then
  `stock_report_snapshot_version:activated` whose `extra` is now **`snapshot_count`, `title`,
  `scheduled`** (no `refresh_quantity_requested`). **No per-row snapshot events.** Refetch (v7 §0.1).

## 5.18 `POST /snapshots/versions/{client_id}/refresh-requested` — the active version only, with a body

Roles: **admin, manager**. Body optional:

```jsonc
{ "keep_manual_requested": true }   // bool, default true
```

Re-freezes every snapshot's Scanner value from the live rows, adds rows created since activation, and
clamps `quantity_missing`. It does not open a new version.

- **Target: the active version only.** A draft has nothing to refresh (it is live). A draft or a
  closed version → **422 `STOCK_REPORT_VERSION_NOT_ACTIVE`** (replaces v7's
  `STOCK_REPORT_VERSION_IS_CLOSED` on this route). Absent/foreign → 404 version.
- `keep_manual_requested: true` → manual values stay in force; the refreshed Scanner value sits
  underneath and a later revert (§5.22) lands on it. `false` → every manual value is cleared and the
  refreshed Scanner value takes over.
- Response: `{ "data": { "stock_report_snapshot_version": { /* §6.7 */ }, "changed": 3, "added": 1 } }`.
  `changed` counts snapshots whose **effective** requested changed.
- Events: `stock_report_item_snapshot:updated` per snapshot whose Scanner value, manual value or
  missing changed, then `stock_report_snapshot_version:refreshed` whose `extra` is
  `snapshot_count`, `changed`, `added`, **`keep_manual_requested`**.
- Completion can drop, as v7.

## 5.19 `PATCH /snapshots/versions/{client_id}` — body shrinks

```jsonc
{ "title": "Upholstery push",                            // any state; null clears
  "scheduled_activation_at": "2026-10-05T06:00:00+02:00" } // drafts only; null unschedules
```

`scheduled_activation_refreshes_requested` **no longer exists** (→ 422 request validation). Everything
else as v7. The `:updated` event's `extra` is now `title`, `scheduled_activation_at`.

## 5.21 Scheduled activation — the open decision, ruled

- A scheduled activation behaves as §5.17 above: it freezes the **live Scanner values of the moment
  it runs** and keeps the manual values. There is no stored refresh choice any more; v7's second
  bullet is void.
- **Ruled (was open in v7):** a scheduled activation is **skipped**, and its schedule cleared, when
  it has been superseded: another draft with a **later** schedule is also due, or a board went live
  **by hand** after this draft's scheduled time. The later plan wins in either processing order, and
  a hand-published board stands. The skipped draft stays a draft, `scheduled_activation_at: null`,
  and `stock_report_snapshot_version:updated` is emitted for it. Nothing else changes: refetch the
  versions list on `:updated`, as v7 §0.1 says.
- A moved schedule never fires at the old time (unchanged).

## 5.22 `PATCH /snapshots/versions/{version_id}/items/{client_id}/requested-quantity` — NEW

Roles: **admin, manager, seller** (the priority twins' roles). The version in the path, the **row's**
id as `{client_id}`. Works on a **draft and on the active version**.

```jsonc
{ "quantity_requested": 7 }      // strict integer ≥ 0 — set the manual value
{ "quantity_requested": null }   // revert
```

- A number sets the manual value: `snapshot.quantity_requested` becomes it and
  `quantity_requested_source` becomes `"manual"`.
- `null` **reverts**: on a **draft** the row's live Scanner value is in force again; on the **active
  version** the frozen Scanner value (`quantity_requested_scanner`) is. Same body, same route, no
  branch on your side.
- Version absent/foreign → 404 version. Version closed → **422 `STOCK_REPORT_VERSION_IS_CLOSED`**.
  Row absent, deleted or foreign, or without a snapshot in that version → 404 `Stock report item not found.`
  Negative, non-integer or a string → 422 (request validation).
- Already the value in force (including `null` on a row with no manual value) → 200 no-op, no event.
- **On the active version**, lowering the requested below what is covered clamps that snapshot's
  `quantity_missing` at once, and `progress` moves: this is the **second and last** exception to
  "completion never goes backwards" (a raise can un-complete an item, a cut can complete it). On a
  draft nothing is clamped (its missing is a guide, clamped at activation).
- Response: `{ "data": { "stock_report_item": <§6.1 row, whose snapshot is THIS version's> } }`.
- Event: one `stock_report_item_snapshot:updated` for the snapshot (the clamp's change is folded
  into it), with `extra.version_id`.
- There is **no** active-version shortcut path for this route (unlike §5.2/5.3/5.7): send the active
  version's id.

---

# 6. Payload shapes — what changes

## 6.6 Item snapshot — `serialize_stock_report_item_snapshot`

The nullability table of v7 §6.6 stands **with `quantity_requested` removed from it**: it is now a
computed field, listed below with the other computed ones (as `state` is on the version).

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `quantity_requested` | integer | no | **the value in force**: the manual value if set; else the frozen Scanner value on an active or closed snapshot; else (draft) the row's live value |
| `quantity_requested_scanner` | integer | no | **what Scanner says or said**: on a draft the row's live value (identical to `stock_report_item.quantity_requested` on the same row); once active, the value frozen at activation or at the last refresh |
| `quantity_requested_source` | `"scanner"` \| `"manual"` | no | which of the two is in force |
| `active_quantity_missing` | integer | **yes** | the same row's `quantity_missing` on the **current active version**; `null` when there is no active version or the row has no snapshot in it. On the active version's own snapshot it equals `quantity_missing`. Present on every read, in every state (a closed version's rows show today's active value). |

Show `active_quantity_missing` beside a draft's own `quantity_missing`, either, both or neither: a
client choice, as the owner asked. It is one value per row, shared by every draft.

Everything else in v7 §6.6 stands. Note the sentence "`quantity_requested` is frozen except…" is
void: on a draft it is live; on an active version it is frozen at activation, changed by a refresh
or a manual value.

## 6.7 Version — `serialize_stock_report_snapshot_version`

v7's table **minus `scheduled_activation_refreshes_requested`**. Everything else stands.

## 6.8 Version progress

As v7, with the draft case restated: a **draft's** progress is fully live — live counters against the
live (or manual) requested and the draft's missing — and it moves whenever Scanner posts. And a second
"can go down" case: a manual requested change on the active version (§5.22).

---

# 7. Events — what changes

| Event | `extra` (v8) |
|---|---|
| `stock_report_item_snapshot:updated` | `stock_report_item_id`, `version_id`, `priority`, `priority_order`, `quantity_missing`, `quantity_resolved`, **`quantity_requested_scanner`** (null on a draft), **`quantity_requested_manual`** (null when none) — **not** `quantity_requested`; apply the rule of §0.1 item 8 or refetch |
| `stock_report_snapshot_version:activated` | `snapshot_count`, `title`, `scheduled` |
| `stock_report_snapshot_version:refreshed` | `snapshot_count`, `changed`, `added`, `keep_manual_requested` |
| `stock_report_snapshot_version:updated` | `title`, `scheduled_activation_at` |

Thirteen names still, unchanged. Actions:

| Action | Events |
|---|---|
| Scanner demand webhook creating a row | `stock_report_item:created` only — the row is already in every draft; refetch draft pages |
| `PATCH …/requested-quantity` (§5.22) | one `stock_report_item_snapshot:updated`, `extra.version_id` = the edited version |
| `POST …/activate` | as v7 (no snapshot events) |
| `POST …/refresh-requested` | `stock_report_item_snapshot:updated` per changed snapshot, then `…version:refreshed` |

# 8. Error identities — what changes

| Identity | Change |
|---|---|
| `STOCK_REPORT_VERSION_NOT_ACTIVE` | **new**: refresh (§5.18) on a draft or a closed version |
| `STOCK_REPORT_VERSION_IS_CLOSED` | now only the row edits (§5.14–5.16, §5.22) on a closed version; no longer on refresh |

All other v7 identities unchanged.

# 9. What is NOT built — additions

- No bulk manual-requested route (one row per call).
- No per-row "who set the manual value" on the wire (it is in history records, not read).
- No copy of manual values through apply-priorities.

# 10. If something here is wrong

As v7 §10: tell us; this file is never edited in place; a change comes as v9 listing the differences.
