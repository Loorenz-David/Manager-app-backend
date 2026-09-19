# Plan 4 — Transition operation: moves, unit counters, inline self-heal, removal, stamps, payloads

```
state: NOT_STARTED
phase: 4 of 15
depends_on: 3 (APPROVED)
projection: mandatory (counter arithmetic, guarded statement, lock discipline)
complex: yes — guarded column-referencing UPDATE with inline repair, write order, lock order
```

## 1. Goal

`move_assignment` — the one operation that moves an assignment between states (including creation
`∅ → B`, the Scanner-only exits `awaiting → resolved` and `in_queue`/`in_progress → resolved_early`,
and `DELETE`) and moves the unit counters with it, self-heals a counter that would go negative,
writes its own columns first and flushes, stamps per MC-17, and returns events built from
`RETURNING` — plus `remove_assignment` (DELETE + task-flag recompute). **Not in this phase:** the
goal-record step (phase 5 adds `apply_goal_effect` after the counter statement; every row here uses
rows with **no goal record**, so `credited_history_record_id` stays NULL), any command or endpoint
that calls the operation (phases 8–13A).

## 2. Read first

1. `master_plan.md` §6.1, §6.5 (`_move_assignment.py`, `_remove_assignment.py`, `_events.py`,
   `_task_flag.py`, `_locks.py`), §6.7, §9 rules 2–4, 6, 16.
2. Intention §5 (rules 1–6, with rule 2 as **superseded by §14F F2** — §14C C47), §5A MC-1 in full
   (allowed-move table **as amended by §14F F1–F2**, counter effect, self-heal block including write
   order, `stored_before`, instruments (a)–(c), the global lock order), MC-16 (counter predicate
   row), §4B MC-15 (writer ii), MC-17 (move/delete/Scanner rows), §9D MC-19 (payload rule "from
   RETURNING"), §12A (record fields, closed trigger set), §14C C10, C39, C44, C45, C47; **§14F F1,
   F2, F3** (the sixth state and its two Scanner-only entries).
3. Plan 3's Review log and `consistency.py` as shipped (the recomputation you call).
4. Repo: `bm/services/commands/cases/message_writes.py:60-75`; `architecture/32_concurrency.md`
   "read-then-assign" paragraph; `app/tests/integration/services/commands/item_economics/test_phase7_concurrency.py:1-60`
   (two-session shape, for the reviewer's optional probe — no two-session row in this phase).

## 3. Dependencies

Phase 3 APPROVED (`recompute_row_counters`, `write_repair_record`, `recompute_task_stock_flag`,
`assert_stock_report_clean`, `record_statements`).

## 4. Files expected to change

New: `bm/services/commands/stock_report/_move_assignment.py`, `_remove_assignment.py`, `_events.py`
(builders only; `coalesce_stock_report_events` arrives in phase 8);
`app/tests/integration/services/commands/stock_report/test_move_assignment.py`,
`test_remove_assignment.py`. Nothing else.

## 5. Tasks

1. `_move_assignment.py`:
   - `ASSIGNMENT_DELETE` sentinel; `IllegalAssignmentMove(RuntimeError)`.
   - `move_assignment(session, assignment, target, *, workspace_id, actor_user_id, now, trigger,
     is_creation=False)`. The caller holds the row lock and the assignment lock (MC-1 steps 4–5) and
     has re-read `state`/`is_deleted`; the operation asserts the move is a ✓ cell of the table
     below given `from = "∅" if is_creation else assignment.state`, returns `[]` on a `=` cell
     without touching the session, raises `IllegalAssignmentMove` on a ✗ or `—` cell. The table is
     MC-1's, with the §14F F2 column added; it is **total** over the six states plus `∅` and
     `DELETE`, and the operation's allowed-set is written from `ACTIVE_ASSIGNMENT_STATES` /
     `TERMINAL_ASSIGNMENT_STATES` plus the two explicit Scanner cells — never a hand-typed list of
     state names (master plan §9 rule 16):

     | from \ to | in_queue | in_progress | awaiting | resolved | resolved_early | failed | DELETE |
     |---|---|---|---|---|---|---|---|
     | ∅ (creation) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
     | in_queue | = | ✓ sync | ✓ sync | ✗ | ✓ **Scanner only** | ✓ sync | ✓ |
     | in_progress | ✓ sync | = | ✓ sync | ✗ | ✓ **Scanner only** | ✓ sync | ✓ |
     | awaiting | ✓ sync | ✓ sync | = | ✓ **Scanner only** | ✗ (F2: never) | ✓ sync | ✓ |
     | resolved | — | — | — | = | — | — | ✓ |
     | resolved_early | — | — | — | — | = | — | ✓ |
     | failed | — | — | — | — | — | = | ✓ |

     Counter effect is §5 rule 5 for every ✓ cell: `−q` on *from* if active, `+q` on *to* if active;
     the three terminal targets add nothing, so a move into `resolved_early` is `−q` on the *from*
     counter only (F2).
   - Write order (MC-1, re-check): (1) own columns — `state` (or `is_deleted/deleted_at/deleted_by_id`
     for DELETE), `updated_by_id/updated_at` per MC-17 (creation: nothing; DELETE: `deleted_*` only;
     otherwise `updated_by_id = actor_user_id or None`, `updated_at = now`); `await session.flush()`.
     (2) the guarded counter statement: `UPDATE stock_report_items SET quantity_in_queue =
     quantity_in_queue + :dq, … WHERE client_id = :id AND quantity_in_queue + :dq >= 0 AND … RETURNING
     <six event fields>` with deltas from §5 rule 5 — **WHERE has no other predicate**. (3) On zero
     rows: fresh `SELECT` of the three counters (`stored_before`), `recompute_row_counters`, one
     `UPDATE … SET <all three absolute> … RETURNING <six fields>` (≠ 1 row → `RuntimeError`), one
     repair record per column with `stored_before + delta ≠ recomputed` (`target_kind
     stock_report_item`, `trigger = "inline:" + trigger`, `created_by_id NULL`), one warning per record
     carrying the delta. (4) *(phase 5 inserts the goal step here.)* (5) Build and return
     `[build_stock_task_assignment_event(kind, ...), build_stock_report_item_updated_event(values from
     RETURNING)]` where kind is `created` / `state-changed` / `deleted`. No commit, no dispatch, no
     `ctx`.
2. `_remove_assignment.py`: `remove_assignment(...)` = `move_assignment(..., ASSIGNMENT_DELETE, ...)`
   then `recompute_task_stock_flag(session, assignment.task_id)`; returns the move's events.
3. `_events.py`: the two builders (payload shapes of master plan §6.7).
4. Tests first from the table. Test files hold the locks the way callers will (row `FOR UPDATE`, then
   assignment `FOR UPDATE`, inside one transaction on `db_session`), call the operation, then read
   back with fresh `SELECT`s (never the stale ORM instance), and end every non-drift scenario with
   `assert_stock_report_clean`.

## 6. Criteria

Fixture: **F0** with row R at `quantity_requested 10`, **no goal record**, assignment A `q = 4` in the
stated state, counters pre-set to the consistent values for that state (e.g. A `in_queue` → R
`quantity_in_queue = 4`). `MV(from → to)` = call `move_assignment` for that pair. "counters" = the
triple `(in_queue, in_progress, awaiting)` read back by a fresh `SELECT`.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `MV(∅ → in_queue)` (`is_creation=True`, A inserted with `state in_queue`, counters 0) | counters `(4, 0, 0)`; events `[stock_task_assignment:created {state: in_queue}, stock_report_item:updated {…, quantity_in_queue: 4, …}]`; helper clean | delta sign flipped (`-q`) → guard trips → record → helper reddens | MC-1 |
| C1(b) | `MV(∅ → in_progress)` | `(0, 4, 0)`; `created`; clean | same | MC-1 |
| C1(c) | `MV(∅ → awaiting)` | `(0, 0, 4)`; `created`; clean | same | MC-1 |
| C1(d) | `MV(in_queue → in_progress)` | `(0, 4, 0)`; `state-changed {state: in_progress}` + `:updated`; clean | apply `+q` without `−q` → `(4, 4, 0)` | MC-1, M1 |
| C1(e) | `MV(in_queue → awaiting)` | `(0, 0, 4)`; clean | same | MC-1 |
| C1(f) | `MV(in_queue → failed)` | `(0, 0, 0)`, state `failed`; `state-changed {state: failed}` + `:updated`; clean | skip the `−q` for a terminal target | MC-1, §5 r5 |
| C1(g) | `MV(in_queue → DELETE)` | `(0, 0, 0)`; `is_deleted true`, `deleted_at == now`, `deleted_by_id == actor`; events `[deleted {state: in_queue}, :updated]`; clean | soft-delete after the counter statement (C5(c) bites too) | MC-1, MC-16 |
| C1(h) | `MV(in_progress → in_queue)` | `(4, 0, 0)`; clean | — (mirror of (d)) | MC-1 (§14C C6) |
| C1(i) | `MV(in_progress → awaiting)` | `(0, 0, 4)`; clean | — | MC-1 |
| C1(j) | `MV(in_progress → failed)` | `(0, 0, 0)`; clean | — | MC-1 |
| C1(k) | `MV(in_progress → DELETE)` | `(0, 0, 0)`; soft-deleted; clean | — | MC-1 |
| C1(l) | `MV(awaiting → in_queue)` | `(4, 0, 0)`; clean | — | MC-1 |
| C1(m) | `MV(awaiting → in_progress)` | `(0, 4, 0)`; clean | — | MC-1 (reopen) |
| C1(n) | `MV(awaiting → resolved)` with `actor_user_id=None` | `(0, 0, 0)`, state `resolved`; `updated_by_id NULL`, `updated_at == now`; events `[state-changed {state: resolved}, :updated]`; clean | keep `awaiting` count → `(0,0,4)` | MC-1 (Scanner only), MC-17 |
| C1(o) | `MV(awaiting → failed)` | `(0, 0, 0)`; clean | — | MC-1 |
| C1(p) | `MV(awaiting → DELETE)` | `(0, 0, 0)`; soft-deleted; clean | — | MC-1 |
| C1(q) | A `resolved`, counters `(0,0,0)`; `MV(resolved → DELETE)` | counters unchanged; soft-deleted; events `[deleted {state: resolved}]` **only** — no `:updated` | emit `:updated` anyway | MC-1, MC-19 ("terminal delete moves no counter") |
| C1(r) | A `failed`; `MV(failed → DELETE)` | as (q) with `state: failed` | same | MC-1 |
| C1(s) | A `in_queue`, counters `(4, 0, 0)`; `MV(in_queue → resolved_early)` with `actor_user_id=None`, `trigger="items_processed"` | counters `(0, 0, 0)`; state `resolved_early`; `updated_by_id IS NULL`, `updated_at == now`; events `[state-changed {state: resolved_early}, :updated {…, quantity_in_queue: 0, …}]`; clean | keep the `in_queue` count (treat the target as `=`) → `(4, 0, 0)` | §14F F2, MC-1 (Scanner only), MC-17 ("Scanner resolves") |
| C1(t) | A `in_progress`, counters `(0, 4, 0)`; `MV(in_progress → resolved_early)` with `actor_user_id=None` | `(0, 0, 0)`; state `resolved_early`; `updated_by_id IS NULL`; events `[state-changed {state: resolved_early}, :updated]`; clean | add `+q` to `quantity_awaiting` (treat it as `awaiting`) → `(0, 0, 4)` | §14F F2, MC-1 |
| C1(u) | A `resolved_early`, counters `(0,0,0)`; `MV(resolved_early → DELETE)` with actor U | counters unchanged; soft-deleted (`deleted_by_id == U`); events `[deleted {state: resolved_early}]` **only** — no `:updated` | emit `:updated` anyway / subtract `q` | §14F F2 ("`resolved_early → DELETE` … like `resolved`"), MC-19 |
| C2(a)–C2(f) | `MV(s → s)` for each of the six states | returns `[]`; `count_writes` over the four MC-9 tables `== 0`; no stamp change | write equal values | MC-1 `=` cells, MC-9 |
| C3(a) | `MV(∅ → resolved)` | raises `IllegalAssignmentMove`; nothing written | allow it | MC-1 ✗ |
| C3(b) | `MV(∅ → failed)` | raises | — | MC-1 ✗ (§5 r3) |
| C3(c) | `MV(∅ → DELETE)` | raises | — | MC-1 ✗ |
| C3(d) | `MV(in_queue → resolved)` | raises | allow it | MC-1 ✗ — the Scanner exit from `in_queue` is `resolved_early`, never `resolved` (§14F F2) |
| C3(e) | `MV(in_progress → resolved)` | raises | — | MC-1 ✗ (§14F F2) |
| C3(f)–C3(i) | `MV(resolved → in_queue / in_progress / awaiting / failed)` | raises, nothing written | allow → terminal revived | MC-1 `—` cells, §5 r1 |
| C3(j)–C3(m) | `MV(failed → in_queue / in_progress / awaiting / resolved)` | raises | same | MC-1, §5 r1 |
| C3(n) | `MV(∅ → resolved_early)` | raises; nothing written | allow it | MC-1 ✗, §14F F2 (entered only from an active state) |
| C3(o) | `MV(awaiting → resolved_early)` | raises; nothing written | allow it (map every active state to `resolved_early`) | §14F F2 ("`awaiting → resolved_early` never happens") |
| C3(p)–C3(t) | `MV(resolved_early → in_queue / in_progress / awaiting / resolved / failed)` | raises, nothing written | allow → terminal revived | §14F F1 (terminal: "nothing moves an assignment out of it except deletion"), §5 r1 |
| C3(u)–C3(v) | `MV(resolved → resolved_early)` and `MV(failed → resolved_early)` | raises | — | MC-1 `—` cells (terminal to terminal) |
| C4(a) | A `q = 8` `in_queue`; `MV(in_queue → in_progress)` | `(0, 8, 0)` (units, not 1) | use `1` instead of `quantity` | HC-2a, M1 |
| C4(b) | Two assignments on R: A `q = 3` `in_queue`, B `q = 5` `in_queue` (different items/tasks), counters `(8,0,0)`; move A | `(5, 3, 0)` | — | M1 |
| C4(c) | Load R into the session; raw `UPDATE stock_report_items SET quantity_requested = 99` in the same transaction; then `MV(in_queue → in_progress)` | the `:updated` payload has `quantity_requested: 99` (from `RETURNING`) | build the payload from the ORM instance → `10` | MC-1 "RETURNING is the only source", MC-19 |
| C5(a) | A `q = 4` `in_queue`; raw `quantity_in_queue = 0`; `MV(in_queue → in_progress)` with `trigger="task_sync"` | move succeeds; counters `(0, 4, 0)`; exactly one repair record `{stock_report_item, R, quantity_in_queue, stored "0", recomputed "0", trigger "inline:task_sync", created_by NULL}`; none for the other two columns; one warning whose message contains the delta `-4`; check `[]` | drop the `>= 0` guard from the WHERE → DB check aborts (`IntegrityError`) → red | MC-1 instrument (a), M1 |
| C5(b) | A `in_queue`; raw `quantity_in_queue = 5` (upward drift); `MV(in_queue → in_progress)` | succeeds; counters `(1, 4, 0)`; **zero** repair records; check reports one `counter_in_queue` (stored 1, expected 0); `repair_stock_report` then clears it | fire inline repair on any mismatch → a record appears | §12A (c): inline fires only downward |
| C5(c) | A `q = 4` `in_queue`; raw `quantity_in_queue = 0`; `remove_assignment(...)` | `quantity_in_queue` 0; one record (`stored "0"`, `recomputed "0"`, `inline:<trigger>`); check `[]` | issue the soft-delete after the counter statement → recomputation still counts A → `quantity_in_queue` 4 → check reports it | MC-1 instrument (b) |
| C6(a) | T with A only; `remove_assignment` | `tasks.is_stock_assignment` false | skip the recompute | MC-15 (ii) |
| C6(b) | T with A (`in_queue`) and B (`resolved`, another item — inserted directly, legal since terminal); remove A | flag stays true | recompute with `state IN active` → false | MC-15 truth (P21) |
| C6(c) | (a) again, recording `tasks.updated_at`, `updated_by_id` before | both byte-identical after | write the flag via the ORM attribute (`_task_flag.py`, already guarded in phase 3 — re-run here at the call site) | MC-15 |
| C7(a) | `MV(in_queue → in_progress)` with `actor_user_id = U`, `now = t0` | A `updated_by_id == U`, `updated_at == t0` | leave stamps to `onupdate` (none exists) → NULL | MC-17 |
| C7(b) | `MV(awaiting → resolved)` with `actor_user_id = None` | `updated_by_id IS NULL`, `updated_at == t0` | stamp a fake system user | MC-17 (null = Scanner) |
| C7(c) | A with prior `updated_by_id = X`; `MV(in_queue → DELETE)` with actor U | `deleted_by_id == U`, `deleted_at == t0`, `updated_by_id` still `X` | stamp `updated_*` on delete | MC-17 (U12) |
| C7(d) | any move | R's `updated_at`/`updated_by_id` unchanged | stamp the row on a counter move | MC-17 "any counter move: unchanged" |

**Required ledger row (charter rule 15, §12A (e)):** plant `from`'s delta as `−2q` in
`_move_assignment.py` (definition site). Expected: every C1 ✓ row from a counted state still
passes the counter and check assertions (self-heal) and **reddens only on the repair-record half of
`assert_stock_report_clean`**. The round records which rows reddened.

## 7. Notes

- Sizing: 62 criterion rows in 7 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- C1(h)–(p) mirror rows carry `—` because C1(d)–(g)'s mutations apply to the same statement; rule 2
  still wants each cell as its own row (the table is total).
- Round 9 (2026-09-19): the table in task 1 replaces MC-1's five-state table (§14C C47); C1(s)–(u),
  C2(f), C3(n)–(v) added so the table stays total over six states. A move into `resolved_early`
  differs from a move into `resolved` only in its *from* state; the counter statement is the same
  builder with a different delta vector.
- MC-11 (two writers) is **not** here — it needs the Scanner resolve and the sync (phase 10).
- Instrument (c) (fresh `stored_before` under the row-deletion cascade) is phase 13's.
- The operation never reads `ctx`, never commits, never dispatches; the test transaction owns the
  locks and rolls back or purges.

## 8. Review log

(empty)
