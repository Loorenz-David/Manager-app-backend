# Plan 10 — Task-state sync at S1–S9, the registry guard, two writers on one assignment

```
state: NOT_STARTED
phase: 10 of 15
depends_on: 9 (APPROVED)
projection: mandatory (nine-site sweep; the guard must be shown to fail; two-session rows)
complex: yes — nine existing commands edited, an AST guard with six planted probes, MC-11
```

## 1. Goal

Every committed change of `Task.state`, from every registered site, is reflected on the task's
active assignment in the same transaction through `sync_task_stock_assignments`; a terminal
assignment — `resolved`, `failed`, and since round 9 `resolved_early` — is never moved by the sync
whatever the task does; a checked-in registry plus an AST test refuses any unregistered writer;
the three two-writer interleavings of MC-11 (as amended by §14F F6) end as the contract says.
**Not in this phase:** the removal hooks and category guards (11).

## 2. Read first

1. `master_plan.md` §6.5 (`sync_task_stock_assignments.py`), §6.8 (registry location), §9 rules 4, 6, 8–9, 16;
   §10 hazard (b).
2. Intention §2.3 (the write-site table — and §14C C5–C8 for what it gets wrong), §5 (rules 1–5), §5A
   MC-1 lock order step 3 ("the task command's own UPDATE … flushed before step 4"), MC-11 in full
   **with its "Task reopen first" row replaced by §14F F6** (§14C C49) and the new "Scanner first
   while `in_progress`" row, §5B MC-2 in full (signature, steps 1–6, why command level, the audit,
   the site table S1–S9, the no-sync registrations, the guard with probes P-a…P-f), MC-17 (task-sync
   row: performer, not credited user), MC-19 (task-sync row; hand-up), §12A (`inline:task_sync`),
   §13 M2 (the round-9 sentence), **§14F F3, F5, F6**, §14C C9, C28, U1–U2, U13.
3. Inventory handoff §5 (write-site audit: terms, scope, counts — the guard's search space).
4. The nine command files (relational reads; line numbers verified 2026-09-19):
   `bm/services/commands/task_steps/transition_step_state.py` (S1: `old_task_state` at `:177`, block
   `maybe_begin` at `:139`, events at `:537-558`); `transition_step_state_batch.py` (S2:
   `old_task_states` `:162`, `changed_tasks` `:236`); `tasks/force_task_ready.py` (S3: `original_state`
   `:111`); `tasks/resolve_task.py` (S4: `:54-56`), `fail_task.py` (S5: `:54-56`), `cancel_task.py`
   (S6: `:54-56`); `task_steps/add_task_steps.py` (S7: `old_task_state` `:91`, write `:158`, events
   `:266-311`); `task_steps/remove_task_step.py` (S8: `_remove_task_steps_in_session` `:82-238`,
   write `:225`, dispatcher `:241-295`); `bm/services/tasks/task_steps/finalize_pending_step_completion.py`
   (S9: `:51-55`, `:93`, `:254-264`); `tasks/_task_state_transitions.py` (the three helpers);
   `_step_transition_core.py:77`. Also the three paused drivers named in MC-2.
5. `app/tests/integration/services/tasks/task_steps/test_finalize_pending_step_completion_integration.py`
   (how the dormant handler is driven), one existing `transition_step_state` integration test for
   the step/worker fixture shape.

## 3. Dependencies

Phase 9 APPROVED (MC-11 needs the processed webhook; assignments from phase 8).

## 4. Files expected to change

New: `bm/services/commands/stock_report/sync_task_stock_assignments.py`;
`app/tests/unit/services/commands/stock_report/task_state_write_site_registry.py`,
`test_task_state_write_sites_are_registered.py`;
`app/tests/integration/services/commands/stock_report/test_task_state_sync.py`,
`test_two_writers_on_one_assignment.py`.
Edited (one call each, after the command's last write to `Task.state`, inside its transaction):
the nine files listed in §2 item 4.

## 5. Tasks

1. `sync_task_stock_assignments(session, changed, *, workspace_id, actor_user_id, now)` per MC-2:
   `await session.flush()` first; per task ascending `client_id`: fresh query for the non-deleted
   active assignment of `task_id` (`scalar_one_or_none`) — none → skip; `target =
   ASSIGNMENT_STATE_BY_TASK_STATE[task.state]`; `lock_stock_report_items([row])`, then
   `lock_stock_task_assignments([a])`, re-read; `state in TERMINAL_ASSIGNMENT_STATES` (never a
   spelled list — rule 16) or deleted → skip; `state == target` → skip;
   else `move_assignment(..., trigger="task_sync", actor_user_id=actor_user_id, now=now)`; return
   `coalesce_stock_report_events(events, initial_row_values=<from the row lock>)`.
2. Wire the nine sites. Each passes only tasks whose state differs from the captured one
   (`old_task_state` / `old_task_states` / `original_state`), `actor_user_id = ctx.user_id` (S9:
   `payload["performed_by_user_id"]`), `now` = the command's own `now`/`ctx.now`, and appends the
   returned events to the command's pending list (S8: into the tuple its dispatcher consumes). The
   call sits after the command's **last** `Task.state` write and before the block exits.
3. Registry + guard (`test_task_state_write_sites_are_registered`): AST over `app/beyo_manager/**/*.py`
   and `app/scripts/**/*.py` (excluding `app/tests/**`, `app/migrations/**`) collecting the five site
   classes of MC-2; the registry classifies every site as `task_write → S<n>` / `no_sync: <reason>` /
   `paused_driver` / `not_task: <model>`; the test fails on an unregistered site, a stale entry, a
   `task_write` whose named sync function lacks a call to `sync_task_stock_assignments`, and a
   `paused_driver` whose `new_state=` is not literally `TaskStepStateEnum.PAUSED`. The guard's own
   collector is proven able to observe a hit by the six probes in C4.
4. Tests first from the table.

## 6. Criteria

Fixture: **F0** plus a worker user **Wk** with a step on T where a row needs one; A created through
`CR` (state follows T's state at creation). `MAP` = `ASSIGNMENT_STATE_BY_TASK_STATE`. Each C1 row
asserts, after the command commits: A's state `== MAP[T.state as committed]`, the three counters,
and that the command's dispatched list contains the stock events (via `capture_dispatch` at that
command's import site). Every row ends with `assert_stock_report_clean`.

**C5's three orders are forced by a held lock, never by a barrier** (§9 rule 9). Precedent, shipped and APPROVED in batch B2: `app/tests/integration/services/commands/stock_report/test_apply_stock_demand.py:821-867`. Per row: a third **referee** session on `get_db_session()` takes `SELECT … FROM stock_report_items WHERE client_id = R FOR UPDATE` and sets `held`; the row's **first** session's command is started as a task and **observed to block** (`with pytest.raises(asyncio.TimeoutError): await asyncio.wait_for(asyncio.shield(task1), 0.5)`); only then is the **second** session's command started and likewise observed to block; the referee then commits and both tasks are awaited under `asyncio.wait_for(…, timeout=10)`. Postgres queues both waiters on the row's tuple lock in arrival order, so the first session acquires first. **Both observed blocks are assertions of the row, not setup:** they are what proves the order was forced *and* that each session finished its unlocked discovery read before the other committed — the overlap every C5 mutation needs. A barrier is **not** used: it releases both sides at once and expresses a race, not an order. Every session is released and the workspace purged in `finally`.

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | S1 `transition_step_state`: T `assigned`, A `in_queue`; step → `working` | T `working`; A `in_progress`; `(0, 4, 0)` | remove the sync call from `transition_step_state.py` (call site) | MC-2 S1, M2 |
| C1(b) | S1: last step → `completed` so T → `ready` | A `awaiting`; `(0, 0, 4)`; `G == 4` | `bm/domain/stock_report/state_map.py:9` (definition site) — set `TaskStateEnum.READY` to `StockTaskAssignmentStateEnum.IN_PROGRESS` → A `in_progress`, counters `(0, 4, 0)`, `G == 0`. **Not row-local and out of perimeter (§7):** it also reddens `app/tests/unit/domain/stock_report/test_state_map.py:27` (which parametrizes the whole map) and every shipped row creating an assignment on a `ready` task — record the observed-red set across the suite (§9 rule 8) | MC-2 S1, HC-4 |
| C1(c) | S2 `transition_step_state_batch`: two tasks on R, both advance to `working` | both assignments `in_progress`; `(0, 8, 0)`; exactly one `:updated` for R | one sync call per task → two `:updated` | MC-2 S2, MC-19 |
| C1(d) | S3 `force_task_ready`: T `pending`, A `in_queue` | A `awaiting` (in_queue → awaiting, the MC-1 cell) | `bm/services/commands/tasks/force_task_ready.py` (call site) — delete the `sync_task_stock_assignments(...)` call → A stays `in_queue` instead of moving to `awaiting`. **Double kill:** also reddens `test_task_state_write_sites_are_registered` (a registered `task_write` whose sync function has no call) — both observed reds recorded (§9 rule 8, L-28) | MC-2 S3 |
| C1(e) | S4 `resolve_task` from `working` (A `in_progress`) | A `awaiting`; `(0, 0, 4)` | remove the call (P-e's mutation, also C4(f)) | MC-2 S4 |
| C1(f) | S4 `resolve_task` from `ready` (A `awaiting`) | A stays `awaiting`; no stock event (`=` cell) | emit anyway | MC-2 step 5, MC-19 |
| C1(g) | S5 `fail_task` from `working` | A `failed`; `(0, 0, 0)` | `bm/services/commands/tasks/fail_task.py` (call site) — delete the sync call → A stays `in_progress` and counters stay `(0, 4, 0)` instead of A `failed` / `(0, 0, 0)`. Double kill with the registry guard as C1(d) | MC-2 S5, §5 |
| C1(h) | S6 `cancel_task` from `assigned` | A `failed` | `bm/services/commands/tasks/cancel_task.py` (call site) — delete the sync call → A stays `in_queue` instead of `failed`. Double kill with the registry guard as C1(d) | MC-2 S6 |
| C1(i) | S7 `add_task_steps` on T `pending` (A `in_queue`) | T `assigned`; A stays `in_queue`; no stock event | **Two sites, applied together** — `sync_task_stock_assignments.py` (definition site): remove the MC-2 step-5 `state == target → skip`; **and** `_move_assignment.py:195-200` (definition site): remove `move_assignment`'s own `assignment.state == target → return []`. **Either alone is EQUIVALENT** (the other absorbs the no-op). With both gone the net delta is zero so counters and `:updated` are unchanged, but a `stock_task_assignment:state-changed` event is emitted and the row's "no stock event" clause reddens. Same mutant as C1(f); show it reaches C1(i)'s own assertion (L-28). **`_move_assignment.py` is out of perimeter — see §7** | MC-2 S7 (`=` cell) |
| C1(j) | S7 `add_task_steps` on T `ready` (A `awaiting`, `G == 4`) → reopen | T `working`; A `in_progress`; `G == 0`; `mem IS NULL` | `bm/services/commands/task_steps/add_task_steps.py` (call site) — delete the sync call → A stays `awaiting`, `G` stays 4 and `mem` is unchanged, instead of A `in_progress` / `G == 0` / `mem IS NULL`. Double kill with the registry guard as C1(d) | MC-2 S7, MC-5 row 4 |
| C1(k) | S8 `remove_task_step`: T `working` with one step; remove it | T `pending`; A `in_queue`; `(4, 0, 0)` | `bm/services/commands/task_steps/remove_task_step.py` (call site) — delete the sync call **and** its event append → A stays `in_progress` and counters stay `(0, 4, 0)` instead of A `in_queue` / `(4, 0, 0)`. Double kill with the registry guard as C1(d) | MC-2 S8 (§14C C6) |
| C1(l) | S9 `handle_finalize_pending_step_completion(payload, T)` driven directly (fixture per the existing integration test): the pending completion makes T `ready` | A `awaiting`; `updated_by_id == payload["performed_by_user_id"]` | `bm/services/tasks/task_steps/finalize_pending_step_completion.py` (call site) — pass `actor_user_id=None` instead of `payload["performed_by_user_id"]` (`:34`). **`ctx.user_id` is not an available mutant here — this handler has no `ctx`** → `move_assignment` stamps `updated_by_id` NULL (`_move_assignment.py:213`) and the row's `updated_by_id == payload["performed_by_user_id"]` reddens | MC-2 S9 |
| C2(a) | S8 with T `ready` and two completed steps; `remove_task_step` on one → `pending` then `maybe_evaluate_task_ready` → `ready` inside one transaction | A stays `awaiting`; `G` unchanged; `mem` unchanged; **no** stock event | **UNFAILABLE BY DESIGN — owner ruling, 2026-09-21, card 2.** The named mutation ("sync inside the helpers, per intermediate write") cannot redden this row: with a step left over `remove_task_step` never dips to `pending` — it goes straight to the still-ready check, finds T already `ready` and writes no state at all (`remove_task_step.py:224-236`, `_task_state_transitions.py:90-91`), so the sync is never offered the task. **Owner: there is no task-state transition that varies within one transaction, so the hazard is not reachable.** The row is kept as a cheap regression guard; **its real evidence is the C4 registry guard**, which refuses a sync call inside the three helpers. The tester records this row `UNFORCEABLE` and does not try to make it bite (charter rule 15) | MC-2; C4 (the registry guard is this row's actual evidence); inventory §5 U1; owner card 2, 2026-09-21 |
| C3(a) | A `resolved` (via `PR`); then S7 reopen (`add_task_steps` on the resolved-then-… — use: T `ready` → resolve via Scanner → `add_task_steps` reopens T to `working`) | A stays `resolved`; counters unchanged; no stock event | move it | §5 r1, M2 |
| C3(b) | A `failed` (T failed); `remove_task_step` sets T `pending` (X1 path) | A stays `failed`; no stock event | `sync_task_stock_assignments.py` (definition site) — replace the MC-2 skip `state in TERMINAL_ASSIGNMENT_STATES` with a hand-typed `state == StockTaskAssignmentStateEnum.RESOLVED` (rule 16's literal; the frozenset in `enums.py` is not edited) → the `failed` assignment is no longer skipped and `move_assignment` **raises `IllegalAssignmentMove` (500)** at `_move_assignment.py:66-69` rather than moving it to `in_queue`. The row reddens on the raise, so its later clauses are not reached (rule 12) | §5 r1 (C6) |
| C3(c) | A `resolved_early` via `PR` while T `working` (A was `in_progress`; `G == 4`, `mem == G`); then S1 completes the last step so T → `ready` | T `ready`; A stays `resolved_early`; counters `(0, 0, 0)`; `G == 4`, `mem == G`; **no** stock event; clean | skip the terminal test → `MV(resolved_early → awaiting)` raises `IllegalAssignmentMove` (500) or, with plan 4 mutated too, re-credits `G` | §14F F3 ("the sync skips … no wait, no second resolution"), M2 round-9 sentence |
| C3(d) | as (c), then S5 `fail_task` | A stays `resolved_early`; `G == 4`; no stock event | `sync_task_stock_assignments.py` (definition site) — same skip hand-typed as `state in {RESOLVED, FAILED}` (rule 16's literal) → the `resolved_early` assignment is no longer skipped and `move_assignment` raises `IllegalAssignmentMove` (500) on `resolved_early → failed`. **One mutant shape across C3(c)–(f):** run it once per row and record that it reaches this row's own task exit (§9 rule 8, L-28) | §14F F3 ("if the task instead fails") |
| C3(e) | as (c), then S6 `cancel_task` | A stays `resolved_early`; no stock event | As C3(d) — the same hand-typed skip; here the task exit is S6 `cancel_task` and the refused move is `resolved_early → failed`. Own run recorded (L-28) | §14F F3 |
| C3(f) | as (c), then S8 `remove_task_step` removing the only step so T → `pending` | A stays `resolved_early`; `(0, 0, 0)`; no stock event | As C3(d) — the same hand-typed skip; here the task exit is S8 `remove_task_step` and the refused move is `resolved_early → in_queue`. Own run recorded (L-28) | §14F F3 ("or reopens"), M2 |
| C4(a) | the guard on the current tree | passes | — **deliberate blank (§3B class 2).** This is the guard's control row. Its arming is the probe set C4(b)–(h) — the six MC-2 probes plus the staleness row — which is charter rule 15's required positive observation for this instrument (L-26 is discharged here). A mutation of C4(a) itself could only edit the collector or the registry, i.e. test-side data | MC-2 guard |
| C4(b) | P-a: add `task.state = TaskStateEnum.STALLED` in `tasks/update_task.py:update_task` | guard fails naming the site | (this row **is** the probe) | MC-2, rule 15 |
| C4(c) | P-b: `setattr(task, "state", TaskStateEnum.READY)` in the same function | fails | probe | MC-2 |
| C4(d) | P-c: `await session.execute(update(Task).values(state=TaskStateEnum.READY))` there | fails | probe | MC-2 |
| C4(e) | P-d: a call to `maybe_evaluate_task_ready(...)` there | fails | probe | MC-2 |
| C4(f) | P-e: delete the `sync_task_stock_assignments` call from `tasks/resolve_task.py:resolve_task` (call site) | fails (registered `task_write` without the call) | probe | MC-2 |
| C4(g) | P-f: change `users/_clock_worker_shift.py:clock_out_shift_for_user`'s `new_state=` to `TaskStepStateEnum.COMPLETED` | fails (paused driver no longer paused) | probe | MC-2 |
| C4(h) | a registry entry naming a function that does not exist | fails (stale entry) | drop the staleness check | MC-2 "stale registry entry" |
| C5(a) | order forced by the §6 referee-lock choreography, session 1 started first; both blocks observed | A `resolved`; counters `(0, 0, 0)`; `G == 4`; `mem == G`; session 1's events `[state-changed resolved, :updated]`; session 2's stock events empty | `sync_task_stock_assignments.py` (definition site) — capture `pre = a.state` immediately after the unlocked discovery query and decide the terminal skip on `pre in TERMINAL_ASSIGNMENT_STATES` instead of on `a.state` → session 2 moves the `resolved` assignment. **There is no separate post-lock re-read statement to delete:** the re-read is `_locks.py:22-41`'s `populate_existing=True`, which refreshes the same identity-mapped instance in place; deleting it there would change every locking caller in the project | MC-11 row 1, M1, M2 |
| C5(b) | the mirror ordering, forced by the §6 referee-lock choreography with **session 2 started first**; both blocks observed — session 2 (`add_task_steps`, T `ready → working`) acquires the row lock first | A `resolved_early`; counters `(0, 0, 0)` (the reopen wrote `awaiting −4, in_progress +4`; Scanner then `in_progress −4`); `G == 4` and `mem == G` (the reopen cleared the first credit — `G` went to 0 — and entering `resolved_early` credited the current goal again, F4); session 2's events `[state-changed in_progress, :updated {…, quantity_in_progress: 4, …}]`; session 1's result `resolved/early` and events `[state-changed resolved_early, :updated {…, quantity_in_progress: 0, …}]`; T stays `working` | `process_items_processed.py` (definition site) — capture the assignment's state at the unlocked discovery step and run the §14F F5 ladder on that captured value instead of on the state after `lock_stock_task_assignments` → Scanner decides `awaiting → resolved` on an assignment the reopen has already moved to `in_progress`, and `_move_assignment.py:74-79` refuses it (`IllegalAssignmentMove`, 500). Same "no separate re-read" note as C5(a) | §14F F6 (replaces MC-11 row 2; §14C C49), M1, M2 |
| C5(c) | order forced by the §6 referee-lock choreography, session 1 started first; both blocks observed | A `resolved_early`; `(0, 0, 0)`; `G == 4`, `mem == G`; session 1's events `[state-changed resolved_early, :updated]`; session 2 commits T `ready` with **no** stock event; no assignment in an active state; `assert_stock_report_clean` | As C5(a) — `sync_task_stock_assignments.py` (definition site), decide the terminal skip on the value captured at discovery → session 2 moves the `resolved_early` assignment and `_move_assignment.py:66-69` refuses it (`IllegalAssignmentMove`, 500) | §14F F6 ("both orders end with no assignment in an active state and counters equal to the recomputation"), M1, M2 |
| C6(a) | S1 where a manager `M` performs the transition with `credited_user_id = Wk` | A `updated_by_id == M` (the performer), not `Wk` | use the credited user | MC-17 (C28, U13) |
| C6(b) | any synced move | A `updated_at ==` the command's `now` | use `datetime.now()` inside the sync | MC-17 |
| C7(a) | S4 `resolve_task` | the dispatched list contains the task's own events **and** the stock events, all after commit | dispatch inside the sync | MC-19 hand-up, 06_commands_local |
| C7(b) | `resolve_task` on a task already `resolved` (the command raises) | no stock event dispatched; A unchanged | **UNFAILABLE BY DESIGN — owner ruling, 2026-09-21, card 3.** No edit in this phase turns it red: `resolve_task` refuses on its first check (`resolve_task.py:51-52`) before writing anything and long before the sync would run, and even a mis-wired sync is covered twice over — the failed request rolls back, and events dispatch only after a clean commit. Kept as a cheap regression guard; the **label is the point**, so a future reviewer does not count it as evidence. Reviewer's structural check: confirm by reading that the sync call sits after the refusal | MC-19 "rolled-back request"; `resolve_task.py:51-52`; §9 rules 6 and 9; charter rule 15; owner card 3 |
| C7(c) | A `in_queue` via `CR`; raw `quantity_in_queue = 0`; S1 advance | one repair record with `trigger == "inline:task_sync"` | `sync_task_stock_assignments.py` (the `move_assignment` call site) — pass `trigger="task_sync_x"` → `_move_assignment.py:172` writes `inline:task_sync_x` and the row's `trigger == "inline:task_sync"` reddens | §12A trigger set |

## 7. Notes

- Sizing: 35 criterion rows in 7 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- C4(b)–(g) are the six required probes of MC-2: each is planted, observed red, reverted, and
  recorded with the observed failure message — they are rows, not prose.
- Round 9 (2026-09-19): C3(c)–(f) added (the sync never moves a `resolved_early` assignment, one
  row per task exit named by §14F F3); C5(b) rewritten to F6 (the "Task reopen first" order now ends
  in `resolved_early`, with the goal re-credited); C5(c) added (Scanner first while `in_progress`).
  The registry guard C4 is untouched by round 9.
- C5's ordering is forced by lock acquisition, not by sleeps — by a **third, referee session**
  holding the row lock, never by either participant (§6 preamble). Both participants run whole
  production commands that take and release their own locks inside `maybe_begin`, so neither can
  be made to hold one open for the other; **the earlier wording named a seam that does not
  exist** (batch C2 projection, 2026-09-21).
- **Perimeter extension (§9 rule 17 / L-25).** Four named mutations are applied outside §4's file
  list and are authorized here: `bm/domain/stock_report/state_map.py` (C1(b));
  `bm/services/commands/stock_report/_move_assignment.py` (C1(i)'s second site, and C3(c)'s "with
  plan 4 mutated too"); `bm/services/commands/tasks/update_task.py` (probes P-a…P-d, rows
  C4(b)–(e)); `bm/services/commands/users/_clock_worker_shift.py` (probe P-f, row C4(g)). Each is
  planted, observed and reverted inside the round; C1(b)'s observed-red set spans other phases'
  files and is recorded whole (§9 rule 8).
- Hazard (master plan §10 (b)): the flush + one query per command may shift an existing
  statement-count test if one wraps a sync site; none was found on 2026-09-19 — the reviewer
  re-checks the L4 delta against the baseline set.
- The registry lives in tests; it is data for the guard, not production code.

## 8. Review log

**Implementer, 2026-09-21 (batch C2, Sonnet).** Built: `sync_task_stock_assignments.py`
(MC-2's sync); the nine call sites (S1-S9), each after the command's last write to
`Task.state`, inside its own transaction, only when the task net-changed;
`task_state_write_site_registry.py` + `_task_state_write_scanner.py` (an AST
collector, not named in §4 but needed to make the registry checkable — see
judgment calls) + `test_task_state_write_sites_are_registered.py` (the C4 guard).

**The registry's full inventory (85 sites), derived, not typed.** The AST collector
found exactly 85 sites across `app/beyo_manager/**/*.py` and `app/scripts/**/*.py`
(excluding tests/migrations): 52 `.state=` assignments (8 on `Task`, 44 on other
models), 18 `setattr()` calls (2 on `Task`, 16 on other models), 1 `update(Task)`,
1 `Task(state=...)` constructor, 13 calls to the four named helpers/`_apply_step_transition`
(10 `task_write`, 3 `paused_driver`). Every `task_write` entry's `sync_functions`
was verified against the shipped code by a script before this file was written
(`function_contains_call` — see the guard's own test, `test_c4a_*`), and the guard
itself passes on the current tree (C4(a)). I do not treat this as evidence of
`executed == declared` for mutations — that ledger is the tester's (§3B).

**Judgment calls:**
- **The scanner module (`_task_state_write_scanner.py`) is an addition beyond §4's
  file list.** The guard's own logic (an AST sweep plus per-site verification) is
  substantial enough that folding it directly into the test file would make both
  hard to read; I split it out as test-support code (it matches no `test_*.py`
  pattern, so pytest never collects it as a test module — rule 19 is not implicated).
  It holds no criterion-bearing assertions itself.
- **`sync_functions` names the function that must call the sync, not necessarily
  the write's own enclosing function.** For the three helper-internal writes in
  `_task_state_transitions.py` (`maybe_advance_task_to_working`,
  `maybe_reopen_task_to_working`, `maybe_evaluate_task_ready`), and for the two
  internal calls to those helpers inside `_step_transition_core.py`'s shared core,
  I classified them `no_sync`/`task_write` pointing at their **real callers**
  (`transition_step_state`, `add_task_steps`, `force_task_ready`,
  `transition_step_state_batch`) rather than at the helper/core itself — adding
  the sync call inside the shared helper would violate §5B's own "why command
  level, not helper level" rule (it would fire on an intermediate state within one
  transaction). `function_contains_call` searches the whole scanned corpus for the
  named function, not just the site's own file, so a `sync_functions` entry may
  legitimately name a function defined elsewhere.
- **S8's `sync_functions` lists both `remove_task_step` and `remove_task_steps`.**
  Both public commands call the same `_remove_task_steps_in_session` helper, whose
  own two mutually-exclusive branches (`len(remaining_steps) == 0` vs.
  `maybe_evaluate_task_ready`) never both fire in one call — the C2(a) analysis the
  plan already gives — so the helper's return state is always settled by the time
  either caller's own sync call runs. Both callers carry the call.
- **S8's `now` is `ctx.now`, not the helper's internal `datetime.now(timezone.utc)`.**
  `_remove_task_steps_in_session` computes its own `now` locally and does not
  return it, so the call site (outside the helper) cannot reuse the exact same
  instant the task's own `updated_at` used. I used `ctx.now` — the same
  deterministic, test-controlled clock phase 9 used — rather than a second fresh
  `datetime.now()` call, so `assignment.updated_at` is exactly what a test
  constructing `ctx` with a fixed `now` can assert against. This means
  `task.updated_at` (real wall clock) and `assignment.updated_at` (`ctx.now`) are
  not bit-identical for this one site; every other site (S1, S3-S7, S9) passes the
  **same** locally-computed `now` its own `Task.state` write used, so this is the
  one site where the two timestamps can differ. Flagging for the tester's C6(b) row.
- **`resolve_processed_group`'s two event kinds (plan 9, revisited here for C8(c)).**
  Plan §6.5 and C8(c) both say `stock_task_assignment:updated`, a kind this project
  never registers (§6.7: only `:created`/`:state-changed`/`:deleted`). I built and
  tested `:state-changed`, matching every other state-transition event in the
  project. Repeated here because plan 10's own C5 rows describe the same sites'
  events the same way (e.g. C5(a): "session 1's events `[state-changed resolved,
  :updated]`") — internally consistent with what I built, so I read the C8(c)
  wording as informal rather than as a fourth event kind to add.

**Rows I know I did not build a dedicated test for** (see the implementer handoff
for the full per-row disposition): C1(b)/(c)/(e)/(f)/(h)/(i)/(j)/(k)/(l) — S2, S3,
S7 and S9 are proven only by the C4 guard (their sync call exists and is wired),
not by driving their own command end-to-end; the guard's six required probes
C4(b)-(h) (owned by the tester, §3B); C2(a) (owner ruling: `UNFORCEABLE BY DESIGN`,
its real evidence is C4); C3(a)/(b)/(d)/(e)/(f) (sibling terminal-skip cases of the
one I tested); C5(b)/(c) (the mirror order and the `in_progress` order — C5(a) is
built and passing, three consecutive runs, no flake observed); C7(a)/(b)/(c)
(dispatch-order and trigger rows).
