---
audience: frontend
subject: Stock Report — draft versions, fourth round: `state=` takes a list, a draft-count read, and the answers to BACKEND_GAPS Q-1..Q-16 (the differences from v7 + v8 + v9)
date: 2026-09-28
status: CONTRACT, published before the backend is built. Build against v7 + v8 + v9 + this file; none is live yet (v7 §0.2).
extends: HANDOFF_TO_FRONTEND_stock_report_snapshots_v9_20260928.md (CONTRACT, unedited) on v8 and v7 (CONTRACT, unedited). Everything in v7, v8 and v9 not restated here stands.
answers: update_stock_report/BACKEND_GAPS_draft_versions_20260927.md (G-2, G-3 accepted; Q-1..Q-16)
companion: HANDOFF_TO_FRONTEND_stock_report_snapshots_v6_20260926.md (CURRENT for what ships today); HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (RATIFIED, unchanged)
source: backend plan update_stock_report/draft_versions_plan.md rev 8
---

# Stock Report — draft versions, v10: what differs from v7 + v8 + v9

A diff, as v7 §10 promises. It carries the **two additions** your gaps document asked for and the owner
accepted (G-2, G-3), and it answers **every question** of that document (Q-1 to Q-16), each as a precision
on the section it belongs to, so the consolidated file can carry the answer without the question.

Section numbers are v7's. A section not listed here is unchanged from v7 + v8 + v9.

## 0. Which document is current

| Document | Status |
|---|---|
| **This file (v10)** | **CONTRACT, not yet live.** A diff on v7 + v8 + v9. Where it restates a section, v10 wins. |
| `…_v9_20260928.md`, `…_v8_20260927.md`, `…_v7_20260927.md` | **CONTRACT, not yet live**, unedited. |
| `…_v6_20260926.md` | **CURRENT until then.** What the server does today. |

At ship, the backend issues one **consolidated** file (now **v11**: v7 + v8 + v9 + v10 merged, full tables)
and points its docs guard at it. v11 adds nothing; it is the same contract in one place. (v9 said v10 would be
that file; v10 is this delta instead, because v9 had already reached you.)

## 0.0 What v10 changes, in one list

1. **`GET /snapshots/versions?state=` accepts a comma list** (§5.9): `state=active,closed` is the history
   page's call. Order unchanged, so the active version comes first. *(G-2)*
2. **New read `GET /snapshots/versions/draft-count`** (§5.23): `{ "draft_count": 2 }`, one count, no rows.
   *(G-3)*
3. **Sixteen precisions**, one per question, none changing a shape: §5.1, §5.2, §5.4, §5.8, §5.9, §5.16,
   §5.19, §5.20, §5.22, §6.6, §6.7, §6.8, §7. The map from question to section is in §11.

## 0.1 What you must change in the app — additions to v7 §0.1, v8 §0.1, v9 §0.1

13. **The history page sends `state=active,closed`** (§5.9) instead of two reads.
14. **The hub's Drafts badge reads `GET /snapshots/versions/draft-count`** (§5.23) and refetches it on
    `stock_report_snapshot_version:created | :activated | :deleted`. Nothing else emits for it.

---

# Part A — routes

## 5.1 `GET /items?version_id=` — two precisions

- **`priority` on a version read** *(Q-2)*: exactly as on the board, scoped to that version. Omitted →
  that version's **null-priority** snapshots (the Unset bucket); `priority=all` → **every** snapshot of the
  version; a list → those priorities. Same parser, same 422 for an unknown token.
- **`missing_only=true` on a draft** *(Q-13)* filters on the **effective** `quantity_missing` (v9 §6.6): a
  borrowing row whose board twin has missing > 0 **is listed**; a row the draft typed `0` for is not; a row
  with nothing typed and no board value (source `none`) is not. A draft's missing board therefore shows the
  board's missing rows until the draft types over them. The outstanding rule (`include_zero_requested`) uses
  the effective requested **and** the effective missing on a draft, the same way.

## 5.2 / 5.3 / 5.7 The v6 shortcuts vs the versioned routes on the active version's id *(Q-3)*

Same command, same write, same response shape, same events. Two differences, both in what happens when the
row or the version is not where the call expects:

| Case | `PATCH /items/{id}/priority` (shortcut) | `PATCH /snapshots/versions/{active}/items/{id}/priority` |
|---|---|---|
| the row has no snapshot in the active version, or there is no active version | 422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT` (v6) | 404 `Stock report item not found.` |
| an activation lands between your read and your PATCH | applies to the **newly** active version, 200 | the id you sent is now closed → 422 `STOCK_REPORT_VERSION_IS_CLOSED` |

Keep the shortcuts for the board and the versioned routes for a draft, as you planned. Both are correct on
the active version.

## 5.4 Scanner creating a row *(Q-11)*

The demand webhook is the **only** code path that creates a `stock_report_items` row (no repair, seed or
manual route creates one), and **every row it creates emits `stock_report_item:created`** — the coalescer
never drops a `:created`. A webhook call that only updates quantities emits `:updated` for changed rows and
nothing for unchanged ones. A row created in a call that then fails (Scanner's deadline) is rolled back with
its event. So: invalidate the versions list on `stock_report_item:created` and no draft's `snapshot_count`
can rise unseen.

## 5.8 `POST /snapshots/versions` — four precisions

- **`extra.state` on `:created`** *(Q-1)*: `"draft"` for `draft: true`, **`"active"`** for `draft: false`
  or no body. Your branch on `=== "draft"` is right.
- **Title** *(Q-6)*: trimmed **first**, then capped. A title whose trimmed length exceeds 200 → **422
  (request validation)**, never truncated. `"   "` → `null`. The same rule on §5.19.
- **Direct active create and missing** *(Q-14)*: with `draft: false` every new snapshot starts at
  `quantity_missing: 0`, as v6. The closing board's missing is **not** carried over — there is no keep
  choice on this path, and the flag is refused with `draft: false` (v9 §5.8). Only activation (§5.17) has
  the drawer.
- **The stored flag without a schedule** *(Q-16)*: `draft: true`, no `scheduled_activation_at`, and
  `scheduled_activation_keeps_active_missing: true` → **stored** (it shows on the version payload and is used
  if a schedule is set later), no refusal, no scheduler row. As §5.19 does.

## 5.9 `GET /snapshots/versions` — `state` takes a list *(G-2)*

Roles, pagination, `priority`, order and each row's shape unchanged.

| Param | Meaning |
|---|---|
| `state` omitted or empty | **every** version: drafts, the active one, closed ones |
| `state=draft` / `active` / `closed` | only that state |
| `state=active,closed` (any comma list of the three) | those states; tokens trimmed, empties ignored, repeats folded |
| any other token (incl. `all`) | **422 `STOCK_REPORT_UNKNOWN_VERSION_STATE`** |

**Order** unchanged: `active_at DESC NULLS FIRST, created_at DESC, client_id DESC`. With
`state=active,closed` the active version is first, then closed ones newest first. The history page is one
call.

## 5.16 `PATCH …/missing-quantity` — nothing new; see §7 for the event promise *(Q-15)*

## 5.19 `PATCH /snapshots/versions/{client_id}` — title rule as §5.8 *(Q-6)*

## 5.20 `DELETE /snapshots/versions/{client_id}` — event timing *(Q-7)*

`stock_report_snapshot_version:deleted` is pushed to the socket **before the HTTP response returns**: the
backend awaits the dispatch inside the command, after the transaction commits. A client inside the deleted
draft may therefore see the event first and a 404 on its next read, or the 404 first if its read was already
in flight. Both orders are as you handle them. The same timing holds for every event in this contract.

## 5.22 `PATCH …/requested-quantity` — as v9; see §6.6 for the read after Scanner moves *(Q-10)*

## 5.23 `GET /snapshots/versions/draft-count` — NEW *(G-3)*

Roles: **admin, manager, worker, seller** (as §5.9). No params. No body.

```jsonc
{ "data": { "draft_count": 2 } }
```

- Counts the workspace's versions whose `state` is `draft`. Always present, `0` when there are none.
- One count statement: no progress, no rows. Cheap enough to refetch on every version event.
- Absent workspace context → as every other route (auth). No refusal identities of its own.
- **No event of its own.** Refetch on `stock_report_snapshot_version:created`, `:activated` and `:deleted`
  (those are the three that change the count). `stock_report_item:created` does not change it.
- Declared beside `/snapshots/versions/active`, before `/snapshots/versions/{client_id}`, so the literal
  segment is never read as a version id.

---

# 6. Payload shapes — what changes

## 6.6 Item snapshot — one precision *(Q-10)*

When Scanner posts a new `quantity_requested` for a row whose **draft** snapshot holds a manual value, the
next read of that draft row shows `quantity_requested_scanner` = the **new live value** and
`quantity_requested` = the manual value, `quantity_requested_source: "manual"`. The event
`stock_report_item:updated` carries the row's live value; mirroring it into the row's
`quantity_requested_scanner` on a draft and leaving `quantity_requested` alone, as your plan does, agrees
with the read. (On the **active** version `quantity_requested_scanner` is the frozen value and does **not**
move with that event; only a refresh moves it.)

## 6.7 Version — how dates are echoed *(Q-8)*

Every ISO 8601 string in this contract, `scheduled_activation_at` included, is echoed **normalised to UTC**
with an explicit `+00:00` offset, e.g. `2026-10-05T04:00:00+00:00`, never `Z` and never the offset it was
sent with. Send any offset; read back UTC. Parse both, as you do.

## 6.8 Version progress — the `priority` filter on a draft *(Q-5)*

Same engine, same parser (§5.1): `?priority=high,medium,low` on `GET /snapshots/versions`,
`GET /snapshots/versions/{id}` and `GET /snapshots/versions/active` selects a draft's snapshots exactly as
the active version's, so a draft card's three bars and the hub card's are computed alike. The only
difference between the two is what the numbers are built on: live requested and effective missing on a
draft (v8 §5.9, v9 §6.8), frozen requested and own missing once active.

---

# 7. Events — two promises

- **Every emission of `stock_report_item_snapshot:updated` carries all eight `extra` keys** *(Q-4)*:
  `stock_report_item_id`, `version_id`, `priority`, `priority_order`, `quantity_missing`,
  `quantity_resolved`, `quantity_requested_scanner`, `quantity_requested_manual`. A key is **never omitted**;
  a value can be `null` (`priority` and `priority_order` on an unprioritised row, `quantity_missing` on a
  draft row that borrows, `quantity_requested_scanner` on a draft, `quantity_requested_manual` when none).
  On every path: the six row-edit routes, §5.22, apply-priorities, the refresh, the clamps, repair.
- **Every write to an active row's `quantity_missing` emits it** *(Q-15)*: a §5.16 mark; the clamp when an
  assignment is created on the board; the clamp after a §5.22 requested change on the active version; the
  refresh's clamp; a repair. So a borrowing draft row can follow the board from that event alone. **The one
  silent path is activation** (v9 §5.17 steps 4–5, no per-row events): the new board's missing values arrive
  with `stock_report_snapshot_version:activated`, on which you already refetch — and after it every draft
  borrows from the **new** active version, so refetch open draft pages on `:activated` too.

Thirteen names still, unchanged. No new events.

# 8. Error identities — what changes

None new. `STOCK_REPORT_UNKNOWN_VERSION_STATE` now also covers an unknown token **inside** a list (§5.9).

# 9. What is NOT built — additions

- No `total` in `stock_report_snapshot_versions_pagination`; the count read (§5.23) is the badge's source.
- No count read for other states.

# 10. If something here is wrong

As v7 §10: tell us; this file is never edited in place; a change comes as the next dated file listing the
differences. **v11** is the consolidated ship-time file and adds nothing.

# 11. Map — BACKEND_GAPS question → section

| Question | Answered in | One line |
|---|---|---|
| G-2 | §5.9 | `state=active,closed` accepted |
| G-3 | §5.23 | `GET …/draft-count` → `{ "draft_count": n }` |
| Q-1 | §5.8 | `:created` `extra.state` is `"active"` for `draft: false` |
| Q-2 | §5.1 | `priority` omitted = the version's Unset bucket; `all` = every snapshot |
| Q-3 | §5.2 | same command; differ only in the 422/404 mapping and after a race with activation |
| Q-4 | §7 | all eight keys always present, `null` where there is no value |
| Q-5 | §6.8 | same filter on a draft's progress |
| Q-6 | §5.8 | trimmed first, then > 200 → 422 |
| Q-7 | §5.20 | event pushed before the response returns |
| Q-8 | §6.7 | echoed as UTC `+00:00` |
| Q-9 | v9 | answered there |
| Q-10 | §6.6 | read agrees: scanner = new live value, requested = manual |
| Q-11 | §5.4 | only the webhook creates rows; every created row emits `:created` |
| Q-12 | v9 | answered there |
| Q-13 | §5.1 | `missing_only` on a draft reads the effective missing |
| Q-14 | §5.8 | direct active create starts at 0 |
| Q-15 | §7 | every active missing write emits, activation excepted (refetch on `:activated`) |
| Q-16 | §5.8 | stored without a schedule |
