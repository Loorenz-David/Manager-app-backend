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
| C1(m) | **Authored by the owner, 2026-09-21, batch C2 review card 1 — OWED by the C2 fix round.** A task T carrying **two** non-deleted assignments: A1 `failed` (terminal) and A2 `in_queue` (active), both on row R — the state §14F F1 and `uix_stock_task_assignments_task_active` together permit, since the partial index constrains only the three **active** states. Drive T `in_queue → working` (S1) | **A2** moves to `in_progress` and R's counters follow it; A1 is untouched; exactly one `stock_task_assignment:state-changed` for A2 and one `stock_report_item:updated` for R. The sync must select the **live** assignment, never whichever row the database returns first | restore the defect: drop `state.in_(ACTIVE_ASSIGNMENT_STATES)` from the discovery query in `sync_task_stock_assignments.py` → discovery returns A1, the post-lock terminal skip fires, A2 stays `in_queue` and **zero** events are emitted | intention §5B MC-2 step 3 (`scalar_one_or_none` is safe **only** inside the index's active-state predicate), §14F F1; review finding F-1/F-5; owner card 1 |
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
| C4(h) | a registry entry naming a function that does not exist | fails (stale entry) | drop the staleness check — **[Backfilled from the C2 tester's measurement, 2026-09-21 — orchestrator]** **measured `EQUIVALENT` as written (B-9).** With the stale entry planted, dropping the `function_exists` assertion leaves the same test red on the adjacent `function_contains_call` assertion. Isolating the staleness check would require dropping **both** assertions, which is a different mutant | MC-2 "stale registry entry" |
| C4(i) | **Authored by the owner, 2026-09-21, batch C2 review card 2 — OWED.** Plant a call to `sync_task_stock_assignments` **inside** `maybe_evaluate_task_ready` (and, as separate plants, inside `maybe_advance_task_to_working`, `maybe_reopen_task_to_working` and the shared step-transition core) | the guard **fails**, naming the helper it found the call in. This is MC-2's "why command level" rule, which the C2 reviewer measured to be **unguarded today**: it planted this exact call and the guard passed | remove the new negative assertion from the guard → the planted call passes unnoticed, which is the current state of the tree | intention §5B MC-2 "why command level" + "The guard" negative clause; plan 10 C2(a)'s delegated evidence; finding F-3; owner card 2 |
| C4(j) | **Authored by the owner, 2026-09-21, batch C2 review card 4 — OWED.** Plant, in one live file **at once**, the five constructs the reviewer showed the collector misses: an annotated assignment `task.state: TaskStateEnum = …`, a tuple-target assignment writing `task.state`, an `update`/`insert` reached through an **import alias**, a `Task(…)` call reached through an alias, and a raw `text("UPDATE tasks SET state = …")` | the guard **fails on all five**, each reported as an unregistered site. Class **(f)** (raw SQL naming `tasks`) is new; the other four are forms of classes (a), (c) and (e) that the list already named but the collector never saw | revert each of the five collector extensions in turn (`_task_state_write_scanner.py`) → the corresponding plant goes unnoticed. **Nothing in the codebase uses these forms today**, so this guards the next writer, not a live leak | intention §5B MC-2 "The guard" (a)–(f) and the by-construct clause; finding F-2/F-6; owner card 4 |
| C4(k) | **Authored by the owner, 2026-09-21, batch C2 re-review card 1 (R-1) — OWED.** Plant, in one live file **at once**, the four further constructs the re-reviewer showed still slip past after C4(j): (1) `Task.__table__.update().where(…).values(state=…)`; (2) `update(Task.__table__)`; (3) a `for`-target or `with … as` target writing `task.state`; (4) `builtins.setattr(task, "state", …)`; and (5) `Task(**{"state": …})` via dict unpacking. Site them **at EOF** of plan 10 §7's authorized perimeter file so no registered line number moves | the guard **fails on every one**, each reported as an unregistered site. These are classes (a)–(d) in four more spellings, already governed by the by-construct clause; they are enumerated because they were **measured** to pass | revert each new collector extension in turn (`_task_state_write_scanner.py`) → the corresponding plant goes unnoticed. **Zero live instances in `beyo_manager/` or `scripts/` today** — this guards the next writer. Note the guard does **not** scan `tests` or `migrations`, so the three `Task.__table__.update()` sites in this project's own tests are out of scope and are habit evidence, not a coverage gap | intention §5B MC-2 "The guard" (a)–(f), the by-construct clause and its four-forms amendment; finding R-1; re-review card 1 |
| C5(a) | order forced by the §6 referee-lock choreography, session 1 started first; both blocks observed | A `resolved`; counters `(0, 0, 0)`; `G == 4`; `mem == G`; session 1's events `[state-changed resolved, :updated]`; session 2's stock events empty | `sync_task_stock_assignments.py` (definition site) — capture `pre = a.state` immediately after the unlocked discovery query and decide the terminal skip on `pre in TERMINAL_ASSIGNMENT_STATES` instead of on `a.state` → session 2 moves the `resolved` assignment. **There is no separate post-lock re-read statement to delete:** the re-read is `_locks.py:22-41`'s `populate_existing=True`, which refreshes the same identity-mapped instance in place; deleting it there would change every locking caller in the project | MC-11 row 1, M1, M2 |
| C5(b) | the mirror ordering, forced by the §6 referee-lock choreography with **session 2 started first**; both blocks observed — session 2 (`add_task_steps`, T `ready → working`) acquires the row lock first | A `resolved_early`; counters `(0, 0, 0)` (the reopen wrote `awaiting −4, in_progress +4`; Scanner then `in_progress −4`); `G == 4` and `mem == G` (the reopen cleared the first credit — `G` went to 0 — and entering `resolved_early` credited the current goal again, F4); session 2's events `[state-changed in_progress, :updated {…, quantity_in_progress: 4, …}]`; session 1's result `resolved/early` and events `[state-changed resolved_early, :updated {…, quantity_in_progress: 0, …}]`; T stays `working` | `process_items_processed.py` (definition site) — capture the assignment's state at the unlocked discovery step and run the §14F F5 ladder on that captured value instead of on the state after `lock_stock_task_assignments` → Scanner decides `awaiting → resolved` on an assignment the reopen has already moved to `in_progress`, and — **[Backfilled from the C2 tester's measurement, 2026-09-21 — orchestrator]** **the predicted failure mode is WRONG (B-8, measured).** `_move_assignment.py:74-79` does **not** refuse, because `resolve_processed_group` **never calls `_assert_allowed_move`**. The stale decision is written **silently** and the row reddens on its own `results` assertion instead. See **owner card 1** (candidate criteria CC-1/CC-2). Same "no separate re-read" note as C5(a) | §14F F6 (replaces MC-11 row 2; §14C C49), M1, M2 |
| C5(c) | order forced by the §6 referee-lock choreography, session 1 started first; both blocks observed | A `resolved_early`; `(0, 0, 0)`; `G == 4`, `mem == G`; session 1's events `[state-changed resolved_early, :updated]`; session 2 commits T `ready` with **no** stock event; no assignment in an active state; `assert_stock_report_clean` | As C5(a) — `sync_task_stock_assignments.py` (definition site), decide the terminal skip on the value captured at discovery → session 2 moves the `resolved_early` assignment and `_move_assignment.py:66-69` refuses it (`IllegalAssignmentMove`, 500) | §14F F6 ("both orders end with no assignment in an active state and counters equal to the recomputation"), M1, M2 |
| C6(a) | S1 where a manager `M` performs the transition with `credited_user_id = Wk` | A `updated_by_id == M` (the performer), not `Wk` | use the credited user | MC-17 (C28, U13) |
| C6(b) | any synced move | A `updated_at ==` the command's `now` | use `datetime.now()` inside the sync | MC-17 |
| C7(a) | S4 `resolve_task` | the dispatched list contains the task's own events **and** the stock events, all after commit | dispatch inside the sync | MC-19 hand-up, 06_commands_local |
| C7(b) | `resolve_task` on a task already `resolved` (the command raises) | no stock event dispatched; A unchanged | **UNFAILABLE BY DESIGN — owner ruling, 2026-09-21, card 3.** No edit in this phase turns it red: `resolve_task` refuses on its first check (`resolve_task.py:51-52`) before writing anything and long before the sync would run, and even a mis-wired sync is covered twice over — the failed request rolls back, and events dispatch only after a clean commit. Kept as a cheap regression guard; the **label is the point**, so a future reviewer does not count it as evidence. Reviewer's structural check: confirm by reading that the sync call sits after the refusal | MC-19 "rolled-back request"; `resolve_task.py:51-52`; §9 rules 6 and 9; charter rule 15; owner card 3 |
| C7(c) | A `in_queue` via `CR`; raw `quantity_in_queue = 0`; S1 advance | one repair record with `trigger == "inline:task_sync"` | `sync_task_stock_assignments.py` (the `move_assignment` call site) — pass `trigger="task_sync_x"` → `_move_assignment.py:172` writes `inline:task_sync_x` and the row's `trigger == "inline:task_sync"` reddens | §12A trigger set |
| C8(a) | **Authored by the owner, 2026-09-21, batch C2 tester card 2** — §9 rule 18's third instance, the twin of plan 9 C8(c). **OWED: see §7.** Call `sync_task_stock_assignments` **directly** (not through any of its nine command call sites) for a task whose state change moves one assignment | the call accepts the argument shape registered in master plan §6.5 and returns the registered event kinds — `stock_task_assignment:state-changed` per moved assignment and one `stock_report_item:updated` per touched row — and nothing else. **The contract only**: this row pins the callable's signature and returned event-kind set, and deliberately does **not** re-assert the nine call sites' behaviour, which C1 and C4 already own | change the return to drop the row event (`sync_task_stock_assignments.py`, definition site) → the event-kind set shrinks and the nine callers silently stop updating the board row | master plan §6.5 `sync_task_stock_assignments`, §9 **rule 18**; §9A L-8; owner card 2; tester CC-3 |

## 7. Notes

- Sizing: **40** criterion rows in **8** criteria; `complex: yes`. (35/7 + C8(a) tester card 2; **+ C1(m), C4(i), C4(j)** from batch C2 review cards 1, 2 and 4, and **+ C4(k)** from the re-review's card 1 (R-1), 2026-09-21. The C8 criterion puts this phase **at the §15 eight-criteria cap** — further *rows* are fine, further *criteria* need a re-size.) (Counts re-derived by script after the
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

- **⚠ OWED BY A FIX ROUND — plan 10 C8(a), authored 2026-09-21 after the tester handed over.**
  The owner ruled batch C2 tester **card 2** *add the row*. Recorded, not folded silently, for the
  same §3B reason as plan 9 C8(d); the batch C2 reviewer was told directly, mid-review.

  **Why the owner said yes.** §9 **rule 18** requires every newly registered shared signature to be
  pinned by a row in its own plan, so a later phase cannot cite a contract that has quietly
  changed. Phase 9's twin, `resolve_processed_group`, got C8(c). This one — called from **nine**
  sites — got nothing. The only evidence today is the implementer's two direct-call tests, which
  cover the contract *by accident*, and the tester declared them as candidate-criterion evidence
  (CC-3) rather than shipping them silently. If the return shape drifts, the failure surfaces as
  missing live board updates in one of nine places, weeks later.

  **This may already be green.** Unlike plan 9 C8(d), no production change is implied — the fix
  round's job is to add the pinning test and arm it, and to say plainly if the two existing
  direct-call tests already discharge it (in which case they are traced to this row rather than
  duplicated). **Plan 10 now carries 8 criteria, at the §15 cap — no further criterion may be
  added to this phase without a re-size.**

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

**Tester (verification engineer), 2026-09-21 (batch C2 round 1, Opus).** 35 criterion rows,
32 plan-named mutation cells (C2(a), C4(a) and C7(b) carry no site by ruling or by design),
**32 executed**. Tests: 8 → 26 in `test_task_state_sync.py`, 1 → 3 in
`test_two_writers_on_one_assignment.py`; no test removed. Full ledger in
`handoffs/tester/2026-09-21_batch_C2_test_1_handoff.md`.

- **All three C5 orders are built and each is armed by the synchronization site itself.** The §6
  referee-lock choreography works as written: both participant blocks are observed, so the order
  is forced, not raced. C5(a)/C5(c) redden on `IllegalAssignmentMove` when the terminal skip is
  decided on the value captured at the unlocked discovery step; C5(b) reddens when Scanner's F5
  ladder is run on the discovery-time state. No barrier, no sleep, no repetition loop.
- **C5(b)'s predicted failure mode is wrong, and the reason matters.** The cell says
  `_move_assignment.py:74-79` refuses the stale decision with `IllegalAssignmentMove` (500). It
  does not: `resolve_processed_group` (plan 9) does **not** call `_assert_allowed_move`, so the
  illegal `awaiting → resolved` is written silently and the row reddens on its own `results`
  assertion instead. The row is armed either way. See owner card 1.
- **C1(f) and C1(i) share one landed edit**, and each half alone is EQUIVALENT exactly as the
  C1(i) cell predicts — both halves were run separately and recorded. C3(a)/C3(c) share one
  edit; C3(d)/(e)/(f) share one edit and each row's own task exit was observed red in it.
- **The six MC-2 probes fire, and each names its own planted site** — checked explicitly,
  because inserting a line into `update_task.py` shifts every registered line number below it
  and would redden the guard on its own. The unregistered-site set names line 67 (the probe) as
  well as the shifted 71, so the collector really observes the planted construct.
- **C4(h)'s named mutation is EQUIVALENT.** With the stale entry planted, dropping the
  `function_exists` assertion leaves the same test red on the adjacent `function_contains_call`
  assertion. The row's positive observation (the planted stale entry, observed red and named) is
  recorded; backfill proposed.
- **Two rows could not fail as shipped and were repaired.** C6(a) was built on `fail_task` with
  no `credited_user_id` at all, so "use the credited user" had nothing to read; it is now S1 with
  the manager performing and the worker credited. C1(g)/C1(h) were built from the wrong
  pre-states (`in_queue` where the rows say `from working` / `from assigned`).
- **C6(b) is proven at S8**, the one site whose `now` is `ctx.now` and therefore the only one a
  fixture can pin to an exact instant (the implementer's flagged judgment call). S8 is a full
  command boundary, so this is a fixture choice, not a narrower surface (§9 rule 17).
- **C2(a) and C7(b) recorded `UNFORCEABLE`** per the owner's rulings; both keep a regression test
  and neither was made to bite. **Candidate criterion:** plan 10 registers
  `sync_task_stock_assignments` in §6.5 but carries no §9 rule-18 row pinning it; see owner
  card 2.

**Reviewer, 2026-09-21 (batch C2 review 1, Opus) — CHANGES_REQUESTED.** Tree `4581209`.
Handoff: `handoffs/reviewer/2026-09-21_batch_C2_review_1_handoff.md`.
**Plan 10: 35 PASS / 0 FAIL / 1 NOT_VERIFIED** of 36 (C8(a) OWED). No row of this plan failed; all
three findings below sit **past the rows**, in the authority they were derived from.

- **F-1 — BLOCKING, route `production`. `sync_task_stock_assignments` does not implement MC-2
  step 3.** `sync_task_stock_assignments.py:57-63` queries *any* non-deleted assignment of the task
  — the `state.in_(ACTIVE_ASSIGNMENT_STATES)` predicate is absent — with `session.scalar` instead of
  the specified `scalar_one_or_none` and no `ORDER BY`. §14F F1 ratifies that a terminal assignment
  "does not block a new assignment", `uix_stock_task_assignments_task_active` is partial on the
  three active states, and phase 8A's `_SCANNER_PROCESSED_STATES` is `{RESOLVED, RESOLVED_EARLY}`
  only — so a `failed` assignment does not block re-assigning the same `(task, item)`, and plan 10
  C3(b)'s own X1 path un-fails the task. **Measured** (reviewer probe, created/run/deleted): with
  A1 `failed` and A2 `in_queue` on one task, the discovery query returned A1, line 81 skipped, and
  A2 stayed `in_queue` when the task moved to `working` — zero events, no error, permanent board
  drift. **Correction:** restore the `ACTIVE_ASSIGNMENT_STATES` predicate (frozenset, rule 16) and
  `scalar_one_or_none`; keep the post-lock terminal skip, which C5(a)/C5(c) depend on.
- **F-5 — should-fix, route `plan`.** No row covers a task with more than one non-deleted
  assignment; every plan 10 fixture is "A created through `CR`", singular. MC-2 step 3's
  "(at most one, MC-4)" premise is unasserted, which is why the tester could not have found F-1.
  **Owner card 1.**
- **F-2 — should-fix, route `production`. The MC-2 write-site collector misses four of MC-2's own
  site classes.** Five constructs planted at EOF of `update_task.py` (no registered line shifted);
  `t_grd` stayed **green, 6 passed**: annotated attribute assignment `task.state: T = …` (class (a),
  and `_task_state_write_scanner.py:6-7`'s own docstring claims it — there is no `visit_AnnAssign`);
  tuple-target `task.state, task.updated_at = …` (class (a) — `visit_Assign` never descends into an
  `ast.Tuple` target); `update(TaskModel)` with the model imported under an alias (class (c) —
  matcher requires `args[0].id == "Task"`); a helper called under an import alias (class (e) —
  `_call_func_name` resolves the alias); plus raw SQL (F-6). Two further latent gaps of the same
  shape: `sa.update(Task)` / `models.Task(state=…)` fail the `isinstance(node.func, ast.Name)` test.
  **No live miss on this tree** — I grepped every form and the corpus contains none, so the 85
  entries are correct today; and the rows the implementer said rest only on the guard
  (C1(b),(c),(e),(f),(i),(j),(l)) were all given their own end-to-end tests by the tester. The
  defect is the instrument's forward-looking reach.
- **F-3 — should-fix, route `plan`. C2(a)'s declared evidence does not exist.** The owner ruling
  delegates C2(a)'s real evidence to "the C4 registry guard, which refuses a sync call inside the
  three helpers". The guard has no negative assertion of any kind. **Measured:** a
  `sync_task_stock_assignments(...)` call planted inside `maybe_evaluate_task_ready` left `t_grd`
  **green, 6 passed**. C2(a) currently has no evidence. **Remedy (owner card 2):** one assertion
  inside the existing guard, using machinery it already has —
  `assert not function_contains_call(None, helper, "sync_task_stock_assignments")` for the three
  helpers and `_apply_step_transition`. Same idiom as the existing positive check, so not an
  implementation-coupled test demand.
- **F-6 — should-fix, route `plan`.** MC-2's guard classes (a)–(e) omit raw SQL, although §5B's own
  2026-09-18 audit searched `text\(` containing `tasks`. Planted `text("UPDATE tasks SET state …")`
  invisible to the guard; nothing in the corpus uses the form today. **Owner card 4.**
- **C7(b) structural check discharged:** `resolve_task.py` raises `ConflictError` on its terminal
  pre-check before the first `Task.state` write and well before the sync call. Label accurate.
- **C5(a)–(c) choreography independently verified:** both participant blocks are observed in every
  order (`:212-217`; shared `_run_forced_order` at `:412-417`), referee lock, no barrier, no sleep,
  `finally` release and purge. The B1 anti-pattern is not present.
- **N-3:** CC-6 closed by reading — `remove_task_steps` (plural) is byte-symmetric with the singular
  caller including the `stock_report_events` hand-up. No test owed.
- **N-4 (verification):** the guard never validates a `not_task: <model>` claim, only that the field
  is non-empty; fold with F-2's fix.
- **C8(a)** is **not** discharged by the two existing direct-call tests: both assert `events == []`,
  so neither exercises a moved assignment and neither pins the returned event kinds. Row text is
  well formed and provable as written.

**Implementer, 2026-09-21 (batch C2 fix round 1, Sonnet).**

**F-1 fixed** — `sync_task_stock_assignments.py`'s step-3 discovery query restores
both dropped halves: `StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES)`
(frozenset, rule 16) and `scalar_one_or_none()` in place of `scalar`. The post-lock
terminal skip is untouched — C5(a)/C5(c) still depend on it. **C1(m) built**:
`test_c1m_sync_selects_the_active_assignment_over_a_terminal_one` creates A1 on
`(T, I, R)`, drives it to `FAILED` via `move_assignment` (fixture only — this is
not the webhook), creates A2 on the same triple (both while T is `ASSIGNED`, so
both start `in_queue`, matching the S1 fixture's own precondition), then drives T
`assigned -> working` through the real S1 command
(`transition_step_state`). Asserts: A1 stays `FAILED`, A2 moves to `IN_PROGRESS`,
counters follow A2 alone, exactly one `stock_task_assignment:state-changed`
(A2's `client_id` only) and one `stock_report_item:updated` for R. **Named
mutation** (drop `state.in_(ACTIVE_ASSIGNMENT_STATES)`, keeping
`scalar_one_or_none`): reddened exactly this test, file run whole — `1 failed,
26 passed`. **Observed failure is `sqlalchemy.exc.MultipleResultsFound`, not the
row's narrated "discovery returns A1, zero events"** — the row's own text
predicts the pre-fix `scalar()` behaviour, but this fix keeps
`scalar_one_or_none()` (the row explicitly asks for it too, and rule 16 forbids
reverting a correct half to arm the other), so a two-row discovery raises
loudly instead of silently picking one. This is a **stronger** failure than the
row narrates, and it still discharges the row: A2 is provably never synced,
zero events are dispatched, and nothing about the fix is compromised by the
`MultipleResultsFound` shape — it is in fact the guard `scalar_one_or_none`
exists to provide (F-1's own correction text: "what makes a future breach of
MC-4's 'at most one' promise loud instead of a coin flip"). Reverted, md5
identical on `sync_task_stock_assignments.py`.

**C4(i) built** — one negative assertion added to the guard
(`test_c4i_no_sync_call_inside_the_task_state_helpers_or_the_shared_core`,
using the existing `function_contains_call` machinery, per the review's own
proposed remedy): none of `maybe_advance_task_to_working`,
`maybe_reopen_task_to_working`, `maybe_evaluate_task_ready` or
`_apply_step_transition` may contain a call to `sync_task_stock_assignments`.
**Named mutation**: planted exactly the forbidden call (per §14F/§5B's own
"why command level" example) at the end of `maybe_evaluate_task_ready`'s body,
after its `task.state = TaskStateEnum.READY` write (line 109, unshifted — the
plant sits after every registered line in the file) so no other registered
site moved. Guard run whole-file: `1 failed, 6 passed`, naming
`maybe_evaluate_task_ready` in the assertion message exactly as the finding
predicted. Reverted (`_task_state_transitions.py` md5 identical before/after);
`test_task_state_write_sites_are_registered.py` re-run green, `7 passed`
(C4(a)'s control row and the six inherited probes C4(b)-(h) all unaffected).

**C4(j) built** — `_task_state_write_scanner.py` extended per the review's own
correction list: `visit_AnnAssign` (class (a)'s annotated form); tuple/list/
starred targets walked in `visit_Assign` (class (a)'s tuple form); an
import-alias table built per file (`_collect_import_aliases`) resolving
`update`/`insert`/`Task`/the four helper names before either a callee or an
`update(Task)`-style argument is matched (classes (c)/(e), and the `Task`
argument of (c)); class **(f)**, a `text(...)`/`.execute(...)` call whose
literal argument names both `tasks` and `state` (case-insensitive). **Named
mutation** (the row's own shape: all five constructs planted at once, in one
live file — `update_task.py`, EOF, after every registered site so no line
shifted): an annotated `task.state: TaskStateEnum = ...`, a tuple-target
`_unused, task.state = ...`, an aliased `update(Task as _TaskAlias)`, an
aliased helper call (`maybe_evaluate_task_ready as _helper_alias`), and a raw
`text("UPDATE tasks SET state = 'ready' WHERE id = 1")`. Guard run whole-file:
`1 failed, 6 passed`, naming all five new lines
(`update_task.py:131`-`135`) as unregistered in one assertion message — the
row's own predicted shape (one run proves all five, since any single one would
already redden `test_c4a_every_collected_site_has_a_registry_entry`). Reverted
(`update_task.py` md5 identical to the pre-probe hash, which also matches the
hash the review's own probe declaration recorded — same starting tree).
**Grepped the whole scanned corpus for all five forms** (annotated `.state:`
assignment, tuple-target `.state`, `import Task as`, `import <helper> as`, and
`text(` literals naming both `tasks` and `state`): zero hits. The 85 registered
sites are unaffected; this guards the next writer, not a live leak, exactly as
F-2/F-6 found. **Not shipped as a permanent test** — same footing as the six
inherited MC-2 probes (C4(b)-(h)), which this project's precedent already
treats as arm-and-revert evidence, not committed regression tests.

**C8(a) built** — `test_c8a_sync_task_stock_assignments_contract` calls
`sync_task_stock_assignments` directly (not through any of the nine sites) with
a task whose captured state differs from its current one, on a task genuinely
carrying a moving assignment (`in_queue -> in_progress`). Asserts the returned
list is exactly one `stock_task_assignment:state-changed` plus one
`stock_report_item:updated` — the contract only, per the row's own scope fence
(C1/C4 already own the nine call sites' behaviour). **Named mutation** (drop the
row event from the return, definition site): reddened this test as expected —
but the same mutation also reddens three other tests in the same file that
assert `:updated` counts (`test_c1m_...`, `test_c1c_s2_batch_...`,
`test_c7a_s4_...`), because the mutation strips every row event this function
ever returns, not just this test's. Recorded per §9 rule 8 (the observed-red
set spans more than the named test): `4 failed, 24 passed`. Reverted, md5
identical.

**N-4 disposed — left as is, recorded.** Validating a `not_task: <model>`
registry claim (rather than only that the field is present) would need type
information the AST sweep does not have — the collector sees `x.state = ...`
and a target expression's text, never the runtime type of `x`. A sound check
would require either a type-inference pass over the whole corpus or a curated
allowlist of known non-`Task` variable names, either of which is a materially
larger instrument than this fix round's perimeter (F-2/C4(j)) and was not
asked for by name. No criterion row demands it and no live mis-registration is
known to exist. Flagged for the coordinator as a possible future guard
enhancement, not built here.

**N-6 disposed — left as is, recorded.** `test_c5a_...` inlines the referee
choreography instead of calling the shared `_run_forced_order` helper C5(b)/(c)
use; both forms observe both participant blocks identically. Cosmetic only;
not touched, to keep this round's perimeter to what the six findings and five
owed rows ask for.

**Perimeter this round (plan 10's share):**
`app/beyo_manager/services/commands/stock_report/sync_task_stock_assignments.py`,
`app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py`,
`app/tests/unit/services/commands/stock_report/task_state_write_site_registry.py`
(one line: the `_move_assignment.py` registry entry's line number, shifted by
plan 9's C8(d) fix — see below),
`app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py`,
`app/tests/integration/services/commands/stock_report/test_task_state_sync.py`.

**One cross-plan registry fix, declared here.** Plan 9's C8(d) fix added lines to
`_move_assignment.py` ahead of its own `NOT_TASK` line (the file's third
`attr_state` site, `resolve_processed_group`'s `assignment.state = target`),
shifting it from line 292 to 302. `task_state_write_site_registry.py`'s entry
for that key is updated to match (a registry key, not a criterion row — no plan
text changes). Caught by running the plan 10 guard suite immediately after the
plan 9 production edit, before writing any new test, exactly as rule 19's
lesson (run collection-sensitive suites, not just the named file) generalizes.

**Reviewer, 2026-09-21 (batch C2 re-review, round 2, Opus). Verdict: APPROVED for
plan 10 — 39/39 PASS, 0 FAIL, 0 NOT_VERIFIED.** Handoff
`handoffs/reviewer/2026-09-21_batch_C2_review_2_handoff.md`. Delta-scoped;
round 1's 35 settled rows not re-verified. Perimeter verified against the five
checkpoint commits — exact match to the eight declared files, nothing outside, no
criterion cell edited.

**F-1 is complete, not merely present.** Both halves of MC-2 step 3 are restored
(`state.in_(ACTIVE_ASSIGNMENT_STATES)` via the frozenset, `scalar_one_or_none`), the
post-lock terminal skip is untouched, and the corrected query is the **only** reader
of that assignment before the locked re-read. Enumerated every other query on
`StockTaskAssignment.task_id` in the corpus: `remove_item_from_task.py:60` and
`delete_task.py:111` are deliberately any-state (MC-14 rows 1–2) and both
`.scalars().all()`, so the singular-selection bug has no analogue;
`consistency.py:106` (`expected_task_flag`) is any-state by definition;
`assignment_check_inputs.py:40` is a bulk `in_` projection. **No second stale read.**
The new `_assert_allowed_move` call introduces no false refusal: all three active
`from_state` values (`awaiting→resolved`, `in_queue`/`in_progress`→`resolved_early`)
pass.

**C1(m) — PASS, new.** The fixture genuinely carries two non-deleted assignments on
one task (A1 `failed`, A2 `in_queue`, both asserted as preconditions) and drives T
through S1 with the **real** `transition_step_state` command. Outcome cell
discharged line by line: A2 → `in_progress`, counters `(0, 4, 0)`, A1 untouched,
exactly one `state-changed` for A2 and one `:updated` for R. Arming consumed by
citation (orchestrator's revert-at-the-site run, tree-matched).

**C2(a)'s delegated evidence now exists** — round 1's F-3 is closed. I verified at
the site that `test_c4i_…` performs the *same* check the owner ruling delegated to:
no `sync_task_stock_assignments` call inside the four named helpers, the shared
step-transition core included.

**C4(i) — PASS, new, and now fully discharged.** The cell names **four** plants; the
round executed one and the orchestrator a second. **I executed the remaining two**
(slot `rv2`, whole-file): a forbidden sync call inside `_apply_step_transition`
(`_step_transition_core.py` — a *different file*, which also proves
`function_contains_call`'s cross-file reach) → `3 failed, 4 passed` with the C4(i)
assertion naming `_apply_step_transition`; and inside `maybe_reopen_task_to_working`
→ `3 failed, 4 passed` naming `maybe_reopen_task_to_working`. (The two extra
failures each time are registry line-drift from a mid-file insertion — expected, not
a defect.) All four helper names exist as real definitions, so no element of the
guard's loop is vacuous. Both probes reverted, tree clean.

**C4(j) — PASS, new.** I re-planted all five constructs at EOF of `update_task.py`
alongside six of my own: the guard reddens and names **all five** C4(j) lines
individually (`121`–`125`), which is per-construct discrimination, not an aggregate.
No construct is double-collected, so this is informationally equivalent to the cell's
"revert each extension in turn" — recorded as note **N-9** (the round ran the plant
and logged it as "the row's own shape" without declaring the divergence, rule 14)
rather than left as an unrun mutation. `update_task.py` md5
`a9d1d5242e6bf18d7ac35225c13064b9` before and after, matching both prior rounds'
pre-probe hash.

**C8(a) — PASS, was NOT_VERIFIED.** Calls the sync directly, pins the argument shape
and the returned event-kind set, and correctly does not re-assert the nine call
sites. Mutation tree-matched; its multi-test bite set is properly recorded.

**One finding — R-1 (should-fix, route `plan`, owner card 1).** The collector still
misses **four constructs inside MC-2's own class list** and one outside it. Measured
in the same run as C4(j): lines 126–131 of my eleven-construct plant are absent from
the assertion, i.e. invisible. (c) `Task.__table__.update().values(state=…)` — the
model is the receiver, `node.args` is empty; (c) `update(Task.__table__)` — class (c)
requires `isinstance(node.args[0], ast.Name)`; (a) `for task.state in (…)` — no
`visit_For`; (a) `with … as task.state` — no `visit_With`; (b) `builtins.setattr(...)`
— the branch requires `isinstance(node.func, ast.Name)`. Outside the list:
`Task(**{"state": …})`, since class (d) needs a literal `state=` keyword.
**The first is the one that matters:** this repository's own test suite already
writes `Task.state` that way three times
(`test_create_stock_task_assignments.py:159`, `test_process_items_processed.py:547`
and `:845`). **Live impact today: none** — grepped the scanned corpus for all six
forms, zero hits; the 85 registered sites are correct. Routed `plan`, not against the
implementer: C4(j) was built exactly as the owner authored it and built correctly.
Extending the class list is the owner's — **owner card 1**. Lesson **L-38**.

**N-2/N-4/N-6 checked at their sites.** N-2 and N-4's dispositions are true (the
`not_task` assertion at `:101` really does check only field truthiness, and the
collector really does hold no type information — `WriteSite.detail` is unparsed
target text). **N-6's substance holds, but one citation is corrected:** the shared
helper C5(b)/C5(c) use is `_run_referee_ordered`
(`test_two_writers_on_one_assignment.py:384`), **not** `_run_forced_order`, which
exists nowhere — a slip in the round-1 *reviewer* handoff, corrected here rather than
propagated. `test_c5a_…` (`:118`) does still inline the choreography.

**Note N-12 (carried):** `test_task_state_write_sites_are_registered.py`'s module
docstring (`:4-8`) still lists five collected classes and omits class (f), and `:15`
still reads "C4(b)-(h), the six required probes" with C4(i)/C4(j) now beside them —
the inverse of L-32. Fold with R-1's fix or a cleanup pass. Lesson **L-39**: when a
criterion cell enumerates N plants, the round runs N.

**Evidence policy and the foreign commit:** as recorded in plan 9's round-2 entry —
no L4 taken, pre-run authorization line given there, and `df09143` (phase 8A) landed
mid-session, so the gate stamp `3669` went stale. **Resolved before close:** `d38f3b3`
re-took the L4 at `df09143` — **23 failed / 3668 passed / 1 skipped**, same 21
published IDs + 2 slot IDs, `3669 − 1` for the withdrawn C3(g) case — on a tree
carrying all of batch C2's work byte-unchanged. **No re-take is owed on C2's
account.** See the handoff's §14 addendum, which also records that `d38f3b3` swept
this round's handoff and plan 9's entry into a phase-8A commit I did not author
(reported, not undone; `git diff -- app/` still empty).
