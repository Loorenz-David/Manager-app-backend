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

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | S1 `transition_step_state`: T `assigned`, A `in_queue`; step → `working` | T `working`; A `in_progress`; `(0, 4, 0)` | remove the sync call from `transition_step_state.py` (call site) | MC-2 S1, M2 |
| C1(b) | S1: last step → `completed` so T → `ready` | A `awaiting`; `(0, 0, 4)`; `G == 4` | — | MC-2 S1, HC-4 |
| C1(c) | S2 `transition_step_state_batch`: two tasks on R, both advance to `working` | both assignments `in_progress`; `(0, 8, 0)`; exactly one `:updated` for R | one sync call per task → two `:updated` | MC-2 S2, MC-19 |
| C1(d) | S3 `force_task_ready`: T `pending`, A `in_queue` | A `awaiting` (in_queue → awaiting, the MC-1 cell) | — | MC-2 S3 |
| C1(e) | S4 `resolve_task` from `working` (A `in_progress`) | A `awaiting`; `(0, 0, 4)` | remove the call (P-e's mutation, also C4(f)) | MC-2 S4 |
| C1(f) | S4 `resolve_task` from `ready` (A `awaiting`) | A stays `awaiting`; no stock event (`=` cell) | emit anyway | MC-2 step 5, MC-19 |
| C1(g) | S5 `fail_task` from `working` | A `failed`; `(0, 0, 0)` | — | MC-2 S5, §5 |
| C1(h) | S6 `cancel_task` from `assigned` | A `failed` | — | MC-2 S6 |
| C1(i) | S7 `add_task_steps` on T `pending` (A `in_queue`) | T `assigned`; A stays `in_queue`; no stock event | — | MC-2 S7 (`=` cell) |
| C1(j) | S7 `add_task_steps` on T `ready` (A `awaiting`, `G == 4`) → reopen | T `working`; A `in_progress`; `G == 0`; `mem IS NULL` | — | MC-2 S7, MC-5 row 4 |
| C1(k) | S8 `remove_task_step`: T `working` with one step; remove it | T `pending`; A `in_queue`; `(4, 0, 0)` | — | MC-2 S8 (§14C C6) |
| C1(l) | S9 `handle_finalize_pending_step_completion(payload, T)` driven directly (fixture per the existing integration test): the pending completion makes T `ready` | A `awaiting`; `updated_by_id == payload["performed_by_user_id"]` | — | MC-2 S9 |
| C2(a) | S8 with T `ready` and two completed steps; `remove_task_step` on one → `pending` then `maybe_evaluate_task_ready` → `ready` inside one transaction | A stays `awaiting`; `G` unchanged; `mem` unchanged; **no** stock event | sync inside the helpers (per intermediate write) → un-credit + re-credit + two events | MC-2 step 1 (U1), HC-4 |
| C3(a) | A `resolved` (via `PR`); then S7 reopen (`add_task_steps` on the resolved-then-… — use: T `ready` → resolve via Scanner → `add_task_steps` reopens T to `working`) | A stays `resolved`; counters unchanged; no stock event | move it | §5 r1, M2 |
| C3(b) | A `failed` (T failed); `remove_task_step` sets T `pending` (X1 path) | A stays `failed`; no stock event | — | §5 r1 (C6) |
| C3(c) | A `resolved_early` via `PR` while T `working` (A was `in_progress`; `G == 4`, `mem == G`); then S1 completes the last step so T → `ready` | T `ready`; A stays `resolved_early`; counters `(0, 0, 0)`; `G == 4`, `mem == G`; **no** stock event; clean | skip the terminal test → `MV(resolved_early → awaiting)` raises `IllegalAssignmentMove` (500) or, with plan 4 mutated too, re-credits `G` | §14F F3 ("the sync skips … no wait, no second resolution"), M2 round-9 sentence |
| C3(d) | as (c), then S5 `fail_task` | A stays `resolved_early`; `G == 4`; no stock event | — | §14F F3 ("if the task instead fails") |
| C3(e) | as (c), then S6 `cancel_task` | A stays `resolved_early`; no stock event | — | §14F F3 |
| C3(f) | as (c), then S8 `remove_task_step` removing the only step so T → `pending` | A stays `resolved_early`; `(0, 0, 0)`; no stock event | — | §14F F3 ("or reopens"), M2 |
| C4(a) | the guard on the current tree | passes | — | MC-2 guard |
| C4(b) | P-a: add `task.state = TaskStateEnum.STALLED` in `tasks/update_task.py:update_task` | guard fails naming the site | (this row **is** the probe) | MC-2, rule 15 |
| C4(c) | P-b: `setattr(task, "state", TaskStateEnum.READY)` in the same function | fails | probe | MC-2 |
| C4(d) | P-c: `await session.execute(update(Task).values(state=TaskStateEnum.READY))` there | fails | probe | MC-2 |
| C4(e) | P-d: a call to `maybe_evaluate_task_ready(...)` there | fails | probe | MC-2 |
| C4(f) | P-e: delete the `sync_task_stock_assignments` call from `tasks/resolve_task.py:resolve_task` (call site) | fails (registered `task_write` without the call) | probe | MC-2 |
| C4(g) | P-f: change `users/_clock_worker_shift.py:clock_out_shift_for_user`'s `new_state=` to `TaskStepStateEnum.COMPLETED` | fails (paused driver no longer paused) | probe | MC-2 |
| C4(h) | a registry entry naming a function that does not exist | fails (stale entry) | drop the staleness check | MC-2 "stale registry entry" |
| C5(a) | MC-11 **Scanner first**: A `awaiting` (`G == 4`); session 1 `PR([SR-x])`, session 2 `add_task_steps` reopening T; barrier after both discovered ids; session 1 takes the row lock first (session 2 is made to wait by session 1 holding the lock until session 2 has started its lock statement — bounded) | A `resolved`; counters `(0, 0, 0)`; `G == 4`; `mem == G`; session 1's events `[state-changed resolved, :updated]`; session 2's stock events empty | skip the post-lock re-read → session 2 moves a resolved assignment | MC-11 row 1, M1, M2 |
| C5(b) | MC-11 **reopen first** (§14F F6): the mirror ordering — session 2 (`add_task_steps`, T `ready → working`) takes the row lock first and commits `awaiting → in_progress`; session 1 (`PR([SR-x])`) then re-reads `in_progress` | A `resolved_early`; counters `(0, 0, 0)` (the reopen wrote `awaiting −4, in_progress +4`; Scanner then `in_progress −4`); `G == 4` and `mem == G` (the reopen cleared the first credit — `G` went to 0 — and entering `resolved_early` credited the current goal again, F4); session 2's events `[state-changed in_progress, :updated {…, quantity_in_progress: 4, …}]`; session 1's result `resolved/early` and events `[state-changed resolved_early, :updated {…, quantity_in_progress: 0, …}]`; T stays `working` | decide on the pre-lock read (`awaiting`) → Scanner moves `awaiting → resolved` on an assignment that is `in_progress` | §14F F6 (replaces MC-11 row 2; §14C C49), M1, M2 |
| C5(c) | MC-11 **Scanner first while `in_progress`** (§14F F6, new row): A `in_progress` (T `working`, `G == 0`); session 1 `PR([SR-x])`, session 2 S1 completing the last step (T → `ready`); session 1 takes the row lock first | A `resolved_early`; `(0, 0, 0)`; `G == 4`, `mem == G`; session 1's events `[state-changed resolved_early, :updated]`; session 2 commits T `ready` with **no** stock event; no assignment in an active state; `assert_stock_report_clean` | skip the post-lock re-read in the sync → session 2 moves a terminal assignment | §14F F6 ("both orders end with no assignment in an active state and counters equal to the recomputation"), M1, M2 |
| C6(a) | S1 where a manager `M` performs the transition with `credited_user_id = Wk` | A `updated_by_id == M` (the performer), not `Wk` | use the credited user | MC-17 (C28, U13) |
| C6(b) | any synced move | A `updated_at ==` the command's `now` | use `datetime.now()` inside the sync | MC-17 |
| C7(a) | S4 `resolve_task` | the dispatched list contains the task's own events **and** the stock events, all after commit | dispatch inside the sync | MC-19 hand-up, 06_commands_local |
| C7(b) | `resolve_task` on a task already `resolved` (the command raises) | no stock event dispatched; A unchanged | — | MC-19 "rolled-back request" |
| C7(c) | A `in_queue` via `CR`; raw `quantity_in_queue = 0`; S1 advance | one repair record with `trigger == "inline:task_sync"` | — | §12A trigger set |

## 7. Notes

- Sizing: 35 criterion rows in 7 criteria; `complex: yes`. (Counts re-derived by script after the
  round-9 fold; see the delta handoff.)
- C4(b)–(g) are the six required probes of MC-2: each is planted, observed red, reverted, and
  recorded with the observed failure message — they are rows, not prose.
- Round 9 (2026-09-19): C3(c)–(f) added (the sync never moves a `resolved_early` assignment, one
  row per task exit named by §14F F3); C5(b) rewritten to F6 (the "Task reopen first" order now ends
  in `resolved_early`, with the goal re-credited); C5(c) added (Scanner first while `in_progress`).
  The registry guard C4 is untouched by round 9.
- C5's ordering is forced by lock acquisition, not by sleeps: the first session holds the row lock
  across an `asyncio.Event` until the second has issued its `FOR UPDATE` (bounded with `wait_for`),
  then releases (master plan §9 rule 9).
- Hazard (master plan §10 (b)): the flush + one query per command may shift an existing
  statement-count test if one wraps a sync site; none was found on 2026-09-19 — the reviewer
  re-checks the L4 delta against the baseline set.
- The registry lives in tests; it is data for the guard, not production code.

## 8. Review log

(empty)
