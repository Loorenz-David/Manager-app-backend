# Plan 9 — Processed webhook: resolution vocabulary, grouped counter update, replay, one owning transaction

```
state: NOT_STARTED
phase: 9 of 15
depends_on: 7, 8 (APPROVED)
projection: mandatory, NOT waivable (rule 17: raw-bytes parsing; grouped statement + asyncpg)
complex: yes — per-row grouping of the counter statement, sorted row locks (X2), owning transaction (X3)
```

## 1. Goal

`POST /api/v1/location-tracker/webhooks/items-processed`: key-authenticated (the phase-7 verifier),
raw-bytes parsed, each `article_number` decided by the §14F F5 order (`item_not_found` →
`no_open_assignment` → `awaiting` → `resolved`, reason `null` → `in_queue`/`in_progress` →
`resolved`, reason `early`, landing the assignment in the terminal state `resolved_early`), every
move performed through `move_assignment` in grouped form (one guarded counter statement per row
carrying the summed delta per column, D6), goal credit per F4, the task never touched, replay-safe,
inside one owning transaction whose row locks are taken ascending. **Not in this phase:** demand
(6–7), task sync (10), the Scanner delete webhook (13A).

## 2. Read first

1. `master_plan.md` §6.1 (outcome/reason enums — `ItemsProcessedReasonEnum` is `item_not_found`,
   `no_open_assignment`, `early`), §6.5 (`items_processed_request.py`, `process_items_processed.py`,
   `_move_assignment.py`'s `resolve_processed_group`), §6.6, §9 rules 4–7, 9, 16.
2. Intention §8.2 and §8A **as superseded by §14F** (§14C C47, C48, C50), §8B MC-8 (processed
   defects; step 7 "duplicates are not an error"), MC-9 (processed replay; "one owning transaction" —
   applied here per re-check X3), MC-10 **with step 2 replaced by §14F F5**, the D6 plan's
   **"Processed, grouped per row"** paragraph (now per row *and per from-column*), §5A MC-1 (write
   order, inline repair with a grouped delta; the table as amended in plan 4 task 1), §6A MC-5 with
   §14F F4 (credit on entering `resolved_early`), MC-11 (the interleavings are proven in phase 10;
   here only the single-writer path), MC-17 ("Scanner resolves" row — applies to both exits),
   MC-19 ("Processed, resolved" row; §14F F8), **§14F F1–F8 in full**, §14C C11, C13, C26, U8.
3. Re-check handoff §4 **X2** and **X3** (verbatim: sort the request's row locks ascending; one
   owning transaction with nothing before it).
4. Scanner v2 handoff §4.2 and §4.3 (read-only; the wire vocabulary this phase must match exactly:
   `resolved`/`null`, `resolved`/`early`, `ignored`/`item_not_found`, `ignored`/`no_open_assignment`).
5. Plans 7 and 8 as shipped (verifier; assignments created through `CR`).

## 3. Dependencies

Phases 7 and 8 APPROVED.

## 4. Files expected to change

New: `bm/services/commands/stock_report/items_processed_request.py`, `process_items_processed.py`;
`app/tests/unit/services/commands/stock_report/test_items_processed_request.py`,
`app/tests/integration/services/commands/stock_report/test_process_items_processed.py`,
`test_process_items_processed_locks.py`.
Edited: `bm/routers/api_v1/location_tracker_webhooks.py` (second route),
`app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py` (second route wiring).

## 5. Tasks

1. `parse_items_processed_body(raw: bytes) -> list[str]`: decode, top-level list ≥ 1, each entry an
   object with `article_number` a non-blank string (unknown keys ignored); every defect collected;
   `ValidationError("Malformed request: …")`. Returns the numbers **as received** (echo) — stripping
   happens in the command.
2. `process_items_processed(ctx)`: verify (workspace id from settings) → parse → `assert not
   ctx.session.in_transaction()` → `maybe_begin` (owner mode; **no statement before it**, X3) →
   workspace `SELECT` (MC-8 step 4) → one `SELECT` of non-deleted items of the workspace whose
   `article_number` is in the set of stripped numbers → one `SELECT` of their non-deleted **active**
   assignments (unlocked id discovery: `client_id`, `stock_report_item_id`, `state`) → lock the
   distinct rows **ascending** in one statement (X2) → lock the candidate assignments ascending →
   re-read state → per entry **in request order** decide on the re-read state, in the §14F F5 order
   (a duplicate later in the request sees the earlier one's effect):
   `item_not_found` (no non-deleted item) → `no_open_assignment` (no non-deleted assignment of the
   item in `ACTIVE_ASSIGNMENT_STATES`; covers never-assigned and terminal-only, `resolved_early`
   included) → re-read `awaiting` → **`resolved`, reason `null`**, target `resolved` → re-read
   `in_queue` or `in_progress` → **`resolved`, reason `"early"`**, target `resolved_early`. No active
   state is ignored. For each moved entry write the assignment's own columns (`state` = the target,
   `updated_by_id NULL`, `updated_at ctx.now`, and for a `resolved_early` target the credit memory
   per F4 when a current goal record exists) and flush; then, rows ascending, **one** guarded
   counter statement per row whose delta vector is the per-column sum over that row's moved
   assignments (`−Σq_awaiting` on `quantity_awaiting`, `−Σq_in_queue` on `quantity_in_queue`,
   `−Σq_in_progress` on `quantity_in_progress`; a column with no mover carries `0`) — zero rows →
   the MC-1 inline repair once for that row with the group's per-column deltas, trigger
   `inline:items_processed`; then the goal step per assignment: no-op for `awaiting → resolved`
   (MC-5 row 3, memory kept), `G += q` for each assignment entering `resolved_early` (F4; one
   column-referencing `UPDATE` on `G` per such assignment, or one with `+Σq` when several share
   `G` — either is within MC-5; the record count instrument below does not depend on it); the task
   is **never** written (F3); events per moved assignment (`state-changed` with the new state) + one
   `:updated` per touched row from `RETURNING`; dispatch after the block; return
   `{"results": [{"article_number": <as received>, "outcome", "reason"}]}` in request order. This is
   `move_assignment` in grouped form: implement it by extending `_move_assignment.py` with a grouped
   entry point `resolve_processed_group(session, assignments, *, row, workspace_id, now, trigger)`
   that computes each assignment's target from its re-read state (`awaiting → resolved`, otherwise
   `resolved_early`), shares the same statement builder and repair code path — never a second
   counter path (HC-3) — and applies the goal step per assignment. The name is registered in
   master plan §6.5 (`_move_assignment.py` row).
3. Router: second route in the same file and shape.
4. Tests first from the table.

## 6. Criteria

Fixture: **F0** with A created through `CR` and driven to the stated state with `move_assignment`
where needed (Scanner-first rows of MC-11 come in phase 10). `PR(body_bytes)` = the command with a
valid key. "401"/"422" as in plan 7. Rows end with `assert_stock_report_clean` unless drift is
planted.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | no `x-api-key` | 401 `Unauthorized.`; nothing written | — | M7, MC-8 |
| C1(b) | wrong key | 401 | — | M7 |
| C1(c) | workspace setting names no workspace | 401 | — | MC-8 step 4 |
| C1(d) | wrong key **and** malformed body | 401 (not 422) | parse first | MC-8 order |
| C1(e) | valid `x-api-key` and a valid body naming a live assignment, but the workspace setting blank (`"   "`) | 401 `Unauthorized.`; **zero statements issued** (the MC-9 statement listener) — the refusal happens in the verifier, before any DB read; the assignment untouched; no event. Run the twin with the API key blank instead | `webhook_verifier.py` (definition site), each run separately: (i) delete the `workspace_id is None or not workspace_id.strip()` guard → the blank id is returned, the command runs and issues at least the workspace `SELECT` → the **zero-statement** clause reddens even if the request still ends 401; (ii) delete the `api_key` guard → same shape | MC-8 step 2; batch B2 review 1 N1, CF-3, owner card 1. Measured 2026-09-21: with guard (i) deleted the whole of batch B stays green, because phase 7's demand path happens to refuse a blank workspace downstream — the zero-statement clause is what makes the guard observable on this phase's path |
| C2(a) | `b"{}"` | 422 | — | MC-8 |
| C2(b) | `b"[]"` | 422 | accept → 200 | MC-8 (U21) |
| C2(c) | `["0000612"]` (entry not an object) | 422 | — | MC-8 |
| C2(d) | `[{}]` | 422 (`article_number` missing) | — | MC-8 |
| C2(e) | `[{"article_number": 612}]` | 422 | coerce with `str()` | MC-8 |
| C2(f) | `[{"article_number": "  "}]` | 422 | — | MC-8 |
| C2(g) | `[{"article_number": "SR-x", "location": "LC1"}]` | 200 | reject unknown keys | MC-8 (U7) |
| C2(h) | entries 0 and 2 malformed | 422 naming both indices; nothing written | — | MC-8 |
| C3(a) | number matching no item | `ignored` / `item_not_found` | — | MC-10 step 2 |
| C3(b) | item exists, never assigned | `ignored` / `no_open_assignment` | — | MC-10 |
| C3(c) | item with only a `resolved` (and separately a `failed`, and separately a `resolved_early`) assignment — three sub-cases, one parametrized test | `ignored` / `no_open_assignment` for each | decide on `state NOT IN (resolved, failed)` (a hand-typed terminal list) → the `resolved_early` sub-case reads `resolved`/`early` | §14F F5, F7 (replay of an early resolution), MC-10 ("covers terminal-only"), rule 16 |
| C3(d) | A `in_queue` (T `pending`) | `resolved` / reason `"early"`; A `resolved_early` | report `ignored` for a non-awaiting state (the retired rule) | §14F F5 (P43), §14C C48, M3 |
| C3(e) | A `in_progress` (T `working`) | `resolved` / reason `"early"`; A `resolved_early` | — | §14F F5 |
| C3(f) | A `awaiting` | `resolved` / reason `null` (JSON `null`, not the string) | report `early` for every resolution | §14F F5, MC-10, M3 |
| C3(l) | every result of C3(a)–(f) | `outcome ∈ {"resolved", "ignored"}` and `reason ∈ {null, "item_not_found", "no_open_assignment", "early"}`; `reason` is `null` exactly when `outcome == "resolved"` from `awaiting` | emit `reason: "awaiting"` / omit the key | §14F F5 closed vocabulary, v2 §4.3 |
| C3(g) | `" SR-x "` for item `SR-x` | matches (outer trim) | — | MC-10 step 1 |
| C3(h) | `"0000612"` vs stored `"000612"` | `item_not_found` (leading zeros significant) | strip zeros | MC-10 (U8) |
| C3(i) | `"sr-x"` vs `"SR-x"` | `item_not_found` (case-sensitive) | `ilike` | MC-10 |
| C3(j) | `"04 2 001 0034"` vs stored `"042 001 0034"` | `item_not_found` (inner spaces significant) | fold whitespace | MC-10, v2 §4.1 |
| C3(k) | matching item in the **foreign** workspace only | `item_not_found` | drop `workspace_id` | M4 |
| C4(a) | A `awaiting` `q = 8`, credited to G (`G == 8`) | A `resolved`; counters `(0, 0, 0)`; `G == 8`; `mem == G`; `updated_by_id IS NULL`, `updated_at == ctx.now` | subtract from G | MC-10, MC-5 row 3, MC-17 |
| C4(b) | same | events `[stock_task_assignment:state-changed {state: resolved}, stock_report_item:updated {quantity_awaiting: 0, …}]` | — | MC-19 |
| C4(c) | same | `tasks.is_stock_assignment` stays true | clear the flag on resolve | MC-15 (P21) |
| C4(d) | A `in_queue` `q = 8` (T `pending`, no step), R has goal record G (`G == 0`, `mem IS NULL`) | A `resolved_early`; counters `(0, 0, 0)`; `G == 8`; `mem == G`; `updated_by_id IS NULL`, `updated_at == ctx.now`; T's `state` still `pending`, `tasks.updated_at` / `updated_by_id` / step count byte-identical; `is_stock_assignment` stays true | write `task.state = READY` (touch the task) / skip the credit → `G == 0` | §14F F2–F4, M2 (round-9 sentence), M5, MC-17 |
| C4(e) | A `in_progress` `q = 8` (T `working` with a `working` step) | as (d): A `resolved_early`; `(0, 0, 0)`; `G == 8`; T still `working`, its step still `working` | — | §14F F2–F4 |
| C4(f) | (d) with **no** goal record on R | A `resolved_early`; `(0, 0, 0)`; `mem IS NULL`; `count_writes` on `stock_report_history_records == 0` | create a goal record | §14F F4 ("with no goal record, nothing is credited") |
| C4(g) | (d) with `capture_dispatch` | events `[stock_task_assignment:state-changed {state: resolved_early}, stock_report_item:updated {quantity_in_queue: 0, …}]`; **no** task event | emit `state: resolved` | §14F F8, MC-19 |
| C5(a) | `[{"article_number": "SR-x"}, {"article_number": "SR-x"}]` with A awaiting | results `[resolved/null, ignored/no_open_assignment]` | evaluate both on the pre-request state → two `resolved` | MC-10 step 3, v2 §4.3 |
| C5(b) | the same body with A `in_queue` | results `[resolved/early, ignored/no_open_assignment]`; A `resolved_early`; `−q` applied once | — | §14F F5, F7 |
| C6(a) | deliver `[SR-x]` twice | second delivery: `count_writes` over the four MC-9 tables `== 0`; no event; result `ignored/no_open_assignment` | — | MC-9, HC-5, M3 |
| C6(b) | deliver `[SR-x]` twice with A `in_queue` at the first delivery | first: `resolved/early`; second: `count_writes == 0`, no event, `ignored/no_open_assignment`; `G` unchanged between the deliveries | — | §14F F7, MC-9 |
| C7(a) | three items on R (three tasks), all `awaiting` (`q` 1, 2, 3), one request naming all three | all `resolved`; `quantity_awaiting` 6 → 0; one `:updated` for R | sum only the first assignment's `q` → `quantity_awaiting` 5 | D6 (processed grouping), HC-3 |
| C7(b) | entries across R and R2 | two `UPDATE`s on `stock_report_items` (one per row), rows ascending | — | D6 |
| C7(c) | (a) with raw `quantity_awaiting = 2` (truth 6) | all resolved; counter 0; exactly one repair record `{stock_report_item, R, quantity_awaiting, stored "2", recomputed "0", inline:items_processed}`; warning delta `-6` | per-assignment repair → three records | MC-1 grouped delta, §12A |
| C7(d) | three items on R: A1 `awaiting` `q = 1` (credited, `G == 1`), A2 `in_queue` `q = 2`, A3 `in_progress` `q = 3`; counters `(2, 3, 1)`; one request naming all three | results `[resolved/null, resolved/early, resolved/early]`; A1 `resolved`, A2/A3 `resolved_early`; counters `(0, 0, 0)`; `G == 6`; one `:updated` for R with all three counters `0` | apply only the `awaiting` column's delta → counters `(2, 3, 0)` | D6 (per row, per column), §14F F2, F4, HC-3 |
| C7(e) | (d) with raw `quantity_in_queue = 0` and `quantity_in_progress = 1` (truth 2 and 3) | all moved; counters `(0, 0, 0)`; **exactly two** repair records for R: `quantity_in_queue` (stored `"0"`, recomputed `"0"`) and `quantity_in_progress` (stored `"1"`, recomputed `"0"`), both `inline:items_processed`; none for `quantity_awaiting` | one record per moved assignment → three | MC-1 trace rule ("one record per counter column where `stored + delta ≠ recomputed`"), §12A |
| C8(a) | after a `200` with a resolve | a **fresh** session (`get_db_session()`) reads A `resolved` (the transaction committed) | execute any statement on `ctx.session` before `maybe_begin` (e.g. the workspace SELECT) → subordinate mode → nothing commits → red | X3, MC-9 "one owning transaction" |
| C8(b) | two concurrent requests: request 1 names items on R then R2, request 2 names items on R2 then R (four awaiting assignments), barrier-released after parse | both return 200; all four assignments `resolved`; no `DBAPIError` | lock rows per entry in request order — **interleaving not forced**; the reviewer verifies the single ascending lock statement structurally | X2, MC-1 lock order |

## 7. Notes

- Sizing: 43 criterion rows in 8 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- **Owner card 1 fold, 2026-09-21.** The count above is the previously derived count **+1**: exactly one criterion row was added to this plan by that fold, verified as a single `^+| C` line in `git diff` (not re-derived by a new script — the published totals and my regex disagree on row shape, and a typed count is the defect this project keeps finding).
- The grouped entry point is the one sanctioned extension of `_move_assignment.py` after phase 4;
  it must call the same guarded-statement builder and the same repair routine (a second copy is a
  review finding).
- C8(b) is declared unable to force its interleaving (master plan §9 rule 9).
- MC-11's three interleavings (Scanner first while `awaiting`; task reopen first; Scanner first
  while `in_progress`) are phase 10's C5.
- Round 9 (2026-09-19): C3(c)–(f) rewritten to the §14F F5 order (the retired reason appears
  nowhere in this plan); C3(l), C4(d)–(g), C5(b), C6(b), C7(d)–(e) added. C7(d) is C7(a)'s
  mixed-state twin. Both rows lost their "exactly one `UPDATE`" clause (owner ruling 2026-09-19: outcomes, not internals); the grouped
  per-column statement stays the implementation rule of task 2, unguarded by a test. The row's guarded statement now carries up to three
  non-zero deltas; the repair-record rule is unchanged (one record per column actually wrong).

## 8. Review log

**Owner, 2026-09-21 — criterion row authored (batch B2 card 1, CF-3).** **C1(e)** added: the shared verifier must refuse a blank workspace setting (or blank API key) *before any DB read*. **No test exists yet — owed by this phase's implementation round.** The reviewer measured that deleting this guard leaves the whole of batch B green, because phase 7's demand path refuses a blank workspace a moment later; that accidental backstop is not guaranteed on this phase's path. The row's **zero-statement** clause, not the 401, is what makes the guard observable — a 401 alone would let the mutation stay equivalent.

(empty)
