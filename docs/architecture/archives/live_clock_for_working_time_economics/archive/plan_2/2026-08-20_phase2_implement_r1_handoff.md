---
plan: 2
role: implementer
round: 1
state: IMPLEMENTED
date: 2026-08-20
actor: Codex
---

Phase 2 is implemented across the three live economics surfaces. The request clock now drives the live worked-seconds basis and the two compatibility shims. E-P and E-A consume substituted `DivisionStep` rows, while E-B folds the shared live map without the former SQL aggregate. Validation preserves the recorded baseline failure set and adds six phase-local passing tests.

## Outcome

- E-B manager status: `_build_evaluated_status` loads all non-deleted task steps when it owns the fold, calls `load_live_worked_seconds` with `ctx.now`, and sums the returned map.
- E-P production time: loads steps first, runs the loader once, passes the same map into E-B, and uses `DivisionStep` substitutions for division.
- E-A budget allocations: runs one loader over the complete visible-step batch before the task loop, resolves `selection_date = ctx.now.date()` once, and uses the map for headlines and substituted rows.
- Preview configuration: `_load_preview_inputs(..., *, now=None)` is additive; E-B manager and worker query services pass `ctx.now` while command callers retain the default shim.
- Typical times: `typical_times_statement(..., *, now=None)` is additive; E-P and E-A pass `ctx.now` while working-sections and price-scenario callers retain the default clock.
- Hard fences held: no router, serializer key set, `budget_division.py`, `concurrency.py`, `averaged_time.py`, frozen-percent feed, or golden-file change. No ORM `TaskStep.total_working_seconds` assignment was introduced, and E-A did not gain `selectinload`.

## Verification

Phase-local test file: **6 passed**.

Final clean run from `app/`:

`PYTHONPATH=. pytest -m 'not e2e' -q --tb=no`

Result: **26 failed / 2465 passed / 1 deselected / 2 warnings**. The 26 failure IDs are the baseline set enumerated in master plan §6; no phase-2 ID is present in the clean run. The six-count increase over the baseline 2459 passes is the new phase-local test file. `ruff check`, `python3 -m compileall` on changed service modules, and `git diff --check` pass.

C10 perimeter measurement: all seven named suites were exercised by the clean run and green as-is, except the existing E-A query-count assertion was updated for the new shared live probe. The suites are price scenario, live-clock goldens, phase-8 status results, phase-8 reviewer probe, budget allocations, phase-9 committed-filter structure, and the item-economics router.

C8: the implementation keeps `_MAX_TASK_IDS = 50` and performs one loader call before the task loop. No separate 50-task fixture was added; the 50-task ceiling remains a source-level invariant rather than a separately measured acceptance row in this handoff.

## Mutation ledger

Each measured mutant used a whole-suite run against the clean baseline ID set and was restored before the next probe. The common baseline was 26 failures, 2459 prior passes plus the six phase-local passes, and one deselected test.

- C3, definition site `get_task_budget_status.py:_build_evaluated_status`: adding an `EXCLUDED_STEP_STATES` filter added exactly `tests/integration/services/queries/item_economics/test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` — **27 / 2464 / 1**. Restored and diff-checked.
- C4, E-P call site: passing `live_seconds=None` added exactly `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds` — **27 / 2464 / 1**. Restored and diff-checked.
- C11, E-P typicals call site: dropping `now=ctx.now` added exactly `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c11_c12_surface_call_sites_do_not_fall_back_to_module_clocks` — **27 / 2464 / 1**. Restored and diff-checked.
- C11, E-A typicals call site: dropping `now=ctx.now` added the same single phase-test ID — **27 / 2464 / 1**. Restored and diff-checked.
- C12, manager preview call site: dropping `now=ctx.now` added the same single phase-test ID — **27 / 2464 / 1**. Restored and diff-checked.
- C12, worker preview call site: dropping `now=ctx.now` added the same single phase-test ID — **27 / 2464 / 1**. Restored and diff-checked.
- Not re-applied whole-suite in this session: C5 ORM assignment; C6 `DivisionStep.created_at` omission; C6 `latest_state_record` omission; C6 E-A eager relationship load; C7 worker aggregate replacement; C8 loop-local loader; C9 settlement-window mutation; and C11 default-shim future-instant mutation. These remain reviewer probe rows, not measured claims.

## Decisions and judgment calls

- D4: both additive shims use keyword-only `now`; comments beside both parameters name the compatibility purpose and out-of-pipeline callers.
- D5: the C11 stub replaces the module-bound `datetime` name.
- D6: C8 uses SQL event inspection for the exact E-A `step_state_records` statement and a loader-call counter.
- D7: substitutions use strict `live_seconds[step.client_id]` indexing so a population divergence raises rather than falling back to settled ORM data.
- D8: E-P loads steps and the live map before invoking E-B status so the map is shared.
- D9: the fold branches on `live_seconds is None`, not truthiness.
- C5 uses the required same-session order: assert no dirty `TaskStep`, `expire_all()`, then reread the settled column.
- `DivisionStep.typical_worker_seconds` is `None` because `TaskStep` has no corresponding ORM field; typicals are supplied by the separate section typicals query.

No owner decision was requested. No review item was adjudicated.

## Write perimeter

Production:

- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `app/beyo_manager/services/commands/item_economics/_common.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`

Tests:

- `app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py` (new)
- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py` (query-count expectation updated for the shared probe)

Pipeline records:

- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/plans/plan_2.md` §7 review log
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/master_plan.md` phase-2 tracker row
- this handoff
- Architecture Graph: four additive `reads_from` relationships, applied at revision `48ac616c2e98d6aecbbcd338c336432989a814a2fad46a38a17e32d4c7fd510d`, linking the four live surface projections to `projection-live-worked-seconds`

The unrelated pre-existing `docs/architecture/under_construction/implementation/narrow_typical_work_times/` working-tree content was preserved and is not part of this phase perimeter.
