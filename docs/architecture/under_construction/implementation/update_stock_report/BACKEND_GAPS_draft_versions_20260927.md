---
audience: backend (carried by the owner)
subject: Stock report draft versions — what the frontend intention needs that v7 + v8 + v9 do not offer
date: 2026-09-27, re-baselined 2026-09-28 on v8, then on v9 (same day)
against: HANDOFF_TO_FRONTEND_stock_report_snapshots_v7_20260927.md + …_v8_20260927.md + …_v9_20260928.md
plan: PLAN_frontend_draft_versions_20260927.md
---

# Backend gaps

Three entries. **G-1 is withdrawn** (owner, 2026-09-27: the frontend skips demotion; kept for the record).
**G-2 and G-3 were accepted by the owner on 2026-09-28 but are in neither v8 nor v9** — they are the two
additions the frontend builds against and expects in the next diff (or in the consolidated v10).

### G-1 — Demote an active version back to a draft — WITHDRAWN (owner, 2026-09-27)

- **What the user needs:** the intention's edit mode "allows the user to … change an active to a draft".
- **Why the contract does not cover it:** v7 §5.19 changes title and schedule only; §5.17 goes draft →
  active only; §5.20 deletes drafts only. Nothing turns an active version into a draft.
- **Proposed backend shape:** none requested.
- **Can it be done another way?** No.
- **Blocks:** nothing — the owner dropped the capability. The form's state picker is read-only when
  editing an active version (plan §F.3).

### G-2 — `state=` accepts one value; the history page wants active + closed — ACCEPTED (owner, 2026-09-28), not in v8 or v9

- **What the user needs:** the history page lists the active version first, then the closed ones, and must
  not show drafts now that v7 §5.9 returns drafts first by default.
- **Why the contract does not cover it:** v7 §5.9 `state` takes exactly one of `draft | active | closed`;
  anything else is 422 `STOCK_REPORT_UNKNOWN_VERSION_STATE`. Neither v8 nor v9 restates §5.9's parameter.
- **Proposed backend shape:** accept a comma list on the same param, mirroring `priority`:
  `GET /snapshots/versions?state=active,closed` (order unchanged: `active_at DESC NULLS FIRST, …`, which
  puts the active version first once drafts are excluded). Unknown token → the existing 422. No new
  response keys or events. The docs guard's §5.9 row must allow the list.
- **Can it be done another way?** Yes (active card from `GET …/versions/active` + `state=closed` pages),
  but the owner chose the backend change.
- **Blocks:** plan §G.4 sends `state=active,closed` and gets a 422 until this ships; the page shows its
  error state until then. Everything else proceeds.

### G-3 — No draft count for the hub badge — REQUESTED (owner, 2026-09-28), not in v8 or v9

- **What the user needs:** the hub's Drafts button reads "Drafts · 2" so a manager sees pending work
  without opening the page; the owner wants it from a cheap dedicated read, not by paging the list.
- **Why the contract does not cover it:** v7 §5.9 pagination reports `has_more`, `limit`, `offset`, never a
  total; no count route exists in v7, v8 or v9.
- **Proposed backend shape:** `GET /api/v1/stock-report/snapshots/versions/draft-count`, roles admin +
  manager + worker + seller (as §5.9), no params. Response `{ "data": { "draft_count": 2 } }`. A count
  query only — no progress, no rows. No new events: the frontend refetches it on
  `stock_report_snapshot_version:created | :activated | :deleted` and on `stock_report_item:created`
  (harmless). (Alternative with the same cost: `"total"` in `stock_report_snapshot_versions_pagination`
  under the `state` filter — but that still returns a page of rows with progress.)
- **Can it be done another way?** Yes (first `state=draft` page, "20+" past twenty), ruled out by the owner.
- **Blocks:** the hub's Drafts badge (plan §H) is hidden until the endpoint ships; everything else proceeds.

## Questions about v7 + v8 + v9

Q-9 and Q-12 are **answered by v9** and kept only so the list stays numbered; Q-13 to Q-16 are new with v9.

- **Q-1 · `extra.state` on `:created` for `draft: false`.** v7 §7 says `…version:created` carries `state`.
  For a `draft: false` create is it `"active"`? The handler branches on `extra.state === "draft"`; any
  other value takes the board-refetch path.
- **Q-2 · `GET /items?version_id=<draft>` and `priority` omitted.** v7 §5.1 says every v6 parameter applies
  "exactly as on the board". So omitted `priority` = the draft's null-priority snapshots (the Unset bucket),
  and `priority=all` = every snapshot of the draft? The draft board reuses the board's bucket picker on
  that assumption.
- **Q-3 · Row-edit routes on the active version by id.** v7 §5.14–5.16 say "send the active version's id
  to edit the board this way". The frontend keeps the v6 shortcuts for the board and uses the versioned
  routes only with a draft's id, except v8 §5.22 which has no shortcut. Any behavioural difference between
  `PATCH /items/{id}/priority` and `PATCH /snapshots/versions/{active}/items/{id}/priority`?
- **Q-4 · Snapshot event keys on refresh and on the §5.22 clamp.** v8 §7 lists eight `extra` keys for
  `stock_report_item_snapshot:updated`. Are all eight always present on every emission (refresh, manual
  requested, priority moves, a typed or cleared missing on a draft — v9 §7), never omitted? The handler
  treats every key as present and would reset a priority to null if one were omitted. (v9 §7 makes
  `quantity_missing` nullable on the event — present as `null`, not absent, is the reading.)
- **Q-5 · Draft `progress` and the `priority` filter.** v8 §5.9: a draft's `progress` is fully live. Does
  `?priority=high,medium,low` filter it the same way as for the active version (`_priority_filter.py`), so
  the draft card's three bars are comparable to the hub card's?
- **Q-6 · Title trimming and the 200-char cap on §5.8.** Is the cap applied before or after trimming, and is
  a 201-char title a 422 (request validation) or silently truncated? The form caps at 200 before trimming.
- **Q-7 · Deleted draft while a client is inside it.** After v7 §5.20, `GET …/versions/{id}` and `GET
  /items?version_id=` are 404 version. Is the `:deleted` event emitted before the HTTP response returns?
  Both orders are handled.
- **Q-8 · `scheduled_activation_at` echo.** Is it echoed back normalised to UTC (`…Z`) or in the offset it
  was sent with? The client sends `Z` and parses either.
- **Q-9 · `active_quantity_missing` in the snapshot event — ANSWERED by v9 §0.1 item 12 + §7.** The
  active version's own `stock_report_item_snapshot:updated` is the signal: the plan patches every
  borrowing draft row (`quantity_missing_source !== "own"`) from that event's `quantity_missing`. See
  Q-15 for the one case left.
- **Q-10 · Row `:updated` on a draft with a manual value (v8 §0.1 item 9).** When Scanner posts a new
  `quantity_requested` for a row whose draft snapshot has a manual value, the event carries the row's live
  value only. The plan mirrors it into `quantity_requested_scanner` and leaves `quantity_requested` (manual)
  alone. Does the read payload agree (`quantity_requested_scanner` = the new live value)?
- **Q-11 · Draft `snapshot_count` after a Scanner row joins (v8 §5.4).** It rises by 1 with no version
  event. The plan invalidates the versions list on `stock_report_item:created`. Is there any case where a
  row is created without that event (e.g. a demand webhook that only updates)?
- **Q-12 · §5.22 `null` on a row that never had a manual value — ANSWERED by v9 §5.22** (the no-op compares
  against the stored manual value only; `null` with nothing stored is a no-op in every state) and, for
  missing, by v9 §5.16 (`null` on a row with nothing typed is a no-op).
- **Q-13 · `missing_only=true` with `version_id=<draft>` (v7 §5.1, v9 §6.6).** v7 §5.1 filters on the
  draft's own `quantity_missing`; v9 §6.6 makes a draft's `quantity_missing` the effective value (typed,
  else borrowed). Does the filter now read the effective value — so a draft's missing board shows the rows
  the board has missing, unless the draft typed 0 — or still only rows with a typed value > 0? The plan
  restarts a draft's missing-mode lists on the active version's snapshot events either way (D.1), but the
  empty-state copy differs.
- **Q-14 · A direct active create (`POST /snapshots/versions`, `draft: false`) and the board's missing
  counts.** v9 §5.17 step 4 (keep or reset) speaks for activation; v9 §5.8 rejects the keep flag with
  `draft: false`. What do the new active snapshots start with — 0 (as v6), or the closing board's values?
  The form offers no choice for this case (plan OC-16); the answer only decides the form's helper line.
- **Q-15 · Every change of an active row's `quantity_missing` emits `stock_report_item_snapshot:updated`?**
  v9 §0.1 item 12 relies on it for the draft rows that borrow. A §5.16 mark on the board does; do the
  clamps too — after a §5.22 requested change on the active version (v8) and after an assignment moves the
  live counters? If any clamp is silent, borrowing draft rows keep a stale count until their next refetch.
- **Q-16 · `scheduled_activation_keeps_active_missing` on create without a schedule.** The form sends the
  flag on every `draft: true` create (v9 §5.8 says draft-only, default `false`). With `draft: true`, no
  `scheduled_activation_at` and the flag `true`, is it stored (as v9 §5.19 does for a PATCH: "simply
  stores it") rather than refused?
