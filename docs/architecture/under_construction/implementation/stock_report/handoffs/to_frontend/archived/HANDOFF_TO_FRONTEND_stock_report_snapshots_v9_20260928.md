---
audience: frontend
subject: Stock Report — draft versions, third round: a draft's missing count is borrowed unless typed, and activation chooses to keep or reset it (the differences from v7 + v8)
date: 2026-09-28
status: CONTRACT, published before the backend is built. Build against v7 + v8 + this file; none is live yet (v7 §0.2).
extends: HANDOFF_TO_FRONTEND_stock_report_snapshots_v8_20260927.md (CONTRACT, unedited) on HANDOFF_TO_FRONTEND_stock_report_snapshots_v7_20260927.md (CONTRACT, unedited). Everything in v7 and v8 not restated here stands.
companion: HANDOFF_TO_FRONTEND_stock_report_snapshots_v6_20260926.md (CURRENT for what ships today); HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, unchanged)
source: backend plan update_stock_report/draft_versions_plan.md rev 7 + projection r2 (2026-09-28)
---

# Stock Report — draft versions, v9: what differs from v7 + v8

A diff, as v7 §10 promises. **One idea** from the owner, and **three corrections** from the backend's
own review of its plan. The idea: **a draft row's missing count works like its requested quantity.**
v8 gave you `active_quantity_missing` to show beside a draft's own `quantity_missing`. Now the draft's
`quantity_missing` **is** that borrowed value until someone types one, and when the draft is activated
the user chooses, in a drawer on the activate action, whether the untyped rows **keep** the board's
current missing counts or **reset** to 0.

Section numbers are v7's. A section not listed here is unchanged from v7 + v8.

## 0. Which document is current

| Document | Status |
|---|---|
| **This file (v9)** | **CONTRACT, not yet live.** A diff on v7 + v8. Where it restates a section, v9 wins. |
| `…_v8_20260927.md`, `…_v7_20260927.md` | **CONTRACT, not yet live**, unedited. |
| `…_v6_20260926.md` | **CURRENT until then.** What the server does today. |

At ship, the backend issues one **consolidated** file (v10: v7 + v8 + v9 merged, full tables) and points
its docs guard at it. v10 adds nothing; it is the same contract in one place.

## 0.0 What v9 changes, in one list

1. **A draft's `quantity_missing` is borrowed unless typed** (§6.6): the draft's own value if a user
   typed one for that row, otherwise the active version's value for the same row, otherwise 0. A new
   `quantity_missing_source` says which. `active_quantity_missing` stays as the raw borrowed value.
2. **Activation gains a body**: `{"keep_active_missing": false}` (§5.17). For rows the draft typed no
   missing for, `true` carries the board's current missing over, `false` starts the new board at 0.
   Show it in a drawer.
3. **The flag is stored on the draft for scheduled activations**: `scheduled_activation_keeps_active_missing`
   on create (§5.8), on the version PATCH (§5.19) and on every version payload (§6.7).
4. **`null` on the versioned missing route clears a draft's typed value** (§5.16), so the row borrows again.
5. **Correction to v8 §5.22:** typing the requested value already shown **pins** it (it is stored and
   the row shows `manual`); the no-op is only "same stored manual value" (§5.22).
6. **Correction to v7/v8 §5.21:** two drafts scheduled for the **same minute** → the draft **created
   later** wins; the other is skipped and stays a draft with its schedule cleared.
7. **Precisions** on request validation: the activate route rejects unknown body keys, and the
   requested-quantity body key is required (§5.17, §5.22).

## 0.1 What you must change in the app — additions to v7 §0.1 and v8 §0.1

10. **Read `quantity_missing` as the number to show on a draft row.** It already contains the borrowed
    value. Use `quantity_missing_source` to label it (`own` = typed on this draft, `active` = borrowed
    from the board, `none` = no board value, shows 0). Show `active_quantity_missing` beside it only if
    you want the board's number visible after the user typed their own.
11. **The activate action opens a drawer** with one choice: keep the board's missing counts on the rows
    this draft did not type, or reset them to 0. Pre-fill it from the draft's
    `scheduled_activation_keeps_active_missing`, send the user's choice as the body. **Manual activation
    uses only the body**; the stored flag is what a *scheduled* activation uses.
12. **A draft's missing counts move on their own** too: when the board's missing changes (a worker marks
    units missing on the active version), every draft row that borrows shows the new number. Treat
    `stock_report_item_snapshot:updated` for the **active** version as a draft-page signal as well, or
    refetch the draft page when you refetch the board.

---

# Part A — routes

## 5.8 `POST /snapshots/versions` — one key returns

```jsonc
{ "draft": false,                                    // bool, default false
  "title": null,                                     // string ≤ 200 or null; trimmed; "" or spaces → null
  "scheduled_activation_at": null,                   // draft only — ISO 8601 WITH offset
  "scheduled_activation_keeps_active_missing": false } // draft only — bool, default false
```

- `scheduled_activation_keeps_active_missing` is what a **scheduled** activation does with the rows the
  draft typed no missing for: `true` keeps the board's current values, `false` resets them to 0.
- Either schedule key sent (even `null` / `false`) with `draft: false` → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**.
- A new draft's rows start with **no typed missing** (they all borrow), no priorities, no manual requested.
- Everything else as v7 + v8.

## 5.16 `PATCH /snapshots/versions/{version_id}/items/{client_id}/missing-quantity` — `null` on a draft

Body: `{"quantity_missing": <strict integer ≥ 0> | null}`. Roles unchanged (admin, manager, worker).

- A number **types** the draft's own value: `quantity_missing` becomes it, `quantity_missing_source`
  becomes `"own"`, and the row stops following the board.
- `null` **clears** it: the row borrows the board's value again (`"active"`, or `"none"` → 0).
- `null` on the **active** version → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`** (an active row always has
  its own number). Non-integer, negative, missing key → 422 (request validation).
- The ceiling refusal `STOCK_REPORT_MISSING_EXCEEDS_CEILING` applies to the typed number, against the
  row's effective requested (v8) and live counters, as v7 §5.16.
- Same stored value (including `null` on a row with nothing typed) → 200 no-op, no event.
- The v6 shortcut `PATCH /items/{client_id}/missing-quantity` keeps its non-null body.

## 5.17 `POST /snapshots/versions/{client_id}/activate` — gains a body

Roles: **admin, manager**. Body optional:

```jsonc
{ "keep_active_missing": false }   // bool, default false
```

- Unknown keys → 422 (request validation). v7's `{"refresh_quantity_requested": …}` → 422. No body and
  `{}` → 200 with the default (reset).
- Steps, replacing v8's list:
  1. The current active version (if any) **closes** exactly as when a version is opened.
  2. Any live row the draft somehow lacks joins it (a safety net; with live membership this adds nothing).
  3. Every snapshot freezes its Scanner requested value from the live row now; manual requested values
     are kept (v8).
  4. **Every snapshot settles its missing**: the draft's typed value where there is one; otherwise, with
     `keep_active_missing: true`, the closing board's value for that row (0 if the row was not on the
     board); with `false`, 0. Then clamped to what the live counters leave uncovered.
  5. The draft becomes active; its schedule is cleared.
- **Manual activation uses only the body.** The draft's stored `scheduled_activation_keeps_active_missing`
  is for scheduled activations. Pre-fill the drawer from it if you like; send the user's choice.
- Refusals and response as v7.
- Events: `stock_report_snapshot_version:closed` (the previous one, if any), then
  `stock_report_snapshot_version:activated` whose `extra` is now **`snapshot_count`, `title`, `scheduled`,
  `keep_active_missing`**. No per-row snapshot events. Refetch (v7 §0.1).

## 5.19 `PATCH /snapshots/versions/{client_id}` — one key returns

```jsonc
{ "title": "Upholstery push",                             // any state; null clears
  "scheduled_activation_at": "2026-10-05T06:00:00+02:00",  // drafts only; null unschedules
  "scheduled_activation_keeps_active_missing": true }      // drafts only
```

- Either schedule key on an active or closed version → **422 `STOCK_REPORT_VERSION_NOT_DRAFT`**.
- Setting only the flag on an unscheduled draft simply stores it.
- The `:updated` event's `extra` is `title`, `scheduled_activation_at`, `scheduled_activation_keeps_active_missing`.
- Everything else as v7 + v8.

## 5.21 Scheduled activation — two precisions

- A scheduled activation behaves as §5.17 with `keep_active_missing` = the draft's stored
  `scheduled_activation_keeps_active_missing`, **read at that moment**. Edit it any time before.
- **Same minute:** when two drafts are scheduled for exactly the same time and both are due, the draft
  **created later** wins. The other is skipped: it stays a draft, its `scheduled_activation_at` becomes
  `null`, and `stock_report_snapshot_version:updated` is emitted for it. Together with v8 §5.21 ("later
  schedule wins; a hand-published board stands") every case is now deterministic.
- Schedules are stored in UTC; send any offset you like (`+02:00` is fine) and read `scheduled_activation_at`
  back as UTC.

## 5.22 `PATCH …/requested-quantity` — correction: typing the shown value pins it

v8 §5.22 said "already the value in force → no-op". **That sentence is replaced:**

- The no-op compares against the **stored manual value** only. A row with no manual value that shows
  `10` (Scanner's number) and receives `{"quantity_requested": 10}` **stores 10** as a manual value:
  `quantity_requested_source` becomes `"manual"`, an event is emitted, and the row **stays at 10** when
  Scanner later asks for 14. That is what a pin is for.
- No-ops: the same manual value again; `null` on a row with no manual value.
- The `quantity_requested` key is **required**: `{}` → 422, `-1` → 422, `"3"` → 422, `null` → 200 (revert).
- Everything else as v8.

---

# 6. Payload shapes — what changes

## 6.6 Item snapshot — `serialize_stock_report_item_snapshot`

`quantity_missing` leaves v7's nullability table (it is now computed on a draft) and joins the computed
fields of v8 §6.6, with one more:

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `quantity_missing` | integer | no | **the number in force**: on an active or closed snapshot its own value, as always; on a **draft** the typed value if there is one, else the active version's value for this row, else 0 |
| `quantity_missing_source` | `"own"` \| `"active"` \| `"none"` | no | `own` = the version's own number (always on active/closed; on a draft, typed); `active` = borrowed from the active version; `none` = draft, nothing typed, no board value (reads 0) |
| `active_quantity_missing` | integer | yes | unchanged from v8: the raw board value, `null` when there is none |

The other computed fields (`quantity_requested`, `quantity_requested_scanner`, `quantity_requested_source`)
are as v8. Note `updated_at` on a draft snapshot is also written when a missing value is typed or cleared.

## 6.7 Version — `serialize_stock_report_snapshot_version`

v8's table **plus**:

| Field | Type | Nullable | Null when |
|---|---|---|---|
| `scheduled_activation_keeps_active_missing` | boolean | no | — |

Present in every state (it only matters on a draft with a schedule).

## 6.8 Version progress

A **draft's** `quantity_missing` and `quantity_target` use the effective missing (typed, else borrowed),
so a draft's progress follows the board's missing counts until the draft types its own.

---

# 7. Events — what changes

| Event | `extra` (v9) |
|---|---|
| `stock_report_snapshot_version:created` | `snapshot_count`, `state`, `title` (unchanged) |
| `stock_report_snapshot_version:activated` | `snapshot_count`, `title`, `scheduled`, **`keep_active_missing`** |
| `stock_report_snapshot_version:updated` | `title`, `scheduled_activation_at`, **`scheduled_activation_keeps_active_missing`** |
| `stock_report_item_snapshot:updated` | as v8; its `quantity_missing` is the **stored** value: `null` on a draft row that borrows. Apply §0.1 item 10's rule or refetch |

Thirteen names still, unchanged.

# 8. Error identities — what changes

| Identity | Change |
|---|---|
| `STOCK_REPORT_VERSION_NOT_DRAFT` | also: `null` missing on the active version (§5.16); the stored missing flag sent on a non-draft (§5.8, §5.19) |

No new identities.

# 9. What is NOT built — additions

- No per-row "keep or reset" at activation: the choice is one flag for every untyped row. Type a value on
  the rows you want to pin.
- No bulk missing route.

# 10. If something here is wrong

As v7 §10: tell us; this file is never edited in place; a change comes as the next dated file listing
the differences. v10 is the consolidated ship-time file and adds nothing.
