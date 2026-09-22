```
batch: C2
phases: [9, 10]
role: implement
round: 1
state: DONE
date: 2026-09-21
actor: Sonnet
```

# Batch C2 implementation handoff — phases 9 → 10 (`stock_report`)

## 0. Gate check

- `SR/planning/intention.md` begins `status: RATIFIED` (round 9, 2026-09-19, re-ratified for
  §14G round 10; "0 cards open") — confirmed.
- `SR/master_plan.md` §4A: batch C1 `APPROVED` (phases 8, 11 `VERIFIED`); batch C2 row was
  `BATCH_NOT_STARTED — waits for C1 APPROVED` — confirmed satisfied. Plan 9 `depends_on: 7, 8
  (APPROVED)`; plan 10 `depends_on: 9`, satisfied in-session (phase 9 implemented with green
  L1 before phase 10 started, per §3B's batch dependency rule).
- `git status --porcelain` empty at start; starting HEAD `9105f71` (phase 8A's checkpoint).
- Read order followed: implementation-executor doctrine (incl. "When the project runs a
  tester") → pipeline charter → master plan §3B, §6, §9, §10 → plan 9 → plan 10 → the intention
  sections both plans' §2 name (§8.2/§8A/§8B MC-8/MC-9/MC-10, §5A MC-1/MC-11/MC-16, §5B
  MC-2/MC-14, §6A MC-5/MC-6, §9D MC-19, §12A, §13 M2, §14F F1-F11) → the shipped phase 1-8/11
  files the plans cite as precedent.

**This project runs the tester role (master plan §3B).** Per the batch prompt: I did not run a
single mutation, did not build the row-level coverage map, and did not write a mutation
ledger. What follows is the tester contract in place of those.

**Mid-batch environment drift (reported, not a defect of mine).** While I worked, six commits
landed on `main` from the concurrent phase 8A/coordinator workstream (docs and prompts only —
`git diff 9105f71..b9e1d7f -- app/beyo_manager/ app/tests/` is empty, verified). My checkpoints
are built on top of `b9e1d7f`, not `9105f71`; no code file I touched was touched by that stream.
A `handoffs/reviewer/2026-09-21_phase_8A_review_1_handoff.md` file also appeared as untracked
mid-session — foreign, not created by me, left untouched and unstaged throughout.

## 1. Checkpoints (clean tree at each)

| Phase | Commit | Note |
|---|---|---|
| 9 | `8a5ebc2` | processed webhook: parse, owning transaction, grouped resolution, replay |
| 10 | `ffa591e` | task-state sync at S1-S9 + the AST write-site registry/guard |
| (docs) | `a79cb10` | master plan §10 env-fact addendum (the `BEYO_TEST_SLOT` finding, §2 below) |

Working tree is clean at HEAD (`a79cb10`) as of this handoff.

## 2. The one L4 stamp

Command: `BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest -m 'not e2e'` (`-n 6 --dist loadfile` from
`pytest.ini`), tree `ffa591e`, clean (the one doc-only commit after it, `a79cb10`, touches no
test or production file).

**Result: 23 failed / 3619 passed / 1 skipped.**

**Failure-ID diff against the published 21-ID baseline, both directions:** the 21 baseline IDs
are all present; **2 extra IDs**, both explained (not a stock_report regression — see below):
`test_database_isolation.py::test_worker_name_resolution_uses_xdist_worker` and
`test_database_isolation.py::test_worker_name_resolution[None-None-beyo_test_main_main]`.
Confirmed independent of my changes: both pass with `BEYO_TEST_SLOT` unset and fail with it set
to `c2` on the byte-identical tree, with or without any stock_report file present. Root cause:
they read `settings.test_slot` (bound from the env var at process start) after
`monkeypatch.delenv("BEYO_TEST_SLOT", ...)`, which cannot undo a value already baked into the
settings singleton — so with a genuinely-exported non-`main` slot they assert `beyo_test_c2_*`
against a hard-coded `beyo_test_main_*` expectation. This is the **first real L4 run of this
project under a non-`main` `BEYO_TEST_SLOT`**; I recorded it in master plan §10 (commit
`a79cb10`) as a known hazard for every later batch run under a non-`main` slot.

**Pass-count arithmetic, reconciled:**
- Batch C1 gate: 3547 passed at `798fc69`.
- Phase 8A's checkpoint `9105f71` added 28 (22 preview integration, 1 evaluator unit, 5
  router): `3547 + 28 = 3575` (per the prompt's own reconciliation, confirmed unchanged through
  `b9e1d7f` — `git diff` empty on `app/`).
- I added 46 tests this batch (9 unit parser + 19 integration process_items_processed + 1
  integration lock/session + 8 integration task-state-sync + 1 integration two-writer race + 6
  unit write-site-guard + 2 unit router), all green: `3575 + 46 = 3621`.
- 2 previously-green tests flipped red under `BEYO_TEST_SLOT=c2` (§2 above, not mine):
  `3621 - 2 = 3619`. **Matches the L4 stamp exactly.**
- Failed: `21 (baseline) + 2 (slot) = 23`. **Matches.** Skipped: `1`, unchanged.

Lint: `ruff check` on every file in my perimeter is clean, except five pre-existing unused
imports in `transition_step_state.py` (`timedelta`, `DelayedSchedulerTypeEnum`,
`SchedulerOriginSourceEnum`, `SchedulerStateEnum`, `DelayedScheduler`) — confirmed present
before my edit (`git show 9105f71:...` reproduces the identical five) and out of my scope fence
to clean up while adding one call site to that file.

## 3. Production write perimeter

**Phase 9 — new:**
- `app/beyo_manager/services/commands/stock_report/items_processed_request.py`
- `app/beyo_manager/services/commands/stock_report/process_items_processed.py`

**Phase 9 — edited:**
- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` (+`resolve_processed_group`)
- `app/beyo_manager/domain/stock_report/enums.py` (+`ItemsProcessedOutcomeEnum`, +`ItemsProcessedReasonEnum`)
- `app/beyo_manager/routers/api_v1/location_tracker_webhooks.py` (+ the second route)

**Phase 10 — new:**
- `app/beyo_manager/services/commands/stock_report/sync_task_stock_assignments.py`

**Phase 10 — edited (one call site each, after the command's last `Task.state` write, inside
its transaction):**
- `app/beyo_manager/services/commands/task_steps/transition_step_state.py` (S1)
- `app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py` (S2)
- `app/beyo_manager/services/commands/tasks/force_task_ready.py` (S3)
- `app/beyo_manager/services/commands/tasks/resolve_task.py` (S4)
- `app/beyo_manager/services/commands/tasks/fail_task.py` (S5)
- `app/beyo_manager/services/commands/tasks/cancel_task.py` (S6)
- `app/beyo_manager/services/commands/task_steps/add_task_steps.py` (S7)
- `app/beyo_manager/services/commands/task_steps/remove_task_step.py` (S8, both
  `remove_task_step` and `remove_task_steps`, plus the `_dispatch_remove_step_events` signature
  gained a `stock_report_events` parameter to carry the sync's events past the transaction
  boundary to the post-commit dispatch)
- `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py` (S9)

**Test files — new:**
- `app/tests/unit/services/commands/stock_report/test_items_processed_request.py`
- `app/tests/integration/services/commands/stock_report/test_process_items_processed.py`
- `app/tests/integration/services/commands/stock_report/test_process_items_processed_locks.py`
- `app/tests/integration/services/commands/stock_report/test_task_state_sync.py`
- `app/tests/integration/services/commands/stock_report/test_two_writers_on_one_assignment.py`
- `app/tests/unit/services/commands/stock_report/task_state_write_site_registry.py`
- `app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py` (support module
  for the guard test, not itself collected as a test — see plan 10's Review log judgment call)
- `app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py`

**Test files — edited:**
- `app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py` (+2 tests, the
  second route's wiring)

**No mutation probes this round** (the tester owns the named-mutation ledger, §3B). One
self-confidence check on the write-site guard, applied and reverted, not part of any ledger:
I injected a fake unregistered `task.state = READY` write into
`app/beyo_manager/services/commands/tasks/update_task.py`, confirmed
`test_task_state_write_sites_are_registered.py` failed (both the unregistered-site and the
stale-entry assertions), then reverted (`git checkout --`) and confirmed the file was returned
to its committed state and the guard passed again. No other file was touched by this check.

**Documents:**
- `SR/plans/plan_9.md` (Review log)
- `SR/plans/plan_10.md` (Review log)
- `SR/master_plan.md` §10 (the `BEYO_TEST_SLOT` env-fact addendum)

**Architecture graph:** one batched `apply_changes` (revision `c1ef5a6c...`), 4 nodes + 5
relationships, all origin `ai_inferred`, evidence-linked: endpoint `items processed webhook`,
domain `processed webhook resolution` (the grouped move), domain `task state to stock
assignment sync`, test `task state write-site guard`; edges: the endpoint depends on the
resolution domain; the resolution domain modifies `stock_task_assignments` and
`stock_report_items`; the sync domain modifies `stock_task_assignments`; the guard test
verifies the sync domain. No promote/reject/edit of any review item.

## 4. Tests I wrote → the row each aimed at (claims, not evidence)

**Plan 9:**
| Test | Row(s) aimed at |
|---|---|
| `test_items_processed_request.py` (9 tests) | C2(b), C2(a) [via non-array body], C2(c), C2(d), C2(e), C2(f), C2(g), C2(h), plus the raw-echo behaviour task 1 names |
| `test_c1a_no_key_is_401_and_writes_nothing` | C1(a) |
| `test_c1e_blank_workspace_setting_is_401_zero_statements` | C1(e) |
| `test_c1c_workspace_setting_names_no_workspace_is_401` | C1(c) |
| `test_c3a/_b/_c/_g/_i/_k_*` | C3(a), C3(b), C3(c), C3(g), C3(i), C3(k) |
| `test_c4_awaiting_resolves_credit_kept_task_untouched` | C4(a), C4(b) [event names], C4(c) |
| `test_c4_in_queue_resolves_early_and_credits_goal` | C4(d), C4(g) [reason/state], part of F8 |
| `test_c4f_no_goal_record_nothing_credited` | C4(f) |
| `test_c5a_duplicate_in_one_request_awaiting` | C5(a) |
| `test_c5b_duplicate_in_one_request_in_queue_applies_delta_once` | C5(b) |
| `test_c6a_replay_awaiting_resolve_is_zero_statements` | C6(a) |
| `test_c6b_replay_after_early_resolve_goal_unchanged` | C6(b) |
| `test_c7a_three_awaiting_assignments_on_one_row_sum_and_one_updated_event` | C7(a) |
| `test_c7c_grouped_repair_carries_the_summed_delta` | C7(c) |
| `test_c8c_resolve_processed_group_contract` | C8(c) |
| `test_c8a_fresh_session_reads_the_committed_resolve` | C8(a) |
| router tests (2) | the route's own wiring (no lettered row; same shape as the shipped
  demand-route tests) |

**Plan 10:**
| Test | Row(s) aimed at |
|---|---|
| `test_task_state_write_sites_are_registered.py` (6 tests) | C4(a) — the guard's own control row |
| `test_s1_transition_step_state_advances_the_assignment` | C1(a) |
| `test_s4_resolve_task_moves_in_progress_to_awaiting` | C1(e) |
| `test_s5_fail_task_moves_the_assignment_to_failed` | C1(g) |
| `test_s6_cancel_task_moves_the_assignment_to_failed` | C1(h) |
| `test_c6a_credited_user_is_the_performer_not_a_third_party` | C6(a) |
| `test_s8_remove_task_step_moves_in_progress_to_in_queue` | C1(k) |
| `test_sync_never_moves_a_resolved_early_assignment` | the §14F F3 terminal-skip invariant
  (sibling of C3(c)/(d)/(e)/(f); driven directly, not through a task-exit command) |
| `test_sync_no_ops_when_the_assignment_is_already_at_target` | the `=` cell (sibling of C1(f)/(i)) |
| `test_c5a_scanner_first_task_sync_second_skips_the_resolved_assignment` | C5(a) |

## 5. One load-bearing pointer per criterion

**Plan 9:**
- The F5 ladder decision: `process_items_processed.py:process_items_processed`, the
  `for index, raw_number, stripped in stripped_by_index:` loop (sequential, `working_state`
  mutated in place for the request-order effect MC-10 step 3 requires).
- The grouped counter statement: `_move_assignment.py:resolve_processed_group`, the
  `_apply_counter_delta(...)` call — same guarded statement and repair routine as
  `move_assignment`.
- The goal-credit step per assignment: `_move_assignment.py:resolve_processed_group`'s
  `apply_goal_effect(...)` call, reusing `_goal_credit.py`'s existing table unmodified (its
  `to_state in (AWAITING, RESOLVED_EARLY)` / `from_state == AWAITING and to_state == RESOLVED`
  branches already covered both of §14F F4's new rows with no code change).
- Replay/zero-statement: the unlocked discovery predicate
  `StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES)` in `process_items_processed.py` — a
  resolved/resolved_early assignment is never discovered, so nothing downstream runs.
- X3 (one owning transaction): `process_items_processed.py`, the
  `if ctx.session.in_transaction(): raise RuntimeError(...)` guard immediately before
  `async with maybe_begin(...)`.
- X2 (sorted locks): `_locks.py:_lock` (phase-3, unedited) — `ORDER BY client_id ... FOR UPDATE`
  in one statement; `process_items_processed.py` passes the full candidate-id sets to
  `lock_stock_report_items`/`lock_stock_task_assignments` once each.

**Plan 10:**
- Where the row lock is taken: `sync_task_stock_assignments.py`, the
  `await lock_stock_report_items(session, workspace_id, [assignment.stock_report_item_id])`
  call, immediately followed by `lock_stock_task_assignments` for the assignment (MC-1 order,
  step 4 then step 5).
- Where the referee's lock sits (C5(a)): a **third** session in
  `test_two_writers_on_one_assignment.py:_referee`, `SELECT ... FROM stock_report_items WHERE
  client_id = :row_id ... FOR UPDATE`, held until both participant tasks are observed blocked.
- Where the post-lock state is read: `sync_task_stock_assignments.py`, `assignment =
  locked_assignments[assignment.client_id]` (the identity-mapped instance
  `_locks.py:_lock`'s `populate_existing=True` refreshed in place) — the very next lines test
  `assignment.is_deleted or assignment.state in TERMINAL_ASSIGNMENT_STATES` and `assignment.state
  == target` against that refreshed value, never the pre-lock one.
- The terminal-skip invariant (§14F F3): the same `assignment.state in
  TERMINAL_ASSIGNMENT_STATES` check — one line, one frozenset, never a spelled list (rule 16).
- The registry/guard (C4(a)): `_task_state_write_scanner.py:collect_write_sites` (the AST
  sweep) checked against `task_state_write_site_registry.py:REGISTRY` in
  `test_task_state_write_sites_are_registered.py`'s five assertions.

## 6. Rows I know I did not exercise

**Plan 9:** C1(b), C1(d), C1(f), C1(g), C1(h) — the shared verifier's own message/order
guarantees, already proven in phase 7's suite, not re-derived on this command's path beyond the
one C1(e)/C1(a)/C1(c) smoke tests above. C2(a) and C2(d) — the plan's own deliberate blanks
(§3B class 2), left to the tester to site. C3(d), C3(e), C3(h), C3(j), C3(l) — sibling cases of
rows I did test one representative of. C4(e) — the `in_progress` sibling of the `in_queue` row I
tested. C7(b), C7(d), C7(e) — the two-row and mixed-state groupings (I tested the three-row,
same-state C7(a)/C7(c)). C8(b) — the plan itself declares this interleaving unforceable and
routes it to the reviewer's structural check.

**Plan 10:** C1(b), C1(c), C1(d), C1(f), C1(i), C1(j), C1(l) — S1's `HC-4` sibling and S2, S3,
S7, S9's own command-level behaviour are proven only by the C4 guard (their sync call is wired
and calls the right function), never driven end-to-end through their own command in this round.
C2(a) — owner-ruled `UNFORCEABLE BY DESIGN`; its real evidence is C4. C3(a), C3(b), C3(d), C3(e),
C3(f) — sibling terminal-skip cases of the one direct-call test I built. C4(b)-(h) — the six
required probes plus the staleness check are the tester's arming work (§3B). C5(b), C5(c) — the
mirror order and the `in_progress` order (C5(a) is built and green, run four times total across
this session with no flake). C6(b) — flagged as a judgment call in plan 10's Review log (S8's
`now` source). C7(a), C7(b), C7(c) — dispatch-order and trigger rows.

## 7. Seams a test would need that the production code does not offer

None found this round. The one seam concern the batch prompt flagged in advance — plan 10's old
C5 wording naming a "hold the lock open" seam that does not exist — was resolved before I
started (the projection already rebuilt C5 on the referee-lock choreography, master plan §6
preamble); I built and confirmed that choreography works as written (C5(a), four consecutive
green runs).

## 8. Judgment calls, deviations, plan issues found

All recorded in-line in each plan's own Review log (§8) — summarized:
- Plan 9: C1(e) needed no new production code (phase 7's shared verifier already refuses a
  blank workspace/key before any DB read); the "per-entry sequential decision, then group by
  row" split between `process_items_processed` and `resolve_processed_group`; the
  `stock_task_assignment:updated` wording in §6.5/C8(c) read as informal (built `:state-changed`,
  the only assignment-transition kind this project registers); `resolve_processed_group`'s
  unconditional per-row `:updated` event (safe only because every caller passes a non-empty,
  all-active group).
- Plan 10: the scanner support module beyond §4's file list; `sync_functions` naming the real
  caller rather than the write's own enclosing function for the three shared-helper writes (so
  the helper itself is never asked to call the sync, per §5B's "why command level" rule); S8's
  two-caller `sync_functions` list; S8's `now` sourced from `ctx.now` rather than the helper's
  internal clock read (the one site where `task.updated_at` and `assignment.updated_at` are not
  bit-identical — flagged for the tester's C6(b)).

No plan defect found that stopped a row; no contradiction with an installed dependency (rule
17) encountered.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this handoff needs the owner — the `stock_task_assignment:updated` wording
question (§6.5/C8(c)) is addressed to the **coordinator** as a documentation-consistency note,
not an owner decision: I built the only event kind this project has ever registered for a state
transition, and no behavioral choice hinges on the answer.
