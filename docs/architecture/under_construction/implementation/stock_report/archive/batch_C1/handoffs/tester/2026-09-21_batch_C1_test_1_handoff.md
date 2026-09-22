```
batch: C1
phases: [8, 11]
role: test
round: 1
state: BLOCKED_PLAN
date: 2026-09-21
actor: Opus
```

# Batch C1 verification handoff — plans 8 and 11 (`stock_report`)

## 0. Summary

93 criterion rows in scope (plan 8: 67; plan 11: 26 live + C4(h) withdrawn). Every row has a
disposition. **No `BLOCKED-PRODUCTION` row** — production behaved correctly under all 103
mutation runs; nothing goes back to the implementer.

95 plan-named mutation cells declared, 95 executed (`executed == declared`, summands in §5),
plus 8 recorded re-sitings/diagnostics. 29 tests added, 0 removed, 1 renamed. Production diff
against the implementer checkpoint is empty.

**What this round bought.** Eleven rows could not fail as shipped or as written, in five shapes:

| Shape | Rows |
|---|---|
| Row's outcome does not distinguish the mechanism from a database constraint | plan 8 **C5(a)** (owner card 1) |
| The behaviour is guarded **twice**, so no single-site mutant exists | plan 8 **C4(k)**, **C6(c)**, **C6(i)**, **C6(e)** |
| The named mutation names a site that is not load-bearing | plan 8 **C1(r)**, **C4(c)**; plan 11 **C2(b)** |
| Fixture satisfied two sufficient causes / could not order against its key | plan 8 **C3(e)**, **C3(a)** (sort sub-check) |
| Test read its own assertion out of a stale identity map, or short-circuited before its own bite | plan 11 **C3(a)**, **C2(c)** |

Plus **plan 11 C5(a)**, whose rollback clause the implementer honestly reported as unobservable:
it is now proven on a second, fresh session and armed.

## ⚠ OWNER DECISIONS REQUIRED (2)

**Card 1 — the two-worker race row cannot fail as written**

- **Question** — Add "and the losing call wrote nothing to `stock_task_assignments`" to plan 8
  C5(a)'s outcome, as you did for C1(j)/C1(k)?
- **Story** — Two warehouse workers tap "assign" on the same chair in the same second. Today one
  gets a clean "already assigned" and nothing is written. If the item lock were ever removed,
  both would reach the insert, the database's own unique index would reject the second, and that
  worker would see *the same message* — so the test we rely on stays green while the request had
  already tried to write. I removed the lock this round and the test did not notice.
- **Branches** — Add the clause: the row fails the moment the lock stops doing the work, at the
  cost of one assertion. · Leave it: the row is green with or without the lock and the reviewer
  checks the lock by reading the code.
- **Recommendation** — Add it: it is the device you already ratified for C1(j)/C1(k), and it is
  one line.
- **On silence** — The gate holds: C5(a) stays `BLOCKED-PLAN`, no clause is added, no test changed.
- **Trace** — plan 8 C5(a) and §7; master plan §9 rule 7 (fifth use); plan 8 §7 owner card A.

**Card 2 — a clause that can only be proven two phases from now**

- **Question** — Move plan 8 C4(l)'s second clause ("the create response and the assignments
  endpoint return the same keys") to plan 13, or drop it?
- **Story** — A frontend developer renders a freshly created assignment from the create response,
  then reloads the board and renders the same assignment from the list endpoint. If the two
  shapes ever drift, the card changes shape on reload. The list endpoint is built in phase 13, so
  nothing in this batch can compare them. The first clause — the fourteen keys — is proven and
  armed.
- **Branches** — Move it to plan 13: the comparison is made once, where both shapes exist. · Drop
  it: the two call the same serializer today and nothing guards it later.
- **Recommendation** — Move it to plan 13; it is the only place it can be true, and costs one row.
- **On silence** — The gate holds: C4(l)'s second clause stays `BLOCKED-PLAN` and no row is authored.
- **Trace** — plan 8 C4(l); master plan §9B ruling 2; plan 13.

## 1. Gate check

- Intention `SR/planning/intention.md` header: `RATIFIED` — confirmed.
- Master plan §4A: batch C1 `IMPLEMENTED`; predecessor batches A, B1, B2 `APPROVED`.
- `git status --porcelain` empty at session start; `HEAD` = `1f96c18`, which contains the
  implementer checkpoint `6eaf2d3`.
- `git diff 6eaf2d3..HEAD -- app/` empty at dispatch — everything after `6eaf2d3` is documentation.
- Implementer L4 stamp baseline-identical (21/3512/1, failure IDs identical both ways), already
  independently re-run by the orchestrator on this tree. **Consumed by citation; not re-run.**

## 2. Checkpoints and the empty production diff

| | Commit |
|---|---|
| Implementer checkpoint | `6eaf2d3` |
| Tester checkpoint | the single `CHECKPOINT (not approved): … tester` commit that carries this file (its SHA is in the session's final message; it is `HEAD` when this handoff lands) |

```
git diff 6eaf2d3..HEAD -- app/beyo_manager/     # empty
```

Verified empty at the moment of the closing stamp (`git diff 6eaf2d3..HEAD -- app/beyo_manager/`
and `git diff -- app/beyo_manager/` both empty; `git status --porcelain` listed only the six
test files below).

## 3. The one L4 stamp

Command: `PYTHONPATH=. pytest -m 'not e2e'` (`-n 6 --dist loadfile` from `pytest.ini`), from
`app/`, tree = the tester checkpoint, clean.

**Result: 21 failed / 3541 passed / 1 skipped** (2 warnings, 0 errors), 72.3 s.

Failure-ID delta against the published 21-ID baseline
(`docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3),
both directions by `comm`: **empty both ways — identical sets.**

Pass arithmetic: the implementer's tree-matched stamp was 21/3512/1; this session added 29 tests
and removed none, so `3512 + 29 = 3541`. The stamp reads **exactly 3541** — the arithmetic closes with no drift this round (the known load-dependent drifter did not move).

*One invalidated stamp, disclosed.* My first attempt added `-p no:logging`, which removes
pytest's logging plugin and therefore the `caplog` fixture; 37 unrelated tests in
`tests/unit/test_worker_shifts_router.py` and neighbours errored at setup. That run is not the
stamp — the command above is. The per-file L1 probe runs carried the same flag; none of the
in-scope files uses `caplog`, and all ten were green under it before any mutation.

Lint: `ruff check` on the six changed test files — clean.

---

# 4. The verification ledger

## 4.1 Plan 8 — table 1: mutations

Scope of every run: **L1**, `PYTHONPATH=. pytest <file>` (whole file, never `-k`), with
`-q -p no:logging --no-header -rf`. Every probe reverted with `git checkout --` and verified
byte-identical with `git diff --quiet` before the next probe was applied; the driver aborts if a
revert fails.

| M-id | Site (`file:symbol`, def/call) | Plan-named? (row) | Landed | Test file run | Observed red: test id → clause | Reverted |
|---|---|---|---|---|---|---|
| M01 | `create_stock_task_assignments.py:_phase3_reason` (def) — drop the `row is None` arm | yes, C1(a) | ✓ | create | `test_stock_report_item_absent_is_refused` → the row lookup crashes instead of refusing; also `test_c1c_row_in_a_foreign_workspace_is_refused` | ✓ |
| M02 | same symbol — drop the `row.is_deleted` arm | yes, C1(b) | ✓ | create | `test_row_soft_deleted_is_refused` → `details` reason | ✓ |
| M03 | `_locks.py:_lock` (def) — drop `model.workspace_id == workspace_id` **[out-of-perimeter, plan 3]** | yes, C1(c) | ✓ | create | `test_c1c_row_in_a_foreign_workspace_is_refused` → the foreign row resolves and is created | ✓ |
| M04 | `_phase3_reason` (def) — delete the task-existence check | yes, C1(d) | ✓ | create | `test_all_or_nothing_valid_entry_writes_nothing_when_a_later_entry_fails` → `reason == task_not_found` @1 becomes `item_not_task_primary` (row (d)'s clause); also `test_c2c…` | ✓ |
| M05 | `_phase3_reason` (def) — delete the item-existence check | yes, C1(e) | ✓ | create | `test_c1e_absent_item_id_is_refused_item_not_found` → reason | ✓ |
| M06 | `_lookup_primary_pairs` (def) — accept any role | yes, C1(f) | ✓ | create | `test_related_item_is_refused_item_not_task_primary` → the RELATED entry is created; also `test_c1t…` | ✓ |
| M07 | `_lookup_primary_pairs` (def) — drop `removed_at IS NULL` | yes, C1(g) | ✓ | create | `test_c1g_retired_primary_link_is_refused_item_not_task_primary` → reason | ✓ |
| M08 | `_TASK_FAILED_OR_CANCELLED_STATES` (def) — drop `FAILED` | yes, C1(h) | ✓ | create | `test_failed_task_is_refused[TaskStateEnum.FAILED]` → `IllegalAssignmentMove` instead of the refusal | ✓ |
| M09 | same — drop `CANCELLED` | yes, C1(i) | ✓ | create | `test_failed_task_is_refused[TaskStateEnum.CANCELLED]` → reason; **and `test_c3d_retry_after_a_409_is_re_evaluated_from_scratch` → C3(d)'s own reason clause** | ✓ |
| M10 | `_lookup_active_item_ids` (def) + its call site — narrow the pre-check to the request's own rows | yes, C1(j) | ✓ | create | `test_item_already_assigned_is_refused_before_any_write` → **only** `count_writes == 0`; the reason clause stayed green, exactly as the cell predicts | ✓ |
| M11 | `_phase3_reason` (def) — delete the `item_already_assigned` pre-check | yes, C1(k) | ✓ | create | `test_c1k_item_already_assigned_on_the_same_row_refuses_before_any_write` → **only** `count_writes == 0`; also C1(j)'s test | ✓ |
| M12 | `_phase3_reason` (def) — delete the `item_has_no_category` check | yes, C1(l) | ✓ | create | `test_item_has_no_category_is_refused` → reason becomes `category_mismatch` | ✓ |
| M13 | `_phase3_reason` (def) — delete the category comparison | yes, C1(m) | ✓ | create | `test_category_mismatch_is_refused` → the K2 item is created; also `test_c1n…` | ✓ |
| M14 | `create_stock_task_assignments` (def) — hoist phase 4 above the phase-3 raise | yes, C1(n) | ✓ | create | `test_c1n_category_mismatch_precedes_the_property_matcher` → 409 instead of 422 `category_mismatch` | ✓ |
| M15 | `create_stock_task_assignments` (def) — skip refused entries, create the rest, raise at the end | yes, C1(o) | ✓ | create | `test_all_or_nothing_valid_entry_writes_nothing_when_a_later_entry_fails` → the "nothing written" clause | ✓ |
| M16 | `_phase3_reason` (def) — delete the `already_processed_by_scanner` check | yes, C1(p) | ✓ | create | `test_already_resolved_pair_is_refused_already_processed_by_scanner` → a second assignment is born; also C1(q), C1(u) tests | ✓ |
| M17 | `_lookup_processed_pairs` (def) + call site — restrict to the request's own rows | yes, C1(q) | ✓ | create | `test_c1q_resolved_early_on_another_row_is_refused_already_processed` → reason | ✓ |
| M18 | `_phase3_reason` (def) — membership keyed on `item_id` alone | yes, C1(r) | ✓ | create | **NO RED** — `EQUIVALENT`: `_lookup_processed_pairs` already filters `task_id.in_(task_ids)`, so the pair for the *old* task is never in the set. Re-sited → M18b | ✓ |
| M18b | `_lookup_processed_pairs` query **and** the membership test — key on `item_id` alone | re-siting of C1(r) | ✓ | create | `test_c1r_a_new_task_for_the_same_item_is_not_affected` → the new task is refused | ✓ |
| M19 | `_lookup_processed_pairs` (def) — drop `is_deleted.is_(False)` | yes, C1(s) | ✓ | create | `test_c1s_a_soft_deleted_resolved_assignment_does_not_refuse` → refused | ✓ |
| M20 | `_phase3_reason` (def) — swap `item_not_task_primary` ↔ `already_processed_by_scanner` | yes, C1(t) | ✓ | create | `test_c1t_item_not_task_primary_comes_before_already_processed` → reason | ✓ |
| M21 | `_phase3_reason` (def) — swap `already_processed_by_scanner` ↔ `task_failed_or_cancelled` | yes, C1(u) | ✓ | create | `test_c1u_already_processed_comes_before_task_failed_or_cancelled` → reason | ✓ |
| M22 | `create_stock_task_assignments` (def) — phase 1 marks only the later occurrence | yes, C2(a) | ✓ | create | `test_duplicate_item_in_batch_names_every_offending_index` → index 0 missing from `details`; also C2(b), C2(c) tests | ✓ |
| M23 | same — drop the repeated-`task_id` detection | yes, C2(b) | ✓ | create | `test_duplicate_task_in_batch_names_every_offending_index` → reasons become `item_not_task_primary` @1 | ✓ |
| M24 | same — raise on phase 1 before phase 3 | yes, C2(c) | ✓ | create | `test_c2c_phase1_and_phase3_reasons_arrive_in_one_error` → the `task_not_found` index is missing | ✓ |
| M25 | `criteria_matcher.py:evaluate_stock_criteria` (def) — `return failures` unsorted **[out-of-perimeter, plan 2]** | yes, C3(a)-i | ✓ | create | **NO RED** — `EQUIVALENT` **by fixture** (see §6) | ✓ |
| M26 | `create_stock_task_assignments` (def) — raise the mismatch with empty `details` | yes, C3(a)-ii | ✓ | create | `test_property_mismatch_without_override_raises_409_with_sorted_failures` → the `details` equality | ✓ |
| M27 | phase-5 insert (def) — `property_mismatch_overridden=False` | yes, C3(b) | ✓ | create | `test_override_on_a_mismatching_entry_creates_with_flag_true` → the flag | ✓ |
| M28 | phase-5 insert (def) — store the flag as sent | yes, C3(c) | ✓ | create | `test_override_on_a_matching_entry_is_ignored` → the flag | ✓ |
| M29 | `requests/__init__.py` (def) — `extra="ignore"` on both models | yes, C3(e) | ✓ | create | `test_unknown_top_level_field_is_refused_422` → no `ValidationError` | ✓ |
| M30 | `requests/__init__.py:CreateStockTaskAssignmentsRequest` (def) — drop `min_length=1` | yes, C3(f) | ✓ | create | `test_empty_entries_is_refused_422` → no `ValidationError` | ✓ |
| M31 | `state_map.py:5` PENDING → AWAITING **[out-of-perimeter, plan 1]** | yes, C4(a) | ✓ | create | `test_creates_assignment_moves_counters_and_returns_full_read_shape` → state and counters; 8 expected collateral reds (plan 8 §7) | ✓ |
| M32 | `state_map.py:6` ASSIGNED → IN_PROGRESS **[plan 1]** | yes, C4(b) | ✓ | create | `test_assignment_state_follows_the_task_state[TaskStateEnum.ASSIGNED-…]` → state | ✓ |
| M33a | `_move_assignment.py:_apply_counter_delta` (def) — counters written from the identity-mapped value instead of column-referencing **[plan 4]** | yes, C4(c) | ✓ | create | **NO RED** — `EQUIVALENT` at this row's boundary (a single create reads what it would compute). Re-sited → M33b | ✓ |
| M33b | `state_map.py:7` WORKING → IN_QUEUE **[plan 1]** | re-siting of C4(c) | ✓ | create | `test_assignment_state_follows_the_task_state[TaskStateEnum.WORKING-…]` → state and `(0,4,0)` | ✓ |
| M34 | `state_map.py:8` STALLED → IN_QUEUE **[plan 1]** | yes, C4(d) | ✓ | create | `test_assignment_state_follows_the_task_state[TaskStateEnum.STALLED-…]` → state | ✓ |
| M35 | `state_map.py:9` READY → IN_QUEUE **[plan 1]** | yes, C4(e) | ✓ | create | `test_c4e_ready_task_creates_awaiting_and_credits_the_goal` → state, `(0,0,4)`, `G == 4` and `mem == G` all die together | ✓ |
| M36 | `_TASK_FAILED_OR_CANCELLED_STATES` (def) — add RESOLVED | yes, C4(f) | ✓ | create | `test_resolved_task_may_still_be_assigned` → refused instead of created | ✓ |
| M37 | phase-5 insert (def) — `quantity=1` | yes, C4(g) | ✓ | create | `test_c4g_quantity_is_copied_from_the_item` → quantity 8 and `(8,0,0)`; 8 expected collateral reds | ✓ |
| M38 | phase-5 insert (def) — `quantity=item.quantity` (drop the floor) | yes, C4(h) | ✓ | create | `test_quantity_floors_at_one` → CHECK violation | ✓ |
| M39 | phase-5 loop (call site) — drop `set_task_stock_flag(..., True)` | yes, C4(i) | ✓ | create | `test_creates_assignment_moves_counters_and_returns_full_read_shape` → `is_stock_assignment is True` | ✓ |
| M40 | phase-5 insert (def) — stamp `updated_by_id`/`updated_at` on creation | yes, C4(j) | ✓ | create | `test_creates_assignment_moves_counters_and_returns_full_read_shape` → `updated_* is None` | ✓ |
| M41 | `create_stock_task_assignments` (def) — drop the phase-5 write-loop sort | yes, C4(k) | ✓ | create | **NO RED** — `EQUIVALENT`: the response is sorted again at `:309`. Re-sited → M41c | ✓ |
| M41c | both sorts (`:244` and `:309`) | re-siting of C4(k) | ✓ | create | `test_two_entries_ascending_item_id_response_order_and_summed_counters` → the response order | ✓ |
| M42 | `serializers.py:serialize_stock_task_assignment` (def) — drop the nested `item` | yes, C4(l) | ✓ | create + serializers | `test_creates_assignment_moves_counters_and_returns_full_read_shape` → the 14-key `set(payload)`; `test_serialize_stock_task_assignment_returns_the_fourteen_keys_with_nested_item_and_task` → the key set | ✓ |
| M43 | `apply_stock_demand.py` step-5 INSERT `values` (def) — add a non-NULL `created_by_id` **[plan 7]** | yes, C4(m)-i | ✓ | apply_stock_demand | `test_c4m_demand_never_stamps_authorship_columns` → `created_by_id is None`; 3 expected collateral reds | ✓ |
| M44 | `apply_stock_demand.py` step-7 raw UPDATE (def) — add `updated_at = now()` **[plan 7]** | yes, C4(m)-ii | ✓ | apply_stock_demand | `test_c4m_demand_never_stamps_authorship_columns` → `updated_at is None` | ✓ |
| M56 | `create_stock_task_assignments` phase 2 (call site) — replace `lock_items` with an unlocked select | yes, C5(a) | ✓ | race | **NO RED** — `EQUIVALENT` at the row's stated outcome. See owner card 1 | ✓ |
| M58 | `_locks.py:_lock` (def) — delete `.order_by(model.client_id)` **[plan 3]** | yes, C5(b) | ✓ | race | **NO RED** — `UNFORCEABLE`; see §6 | ✓ |
| M47 | `_remove_assignment.py:21` (call site) — drop `recompute_task_stock_flag` **[plan 4]** | yes, C6(a) | ✓ | delete | `test_deletes_in_queue_assignment_zeroes_counters_and_clears_flag` → `is_stock_assignment is False`; 3 collateral reds via `assert_stock_report_clean` | ✓ |
| M48 | `_goal_credit.py:129` (call site) — drop `_uncredit` in the `from_state == AWAITING` branch **[plan 5]** | yes, C6(b) | ✓ | delete | `test_c6b_deleting_an_awaiting_assignment_uncredits_the_goal` → `G == 0` | ✓ |
| M49 | `_move_assignment.py:260` (def) — remove the `any(delta != 0)` guard **[plan 4]** | yes, C6(c) **and** C6(i)-ii | ✓ | delete | **NO RED** — `EQUIVALENT`: the coalescer drops a `:updated` whose payload equals the row's initial values, so the guard is doubled. Re-sited → M49b | ✓ |
| M49b | the same guard **and** `_events.py:coalesce_stock_report_events`' equals-initial drop | re-siting of C6(c)/C6(i)-ii | ✓ | delete | `test_deleting_resolved_assignment_leaves_counters_untouched` → the event-name list (C6(c)); `test_c6i_deleting_a_resolved_early_assignment_keeps_its_goal_credit` → its own event-name list (C6(i)) | ✓ |
| M50 | `delete_stock_task_assignments` (def) — remove the found ones, raise afterwards | yes, C6(d) | ✓ | delete | `test_absent_id_refuses_the_whole_batch` → `A.is_deleted is False` | ✓ |
| M51 | `delete_stock_task_assignments` discovery (def) — drop `is_deleted.is_(False)` | yes, C6(e) | ✓ | delete | **NO RED** — `EQUIVALENT`: the post-lock re-read catches it. Re-sited → M51b | ✓ |
| M51b | discovery filter **and** the post-lock re-read | re-siting of C6(e) | ✓ | delete | `test_already_deleted_id_is_not_found` → no `NotFound` | ✓ |
| M52 | `delete_stock_task_assignments` discovery (def) — drop the workspace filter | yes, C6(f) | ✓ | delete | `test_foreign_workspace_id_is_not_found` → no `NotFound` | ✓ |
| M53 | `services/queries/stock_report/consistency.py:expected_task_flag` (def) — restrict to `ACTIVE_ASSIGNMENT_STATES` **[plan 3]** | yes, C6(g) | ✓ | delete | `test_c6g_flag_stays_true_while_another_assignment_of_the_task_survives` → the flag goes false | ✓ |
| M54 | `delete_stock_task_assignments` (call site) — dispatch without coalescing | yes, C6(h) | ✓ | delete | `test_two_assignments_on_one_row_coalesce_to_one_updated_event` → two `:updated` | ✓ |
| M55 | `_move_assignment.py:_delta_vector` (def) — subtract `q` on every non-creation move **[plan 4]** | yes, C6(i)-i | ✓ | delete | `test_c6i_deleting_a_resolved_early_assignment_keeps_its_goal_credit` → counters/self-heal | ✓ |
| M45 | `create_stock_task_assignments` (call site) — dispatch the raw event list | yes, C7(a) | ✓ | create | `test_two_entries_on_one_row_dispatch_two_created_and_one_coalesced_updated` → two `:updated` | ✓ |
| M46 | `create_stock_task_assignments` — move the dispatch inside the transaction block | yes, C7(b) | ✓ | create | **NO RED** — `EQUIVALENT` by construction; see §6 | ✓ |
| M57 | `delete_stock_task_assignments` (call site) — `trigger="manual"` | yes, C7(c) | ✓ | delete | `test_repair_record_carries_the_delete_assignments_trigger` → `inline:delete_assignments` | ✓ |
| R01 | `stock_report.py` create-route decorator (def) — drop `ADMIN` | yes, C8(a) | ✓ | router | `…reach_service_for_permitted_roles[POST-/assignments-body0-admin]` | ✓ |
| R02 | same — drop `MANAGER` | yes, C8(b) | ✓ | router | `…[POST-/assignments-body0-manager]` (plus the two rendering tests, which use `manager`) | ✓ |
| R03 | same — drop `WORKER` | yes, C8(c) | ✓ | router | `…[POST-/assignments-body0-worker]` | ✓ |
| R04 | same — add `SELLER` | yes, C8(d) | ✓ | router | `test_assignment_routes_reject_seller[POST-/assignments-body0-seller]` | ✓ |
| R05 | delete-route decorator (def) — drop `ADMIN` | yes, C8(e) | ✓ | router | `…[POST-/assignments/delete-body1-admin]` | ✓ |
| R06 | same — drop `MANAGER` | yes, C8(f) | ✓ | router | `…[POST-/assignments/delete-body1-manager]` | ✓ |
| R07 | same — drop `WORKER` | yes, C8(g) | ✓ | router | `…[POST-/assignments/delete-body1-worker]` | ✓ |
| R08 | same — add `SELLER` | yes, C8(h) | ✓ | router | `test_assignment_routes_reject_seller[POST-/assignments/delete-body1-seller]` | ✓ |
| R09 | `stock_report.py:_STRUCTURED_ASSIGNMENT_ERRORS` (def) — drop `StockAssignmentRefused` | yes, C8(i) | ✓ | router | `test_stock_assignment_refused_renders_code_and_details` → `code`/`details` dropped | ✓ |
| R10 | same — drop `StockAssignmentPropertyMismatch` | yes, C8(j) | ✓ | router | `test_stock_assignment_property_mismatch_renders_code_and_details` | ✓ |

## 4.2 Plan 8 — table 2: rows (forward coverage map)

`existing` = the implementer's test, reused unchanged. Test-file shorthand: **create** =
`tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py`;
**race** = `…_race.py`; **delete** = `…/test_delete_stock_task_assignments.py`;
**router** = `tests/unit/routers/api_v1/test_stock_report_router.py`; **ser** =
`tests/unit/domain/stock_report/test_stock_report_serializers.py`; **demand** =
`…/test_apply_stock_demand.py`.

| Row | Observable (boundary → exact outcome) | Test id | Source | If new/strengthened: what it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| C1(a) | `CR` with an absent row id → refused `stock_report_item_not_found` @0 | create::`test_stock_report_item_absent_is_refused` | existing | — | M01 | ARMED |
| C1(b) | R soft-deleted → same reason | create::`test_row_soft_deleted_is_refused` | existing | — | M02 | ARMED |
| C1(c) | R in a foreign workspace (same category, same criteria) → same reason | create::`test_c1c_row_in_a_foreign_workspace_is_refused` | new | the only cross-workspace **reference** in this file; no other test would notice `lock_stock_report_items` losing its tenancy filter | M03 | ARMED |
| C1(d) | absent `task_id` → `task_not_found` | create::`test_all_or_nothing_valid_entry_writes_nothing_when_a_later_entry_fails` | existing | — | M04 | ARMED-SHARED (the reason clause of the `details` equality fired) |
| C1(e) | absent `item_id` → `item_not_found` | create::`test_c1e_absent_item_id_is_refused_item_not_found` | new | that the item-existence check precedes the PRIMARY check; nothing else names an absent item | M05 | ARMED |
| C1(f) | RELATED link → `item_not_task_primary` | create::`test_related_item_is_refused_item_not_task_primary` | existing | — | M06 | ARMED |
| C1(g) | PRIMARY link with `removed_at` → `item_not_task_primary` | create::`test_c1g_retired_primary_link_is_refused_item_not_task_primary` | new | the `removed_at IS NULL` term specifically; C1(f)'s RELATED fixture leaves it untested | M07 | ARMED |
| C1(h) | T `failed` → `task_failed_or_cancelled` | create::`test_failed_task_is_refused[TaskStateEnum.FAILED]` | strengthened (parametrized) | — | M08 | ARMED |
| C1(i) | T `cancelled` → same reason | create::`test_failed_task_is_refused[TaskStateEnum.CANCELLED]` | new (second param) | the `CANCELLED` member of the refused set; the shipped test covered only `FAILED` (charter rule 2, enumerate) | M09 | ARMED |
| C1(j) | I active on another row → reason **and** `count_writes == 0` | create::`test_item_already_assigned_is_refused_before_any_write` | existing | — | M10 | ARMED (only the `count_writes` clause reddens, as the cell states) |
| C1(k) | I active on **R**, request names R → reason **and** `count_writes == 0` | create::`test_c1k_item_already_assigned_on_the_same_row_refuses_before_any_write` | new | the same-row case; the shipped test only built the other-row case, so the cell's own mutant had no fixture | M11 | ARMED |
| C1(l) | I `item_category_id NULL` → `item_has_no_category` | create::`test_item_has_no_category_is_refused` | existing | — | M12 | ARMED |
| C1(m) | I and R in different categories → `category_mismatch` | create::`test_category_mismatch_is_refused` | existing | — | M13 | ARMED |
| C1(n) | wrong category **and** failing properties → 422 `category_mismatch`, not 409 | create::`test_c1n_category_mismatch_precedes_the_property_matcher` | new | the phase-3-before-phase-4 precedence (U18); every other row satisfies at most one of the two predicates | M14 | ARMED |
| C1(o) | `[valid, task_not_found]` → one `details` element, nothing written | create::`test_all_or_nothing_valid_entry_writes_nothing_when_a_later_entry_fails` | existing | — | M15 | ARMED |
| C1(p) | resolved (T,I), retry on **R** → `already_processed_by_scanner` | create::`test_already_resolved_pair_is_refused_already_processed_by_scanner` | strengthened (fixture) | the shipped fixture retried on a *different* row whose criteria the item fails, so dropping the check produced a 409 rather than the second assignment the cell names | M16 | ARMED |
| C1(q) | `resolved_early` (T,I), retry on R2 → same reason ("on any row") | create::`test_c1q_resolved_early_on_another_row_is_refused_already_processed` | new | that the check is not keyed on the row; also the only `resolved_early` fixture on the create path | M17 | ARMED |
| C1(r) | resolved (T,I), **new** task T2 PRIMARY on I → created `in_queue` | create::`test_c1r_a_new_task_for_the_same_item_is_not_affected` | new | the pair key, from the permissive side — that §14F F9 does not blacklist the item | M18 (equivalent), **M18b** | ARMED (re-sited) |
| C1(s) | resolved **and soft-deleted** → created | create::`test_c1s_a_soft_deleted_resolved_assignment_does_not_refuse` | new | the `is_deleted` term of the processed lookup | M19 | ARMED |
| C1(t) | resolved **and** RELATED → `item_not_task_primary` | create::`test_c1t_item_not_task_primary_comes_before_already_processed` | new | MC-13's adjacent-pair order; both predicates hold at once | M20 | ARMED |
| C1(u) | resolved **and** T failed → `already_processed_by_scanner` | create::`test_c1u_already_processed_comes_before_task_failed_or_cancelled` | new | the other adjacent pair | M21 | ARMED |
| C2(a) | same item at 0 and 2 → both indices | create::`test_duplicate_item_in_batch_names_every_offending_index` | existing | — | M22 | ARMED |
| C2(b) | same task at 0 and 1 → both indices | create::`test_duplicate_task_in_batch_names_every_offending_index` | existing | — | M23 | ARMED |
| C2(c) | (a) plus an absent-task entry → one 422 with all three | create::`test_c2c_phase1_and_phase3_reasons_arrive_in_one_error` | new | that phase 1's reasons are *collected into* phase 3's error rather than raised early | M24 | ARMED |
| C3(a) | matcher failure without override → 409, exact `details`, failures sorted, nothing written | create::`test_property_mismatch_without_override_raises_409_with_sorted_failures` | existing | — | M25 (equivalent, sort), **M26** (details) | ARMED — the sort sub-check is `EQUIVALENT` by fixture (§6, fixture fold proposed) |
| C3(b) | resent with override → created, flag true, `in_queue`, `(1,0,0)` | create::`test_override_on_a_mismatching_entry_creates_with_flag_true` | existing | — | M27 | ARMED |
| C3(c) | override on a matching entry → flag false | create::`test_override_on_a_matching_entry_is_ignored` | existing | — | M28 | ARMED |
| C3(d) | after a 409, T cancelled, retry with override → 422 `task_failed_or_cancelled` | create::`test_c3d_retry_after_a_409_is_re_evaluated_from_scratch` | new | that the retry re-runs phase 3 before phase 4; nothing else sends an override into a refusal | M09 | ARMED-SHARED (M09 fired on this test's own `details` assertion) |
| C3(e) | unknown field, top level or entry → `ValidationError` 422 | create::`test_unknown_top_level_field_is_refused_422` | strengthened (fixture + second clause) | the shipped fixture also sent `entries: []`, so `extra="ignore"` left it green on C3(f)'s cause | M29 | ARMED |
| C3(f) | `{"entries": []}` → 422 | create::`test_empty_entries_is_refused_422` | existing | — | M30 | ARMED |
| C4(a) | T `pending` → `in_queue`, `(4,0,0)` | create::`test_creates_assignment_moves_counters_and_returns_full_read_shape` | existing | — | M31 | ARMED |
| C4(b) | T `assigned` → `in_queue`, `(4,0,0)` | create::`test_assignment_state_follows_the_task_state[…ASSIGNED…]` | new | the ASSIGNED cell of the state map; no shipped test left `pending` | M32 | ARMED |
| C4(c) | T `working` → `in_progress`, `(0,4,0)` | create::`test_assignment_state_follows_the_task_state[…WORKING…]` | new | the WORKING cell | M33a (equivalent), **M33b** | ARMED (re-sited) |
| C4(d) | T `stalled` → `in_progress` | create::`test_assignment_state_follows_the_task_state[…STALLED…]` | new | the STALLED cell | M34 | ARMED |
| C4(e) | T `ready` → `awaiting`, `(0,0,4)`, `G == 4`, `mem == G` | create::`test_c4e_ready_task_creates_awaiting_and_credits_the_goal` | new | the READY cell **and** the goal credit on creation — the only create-path test with a goal record | M35 | ARMED |
| C4(f) | T `resolved` → `awaiting`, `G == 4` | create::`test_resolved_task_may_still_be_assigned` | strengthened (goal added) | the `G == 4` clause, which the shipped test omitted (no goal record existed) | M36 | ARMED |
| C4(g) | I `quantity 8` → A quantity 8, `(8,0,0)` | create::`test_c4g_quantity_is_copied_from_the_item` | new | a quantity distinct from F0's 4, which is what separates "copied" from "constant" | M37 | ARMED |
| C4(h) | I quantity raw 0 → A quantity 1 | create::`test_quantity_floors_at_one` | existing | — | M38 | ARMED |
| C4(i) | any creation → `tasks.is_stock_assignment == true` | create::`test_creates_assignment_moves_counters_and_returns_full_read_shape` | existing | — | M39 | ARMED |
| C4(j) | any creation → `created_by_id == U`, `updated_* IS NULL` | create::`test_creates_assignment_moves_counters_and_returns_full_read_shape` | existing | — | M40 | ARMED |
| C4(k) | two entries supplied descending → response ascending by `item_id`, `(8,0,0)` | create::`test_two_entries_ascending_item_id_response_order_and_summed_counters` | existing | — | M41 (equivalent), **M41c** | ARMED (re-sited; double sort, backfill proposed) |
| C4(l) | response element = the fourteen keys with nested `item`/`task` | create::`…full_read_shape`; ser::`test_serialize_stock_task_assignment_returns_the_fourteen_keys_with_nested_item_and_task` | existing | — | M42 | ARMED (clause 1) / **BLOCKED-PLAN** (clause 2 — owner card 2) |
| C4(m) | demand create → authorship all NULL; demand quantity change → `updated_*` still NULL | demand::`test_c4m_demand_never_stamps_authorship_columns` | existing | — | M43, M44 | ARMED (one mutation per half, rule 12) |
| C5(a) | two sessions, same item, two rows → exactly one active; the loser refused `item_already_assigned`; winner's counters correct | race::`test_c5a_concurrent_create_on_the_same_item_leaves_exactly_one_active` | existing | — | M56 | **BLOCKED-PLAN** — the named mutation is equivalent at the row's stated outcome (owner card 1) |
| C5(b) | two sessions, two items, opposite request order → both complete, no deadlock, one active per item, both rows' counters correct | race::`test_c5b_two_sessions_crossing_two_items_never_deadlock` | new | the only test in the project that forces a crossing two-item acquisition; it is the row's outcome and it holds | M58 | **UNFORCEABLE** (owner's authorized fallback; structural check in §6) |
| C6(a) | `DL([A])` on `in_queue` → `(0,0,0)`, the three deletion stamps, flag false, `[assignment:deleted{in_queue}, row:updated]` | delete::`test_deletes_in_queue_assignment_zeroes_counters_and_clears_flag` | strengthened | `deleted_at == ctx.now` and the exact dispatched event list — both clauses of the outcome were unasserted | M47 | ARMED |
| C6(b) | `DL([A])` on `awaiting` credited → `G == 0`, `mem IS NULL` | delete::`test_c6b_deleting_an_awaiting_assignment_uncredits_the_goal` | new | the MC-5 uncredit on delete; no shipped delete test had a goal record | M48 | ARMED |
| C6(c) | `DL([A])` on `resolved` → no counter change, **no `:updated`**, `deleted` event, flag false | delete::`test_deleting_resolved_assignment_leaves_counters_untouched` | strengthened | the "no `:updated`" and flag clauses, both unasserted | M49 (equivalent), **M49b** | ARMED (re-sited; double guard) |
| C6(d) | `DL([A, absent])` → `NotFound`, A not deleted | delete::`test_absent_id_refuses_the_whole_batch` | existing | — | M50 | ARMED |
| C6(e) | `DL([A_deleted])` → `NotFound`, nothing written | delete::`test_already_deleted_id_is_not_found` | existing | — | M51 (equivalent), **M51b** | ARMED (re-sited) |
| C6(f) | `DL([A_foreign])` → `NotFound` | delete::`test_foreign_workspace_id_is_not_found` | existing | — | M52 | ARMED |
| C6(g) | T holds A (`in_queue`) and a `failed` B; `DL([A])` → flag stays true | delete::`test_c6g_flag_stays_true_while_another_assignment_of_the_task_survives` | new | that the flag predicate is "any non-deleted", not "any active"; every other delete test leaves the task empty | M53 | ARMED |
| C6(h) | `DL([A, B])` → both ids, one coalesced `:updated` | delete::`test_two_assignments_on_one_row_coalesce_to_one_updated_event` | existing | — | M54 | ARMED |
| C6(i) | `DL([A])` on `resolved_early` credited → no counter change, no `:updated`, `deleted{resolved_early}`, flag false, `G == 4`, `mem == G` kept | delete::`test_c6i_deleting_a_resolved_early_assignment_keeps_its_goal_credit` | new | the F1–F2/F4 "credit is never removed" rule on a terminal delete; nothing else asserts a *kept* credit | M55, M49b | ARMED (one mutation per half) |
| C7(a) | `CR` with two entries on R → two `:created`, one `:updated` with the final counters | create::`test_two_entries_on_one_row_dispatch_two_created_and_one_coalesced_updated` | existing | — | M45 | ARMED |
| C7(b) | `CR` failing at phase 3 → `capture_dispatch` empty | create::`test_refused_request_dispatches_nothing` | existing | — | M46 | **EQUIVALENT** — no placement of the dispatch call can make the row fail (§6) |
| C7(c) | drift + `DL([A])` → one repair record `inline:delete_assignments` | delete::`test_repair_record_carries_the_delete_assignments_trigger` | existing | — | M57 | ARMED |
| C8(a) | create route as admin → reached | router::`…permitted_roles[POST-/assignments-body0-admin]` | existing | — | R01 | ARMED |
| C8(b) | …as manager → reached | router::`…[POST-/assignments-body0-manager]` | existing | — | R02 | ARMED |
| C8(c) | …as worker → reached | router::`…[POST-/assignments-body0-worker]` | existing | — | R03 | ARMED |
| C8(d) | …as seller → 403 | router::`test_assignment_routes_reject_seller[POST-/assignments-body0-seller]` | existing | — | R04 | ARMED |
| C8(e) | delete route as admin → reached | router::`…[POST-/assignments/delete-body1-admin]` | existing | — | R05 | ARMED |
| C8(f) | …as manager → reached | router::`…[POST-/assignments/delete-body1-manager]` | existing | — | R06 | ARMED |
| C8(g) | …as worker → reached | router::`…[POST-/assignments/delete-body1-worker]` | existing | — | R07 | ARMED |
| C8(h) | …as seller → 403 | router::`test_assignment_routes_reject_seller[POST-/assignments/delete-body1-seller]` | existing | — | R08 | ARMED |
| C8(i) | faked `StockAssignmentRefused` → 422 with `code` + `details` | router::`test_stock_assignment_refused_renders_code_and_details` | existing | — | R09 | ARMED |
| C8(j) | faked `StockAssignmentPropertyMismatch` → 409 with `code` + `details` | router::`test_stock_assignment_property_mismatch_renders_code_and_details` | existing | — | R10 | ARMED |

## 4.3 Plan 8 — table 3: removed or consolidated tests

| Test id | Why redundant | Survivor | Survivor reddened under M-id |
|---|---|---|---|
| — | none removed | — | — |

One test was **renamed, not removed**: delete::`test_unknown_field_and_empty_client_ids_are_refused`
→ `test_empty_client_ids_is_refused`. Its old name claimed an unknown-field clause its body never
exercised (`DeleteStockTaskAssignmentsRequest` carries no `extra="forbid"`). Kept, declared as a
candidate criterion in §8.

---

## 4.4 Plan 11 — table 1: mutations

| M-id | Site (`file:symbol`, def/call) | Plan-named? (row) | Landed | Test file run | Observed red: test id → clause | Reverted |
|---|---|---|---|---|---|---|
| N01 | `delete_task.py` (call site) — remove the removal-hook loop | yes, C1(a) | ✓ | task_side | `test_c1a_deleting_task_removes_active_assignment_and_updates_counters` → `A.is_deleted`; all four tests in the file | ✓ |
| N02 | `delete_task.py` discovery (def) — restrict to `ACTIVE_ASSIGNMENT_STATES` | yes, C1(b) | ✓ | task_side | `test_c1b_deleting_task_removes_resolved_assignment_without_counter_change` → `A.is_deleted`; also C1(c)'s test | ✓ |
| N03 | `delete_task.py` removal loop (def) — take only the first found | yes, C1(c) | ✓ | task_side | `test_c1c_deleting_task_removes_every_non_deleted_assignment_of_the_task` → one of `a`/`b` survives | ✓ |
| N04 | `remove_item_from_task.py` (call site) — remove the PRIMARY-unlink removal loop | yes, C2(a) **and** C2(c) | ✓ | item_side | `test_c2a_unlinking_primary_item_removes_its_active_assignment` → `A.is_deleted`; **`test_c2c_swap_then_create_on_the_new_primary_succeeds` → the `CR` half** (the create is refused by the `IntegrityError` backstop), which is the bite the cell names; also C6(b)'s trigger test | ✓ |
| N05 | `remove_item_from_task.py` (def) — act on any role | yes, C2(b) | ✓ | item_side | **NO RED** — `EQUIVALENT`: the discovery query is keyed on `(task_id, item_id)`, so a RELATED item matches nothing whatever the role check says. Re-sited → N05b | ✓ |
| N05b | the role check **and** the `item_id` term of the discovery query | re-siting of C2(b) | ✓ | item_side | `test_c2b_unlinking_a_related_item_does_nothing_to_the_primarys_assignment` → `A.is_deleted is False` | ✓ |
| N07 | `delete_item.py` (def) — also soft-delete the item's tasks | yes, C3(a) | ✓ | item_side | `test_c3a_deleting_item_removes_its_active_assignment_task_untouched` → `task.is_deleted is False`. First run was green because the test read the Task from the identity map; the test now reads with `populate_existing` and the same mutant reddens | ✓ |
| N08 | `delete_item.py` discovery (call site) — restrict to `ACTIVE_ASSIGNMENT_STATES` | yes, C3(b) | ✓ | item_side | `test_c3b_deleting_item_leaves_a_failed_assignment_untouched_in_counters` → `A.is_deleted` | ✓ |
| N09 | `update_item.py:_update_item_in_session` (call site) — drop the guard call | yes, C4(a) | ✓ | category_guard | `test_c4a_changing_category_with_active_assignment_is_refused` → no `ConflictError`; also C4(d), C4(e) | ✓ |
| N10 | `update_item.py` (def) — compare request to stored without None-awareness | yes, C4(b) | ✓ | category_guard | **NO RED** — `EQUIVALENT`, exactly as owner card E declares (the no-op is guarded twice) | ✓ |
| N11 | `update_item.py` (def) — drop the `model_fields_set` term | yes, C4(c) | ✓ | category_guard | `test_c4c_changing_an_unrelated_field_with_active_assignment_is_allowed` → 409 on an unrelated field | ✓ |
| N12 | `_category_guard.py` (def) — treat `None → X` as no change | yes, C4(d) | ✓ | category_guard | `test_c4d_null_to_a_category_is_a_change` → no `ConflictError` | ✓ |
| N13 | `_category_guard.py` (def) — treat `X → None` as no change | yes, C4(e) | ✓ | category_guard | `test_c4e_a_category_to_null_is_a_change` → no `ConflictError` | ✓ |
| N14 | `_category_guard.py` (def) — drop the active-state filter | yes, C4(f) | ✓ | category_guard | `test_c4f_changing_category_of_a_resolved_only_assignment_is_allowed` → 409; also C4(i) | ✓ |
| N15 | `_category_guard.py` (def) — drop `is_deleted.is_(False)` | yes, C4(g) | ✓ | category_guard | `test_c4g_changing_category_of_a_soft_deleted_only_assignment_is_allowed` → 409 | ✓ |
| N16 | `_category_guard.py` (def) — hand-typed `state NOT IN (resolved, failed)` | yes, C4(i) | ✓ | category_guard | `test_c4i_changing_category_of_a_resolved_early_only_assignment_is_allowed` → 409 (§9 rule 16) | ✓ |
| N17 | `find_or_create_item.py` (def) — guard moved after the `_DIRECT_FIELDS` loop | yes, C5(a)-i | ✓ | category_guard | **NO RED** — `EQUIVALENT`: the rollback makes the order of writes before the refusal unobservable | ✓ |
| N18 | `_category_guard.py` (def) — commit before the refusal escapes ("raise outside the transaction") | yes, C5(a)-ii | ✓ | category_guard | `test_c5a_create_task_naming_a_new_category_for_an_actively_assigned_item_is_refused` → the task/note/customer counts in W | ✓ |
| N19 | `find_or_create_item.py` (def) — drop the `model_fields_set` term | yes, C5(c) | ✓ | category_guard | `test_c5c_create_task_omitting_category_with_active_assignment_is_allowed` → 409 | ✓ |
| N20 | `_category_guard.py` (def) — delete the active-assignment lookup, always refuse | yes, C5(d) | ✓ | category_guard | `test_c5d_no_assignment_at_all_category_change_through_create_task_behaves_as_today` → 409 instead of a created task; also C4(f)/(g)/(i) | ✓ |
| N21 | `find_or_create_item.py` (call site) — delete the guard call | yes, C5(e) | ✓ | category_guard | `test_c5e_find_or_create_item_directly_refuses_with_active_assignment` → no `ConflictError` (the items-route ctx, the bite the cell names); also C5(a)'s test | ✓ |
| N22 | `delete_task.py` (call site) — `trigger="manual"` | yes, C6(a) | ✓ | task_side | `test_c6a_repair_record_carries_the_delete_task_trigger` → `inline:delete_task` | ✓ |
| N23 | `remove_item_from_task.py` (call site) — `trigger="manual"` | yes, C6(b) | ✓ | item_side | `test_c6b_repair_record_carries_the_remove_item_from_task_trigger` | ✓ |
| N24 | `delete_item.py` (call site) — `trigger="manual"` | yes, C6(c) | ✓ | item_side | `test_c6c_repair_record_carries_the_delete_item_trigger` | ✓ |
| N25 | `remove_item_from_task.py` (call site) — drop the new Task lock | yes, C7(a) | ✓ | item_side | **NO RED** — no test observes it; the row is declared unforceable by the plan | ✓ |
| N26 | `delete_item.py` (def) — drop the new Item `FOR UPDATE` | yes, C7(b) | ✓ | item_side + removal_locks | item_side: no red. **removal_locks::`test_delete_item_locks_item_first_then_rows_then_assignments` → the MC-1 statement order** | ✓ |

## 4.5 Plan 11 — table 2: rows

Test-file shorthand: **task_side** = `…/test_task_side_removals.py`; **item_side** =
`…/test_item_side_removals.py`; **guard** = `…/test_category_guard.py`; **locks** =
`…/test_removal_locks.py`.

| Row | Observable (boundary → exact outcome) | Test id | Source | If new/strengthened: what it detects that nothing else did | M-id(s) | Disposition |
|---|---|---|---|---|---|---|
| C1(a) | `delete_task(T)` with A `awaiting` → T and A soft-deleted, `(0,0,0)`, `G == 0`, flag false, both stock events dispatched | task_side::`test_c1a_…` | strengthened | the task-flag clause and the dispatched stock events, neither asserted | N01 | ARMED |
| C1(b) | A `resolved`; `delete_task(T)` → A soft-deleted, counters unchanged, **no `:updated`**, flag false | task_side::`test_c1b_…` | strengthened | the "no `:updated`" and flag clauses | N02 | ARMED |
| C1(c) | T holds a `failed` A and an `in_queue` B → both soft-deleted, R2 `(0,0,0)`, R unchanged, flag false | task_side::`test_c1c_…` | strengthened | R's counters and the flag | N03 | ARMED |
| C2(a) | `remove_item_from_task(T, I)` → link retired, A soft-deleted, `(0,0,0)`, flag false, stock events dispatched | item_side::`test_c2a_…` | strengthened | the dispatched stock events | N04 | ARMED |
| C2(b) | unlink a RELATED J → A untouched, counters unchanged, **no stock event** | item_side::`test_c2b_…` | strengthened | the "no stock event" clause, and a fixture that makes the role check the only thing under test | N05 (equivalent), **N05b** | ARMED (re-sited) |
| C2(c) | unlink I, add J as PRIMARY → no non-deleted assignment for T, and `CR([J on R])` succeeds | item_side::`test_c2c_…` | strengthened (assertion order) | the removal assertion moved **after** the `CR`, so the shared mutation reaches this row's own bite instead of short-circuiting on C2(a)'s clause (rule 12 / L-28) | N04 | ARMED-SHARED (the `CR` half fired) |
| C3(a) | `delete_item(I)` with A `in_progress` → I and A soft-deleted, `(0,0,0)`, **T not deleted and its state unchanged**, flag false | item_side::`test_c3a_…` | strengthened (fresh read) | the Task is now read back from the database; the identity-mapped read could not see a Core-statement deletion, so the row could not fail | N07 | ARMED |
| C3(b) | A `failed`; `delete_item(I)` → A soft-deleted, counters unchanged | item_side::`test_c3b_…` | existing | — | N08 | ARMED |
| C4(a) | A active; `update_item(I, K2)` → `ConflictError` 409 with the exact sentence; category, snapshots and `updated_at` unchanged | guard::`test_c4a_…` | strengthened | the two snapshot columns, which the outcome names and the test omitted | N09 | ARMED |
| C4(b) | A active; `update_item(I, K)` (same) → allowed | guard::`test_c4b_setting_the_same_category_is_not_a_change` | new | the no-op path had no test at all; the row's own mutant is measured, not assumed | N10 | **EQUIVALENT** (owner card E — known-unarmed by ruling, not reopened) |
| C4(c) | A active; `update_item(I, designer="x")` → allowed | guard::`test_c4c_…` | existing | — | N11 | ARMED |
| C4(d) | category raw-set NULL, A active; `update_item(I, K)` → 409 | guard::`test_c4d_null_to_a_category_is_a_change` | new | the `None → X` direction of the None-awareness | N12 | ARMED |
| C4(e) | A active; `update_item(I, None)` → 409 | guard::`test_c4e_a_category_to_null_is_a_change` | new | the opposite direction (L-12: one mutant per direction) | N13 | ARMED |
| C4(f) | A `resolved` only → allowed, category changed | guard::`test_c4f_…` | existing | — | N14 | ARMED |
| C4(g) | A soft-deleted only → allowed | guard::`test_c4g_…` | existing | — | N15 | ARMED |
| ~~C4(h)~~ | WITHDRAWN (owner card F) — not in scope, counts toward nothing | — | — | — | — | WITHDRAWN |
| C4(i) | A `resolved_early` only → allowed, category changed | guard::`test_c4i_…` | existing | — | N16 | ARMED |
| C5(a) | `create_task` naming K2 for an actively assigned item → 409 with the same sentence; **no task row, no task note, no customer row**; I unchanged | guard::`test_c5a_…` | strengthened (second session) | the rollback clause, which the implementer correctly reported as unobservable inside `db_session`; the command now runs on a fresh `get_db_session()`, production's own topology | N17 (equivalent), **N18** | ARMED |
| C5(b) | same with K → task created, I unchanged | guard::`test_c5b_create_task_naming_the_same_category_is_allowed` | new | the no-op path through `create_task` had no test | — (deliberate blank) | **EQUIVALENT** (owner card E; not reopened) |
| C5(c) | category omitted from the item payload → task created, category unchanged | guard::`test_c5c_…` | existing | — | N19 | ARMED |
| C5(d) | item with **no** assignment; `create_task` with K2 → task created, I in K2 | guard::`test_c5d_…` | existing | — | N20 | ARMED |
| C5(e) | `find_or_create_item` via the items-route ctx with a different category → 409 | guard::`test_c5e_…` | existing | — | N21 | ARMED |
| C6(a) | drift + `delete_task(T)` → one repair record `inline:delete_task` | task_side::`test_c6a_…` | new | the trigger string at `delete_task`'s call site; the implementer wired it but tested none of the three | N22 | ARMED |
| C6(b) | drift + `remove_item_from_task(T, I)` → `inline:remove_item_from_task` | item_side::`test_c6b_…` | new | the trigger string at that call site | N23 | ARMED |
| C6(c) | drift + `delete_item(I)` → `inline:delete_item` | item_side::`test_c6c_…` | new | the trigger string at that call site | N24 | ARMED |
| C7(a) | unlink vs create, barrier-released → no active assignment for a non-PRIMARY item | — (none; plan declares the interleaving unforceable) | — | — | N25 | **UNFORCEABLE** — reviewer's structural check: `remove_item_from_task.py` takes `lock_tasks(..., {request.task_id})` *before* its discovery block and before the `TaskItem` write. No automated instrument covers it (`test_removal_locks.py` covers `delete_task` and `delete_item` only) |
| C7(b) | delete_item vs create, barrier-released → no active assignment on a deleted item | locks::`test_delete_item_locks_item_first_then_rows_then_assignments` (structural instrument only) | existing | — | N26 | **UNFORCEABLE** — but the lock statement itself is observed: dropping it reddens the MC-1 statement-order test |

## 4.6 Plan 11 — table 3: removed or consolidated tests

| Test id | Why redundant | Survivor | Survivor reddened under M-id |
|---|---|---|---|
| — | none removed | — | — |

---

## 5. Arithmetic (derived by command, printed)

**Rows in scope = sum of dispositions.**

Plan 8, by criterion (script over the criteria table's `^| C` lines):
`C1:21 + C2:3 + C3:6 + C4:13 + C5:2 + C6:9 + C7:3 + C8:10 = 67`.
Dispositions, one per row, summing to 67:
`ARMED 61 · ARMED-SHARED 2 (C1(d), C3(d)) · EQUIVALENT 1 (C7(b)) · UNFORCEABLE 1 (C5(b)) ·
BLOCKED-PLAN 2 (C5(a) whole row; C4(l) — its clause 1 is armed by M42, its clause 2 is the
blocked half and the row is counted here, once) · BLOCKED-PRODUCTION 0`.
`61 + 2 + 1 + 1 + 2 = 67`.

Plan 11: `C1:3 + C2:3 + C3:2 + C4:9 + C5:5 + C6:3 + C7:2 = 27`, of which **C4(h) is WITHDRAWN**
→ **26 live rows, 26 dispositions**: `ARMED 21 · ARMED-SHARED 1 (C2(c)) · EQUIVALENT 2 (C4(b),
C5(b)) · UNFORCEABLE 2 (C7(a), C7(b)) · BLOCKED-* 0`.

**Plan-named mutations: declared == executed.**

Plan 8 declared, per criterion (one per named cell; a cell naming two distinct defects counts two —
C3(a) "unsorted failures; missing `details`", C4(m) "(i) … (ii) …", C6(i) "subtract q on delete /
emit `:updated`"; C8(a)–(d) and C8(e)–(h) are four cells each; **C3(d)** is a deliberate blank and
declares none):
`C1:21 + C2:3 + C3:6 + C4:14 + C5:2 + C6:10 + C7:3 + C8:10 = 69`.
Executed: 69 (every cell applied at its named site and run at L1). Distinct mutant *edits* = 68,
because C6(c) and C6(i)-ii are the same edit (M49/M49b) — measured to reach both rows' own
assertions, per §9 rule 8.

Plan 11 declared (**C5(b)** is a deliberate blank, **C4(h)** withdrawn; C5(a) names two):
`C1:3 + C2:3 + C3:2 + C4:8 + C5:5 + C6:3 + C7:2 = 26`. Executed: 26. Distinct edits = 25, because
C2(a) and C2(c) are the same edit (N04), measured to reach C2(c)'s own bite.

**Total declared 95 == total executed 95.** Plus 8 recorded extra runs (re-sitings and two
re-runs after a test fix): M18b, M33b, M41c, M49b, M51b, N05b, N07 (re-run), N10 (re-run).
**Total mutation runs: 103.**

**Reverse map: tests in the phase's files == tests referenced by table 2.**

| File | Tests | All traced? |
|---|---|---|
| create | 40 | yes |
| race | 2 | yes |
| delete | 11 | 10 to rows + 1 candidate criterion (`test_empty_client_ids_is_refused`) |
| task_side | 4 | yes |
| item_side | 8 | 7 to rows + 1 candidate criterion (`test_delete_item_absent_raises_not_found`) |
| guard | 13 | yes |
| locks | 2 | 1 is C7(b)'s structural instrument; 1 (`test_delete_task_locks_…`) is a candidate criterion |
| ser | 4 | 1 to C4(l); 3 are §9 rule 18 signature pins for `serialize_item_compact` / `serialize_task_compact` (declared, §8) |
| router (assignment rows only) | 10 | yes |
| demand (C4(m) only) | 1 | yes |
| **total in scope** | **95** | 3 candidate criteria, 3 rule-18 pins, 0 silent orphans |

**Pass-count delta = new − removed = 29 − 0 = 29.** Per file: create +18 (14 functions + 1 extra
`failed/cancelled` param + 3 state-map params), race +1, delete +3, task_side +1, item_side +2,
guard +4.

## 6. Blocked and unarmable rows, by class

**BLOCKED-PRODUCTION: none.** Production was correct under every probe. Nothing returns to the
implementer.

**BLOCKED-PLAN (2).**
- **plan 8 C5(a)** — owner card 1. Measured (M56): removing the Item lock leaves the test green,
  because both sessions then reach the INSERT, `uix_stock_task_assignments_item_active` rejects
  the second, and the `IntegrityError` backstop answers the same 422 with the same reason. The
  row's outcome cannot distinguish the lock from the constraint. The plan's own §7 already says
  the loser's answer should be the **pre-check**; the clause that would say so
  (`count_writes(statements, {"stock_task_assignments"}) == 0` for the loser) is an outcome
  change and is the owner's.
- **plan 8 C4(l), second clause** — owner card 2. `GET /items/{client_id}/assignments` is phase
  13 and does not exist; the key-set comparison has no second operand in this batch. Clause 1
  (the fourteen keys with nested `item`/`task`) is ARMED by M42 on two surfaces.

**EQUIVALENT (3 rows, plus 7 cells re-sited).**
- **plan 8 C7(b)** — a phase-3 refusal raises before any dispatch statement and `events` is still
  empty at that point, so no placement of the dispatch call can produce a non-empty
  `capture_dispatch` list. The row is structurally true; its test can still fail if the command
  ever dispatched unconditionally, which is what it guards.
- **plan 11 C4(b)** and **C5(b)** — the owner's card E ruling, re-measured for C4(b) (N10, green)
  and honoured for C5(b) (deliberate blank). Not reopened.
- Cells measured equivalent and then re-sited (both runs in table 1): plan 8 C1(r) (M18→M18b),
  C4(c) (M33a→M33b), C4(k) (M41→M41c), C6(c)/C6(i)-ii (M49→M49b), C6(e) (M51→M51b); plan 11
  C2(b) (N05→N05b), C5(a)-i (N17, no re-site needed — C5(a)-ii arms the row).

**UNFORCEABLE (3).**
- **plan 8 C5(b)** — the owner's authorized fallback, taken on measurement. The test is built and
  green; the named mutation (delete `.order_by(model.client_id)` from `_locks.py:_lock`) leaves
  it green because the `IN` list is still `sorted(client_ids)` and both sessions therefore receive
  the rows in the same physical order, so the crossing pair does not deadlock. *Reviewer's
  structural check:* `_locks.py:22-41` — every lock class is acquired by a single
  `SELECT … WHERE client_id IN (…) ORDER BY client_id … FOR UPDATE`, and
  `create_stock_task_assignments.py` calls `lock_items` once with a set, so acquisition order is
  a property of that one statement, not of the request.
- **plan 11 C7(a)** and **C7(b)** — declared unforceable by the plan; §3B says the tester does not
  try to make them bite. Both named mutations were still executed and recorded. C7(b)'s lock has
  an automated instrument (`test_removal_locks.py`); C7(a)'s does not — see table 4.5.

**Unarmed sub-check (1), routed as a fixture fold, not a card.**
- **plan 8 C3(a), "failures sorted by key"** — unarmable with the row's own fixture. The criteria
  live in a JSONB column; Postgres stores JSONB keys by (length, then bytewise), and for
  `quantity` / `upholstery` / `wood_group` that order is already alphabetical. Measured directly:
  `'{"wood_group":1,"quantity":2,"upholstery":3}'::jsonb` renders
  `{"quantity": …, "upholstery": …, "wood_group": …}`. So `sorted(failures, key=…)` is a no-op
  here and M25 is equivalent (L-14: an ordering row needs a fixture ordered *against* its key).
  A discriminating fixture needs a short key late in the alphabet — e.g. `zone` beside
  `upholstery`, which JSONB stores as `zone, upholstery`. That is a **fixture cell**, so it folds
  to the coordinator (§3B class 3), not to the owner. C3(a)'s other sub-check is ARMED (M26).

## 7. Removed tests

None. One rename (§4.3).

## 8. Candidate criteria (charter trace chain link 3)

1. **`delete_stock_task_assignments`'s request contract is pinned by no row.** §9 rule 18 asks
   every signature registered in §6.5 to be pinned by a row in its own plan;
   `DeleteStockTaskAssignmentsRequest` is registered and no row asserts its shape or the error it
   raises. The implementer's `test_empty_client_ids_is_refused` does exactly that and is kept
   against this candidate. *Note for the coordinator:* the create request forbids unknown fields
   and the delete request does not — an asymmetry no row decides.
2. **`delete_item` still raises `NotFound` for an absent id after the new `FOR UPDATE` load.**
   `test_delete_item_absent_raises_not_found` traces to no row; it guards the `scalar_one_or_none`
   check surviving the lock this phase added to that select. Cheap and real; kept against this
   candidate.
3. **`delete_task`'s MC-1 statement order.** `test_delete_task_locks_rows_then_assignments_after_the_existing_task_lock`
   traces to no lettered row (plan 11 C7 names `remove_item_from_task` and `delete_item` only).
   It is the same instrument C7(b) uses. Kept against this candidate.
4. **Category change plus another field in one request** (the implementer's §8 item 4; I agree
   after reading both call sites). `update_item.py` and `find_or_create_item.py` place the
   guard's `populate_existing` re-select **before** the `_DIRECT_FIELDS` loop, because running it
   after would silently discard every other field change in a request that also changes the
   category. No row in either plan sends both in one request, so a mutation reintroducing the
   wrong order is caught by nothing. *Suggested row:* `update_item(I, item_category_id=K2,
   designer="x")` on an item with **no** assignment → both the category and `designer` are
   persisted. Named mutation: move the guard block after the `_DIRECT_FIELDS` loop → `designer`
   is discarded.
5. **The HTTP surface's error envelope is not uniform** (the implementer's §8 item 3). The router
   validates with its own FastAPI body models, so an unknown top-level field over HTTP returns
   FastAPI's validation error, not `ValidationError`/`StockAssignmentRefused`. C3(e) is proven at
   the command boundary, which is what the plan's own fixture shorthand specifies. Recording it
   because the frontend contract (phase 14) will describe one envelope.

## 9. Proposed plan-cell backfills (the coordinator folds these; I edited no cell)

| Plan / row | Current cell | Proposed |
|---|---|---|
| 8 C3(d) | deliberate blank (class 2, "no site exists") | **Sited on real code:** drop `CANCELLED` from `_TASK_FAILED_OR_CANCELLED_STATES` (`create_stock_task_assignments.py`, definition site) — the same mutation as C1(i); measured to fire on C3(d)'s own `details` assertion |
| 8 C1(r) | "key the check on `item_id` alone → refused" | Name both halves: drop `StockTaskAssignment.task_id.in_(task_ids)` from `_lookup_processed_pairs` **and** key the membership test on `item_id` (definition site). The membership change alone is inert |
| 8 C4(c) | "write counters directly" | Name a site. Proposed: set the `TaskStateEnum.WORKING` cell of `ASSIGNMENT_STATE_BY_TASK_STATE` (`state_map.py:7`, definition site) to `IN_QUEUE` — it kills both of the row's clauses. Record that the §9 rule 3 ORM-write shape is equivalent at this row's boundary (measured, M33a) |
| 8 C4(k) | "drop the ascending-`item_id` sort at the phase-5 write loop" | "drop **both** ascending-`item_id` sorts — the phase-5 write loop (`:244`) and the response build (`:309`). Either alone is an equivalent mutant." |
| 8 C6(c) / C6(i) | "remove the `if any(value != 0 …)` guard" / "emit `:updated`" | Add the second guard: "…**and** the `event.extra == initial` drop in `coalesce_stock_report_events` (`_events.py`, definition site). Either alone is equivalent." |
| 8 C6(e) | "drop the `is_deleted.is_(False)` predicate from the delete command's discovery/re-read" | Make "and" explicit: the discovery filter **and** the post-lock re-read's `if assignment.is_deleted` extend. Dropping only the discovery filter is equivalent — the re-read catches it |
| 8 C3(a) fixture | `{"quantity":["4"],"upholstery":["down"],"wood_group":["teak"]}` | Add or substitute a **short, late-alphabet** criterion key (e.g. `zone`) so the JSONB storage order differs from alphabetical; otherwise the "sorted failures" sub-check cannot fail (L-14). Fixture cell → coordinator fold |
| 8 C5(a) | outcome as written | Owner card 1 — add the `count_writes == 0` clause for the losing call |
| 8 C4(l) | second clause | Owner card 2 — move to plan 13 |
| 11 C2(b) | "act on any role" | Name the load-bearing term: the role check **and** the `StockTaskAssignment.item_id == request.item_id` term of the hook's discovery query (`remove_item_from_task.py`, definition site). The role check alone is equivalent |
| 11 C5(a) | "guard after the first write / raise outside the transaction" | Keep both but mark the first **expected equivalent** (the rollback hides write order, measured N17). The arming half is the second: proposed concrete site — the refusal escaping an already-committed transaction (`_category_guard.py`, definition site) |
| 11 C7(a) | "drop the new Task lock — interleaving not forced; reviewer verifies the lock statement" | Note that, unlike C7(b), **no automated instrument observes it**: `test_removal_locks.py` covers `delete_task` and `delete_item` only. Either add `remove_item_from_task` to that file (one case) or state that C7(a)'s check is a reading check |

## 10. What variation I did **not** spend

So the reviewer knows where its budget buys something new:

- **One mutant shape per site.** Where a cell named a defect, I ran that defect and stopped; I did
  not run a second mutant of the same sign at the same site, and I did not invent extra mutants
  for rows already armed.
- **No `TZ`, locale or clock variation.** Nothing in these two plans depends on a timezone; the
  only time assertions are `updated_at IS NULL`, `deleted_at == ctx.now` and `created_at`
  serialization.
- **No worker-matrix or repetition variation.** The two-session rows ran once each, forced by a
  barrier with bounded waits. No test was looped for confidence (doctrine "determinism comes from
  the construction").
- **No boundary sweep on quantities.** C4(g) uses 8 and C4(h) uses 0; I did not add 1, 2 or large
  values.
- **No permutation of batch sizes.** C2(c) uses four entries because the row names four; I did
  not generalise to N.
- **No cross-phase regression sweep.** I ran L1 per file and exactly one L4. The expected
  collateral reds under the `state_map.py` and `quantity` mutants (plan 8 §7) were observed inside
  the create file only; I did not run plans 1–7's suites under those probes, because §7 already
  records what they do.
- **Nothing on the HTTP surface beyond the role cells and the two renderings.** C3(e)'s
  router-level asymmetry is a candidate criterion, not a test I added.
- **Untouched by me and therefore untested in this round:** the `IntegrityError` backstop's own
  happy path (plan 8 §7 says the reviewer checks it structurally), and every phase-9/10/12/13
  surface.

## 11. Write perimeter

**Files I changed and kept (all tests; no production file):**

```
app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py
app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments_race.py
app/tests/integration/services/commands/stock_report/test_delete_stock_task_assignments.py
app/tests/integration/services/commands/stock_report/test_task_side_removals.py
app/tests/integration/services/commands/stock_report/test_item_side_removals.py
app/tests/integration/services/commands/stock_report/test_category_guard.py
docs/architecture/under_construction/implementation/stock_report/plans/plan_8.md      (Review log only)
docs/architecture/under_construction/implementation/stock_report/plans/plan_11.md     (Review log only)
docs/architecture/under_construction/implementation/stock_report/handoffs/tester/2026-09-21_batch_C1_test_1_handoff.md
```

**Files a mutation probe touched and reverted (listed separately; every one verified
byte-identical with `git diff --quiet` before the next probe):**

In this batch's own perimeter:
```
app/beyo_manager/services/commands/stock_report/create_stock_task_assignments.py
app/beyo_manager/services/commands/stock_report/delete_stock_task_assignments.py
app/beyo_manager/services/commands/stock_report/requests/__init__.py
app/beyo_manager/services/commands/stock_report/_category_guard.py
app/beyo_manager/services/commands/stock_report/_events.py
app/beyo_manager/domain/stock_report/serializers.py
app/beyo_manager/routers/api_v1/stock_report.py
app/beyo_manager/services/commands/tasks/delete_task.py
app/beyo_manager/services/commands/tasks/remove_item_from_task.py
app/beyo_manager/services/commands/items/delete_item.py
app/beyo_manager/services/commands/items/update_item.py
app/beyo_manager/services/commands/items/find_or_create_item.py
```

Out-of-perimeter, all authorized by plan 8 §7:
```
app/beyo_manager/domain/stock_report/state_map.py                      (plan 1 — C4(a),(b),(c re-site),(d),(e))
app/beyo_manager/domain/stock_report/criteria_matcher.py               (plan 2 — C3(a)-i)
app/beyo_manager/services/commands/stock_report/_locks.py              (plan 3 — C1(c), C5(b))
app/beyo_manager/services/queries/stock_report/consistency.py          (plan 3 — C6(g))
app/beyo_manager/services/commands/stock_report/_move_assignment.py    (plan 4 — C4(c), C6(c), C6(i))
app/beyo_manager/services/commands/stock_report/_remove_assignment.py  (plan 4 — C6(a))
app/beyo_manager/services/commands/stock_report/_goal_credit.py        (plan 5 — C6(b))
app/beyo_manager/services/commands/stock_report/apply_stock_demand.py  (plan 7 — C4(m))
```

`criteria_matcher.py` is the one file **not** listed in plan 8 §7's perimeter extension: C3(a)'s
"unsorted failures" mutation lives in plan 2's matcher, not in this phase's files. Reported here
rather than declined (L-25/L-31); the probe was applied and reverted like the others, and the
§7 list should gain it at the fold.

**Tooling:** the probe driver and the specs live in the session scratchpad
(`.../scratchpad/mut.py`, `mut2.py`, `spec_*.json`), outside the repository; nothing was written
into the project tree.
