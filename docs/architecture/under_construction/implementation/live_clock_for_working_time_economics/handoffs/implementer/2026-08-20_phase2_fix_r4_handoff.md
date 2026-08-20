---
plan: 2
role: implementer
round: 4
state: IMPLEMENTED
date: 2026-08-20
actor: Codex
---

# Phase 2 fix r4 handoff

Fix r4 is implemented and validated. The phase proof now discriminates the live
category, proves frozen-clock byte identity on all four consumers, pins the C6
allowance preconditions, checks the complete money-free worker payload, and keeps
the compatibility shim fixture independent of the calendar date. Production logic
was not changed.

⚠ OWNER DECISIONS REQUIRED (0)

None.

## Finding closure

- **B1(a): closed.** Added a positive-allowance fixture. Contract side is
  `allowance_seconds=186`, `worked_seconds=1500`, `left_seconds=-1314`,
  `share_state="over_share"`; the settled substitution at
  `get_task_production_time.py:get_task_production_time` changes the category to
  `on_track`. Both sides are exact assertions.
- **B1(b): closed.** Added two-call byte comparisons at frozen `ctx.now` for E-P,
  E-B manager, E-B worker, and single-task E-A. Each endpoint's loader counter is
  exactly two across the two requests. Non-vacuity comes from the open record and
  committed evaluation; E-A remains single-task because its task query has no
  ordering contract.
- **S1: closed.** C6 asserts that no excluded fixture step has an open record, and
  captures the `DivisionStep` input to assert settled `charged_seconds=1440`.
  It also compares the `typical` blocks before and after settlement/recompute.
  The no-open assertion would fail if an excluded step gained an open record; that
  is the load-bearing condition for allowance independence.
- **S2: closed.** C7 now recursively walks every key of the serialized worker
  payload and asserts the live actual value exceeds the settled basis while the
  five named fields equal the manager face. The settled-basis worker mutation
  reddened the row.
- **S3: closed.** C11 derives each fixture `closed_at` from
  `datetime.now(UTC) - timedelta(days=1)` and keeps the `typical_times_statement`
  call argument-free. The row therefore exercises the default wall-clock shim
  without expiring on a repository date.
- **S4: closed.** Added the required fail-loud strict-indexing consequence comment
  at both `DivisionStep` substitution sites.
- **N4: closed.** Changed `typical_times_statement` to the shared `is not None`
  shim form. The future-instant default mutation still reddens the same prior
  C11 set.

## Validation and mutation ledger

All measurements below were taken at `HEAD 771ff46`; no foreign commit landed
during the sweep. The clean intended tree measured **26 failed / 2478 passed / 1
deselected / 2 warnings**. Its complete 26-ID failure set is byte-identical to
master plan §6; no baseline ID was removed.

| Row | Contract side | Mutation side | Added IDs | Removed IDs |
|---|---|---|---|---|
| B1(a), settled substitution at `get_task_production_time.py:get_task_production_time` | **26 / 2478 / 1**; C2 exact values above and `over_share` | **30 / 2474 / 1**; `total_working_seconds=step.total_working_seconds` | `test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`, `test_c2_positive_allowance_moves_share_state_under_live_basis`, `test_c6_allowances_are_byte_identical_after_settlement_recompute`, `test_c9_settlement_window_drop_is_visible_until_recompute` | ∅ |
| B1(b), frozen-clock byte identity | Focused phase row: **17 passed**; each endpoint's two payload bytes equal and counter is 2 | No new mutation was required by the fix prompt; the carried C4 `live_seconds=None` mutation remains the existing one-loader guard | Non-vacuity established by committed evaluation/open record; E-A call is single-task | ∅ |
| S1(i), excluded-record assertion and settled charge on division input | Focused C6 row passes; no excluded step has an open record; every captured division input charges 1440 settled seconds | No independent production mutant is named; the assertion's failure condition is an excluded step acquiring an open record | N/A | ∅ |
| S2(a), worker settled-basis delegation at `get_task_budget_status_worker.py:get_task_budget_status_worker` | **26 / 2478 / 1**; worker live actual exceeds settled actual and equals manager face | **29 / 2475 / 1**; worker receives settled step totals | `test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`, `test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds`, `test_c4_frozen_open_record_payloads_are_byte_identical` | ∅ |
| S3/N4, C11 default future-instant mutation at `get_working_section_typical_times.py:typical_times_statement` | **26 / 2478 / 1**; dynamic wall-clock fixture passes | **35 / 2469 / 1**; future default cutoff | `test_c11_typicals_compatibility_shim_keeps_five_sample_median`, `test_phase5_c3_typical_counts_only_the_requested_tasks_steps`, `test_typical_query_uses_group_median_and_returns_empty_sections`, `test_typical_query_aggregates_same_task_section_steps_before_sampling`, `test_typical_query_admits_old_first_pass_when_recent_rework_closes_group`, `test_typical_query_uses_continuous_median_and_half_even_rounding[continuous-interpolation]`, `test_typical_query_uses_continuous_median_and_half_even_rounding[half-even-rounding]`, `test_typical_query_excludes_non_completed_and_marked_wrong_steps_independently`, `test_typical_query_requires_five_qualifying_groups` | ∅ |

Focused phase tests: **17 passed**. Ruff: **all checks passed**. Every mutation
was applied at its named site, measured with the whole suite, and reverted.

## Write perimeter

### Intended fix changes

- `app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`
  — new/extended C2, C4, C6, C7, and C11 proof rows and fixture helpers.
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
  — one D7 comment only.
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
  — one D7 comment only.
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  — one equivalent N4 cutoff-expression form only.
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/master_plan.md`
  — phase 2 tracker row only.
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/plans/plan_2.md`
  — appended r4 Review-log entry.
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/implementer/2026-08-20_phase2_fix_r4_handoff.md`
  — this handoff.

### Mutation-probe files, applied and reverted

- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
  — B1(a) settled substitution.
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`
  — S2(a) settled-basis worker delegation.
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  — S3/N4 future-instant default.

The probe files above were restored and are listed separately so perimeter review
can distinguish temporary mutations from shipped edits. No Architecture Graph
state was written; status/search orientation only, and no architectural delta is
owed for this test/comment/shim-form fix.
