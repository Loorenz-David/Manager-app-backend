---
plan: 2
role: implementer
round: 2
state: IMPLEMENTED
date: 2026-08-20
actor: Codex
project: live_clock_for_working_time_economics
---

The phase-2 proof gaps are closed in the declared test perimeter. The production
implementation was not changed; the new tests cover the four C6 rows, C3's
population boundary, C8 batching, C9's disclosed settlement window, and C11's
compatibility shim. The final non-e2e run preserves the master baseline failure
set exactly, and all temporary mutation edits were restored.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Findings closed

- **B1:** added all four C6 rows, including both independent governing-step ordering fixtures and the all-COMPLETED E-A allowance assertion.
- **B2:** added the production-transition C9 row: `2040` before close, `1440` after close without analytics recompute, `2040` after `_recompute_step_time_totals`.
- **B3:** added three-task/one-worker (`1 probe + 1 sweep`) and three-task/two-worker (`1 probe + 2 sweeps`) rows.
- **B4:** re-applied the named mutation probes, whole-suite, with added and removed failure-ID sets recorded below; every probe was reverted.
- **S1:** the phase file now asserts the E-B manager face absolutely at `840`; the population-filter mutant produces `600`.
- **S2:** the five-sample typicals fixture asserts `sample_count == 5` and median `3600`; the future-instant definition mutant produces zero qualifying samples.
- **S3:** a temporary 50-task measurement fixture (one open record per task, one worker) observed one open-record probe and one worker sweep; 51 IDs were rejected before querying. The measurement-only test was removed because this is a Review-log obligation, not a criterion.

## Validation

Final clean command, run from `app/`:

```text
PYTHONPATH=. pytest -m 'not e2e' -q --tb=no --disable-warnings
```

Result: **26 failed / 2476 passed / 1 deselected / 2 warnings**. The failing IDs are exactly the 26 IDs enumerated in master plan §6: added-ID diff `∅`, removed-ID diff `∅`. The phase-local file has **15 passed**. `ruff check` on the phase file, compile checks, and `git diff --check` pass.

The mutation runs were captured against the clean pre-probe tree at **26 failed / 2474 passed / 1 deselected**; the two clean runs have the same 26-ID failure set. For every row below, the removed-ID set was `∅`; “added IDs” are the exact IDs newly failing under the mutant.

## Fourteen-row mutation ledger

1. **C3 population filter** — site: `get_task_budget_status.py:_build_evaluated_status`, adding `EXCLUDED_STEP_STATES` to the step query. Contract: E-B manager `actual_worker_seconds == 840`, with the SKIPPED step contributing `240`. Mutant: `600`. Added IDs: `tests/integration/services/queries/item_economics/test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct`; `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c3_population_fold_counts_nonzero_skipped_consumption_on_manager_face`.

2. **C4 E-P live-map threading** — site: `get_task_production_time.py`, passing `live_seconds=None` to E-B. Contract: one loader invocation and one shared map. Mutant: the E-P surface computes independently. Added ID: `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds`.

3. **C5 ORM assignment** — site: E-P's `TaskStep` loop in `get_task_production_time.py`, assigning live seconds to `total_working_seconds`. Contract: settled ORM value remains unchanged and the division row sees live `600`. Mutant: persisted/read live value becomes `600`. Added IDs: `test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`, `test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds`, `test_c6_allowances_are_byte_identical_after_settlement_recompute`, `test_c6_created_at_is_carried_into_the_production_division_row`, and `test_c9_settlement_window_drop_is_visible_until_recompute` in `test_phase2_live_surfaces.py`.

4. **C6 `created_at` omission** — site: E-P `DivisionStep` substitution in `get_task_production_time.py`. Contract: governing step `stp_b`; mutant: `stp_a`. Added IDs: the phase created-at row plus `test_c4_persisted_rate_is_the_calculator_output_and_rederives_exactly`, `test_preview_status_enumeration_has_sole_predicate_rows_and_never_creates_evaluations[status-row-10-not-evaluated]`, `test_valuation_chain_preview_delete_and_history`, `test_c8_fingerprint_uses_full_ids_fixed_order_and_changes_by_model`, `test_c18_null_domain_forces_null_suggestion_with_break_even`, `test_c4_c6a_c6b_c25a_c25b_grouped_row_preserves_state_and_snapshot`, and `test_prechange_payloads_match_byte_golden_files`.

5. **C6 `latest_state_record` omission** — same E-P substitution site. Contract: later-entered `stp_b`; mutant: `stp_a`. Added IDs: the phase created-at and latest-state rows, `test_prechange_payloads_match_byte_golden_files`, and `test_c4_c6a_c6b_c25a_c25b_grouped_row_preserves_state_and_snapshot`.

6. **C6 E-A eager relationship load** — site: E-A `TaskStep` load in `get_task_budget_allocations.py`, adding `selectinload(TaskStep.latest_state_record)`. Contract: allowance/left pairs A `(100,0)`, B `(1100,900)`. Mutant: residual allowance moves to the other governing step. Added IDs: `test_c6_all_completed_e_a_section_keeps_allowances_without_eager_state_load`, `test_c8_three_task_batch_shares_one_probe_and_one_worker_sweep`, `test_c8_three_task_batch_runs_one_sweep_per_active_worker`, and the existing `test_c8_allocations_batch_has_one_open_record_probe`.

7. **C7 worker settled aggregate replacement** — site: `get_task_budget_status_worker.py:get_task_budget_status_worker`. Contract: worker actual/remaining/percent/variance equals the live manager face and exceeds settled basis; mutant: worker stays settled. Added IDs: `test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free` and `test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds`.

8. **C8 loop-local loader** — site: `get_task_budget_allocations.py:get_task_budget_allocations`, moving `load_live_worked_seconds` inside the task loop. Contract: three tasks/one worker `1 probe + 1 sweep`; three tasks/two workers `1 probe + 2 sweeps`. Mutant: `3 probes + 3 sweeps`. Added IDs: `test_c8_three_task_batch_shares_one_probe_and_one_worker_sweep` and `test_c8_three_task_batch_runs_one_sweep_per_active_worker`.

9. **C9 settlement-window row** — site/recipe: `_step_transition_core.py:_apply_step_transition(..., now=t)` followed by E-P read without analytics recompute. Contract: `2040 → 1440 → 2040`. Plan §5 names the production transition recipe but does not name an independent production mutation for this criterion; no separate mutant is claimed. The contract row passes in the phase file.

10. **C11 default shim** — site: `get_working_section_typical_times.py:typical_times_statement`, replacing the no-clock fallback with `datetime(2099, 1, 1, tzinfo=timezone.utc)`. Contract: five samples, median `3600`; mutant: zero qualifying samples. Added IDs: `test_c11_typicals_compatibility_shim_keeps_five_sample_median` plus the expected typical-times dependent IDs: `test_phase5_c3_typical_counts_only_the_requested_tasks_steps`, `test_typical_query_uses_group_median_and_returns_empty_sections`, `test_typical_query_aggregates_same_task_section_steps_before_sampling`, `test_typical_query_admits_old_first_pass_when_recent_rework_closes_group`, both `test_typical_query_uses_continuous_median_and_half_even_rounding[...]` cases, `test_typical_query_excludes_non_completed_and_marked_wrong_steps_independently`, and `test_typical_query_requires_five_qualifying_groups`.

11. **C11 E-P call site** — site: `get_task_production_time.py`, dropping `now=ctx.now`. Contract: module-clock stub reads `0`; mutant: it reads the module clock. Added ID: `test_c11_c12_surface_call_sites_do_not_fall_back_to_module_clocks`.

12. **C11 E-A call site** — site: `get_task_budget_allocations.py:_load_typicals`, dropping `now=ctx.now`. Contract: stub reads `0`; mutant: module-clock read. Added ID: the same shared C11/C12 call-site test.

13. **C12 manager preview call site** — site: `get_task_budget_status.py`, dropping `now=ctx.now` from `_load_preview_inputs`. Contract: `today_utc` stub reads `0`; mutant: module-clock read. Added ID: the same shared C11/C12 call-site test.

14. **C12 worker preview call site** — site: `get_task_budget_status_worker.py`, dropping `now=ctx.now` from `_load_preview_inputs`. Contract: `today_utc` stub reads `0`; mutant: module-clock read. Added ID: the same shared C11/C12 call-site test.

## C10 perimeter measurement

The seven named suites remained green as-is, except the already-required E-A
query-count update for the shared live probe: `test_price_scenario_query.py`,
`test_live_clock_goldens.py`, `test_phase8_status_results.py`,
`test_phase8_reviewer_r1_probe.py`, `test_budget_allocations_query.py`,
`test_phase9_committed_filter_structure.py`, and the item-economics router.

## Delegations and graph

D4–D9 were carried unchanged from plan §6; no new judgment call was made. No
Architecture Graph delta is owed: this round changed tests and pipeline records
only, and no `archgraph_*` mutation was performed.

## Write perimeter

Final committed-intent files:

- `app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/plans/plan_2.md`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/master_plan.md`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/implementer/2026-08-20_phase2_fix_r2_handoff.md`

Mutation-probe files, all restored and absent from the production diff:

- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py` (not mutated this round; listed because the C9 boundary was checked as the inherited phase-1 guard)

No golden JSON, serializer, router, or Architecture Graph file was changed by
this round.
