# Plan 5 — Goal credit: the MC-5 total event table, goal self-heal, the worked sequence

```
state: NOT_STARTED
phase: 5 of 15
depends_on: 4 (APPROVED)
projection: mandatory (money-like running total, guarded subtraction, credit memory)
complex: no
```

## 1. Goal

Add the goal-record step to `move_assignment`: credit the current goal record when an assignment
enters `awaiting` **or `resolved_early`** (§14F F4, card 14 → A), remember it, subtract from the
remembered record when completed work is undone, keep the credit on Scanner's resolve and on every
exit from a terminal state, self-heal a total that would go negative. **Not in this phase:**
goal-record *creation* rules (the demand webhook, phase 6 — records here are inserted as ORM
instances), priority/order records (phase 12), any command.

## 2. Read first

1. `master_plan.md` §6.5 (`_goal_credit.py`), §9 rules 2–3, 16.
2. Intention §6.1–§6.2, §6A MC-5 in full (the total event table, floor replaced by self-heal, what
   protects R, recomputation incl. deleted, the worked sequence), **§14F F4 and F11** (the two rows
   MC-5 gains, and `resolved_early → DELETE` behaving as `resolved → DELETE`), §12A (record fields
   for `history_record`), §14C C10, C17, C40, §14D D1, §17 "Closed (round 9)" card 14.
3. Plan 4 as shipped (`_move_assignment.py` write order; the goal step goes between the counter
   statement and the event build) and its Review log.

## 3. Dependencies

Phase 4 APPROVED.

## 4. Files expected to change

New: `bm/services/commands/stock_report/_goal_credit.py`,
`app/tests/integration/services/commands/stock_report/test_goal_credit.py`.
Edited: `bm/services/commands/stock_report/_move_assignment.py` (one call inserted after the
counter statement, before the events).

## 5. Tasks

1. `_goal_credit.py`: `current_goal_record_id(session, row_id)` = the non-deleted
   `quantity_requested_change` record with the greatest `(created_at, client_id)`, read under the
   row lock the caller holds; `apply_goal_effect(session, assignment, *, from_state, to_state,
   trigger, now)` implementing MC-5's table exactly: enter `awaiting` (from `∅`, `in_queue`,
   `in_progress`) → if a current goal G exists, `UPDATE … SET quantity_awaiting = quantity_awaiting +
   :q WHERE client_id = :g` and set `assignment.credited_history_record_id = G` (flushed as part of
   the own-columns write — so the memory write happens in step (1) of the write order and the
   `UPDATE` in this step); **enter `resolved_early` (from `in_queue` or `in_progress`) → exactly the
   same as entering `awaiting`: credit `G` if it exists and remember it, else nothing** (§14F F4;
   the memory is by construction NULL before, because those two states never hold a credit);
   `awaiting → resolved` → nothing; `awaiting → in_queue/in_progress/failed/DELETE`
   with memory R → clear the memory first (own-columns write, flushed), then the guarded `UPDATE …
   SET quantity_awaiting = quantity_awaiting − :q WHERE client_id = :r AND quantity_awaiting − :q >= 0`;
   zero rows → fresh `SELECT` of `stored_before`, `recompute_goal_total(R)` (deleted included), `UPDATE
   … SET quantity_awaiting = :recomputed`, one repair record (`history_record`, R, `quantity_awaiting`,
   `stored_before`, recomputed, `inline:<trigger>`, NULL author) + warning with delta; memory NULL →
   nothing; `resolved → DELETE` **and `resolved_early → DELETE`** → nothing, memory kept (F4: the
   credit is "never removed"; F11: the goal total sums every credited assignment, `resolved_early`
   included). The "terminal" test in this function reads `TERMINAL_ASSIGNMENT_STATES` (rule 16).
2. Wire it into `move_assignment` after the counter statement. Creation (`∅ → awaiting`) passes
   `from_state = None`.
3. Tests first from the table.

## 6. Criteria

Fixture: **F0** with goal record **G** (type `quantity_requested_change`, `quantity_requested 10`,
`quantity_awaiting 0`, `created_by NULL`) inserted as an ORM instance with an **explicit**
`created_at`; where a second goal **G2** is named it is inserted with an **explicit, strictly
greater** `created_at` (the current-goal rule orders by `(created_at, client_id)` and ULID
client_ids do not order reliably inside one millisecond). R's three counters are pre-set to the
values consistent with A's stated state, and `tasks.is_stock_assignment` follows plan 4's rule:
seeded **`true`** wherever A ends non-deleted, left **`false`** for the rows that end with A
soft-deleted — C1(i), C1(l), C1(q), C2(c), and step (6) of C3(a). Every row ends with
`assert_stock_report_clean` unless it plants drift. `mem(A)` = `credited_history_record_id`.

> **Fold note (orchestrator, 2026-09-21, batch B projection F5-1 — lessons L-17/L-16/L-14).** The
> `created_at` and task-flag sentences are fixture-cell amendments; no outcome cell changed. Without
> the task-flag rule every "clean" row fails against the shipped check (plan 4's fold note has the
> measurement). Without explicit `created_at` values the current-goal tiebreak is non-deterministic,
> which silently disarms C1(j) and C3(a).

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | `MV(∅ → awaiting)`, A `q = 4` | `G.quantity_awaiting == 4`; `mem(A) == G` | skip credit on creation | MC-5 row 1 |
| C1(b) | `MV(in_queue → awaiting)` | `G == 4`; `mem == G` | credit `1` instead of `q` | MC-5 row 1, HC-2a |
| C1(c) | `MV(in_progress → awaiting)` | `G == 4`; `mem == G` | — (mirror of (b): the same credit statement with a different *from* state; declared as a mirror so the ledger's `declared` count is honest) | MC-5 row 1 |
| C1(d) | no goal record; `MV(in_queue → awaiting)` | no history write (`count_writes` on `stock_report_history_records == 0`); `mem IS NULL` | create a goal record on the fly | MC-5 row 2 |
| C1(e) | A `awaiting`, `mem = G`, `G = 4`; `MV(awaiting → resolved)` | `G == 4`; `mem == G` (kept) | subtract on resolve | MC-5 row 3, M5 |
| C1(f) | A `awaiting`, `mem = G`, `G = 4`; `MV(awaiting → in_queue)` | `G == 0`; `mem IS NULL` | keep the memory | MC-5 row 4 |
| C1(g) | same; `MV(awaiting → in_progress)` | `G == 0`; `mem IS NULL` | — (mirror of (f): the same guarded subtraction and memory clear; declared as a mirror) | MC-5 row 4 |
| C1(h) | same; `MV(awaiting → failed)` | `G == 0`; `mem IS NULL` | — (mirror of (f): the same guarded subtraction and memory clear; declared as a mirror) | MC-5 row 4 |
| C1(i) | same; `MV(awaiting → DELETE)` | `G == 0`; `mem IS NULL`; A soft-deleted | — (mirror of (f): the same guarded subtraction and memory clear; declared as a mirror) | MC-5 row 5 |
| C1(j) | A `awaiting` `mem = G` (`G = 4`), G inserted with an explicit `created_at = t0`; then G2 inserted with an explicit `created_at = t0 + 1 s` (awaiting 0) so `current_goal_record_id` is unambiguously G2 regardless of ULID ordering; `MV(awaiting → in_progress)` | `G == 0`, `G2 == 0` (subtraction lands on the credited record, not the current one) | subtract from `current_goal_record_id` → `G2 = −4` guard trips / wrong record | MC-5 row 4 "even if R is no longer current", M5 |
| C1(k) | A `awaiting` with `mem IS NULL` (entered before any goal); G inserted afterwards; `MV(awaiting → in_queue)` | `G == 0`; no history write | subtract from current anyway | MC-5 row 6 |
| C1(l) | A `resolved`, `mem = G` (`G = 4`); `MV(resolved → DELETE)` | `G == 4`; `mem == G` | clear on delete | MC-5 row 7 |
| C1(m) | A `in_queue`, `mem IS NULL`; `MV(in_queue → failed)` | no history write; `mem IS NULL` | credit on entering **any** terminal state (extend the credit test from `{awaiting, resolved_early}` to `TERMINAL_ASSIGNMENT_STATES ∪ {awaiting}`), `_goal_credit.py` (definition site) → `G` is credited 4 and a history write appears → red | MC-5 row 8 |
| C1(n) | A `in_queue` `q = 4`, `mem IS NULL`; `MV(in_queue → resolved_early)` (actor None) | `G.quantity_awaiting == 4`; `mem(A) == G` | treat `resolved_early` like `failed` (terminal, no credit) → `G == 0` | §14F F4 (card 14 → A), MC-5 new row 1, M5 |
| C1(o) | A `in_progress` `q = 4`; `MV(in_progress → resolved_early)` | `G == 4`; `mem == G` | credit `1` instead of `q` | §14F F4, HC-2a |
| C1(p) | no goal record; `MV(in_queue → resolved_early)` | no history write (`count_writes` on `stock_report_history_records == 0`); `mem IS NULL` | create a goal record on the fly | §14F F4, MC-5 new row 2 |
| C1(q) | A `resolved_early`, `mem = G` (`G = 4`); `MV(resolved_early → DELETE)` | `G == 4`; `mem == G` (kept) | subtract on delete (treat it as `awaiting → DELETE`) → `G == 0` | §14F F4 ("never removed"), MC-5 row 7 by analogy |
| C2(a) | A `awaiting` `q = 4` `mem = G`; raw `UPDATE … SET quantity_awaiting = 1 WHERE client_id = G`; `MV(awaiting → in_progress)` with `trigger="task_sync"` | move succeeds; `G == 0` (recomputed: memory cleared and flushed before the Σ); one repair record `{history_record, G, quantity_awaiting, stored "1", recomputed "0", inline:task_sync, created_by NULL}`; warning with delta `-4`; check `[]` (the M1 check's `goal_total` kind is now consistent) | drop the guard → `ck_stock_report_history_records_quantity_awaiting_nonneg` aborts → red | MC-5 self-heal, §12A |
| C2(b) | A1 inserted `resolved` with `mem = G`, `q = 2`, then soft-deleted **by direct column write** (`is_deleted = true`, `deleted_at` set, `credited_history_record_id` left at G — there is no delete command in this phase); A2 then created `awaiting`, `mem = G`, `q = 3` on the same (I, T) (legal: A1 is neither active nor live); raw `UPDATE stock_report_history_records SET quantity_awaiting = 0 WHERE client_id = :g` (truth 5); `MV(A2: awaiting → in_queue)` | `G == 2` (A1's deleted resolved credit counted); record stored `"0"` recomputed `"2"` | exclude deleted assignments from the Σ → recomputed `0` → red | MC-5 recomputation (C17, MC-16 row) |
| C2(c) | A `awaiting` `mem = G` (`G = 4`); raw `G = 5` (upward); `MV(awaiting → resolved)` then `MV(resolved → DELETE)` | no repair record from either move; check reports one `goal_total` (stored 5, expected 4); `repair_stock_report` clears it with one `manual` record | run the self-heal block unconditionally instead of only on a 0-row result: in `_goal_credit.py` (definition site), after the guarded subtraction returns **1** row, compare `G`'s value against `recompute_goal_total(session, G)` and write a record + absolute UPDATE on any difference → a record appears on the first move and "no repair record from either move" reddens | §12A (c) for goal totals |
| C2(d) | In this order on the kit's (I, T): A1 `in_queue` `q = 2` → `MV(in_queue → resolved_early)` (G becomes 2, `mem(A1) = G`; A1 is now terminal so the active-state unique indexes free the pair); then A2 created `awaiting` `q = 3` with `mem = G` (G becomes 5); then raw `UPDATE stock_report_history_records SET quantity_awaiting = 0 WHERE client_id = :g` (truth 5); then `MV(A2: awaiting → in_queue)` | `G == 2` (A1's `resolved_early` credit counted by the recomputation); record stored `"0"` recomputed `"2"` | Σ filtered to `state IN (awaiting, resolved)` → recomputed `0` → red | §14F F11 (recomputation includes `resolved_early`), MC-5 recomputation |
| C3(a) | The worked sequence, exact: row at 10 with G1 (0) inserted at an explicit `created_at = t0`; steps (1) A `q = 4` `∅ → awaiting`; (2) G2 inserted with an explicit `created_at = t0 + 1 s` (0); (3) `MV(awaiting → in_progress)`; (4) `MV(in_progress → awaiting)`; (5) `MV(awaiting → resolved)` with actor None; (6) `remove_assignment` | after (1) `G1 == 4`, `mem == G1`; after (3) `G1 == 0`, `mem IS NULL`; after (4) `G2 == 4`, `mem == G2`, `G1 == 0`; after (5) `G2 == 4`, `mem == G2`; after (6) counters `(0,0,0)`, `G2 == 4`, A soft-deleted; `recompute_goal_total(G1) == 0`, `recompute_goal_total(G2) == 4`; check `[]`; zero repair records | any of C1's mutations | MC-5 worked sequence, M5 |

## 7. Notes

- Sizing: 22 criterion rows in 3 criteria; `complex: no` — arithmetic and one
  guarded statement, no concurrency or set-based SQL. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- Round 9 (2026-09-19): C1(n)–(q) and C2(d) added for the two MC-5 rows §14F F4 introduces. The
  credit on entering `resolved_early` is the same statement as the credit on entering `awaiting`;
  only the state test that selects it changes. In a phase-5 fixture `resolved_early` is reached
  with `MV(in_queue → resolved_early)` (phase 4's operation); the processed webhook that performs it
  in production is phase 9.
- Goal-record *creation* by demand and the `0→5, 5→5, 5→3, 3→4` sequence are phase 6 (MC-6).
- The credit memory is written in the own-columns step and flushed **before** any statement on R
  (MC-5 order), so the recomputation in C2(a) excludes the moving assignment — that is why
  `recomputed` is `0` there.

## 8. Review log

(empty)
