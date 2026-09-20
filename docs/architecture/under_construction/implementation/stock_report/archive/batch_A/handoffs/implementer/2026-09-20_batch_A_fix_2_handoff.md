---
plan: batch A (1, 2, 3)
role: implement
round: batch_A-fix-2
state: IMPLEMENTED
date: 2026-09-20
actor: Codex
tree: fbf6ca3 + worktree fingerprint dd7867bc186ab255823236b43781dca04afb066b
---

# Batch A fix round 2 handoff

## 1. Gate check record

- `planning/intention.md` begins `status: RATIFIED` (round 9).
- `master_plan.md` §4A shows batch A `FIX_PROMPT_READY` for this prompt.
- `git status --porcelain` was empty at entry.
- `983d774` is an ancestor of `HEAD` (`fbf6ca3`).
- Architecture Graph status was read: initialized and valid, 211 nodes / 327 edges, no diagnostics;
  no graph write was made because the prompt forbids it.

## 2. Coverage map

Each plan-3 criterion row is mapped below. “Exact” means the test asserts the row's specified
outcome shape; “weaker” would mean only a subset, and none of the rows below is knowingly weaker.

- C1(a) → `test_counter_and_signature_divergences_are_reported` (queue counter exact values).
- C1(b) → `test_active_counter_divergence_kinds_are_reported[ in_progress ]` (exact values).
- C1(c) → `test_active_counter_divergence_kinds_are_reported[ awaiting ]` (exact values).
- C1(d) → `test_task_flag_divergence_is_reported_when_assignment_is_missing` (exact true→false values).
- C1(e) → `test_counter_and_signature_divergences_are_reported` (exact false→true task flag).
- C1(f) → `test_order_density_reports_only_the_row_that_needs_renumbering` (exact row and no extra rows).
- C1(g) → `test_null_priority_order_appends_after_the_group_maximum` and
  `test_null_priority_order_reports_after_sparse_group_maximum` (exact dense and sparse expectations).
- C1(h) → `test_null_priority_order_is_reported_when_priority_is_missing` (exact values).
- C1(i) → `test_goal_signature_and_density_divergences_are_reported` (exact goal tuple).
- C1(j) → `test_goal_signature_and_density_divergences_are_reported` (exact signature tuple).
- C1(k) → `test_consistency_does_not_report_foreign_workspace_drift` (exact `[]`; all ten drift kinds
  are planted in the foreign workspace and the five filter mutations each redden it).
- C1(l) → `test_resolved_early_is_terminal_but_still_counts_toward_goal_total` (exact `[]`).
- C2(a) → `test_consistency_service_returns_workspace_timestamp_and_divergences` (exact row snapshots
  before/after and envelope).
- C2(b) → `test_goal_signature_and_density_divergences_are_reported` (exact sorted kind order).
- C2(c) → `test_consistency_service_returns_workspace_timestamp_and_divergences` (exact envelope).
- C3(a) → `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change` (exact record tuple,
  repaired divergence, and clean check).
- C3(b) → `test_manual_repair_fixes_each_active_counter_and_records_exact_fields[ in_progress ]` (exact).
- C3(c) → `test_manual_repair_fixes_each_active_counter_and_records_exact_fields[ awaiting ]` (exact).
- C3(d) → `test_manual_repair_clears_false_positive_task_flag` (full task record tuple, flag false, clean check).
- C3(e) → `test_manual_repair_fixes_counter_and_task_flag_and_records_each_change` (exact false→true tuple).
- C3(f) → `test_repair_records_one_net_change_per_priority_order_field` (exact group record and one net change).
- C3(g) → `test_repair_records_one_net_change_per_priority_order_field` (exact item NULL→3 record).
- C3(h) → `test_manual_repair_clears_priority_nullness_and_records_one_item_change` (exact 1→NULL record).
- C3(i) → `test_manual_repair_fixes_goal_total_and_writes_history_record` (exact history record).
- C4(a) → `test_manual_repair_leaves_signature_divergence_unrepaired` (exact not-repaired/no-record outcome).
- C5(a) → `test_clean_manual_repair_makes_no_stock_writes_or_events` (exact no-op/write count/events).
- C6(a) → `test_repair_records_one_net_change_per_priority_order_field` (exact one record per target/field).
- C6(b) → `test_task_flag_repair_does_not_change_task_stamps` (exact unchanged task stamps).
- C6(c) → `test_counter_repair_stamps_only_the_changed_stock_report_row` (exact changed/unchanged stamps).
- C6(d) → `test_density_repair_stamps_only_the_renumbered_row` (exact changed/unchanged stamps).
- C6(e) → `test_repair_dispatches_only_changed_stock_report_rows` (exact one row event and payload).
- C6(f) → `test_repair_records_one_net_change_per_priority_order_field` (SQL NULL, not text NULL).
- C7(a) → `test_assert_stock_report_clean_rejects_a_stray_repair_record` (exact raised assertion).
- C7(b) → `test_clean_seed_has_no_stock_report_divergences` (clean helper passes).
- C8(a) → `test_stock_report_routes_reach_service_for_permitted_roles[GET-admin]` (exact reached/200).
- C8(b) → `test_stock_report_routes_reach_service_for_permitted_roles[GET-manager]` (exact reached/200).
- C8(c) → `test_stock_report_routes_reject_non_manager_roles[GET-worker]` (exact 403/not reached).
- C8(d) → `test_stock_report_routes_reject_non_manager_roles[GET-seller]` (exact 403/not reached).
- C8(e) → `test_stock_report_routes_reach_service_for_permitted_roles[POST-admin]` (exact reached/200).
- C8(f) → `test_stock_report_routes_reach_service_for_permitted_roles[POST-manager]` (exact reached/200).
- C8(g) → `test_stock_report_routes_reject_non_manager_roles[POST-worker]` (exact 403/not reached).
- C8(h) → `test_stock_report_routes_reject_non_manager_roles[POST-seller]` (exact 403/not reached).

The reverse map is clean: every test in the two touched criterion files discharges a listed row or is
the C1(k) fixture/helper required to arm that row. The deleted schema comparison test is the duplicate
owned by plan 1 C2(a), not an orphan criterion.

## 3. F-R1 — workspace filter and C1(k)

Production changes:

- `consistency.py::expected_task_flag` is now
  `expected_task_flag(session, workspace_id, task_id)` and includes
  `StockTaskAssignment.workspace_id == workspace_id` in its `WHERE`.
- `compute_stock_report_divergences` passes `workspace_id` to the helper.
- `_task_flag.py::recompute_task_stock_flag` carries `workspace_id` through to the helper.

C1(k) now builds clean own-workspace rows/history plus foreign counter (all three active states),
signature, goal-total, task-flag, order-density, and nullness drift. Cross-workspace assignment rows
reference own rows/history/task where necessary to make the counter, goal, and task filters observable;
the normal check for the own workspace returns exactly `[]`.

The five named filter mutations were each applied, run, observed red, and reverted:

1. `stock_report_items` select — `test_consistency_does_not_report_foreign_workspace_drift` failed
   with foreign row divergences.
2. `stock_report_history_records` select — the same test failed with the foreign goal-total drift.
3. `tasks` select — the same test failed with a foreign task-flag divergence.
4. `_recompute_row_counters_for_workspace` — the same test failed with foreign counter leakage into
   own rows.
5. `_recompute_goal_totals_for_workspace` — the same test failed with foreign credit leakage into
   the own history total.

## 4. F-R2 — task repair record

`test_manual_repair_clears_false_positive_task_flag` now asserts the full record tuple:
`(task, T, is_stock_assignment, "true", "false", manual, U, ctx.now)` and then asserts
`compute_stock_report_divergences(...) == []`.

The named mutation hard-coding the task record's `recomputed_value` to `"true"` reddened that test at
the repair-record assertion.

## 5. F-R3 — duplicate criterion

Deleted `test_consistency_matches_migrated_worker_schema` from
`app/tests/integration/services/queries/stock_report/test_consistency_check.py`. It was byte-for-byte
the plan-1 C2(a) test in `test_stock_report_schema.py`; plan 1 remains the sole owner.

## 6. Mutation ledger

Declared = 7 and executed = 7: C1(k) five filter sites (5) + F-R2 task record value (1) + the
workspace predicate guarding the changed `expected_task_flag` signature (1).

| Site and hypothesis | Scope / command | Tree | Observed result |
|---|---|---|---|
| `consistency.py` stock-report-item select: remove workspace predicate | L1 C1(k) test | `fbf6ca3` + temporary mutation | RED: foreign row divergence assertion |
| `consistency.py` history select: remove workspace predicate | L1 C1(k) test | `fbf6ca3` + temporary mutation | RED: foreign goal-total divergence |
| `consistency.py` task select: remove workspace predicate | L1 C1(k) test | `fbf6ca3` + temporary mutation | RED: foreign task-flag divergence |
| `consistency.py::_recompute_row_counters_for_workspace`: remove workspace predicate | L1 C1(k) test | `fbf6ca3` + temporary mutation | RED: counter leakage into own row |
| `consistency.py::_recompute_goal_totals_for_workspace`: remove workspace predicate | L1 C1(k) test | `fbf6ca3` + temporary mutation | RED: goal-credit leakage |
| `repair_stock_report.py`: hard-code task `recomputed_value` to `"true"` | L1 C3(d) test | `fbf6ca3` + temporary mutation | RED: exact record assertion |
| `consistency.py::expected_task_flag`: remove workspace predicate | L1 C1(k) test | `fbf6ca3` + temporary mutation | RED: cross-workspace task assignment leaks |

Every mutation was reverted; final diff contains no probe-only production change.

## 7. Test stamps and baseline comparison

The pre-edit targeted baseline was `34 passed` on `fbf6ca3`. After the intentional duplicate-test
deletion, the touched L1 files passed `33 passed`.

- L1: `PYTHONPATH=. pytest -q tests/integration/services/queries/stock_report/test_consistency_check.py tests/integration/services/commands/stock_report/test_repair_stock_report.py` — **33 passed**; tree `fbf6ca3` plus worktree fingerprint `dd7867bc186ab255823236b43781dca04afb066b`.
- L2: `PYTHONPATH=. pytest tests/unit/domain/stock_report tests/integration/models/stock_report/test_stock_report_schema.py tests/integration/services/queries/stock_report tests/integration/services/commands/stock_report tests/integration/services/commands/reset tests/integration/helpers/test_stock_report_helper.py -q` — **154 passed**; tree `fbf6ca3` plus worktree fingerprint `dd7867bc186ab255823236b43781dca04afb066b`. The prior 155 count is 154 after the explicitly deleted duplicate.
- L4: `PYTHONPATH=. pytest -m 'not e2e' --tb=no -q` — **21 failed / 3265 passed / 1 skipped / 2 warnings** in 65.78s; same 21 failure IDs as the §10 baseline, with no new or missing ID; tree `fbf6ca3` plus worktree fingerprint `dd7867bc186ab255823236b43781dca04afb066b`.

The 21 failure IDs are exactly the archive's §3 list: the two Shopify dimension migrations, sign-in role
name, three upholstery inventory cases, two bootstrap cases, two item-router cases, two item-position
cases, two working-section batch cases, two working-section ordering cases, two audit-log cases, worker
stats split, case-type serializer, and the two remaining item-router/upholstery router cases as
enumerated there. Set comparison was bidirectional: current minus baseline = `∅`; baseline minus
current = `∅`.

Ruff on all touched Python files and `git diff --check` both passed.

## 8. Write perimeter and commits

Entry status was empty. The cycle-scoped applied perimeter is:

- `app/beyo_manager/services/queries/stock_report/consistency.py` — production fix.
- `app/beyo_manager/services/commands/stock_report/_task_flag.py` — caller signature threading.
- `app/tests/integration/services/queries/stock_report/test_consistency_check.py` — C1(k) fixture,
  helper, and duplicate-test deletion.
- `app/tests/integration/services/commands/stock_report/test_repair_stock_report.py` — C3(d) assertions.
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_1.md` — one review-log entry.
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_2.md` — one review-log entry.
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_3.md` — one review-log entry.
- this handoff file.

Mutation probes touched the first four code/test files above only; all probe edits were applied and
reverted byte-for-byte before the final stamps. No master plan, intention, Scanner repository,
Scanner handoff, tracker row, role prompt, `.archgraph` file, or unrelated test was changed.

`git diff --stat 983d774..` was checked separately from the cycle status because that range includes
the orchestrator's pre-existing prompt/master-plan/reviewer-handoff commits. The cycle status and
final perimeter list above are the authoritative check for this session. The final checkpoint commit
uses the required message: `CHECKPOINT (not approved): stock_report batch A fix 2 — workspace isolation,
repair record, and duplicate criterion`.

## 9. Commits

- Final checkpoint: `5dbb9eb11dd8ebc0275ba24a4543f0a83f84612f`, with the required message above.
- This handoff-only record update is the closing documentation commit; it does not alter the tested
  production or test tree.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The owner ruling restoring the workspace filter was already supplied in the prompt and was
implemented verbatim.
