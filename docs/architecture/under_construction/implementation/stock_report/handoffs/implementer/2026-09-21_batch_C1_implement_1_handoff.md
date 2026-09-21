```
batch: C1
phases: [8, 11]
role: implement
round: 1
state: DONE
date: 2026-09-21
actor: Sonnet
```

# Batch C1 implementation handoff — phases 8 → 11 (`stock_report`)

## 0. Gate check

- `SR/planning/intention.md` begins `status: RATIFIED` — confirmed (round 9, 2026-09-19; "0
  cards open").
- `SR/master_plan.md` §4A: batches A, B1, B2 `APPROVED`; batch C1 `PROJECTED` with the fold
  applied and "Next: the implementer prompt" — confirmed. Predecessor batches for phases 8
  and 11 (A, B) are `APPROVED`.
- `git status --porcelain` empty at start; HEAD `493526c`.
- Read order followed: master plan §3B, §6, §9, §10 → plan 8 → plan 11 → the governing
  contracts (intention §9C MC-12/MC-13, §5B MC-14) → the repo files the plans name.

This project runs the tester role (master plan §3B). Per the batch prompt: I did not run a
single mutation, did not build the row-level coverage map, and did not write a mutation
ledger. What follows is the tester contract in place of those.

## 1. Checkpoints (clean tree at each)

| Phase | Commit | Note |
|---|---|---|
| 8 | `00c21c9` | assignment batch create/delete, matcher, race error, role cells |
| 11 | `4561746` | removal hooks and the category guard (new files only — see next row) |
| 11 (fix) | `6eaf2d3` | the five production edits `4561746`'s message described but its `git add` invocation missed (an earlier invocation with a since-renamed path aborted silently); no new behaviour, makes the tree match the claim |

Working tree is clean at HEAD (`6eaf2d3`) as of this handoff.

## 2. The one L4 stamp

Command: `PYTHONPATH=. pytest -m 'not e2e'` (`-n 6 --dist loadfile` from `pytest.ini`), tree
`6eaf2d3`, clean.

**Result: 21 failed / 3512 passed / 1 skipped** (collected 3534, 1 deselected for `e2e`).

Failure-ID diff against the published 21-ID baseline (`docs/architecture/archives/
test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3), both
directions, by filename+test name (path prefixes normalized): **empty both ways — identical
sets.** (I hit one collection **error**, not a failure, on the first attempt — see §7's
environment finding — fixed before this stamp was taken; the stamp above is the post-fix
run.)

Pass-count arithmetic: the last recorded stamp (batch B2, tree `29b4395`) was 21/3445/2.
This batch's own new tests: phase 8 — 22 (`test_create_stock_task_assignments.py`) + 1
(`_race.py`) + 8 (`test_delete_stock_task_assignments.py`) + 4 (serializers) + 1 (C4(m) in
`test_apply_stock_demand.py`) + 10 net new in the router file (18 total there now, 8 were
pre-existing) = 46. Phase 11 — 3 (`test_task_side_removals.py`) + 6
(`test_item_side_removals.py`) + 9 (`test_category_guard.py`) + 2 (`test_removal_locks.py`)
= 20. Total new: 66. `3445 + 66 = 3511`, one short of `3512` — the extra pass is the
analytics/shift drifter this project has seen recover before (`test_c3_real_concurrent_open_
insert_translates_the_loser[model]`-shaped time dependency; I did not chase which specific
test flipped, since the failure-ID sets already match exactly in both directions and that is
the comparator this project uses, not a raw pass count). Skip count 2 → 1: see §8, not a
regression — neither of the two candidate conditional-skip files (`test_database_isolation.
py`, `test_system_transition_reasons_retirement.py`) is in this batch's perimeter (`git diff`
confirms no changes to either).

Lint: `ruff check` on every file this batch touched — clean. Whole-repo `ruff check .` shows
140 pre-existing findings in files this batch never touched (confirmed by grep against the
touched-file list).

## 3. Production write perimeter

**New files:**
- `bm/domain/stock_report/serializers.py`
- `bm/services/commands/stock_report/requests/__init__.py`
- `bm/services/commands/stock_report/create_stock_task_assignments.py`
- `bm/services/commands/stock_report/delete_stock_task_assignments.py`
- `bm/services/commands/stock_report/_category_guard.py`

**Edited files:**
- `bm/errors/stock_report.py` (+`StockAssignmentRefused`, +`StockAssignmentPropertyMismatch`)
- `bm/services/commands/stock_report/_events.py` (+`coalesce_stock_report_events`)
- `bm/routers/api_v1/stock_report.py` (+2 routes, structured-error rendering)
- `bm/services/commands/tasks/delete_task.py` (removal hook)
- `bm/services/commands/tasks/remove_item_from_task.py` (new Task lock, removal hook)
- `bm/services/commands/items/delete_item.py` (new Item lock, removal hook)
- `bm/services/commands/items/update_item.py` (category guard)
- `bm/services/commands/items/find_or_create_item.py` (category guard, existing-item branch)

**No mutation probes were run this round** (skipped per the tester-role split), so there is
no probe-file list to declare separately — every file above is a genuine, kept change.

**Test files — new:**
`tests/unit/domain/stock_report/test_stock_report_serializers.py` (created as
`test_serializers.py`, renamed same round — see §8),
`tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py`,
`test_create_stock_task_assignments_race.py`, `test_delete_stock_task_assignments.py`,
`test_task_side_removals.py`, `test_item_side_removals.py`, `test_category_guard.py`,
`test_removal_locks.py`.

**Test files — edited:**
`tests/unit/routers/api_v1/test_stock_report_router.py` (assignment role cells, C8(i)/(j)),
`tests/integration/services/commands/stock_report/test_apply_stock_demand.py` (+1 test,
C4(m), no production change to `apply_stock_demand.py`).

**Plan files edited:** `SR/plans/plan_8.md` and `SR/plans/plan_11.md` — Review log entries
only.

## 4. Tests I wrote → the row each aimed at (claims, not evidence)

**Plan 8:**

| Test | Row(s) aimed at |
|---|---|
| `test_creates_assignment_moves_counters_and_returns_full_read_shape` | C4(a)/(i)/(j), C4(l) (partial — see §6) |
| `test_quantity_floors_at_one` | C4(g)/(h) (floor behaviour; not the literal-vs-max distinction) |
| `test_resolved_task_may_still_be_assigned` | C4(f) |
| `test_two_entries_ascending_item_id_response_order_and_summed_counters` | C4(k) |
| `test_stock_report_item_absent_is_refused` | C1(a) |
| `test_row_soft_deleted_is_refused` | C1(b) |
| `test_related_item_is_refused_item_not_task_primary` | C1(f) (RELATED shape; not (g)'s removed-link shape) |
| `test_already_resolved_pair_is_refused_already_processed_by_scanner` | C1(p) |
| `test_failed_task_is_refused` | C1(h)/(i) (failed only; not the cancelled variant) |
| `test_item_already_assigned_is_refused_before_any_write` | C1(j)/(k) (the `count_writes == 0` clause) |
| `test_item_has_no_category_is_refused` | C1(l) |
| `test_category_mismatch_is_refused` | C1(m) |
| `test_all_or_nothing_valid_entry_writes_nothing_when_a_later_entry_fails` | C1(o) |
| `test_duplicate_item_in_batch_names_every_offending_index` | C2(a) |
| `test_duplicate_task_in_batch_names_every_offending_index` | C2(b) |
| `test_property_mismatch_without_override_raises_409_with_sorted_failures` | C3(a) |
| `test_override_on_a_mismatching_entry_creates_with_flag_true` | C3(b) |
| `test_override_on_a_matching_entry_is_ignored` | C3(c) |
| `test_unknown_top_level_field_is_refused_422` | C3(e) |
| `test_empty_entries_is_refused_422` | C3(f) |
| `test_two_entries_on_one_row_dispatch_two_created_and_one_coalesced_updated` | C7(a) |
| `test_refused_request_dispatches_nothing` | C7(b) |
| `test_c5a_concurrent_create_on_the_same_item_leaves_exactly_one_active` (race file) | C5(a) |
| `test_deletes_in_queue_assignment_zeroes_counters_and_clears_flag` | C6(a) |
| `test_deleting_resolved_assignment_leaves_counters_untouched` | C6(c) |
| `test_absent_id_refuses_the_whole_batch` | C6(d) |
| `test_already_deleted_id_is_not_found` | C6(e) |
| `test_foreign_workspace_id_is_not_found` | C6(f) |
| `test_two_assignments_on_one_row_coalesce_to_one_updated_event` | C6(h) |
| `test_repair_record_carries_the_delete_assignments_trigger` | C7(c) |
| `test_unknown_field_and_empty_client_ids_are_refused` | (delete request validation; no lettered row names this — request-shape sanity) |
| `test_serialize_item_compact_*`, `test_serialize_task_compact_*`, `test_serialize_stock_task_assignment_*` | C4(l) (the fourteen-key shape and its own internal consistency, not the cross-endpoint-with-phase-13 clause) |
| `test_stock_report_routes_reach/reject_*`, `test_assignment_routes_*` | C8(a)-(h) |
| `test_stock_assignment_refused_renders_code_and_details`, `test_stock_assignment_property_mismatch_renders_code_and_details` | C8(i)/(j) |
| `test_c4m_demand_never_stamps_authorship_columns` | C4(m) |

**Plan 11:**

| Test | Row(s) aimed at |
|---|---|
| `test_c1a_deleting_task_removes_active_assignment_and_updates_counters` | C1(a) |
| `test_c1b_deleting_task_removes_resolved_assignment_without_counter_change` | C1(b) |
| `test_c1c_deleting_task_removes_every_non_deleted_assignment_of_the_task` | C1(c) |
| `test_c2a_unlinking_primary_item_removes_its_active_assignment` | C2(a) |
| `test_c2b_unlinking_a_related_item_does_nothing_to_the_primarys_assignment` | C2(b) |
| `test_c2c_swap_then_create_on_the_new_primary_succeeds` | C2(c) |
| `test_c3a_deleting_item_removes_its_active_assignment_task_untouched` | C3(a) |
| `test_c3b_deleting_item_leaves_a_failed_assignment_untouched_in_counters` | C3(b) |
| `test_delete_item_absent_raises_not_found` | (existence check; no lettered row — item-deletion NotFound is not separately numbered) |
| `test_c4a_changing_category_with_active_assignment_is_refused` | C4(a) |
| `test_c4c_changing_an_unrelated_field_with_active_assignment_is_allowed` | C4(c) |
| `test_c4f_changing_category_of_a_resolved_only_assignment_is_allowed` | C4(f) |
| `test_c4g_changing_category_of_a_soft_deleted_only_assignment_is_allowed` | C4(g) |
| `test_c4i_changing_category_of_a_resolved_early_only_assignment_is_allowed` | C4(i) |
| `test_c5a_create_task_naming_a_new_category_for_an_actively_assigned_item_is_refused` | C5(a) (partial — see §6) |
| `test_c5c_create_task_omitting_category_with_active_assignment_is_allowed` | C5(c) |
| `test_c5d_no_assignment_at_all_category_change_through_create_task_behaves_as_today` | C5(d) |
| `test_c5e_find_or_create_item_directly_refuses_with_active_assignment` | C5(e) |
| `test_delete_task_locks_rows_then_assignments_after_the_existing_task_lock` | MC-1 lock order for `delete_task` (not a lettered row; C7's declared-unforceable rows are not this) |
| `test_delete_item_locks_item_first_then_rows_then_assignments` | MC-1 lock order for `delete_item` (same caveat) |

## 5. One load-bearing pointer per criterion group

- **Plan 8 C1** (refusal chain) — `create_stock_task_assignments.py:_phase3_reason` (the
  nine-branch chain, in MC-13's order).
- **Plan 8 C2** (duplicates) — `create_stock_task_assignments.py:create_stock_task_assignments`,
  the `Counter`-based phase-1 block at the top of the function.
- **Plan 8 C3** (matcher) — `create_stock_task_assignments.py`, the phase-4 loop calling
  `evaluate_stock_criteria` (imported from `criteria_matcher.py`, unchanged).
- **Plan 8 C4** (writes) — `create_stock_task_assignments.py`, the phase-5 loop; state via
  `state_map.ASSIGNMENT_STATE_BY_TASK_STATE`; quantity via `max(item.quantity, 1)`.
- **Plan 8 C5(a)** — the lock: `_locks.py:lock_items` (unchanged, phase 3), called from
  `create_stock_task_assignments.py`'s phase-2 block. **Post-lock re-read**: the phase-3 chain
  reads `locked_rows`/`locked_tasks`/`locked_items` — the dicts `lock_*` returns after its own
  `FOR UPDATE` — never a pre-lock reference.
- **Plan 8 C5(b)** — see §6; no site in this phase's files.
- **Plan 8 C6** (delete) — `delete_stock_task_assignments.py:delete_stock_task_assignments`,
  the discovery→lock→re-read→loop sequence.
- **Plan 8 C7** (coalescing) — `_events.py:coalesce_stock_report_events`.
- **Plan 8 C8** — `routers/api_v1/stock_report.py`, the two `require_roles([...])`
  decorators and the `_run` helper's structured-error branch.
- **Plan 11 C1** — `delete_task.py`, the block between `cancelled_item_upholstery_ids = …`
  and `task.is_deleted = True`.
- **Plan 11 C2** — `remove_item_from_task.py`, the `if task_item.role == TaskItemRoleEnum.
  PRIMARY:` block, placed before `task_item.removed_at = …`.
- **Plan 11 C3** — `delete_item.py`, the block between the Item lock and `item.is_deleted =
  True`.
- **Plan 11 C4/C5** — `_category_guard.py:assert_item_category_change_allowed`; called from
  `update_item.py` (guard block ahead of the `_DIRECT_FIELDS` loop — see §8's judgment call)
  and `find_or_create_item.py`'s existing-item branch (guard block ahead of its own
  `_DIRECT_FIELDS` loop).
- **Plan 11 C6** — the `trigger=` keyword at each of the three `remove_assignment(...)` call
  sites (`delete_task.py`, `remove_item_from_task.py`, `delete_item.py`) — not independently
  tested this round (see §6).
- **Plan 11 C7** — declared unforceable by the plan itself; the lock statements are in
  `remove_item_from_task.py` (new Task lock, before the discovery block) and `delete_item.py`
  (new Item lock, the function's first statement).

**No concurrency row in this batch other than plan 8 C5(a) needed a two-session test** (C5(b)
is discussed in §6; plan 11's C7 rows are declared unforceable by the plan).

## 6. Rows I know I did not exercise

**Plan 8:** C1(c), (d), (e), (n), (q), (r), (s), (t), (u); C2(c); C3(d) (deliberate blank);
C4(b)-(e) (state-map cells, out-of-perimeter mutation targets per plan 8 §7 — I did not write
a test naming those specific task states beyond `pending`/`resolved`); the second clause of
C4(l) (cross-check against `GET /items/{client_id}/assignments`, phase 13, doesn't exist yet
in this batch); C5(b) (see below); C6(b), (g), (i); C8's individual per-role-drop mutant shape
(my router tests prove reach/refuse, not that dropping exactly one role in the decorator list
reddens exactly one sub-row — that is mutation work).

**Plan 11:** C4(b), (d), (e); C5(b) (declared known-unarmed by the plan); C6(a)-(c) (the
trigger-string rows — I wired the correct `trigger=` string at each call site but did not add
a test asserting the resulting `inline:<trigger>` string, unlike plan 8's C7(c) which I did
build); C7(a), (b) (declared unforceable).

**C5(b) — flagged for the tester, not just named.** Plan 8's C5(b) row names its mutation
site as "remove the `sorted(...)` from the Item-lock acquisition in
`create_stock_task_assignments.py` (definition site)". That call does not exist in the file I
wrote: `create_stock_task_assignments.py` passes an unordered Python `set` of `item_ids`
straight to phase-3's approved `lock_items` (`_locks.py`), whose single `SELECT … ORDER BY
client_id … FOR UPDATE` already guarantees deterministic ascending lock acquisition inside one
atomic statement, regardless of the order ids arrive in — there is no `sorted()` call in my
file to remove. I believe the production requirement ("acquire the locks in sorted order,
deterministically") is met by construction via that one call, and I did not add anything.
I did not build a two-session test for C5(b) (I did build one for C5(a) — see
`test_create_stock_task_assignments_race.py`): there is no phase-8-authored branch for such a
test to exercise red→green, and forcing the opposite-order interleaving to prove the deadlock
cannot occur is exactly the adversarial proof this project's tester owns. Sending this up now
so arming doesn't start by hunting for a `sorted()` line that was never written.

## 7. Seams a test would need that production doesn't offer

None found this round. Every row I read as needing a seam (the two-session C5 rows, the
lock-order rows) already has one via the approved `_locks.py` helpers and `get_db_session()`.

## 8. Judgment calls, deviations, and things found wrong in the plans

1. **Phase-1 duplicate check order** (plan 8): item_id checked before task_id when an entry
   could name either. Not specified by the plan; no criterion exercises both at once.
2. **Phase-4 matcher batching** (plan 8): collects every post-phase-3 entry's mismatch into
   one `StockAssignmentPropertyMismatch` rather than stopping at the first. The plan's C3(a)
   sentence is singular, but the surrounding design is all-or-nothing everywhere else; no
   criterion tests two simultaneous mismatches, so this is undeclared either way.
3. **Router body models** (plan 8): I added fully-typed FastAPI body classes
   (`_CreateStockTaskAssignmentsBody`, `_DeleteStockTaskAssignmentsBody`) matching this
   codebase's established convention rather than a raw-dict passthrough — master plan §6.5/§6.6
   registers only the command-level request classes, not a router-level shape. Consequence: an
   HTTP client sending an unrecognized top-level field gets FastAPI's own validation error, not
   `StockAssignmentRefused`. C3(e) is proven at the `CR()`/command boundary only, per the
   plan's own fixture shorthand (which bypasses the router) — this is where the plan's own
   proof method already lives, so I did not treat it as a gap, but a future reviewer or the
   frontend may expect a uniform error envelope across the whole HTTP surface and this phase
   does not provide one.
4. **Guard placement relative to `_DIRECT_FIELDS`** (plan 11): in both `update_item.py` and
   `find_or_create_item.py`, I placed the category guard's lock-and-refresh (which uses
   `populate_existing=True`, overwriting any not-yet-flushed in-memory attribute changes)
   *before* the `_DIRECT_FIELDS` loop, not only before the `item_category_id =` assignment line
   the plan's task text literally names. Placing it after that loop would silently drop the
   request's other field changes whenever a category change is requested in the same call. No
   criterion in either plan exercises "category change plus another field in one request" —
   this is an undeclared judgment call, and a mutation reintroducing the wrong ordering would
   not be caught by anything I wrote or, as far as I can tell, any named cell in plan 11.
5. **C5(a)'s "whole creation rolls back" claim (plan 11) is not independently observable at my
   test's scope.** `db_session` is in one continuously-autobegun transaction for the whole test
   (confirmed by direct instrumentation — `session.in_transaction()` is `True` immediately
   after a prior owner-mode command commits, the moment any further statement touches the
   session), so `create_task`'s own `maybe_begin` never reaches owner mode inside my test and
   never gets a chance to roll back — a same-session read sees the flushed-but-uncommitted Task
   row regardless of whether a real, fresh-per-request session (the actual production
   topology, per `get_db()`) would have discarded it. My test proves the guard fires with the
   exact message and the item's own category is unaffected; it does not prove the task-and-
   everything-else rollback, which the intention argues analytically (§5B: "no `begin_nested`
   wraps the call, no earlier step commits"). Naming this rather than asserting something my
   fixture cannot actually discriminate.
6. **Owner card A's `count_writes == 0` clause** (plan 8 C1(j)/(k)): built exactly as specified
   — one test, `record_statements` around the call, asserting zero writes to
   `stock_task_assignments`.
7. **§9B ruling 2** (the fourteen-key response shape moved into phase 8): built as specified;
   `serialize_item_compact`/`serialize_task_compact`/`serialize_stock_task_assignment` all ship
   in `bm/domain/stock_report/serializers.py` this phase, `serialize_stock_report_item` (phase
   12's) is not added (charter rule 4 — no caller yet).
8. **Environment finding, fixed in this round.** The new unit test
   `tests/unit/domain/stock_report/test_serializers.py` (created for phase 8) collided at the
   whole-suite L4 with the pre-existing `tests/unit/domain/shopify/test_serializers.py`: this
   test tree has no `__init__.py` files anywhere, so pytest's rootdir import mode uses the bare
   filename as the module name, and the second file collected on a name clash errors out instead
   of running (a collection **error**, not a normal test failure — it does not show up in `-q`
   summaries the same way, which is how it survived my phase-8 L1/L2 runs and the phase-8
   checkpoint). Renamed to `test_stock_report_serializers.py`; re-ran the full L4, clean. Worth
   a standing rule (`§9` addition) if this project adds more `test_serializers.py`/similarly
   generic-named files under different subpackages — an L1/L2 run of the new file alone will
   never catch this, only a full-suite collection will.
9. **Checkpoint bookkeeping mistake, self-caught.** My first phase-11 checkpoint commit
   (`4561746`) staged only the new files because an earlier `git add` invocation (that included
   a not-yet-renamed path) aborted before staging anything and I committed without re-checking
   `git status`. Caught it before this handoff by re-running `git status --porcelain` post-
   commit; fixed with a second, clearly-labelled commit (`6eaf2d3`) adding the missing
   production edits, rather than amending. Flagging per charter's own logic on self-caught
   mistakes: reporting this is the job working correctly, not a defect to hide.

## 9. Owner decisions required

**Nothing needs the owner.** Zero cards. Everything above (the C5(b) mutation-site note, the
guard-ordering judgment call, the C5(a) rollback-testability limit) is information for the
tester and reviewer, not a question only the owner can answer.
