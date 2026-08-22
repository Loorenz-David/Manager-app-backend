---
plan: 1
role: implementer
round: 1
state: IMPLEMENTED
actor: Codex
date: 2026-08-20
---

# Phase 1 implementation handoff

Phase 1 is implemented and verified. The live worked-seconds foundation now
has a request-scoped `ServiceContext.now`, a pure batched loader, deterministic
payload goldens, and focused integration coverage for C3–C10.

## Owner decisions required

**⚠ OWNER DECISIONS REQUIRED (0)**

None.

## Shipped

- Captured and replayed the three required payload goldens before the live
  loader existed. Checkpoint: `1081a2b`.
- Added `ServiceContext.now`, stamped once at context construction and kept as
  request data rather than configuration.
- Added
  `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py`.
  It batches the open-record probe, anchors each user's contribution window at
  that user's minimum open entry minus one day, delegates interval arithmetic to
  `compute_record_contributions`, and returns integer live seconds without ORM
  assignment.
- Added 17 focused loader tests covering C3–C10 plus the golden replay test.
- Added fixed-ID, flush-only golden fixtures for production time, budget status,
  and budget allocations.
- Recorded one additive Architecture Graph delta: an inferred
  `Live worked-seconds loader` projection with `reads_from` to
  `table-step-state-record` and `calls` to
  `src-compute-record-contributions`. No review decision was enacted.

The loader also explicitly rejects a naive `now` with the required `TypeError`.
This guard is intentional: the configured asyncpg path normalizes a naive bind
value at the SQL boundary, so the loader preserves the contract with a loud
boundary check before arithmetic is delegated.

## Delegation outcomes

- D1: used two overlapping 30-minute cross-task records for the C3 row-3
  fixture; each worker receives 900 seconds.
- D2: used a throwaway capture script at
  `/private/tmp/capture_live_clock_goldens.py`; it was not shipped.
- D3: used flush-only golden fixtures with fixed IDs and no committed-step
  records.

## Verification

- Focused phase tests: **18 passed**.
- Ruff: **all checks passed**.
- Baseline non-e2e suite: **26 failed, 2436 passed, 1 deselected, 2 warnings**.
- Final non-e2e suite: **26 failed, 2454 passed, 1 deselected, 2 warnings**.
- The final failure set is exactly the same 26 inherited IDs enumerated in
  master plan §6; no phase test failed in the final suite.
- Final loader revert hash used for every mutation run:
  `6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca`.

## Mutation ledger

Each mutation was run against the whole non-e2e suite, then reverted and the
loader hash was verified. `B` below means exactly the master plan §6 baseline
set of 26 failure IDs.

| Mutation | Observed red set |
|---|---|
| Naive `now - entered_at` at the loader call site | `B ∪ {test_live_worked_seconds.py::test_c3_row_2_sweep_changes_divisor_mid_interval, test_live_worked_seconds.py::test_c3_row_3_cross_task_open_record_is_in_the_divisor, test_live_worked_seconds.py::test_c3_row_4_closed_overlap_shapes_the_open_record_share, test_live_worked_seconds.py::test_c4_record_marked_wrong_has_no_live_term, test_live_worked_seconds.py::test_c4_step_marked_wrong_drops_it_and_releases_sibling_share, test_live_worked_seconds.py::test_c5_t2_batch_row_rejoins_settlement_within_one_second, test_live_worked_seconds.py::test_c6_deleted_step_still_divides_live_sibling, test_live_worked_seconds.py::test_c7_window_anchors_at_minimum_open_entry}` |
| `max(entered_at)` instead of `min(entered_at)` for the window anchor | `B ∪ {test_live_worked_seconds.py::test_c7_window_anchors_at_minimum_open_entry}` |
| Inserted `datetime.now(now.tzinfo)` as the sweep timestamp | `B ∪ {test_live_worked_seconds.py::test_c3_row_1_distinct_workers_are_not_divided_by_section_records, test_c3_row_2_sweep_changes_divisor_mid_interval, test_c3_row_3_cross_task_open_record_is_in_the_divisor, test_c3_row_4_closed_overlap_shapes_the_open_record_share, test_live_worked_seconds.py::test_c4_step_marked_wrong_drops_it_and_releases_sibling_share, test_live_worked_seconds.py::test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped, test_c5_t2_batch_row_rejoins_settlement_within_one_second, test_c5_t2_single_open_record_rejoins_settlement_within_one_second, test_c6_deleted_step_still_divides_live_sibling, test_c7_window_anchors_at_minimum_open_entry, test_c8_loader_is_deterministic_and_does_not_read_its_module_clock, test_c10_loader_never_persists_live_seconds_on_task_step}` |

## Checkpoints and perimeter

- Golden checkpoint: `1081a2b` — `CHECKPOINT (not approved): capture
  live-clock payload goldens`.
- Implementation checkpoint: `a7659bc` — `CHECKPOINT (not approved): implement
  live worked-seconds foundation`.
- The plan implementation log was updated in `plans/plan_1.md`.
- The master plan tracker was not updated; that remains coordinator-owned.

Phase write perimeter:

- `.archgraph/architecture.yml`
- `app/beyo_manager/services/context.py`
- `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py`
- `app/tests/integration/services/queries/item_economics/test_live_worked_seconds.py`
- `app/tests/integration/services/queries/item_economics/test_live_clock_goldens.py`
- `app/tests/integration/services/queries/item_economics/goldens/golden_production_time.json`
- `app/tests/integration/services/queries/item_economics/goldens/golden_budget_status.json`
- `app/tests/integration/services/queries/item_economics/goldens/golden_budget_allocations.json`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/plans/plan_1.md`
- this handoff file

Architecture Graph revision after the additive delta:
`9e29e8309d8137e4be9310009abfaa1f54e43d02100dc8bd3acbe2db44f7e4ae`.
Graph status remained valid with zero diagnostics and zero stale nodes; three
items remain pending review under the graph's review policy.
