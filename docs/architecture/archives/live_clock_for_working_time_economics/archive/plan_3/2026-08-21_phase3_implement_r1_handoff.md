---
plan: 3
role: implement
state: IMPLEMENTED
date: 2026-08-21
actor: Codex
---

# Phase 3 implement r1 handoff

Implemented D9: the E-P `final.percent_consumed` and E-B worker `result.percent_consumed`
now derive from each frozen result's stored `actual_worker_minutes +
variance_worker_minutes` denominator. The live budget/status percent remains request-level
and ticking. The calculation is guarded at both sites by `result is not None`.

⚠ OWNER DECISIONS REQUIRED (0)

None.

## Delegations and judgments

- **P3-D1:** took the default two-serializer-site shape. This keeps the computation at
  the two registered feed sites and avoids changing `TaskBudgetStatus` or router fixtures.
- **P3-D2:** extended `app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`
  with C1, C2, C3, C4a, C4c, C6a and C6b coverage; C4b is asserted in C1.
- **P3-D3:** chose and recorded exact literals beside fixtures: C1/C2/C4b/C4c frozen
  `100.00`, live `120.00 → 170.00`; C3 frozen `80.00` after stored `20.00 + 5.00`,
  current re-commit `30.00`; C6a frozen `15.00` at current allowance `0.00`; C6b
  frozen allowance `0.00` and `null` percent.
- `test_c17_frozen_final_uses_live_percent_without_money` was left unchanged and its
  no-drift coincidence is recorded in plan 3's Review log: stored `20.00 / 80.00`
  reconstructs `100.00`, matching its live fixture's `20.00 / 100.00` basis.

## Verification ledger

Evidence identity for the final L4 stamp: `HEAD 88c8f5ff73e16de87fc5660783559f23b6b1ccca`
with asserted-dirty diff digest `d2ca0320cfc0efce0e6c3222eb15bf0653afa6911f76f87ff2887c3542625e8e`.
The checkpoint commit below makes the final handoff tree clean without changing the
tested production/test content.

| Hypothesis / scope | Exact command or mutation | Result | Failure-ID delta |
|---|---|---:|---|
| C1/C2/C3/C4a/C4b/C4c/C6 L1 contract surface | `PYTHONPATH=. pytest -q ...test_phase2_live_surfaces.py ...test_live_clock_goldens.py ...test_phase8_serializers.py ...test_item_economics_handoff_accuracy.py` | 90 passed | ∅ / ∅ |
| C1 E-P call-site mutation, L1 | Feed `percent_consumed` into `_serialize_production_time_final` | 1 failed | `+test_phase2_live_surfaces.py::test_c1_ep_final_freezes_while_budget_percent_ticks`; no removals |
| C2 E-B call-site mutation, L1 | Feed `status.percent_consumed` into `_serialize_result` | 1 failed | `+test_phase2_live_surfaces.py::test_c2_worker_result_percent_uses_frozen_result_figures`; no removals |
| C3 E-P reconstruction-site mutation, L1 | Use current `row["allowed_worker_minutes"]` as denominator | 1 failed | `+test_phase2_live_surfaces.py::test_c3_recommit_changes_live_denominator_not_frozen_percent`; no removals |
| C3 E-B reconstruction-site mutation, L1 | Use current `status.allowed_worker_minutes` as denominator | 1 failed | `+test_phase2_live_surfaces.py::test_c3_recommit_changes_live_denominator_not_frozen_percent`; no removals |
| C4a manager result-key mutation, L1 | Emit `percent_consumed` from `_serialize_result`'s manager branch | 1 failed | `+test_phase2_live_surfaces.py::test_c4a_manager_result_block_has_no_percent_consumed_key`; no removals |
| C4b E-P live-budget mutation, L1 | Feed the frozen percent into the E-P budget block | 1 failed | `+test_phase2_live_surfaces.py::test_c1_ep_final_freezes_while_budget_percent_ticks`; no removals |
| C4c E-B live-top-level mutation, L1 | Feed the frozen percent into E-B's top-level field | 1 failed | `+test_phase2_live_surfaces.py::test_c4c_worker_top_level_percent_still_ticks`; no removals |
| C5 E-P site, L4 | Replace reconstructed denominator with `result.actual_worker_minutes` | 31 failed / 2481 passed / 1 deselected | baseline 26 plus golden, `test_c17`, and phase C3/C6a/C6b; no baseline removals |
| C5 E-B site, L4 | Replace reconstructed denominator with `result.actual_worker_minutes` | 30 failed / 2482 passed / 1 deselected | baseline 26 plus golden and phase C3/C6a/C6b; no baseline removals |
| C6a E-P boundary mutation, L1 | Blank frozen percent when current status is `infeasible` | 1 failed | `+test_phase2_live_surfaces.py::test_c6a_frozen_percent_survives_infeasible_current_evaluation`; no removals |
| C6a E-B boundary mutation, L1 | Same blanking at E-B reconstruction site | 1 failed | same C6a ID; no removals |
| C6b E-P boundary mutation, L1 | Use positive `actual_worker_minutes` fallback denominator | 1 failed | `+test_phase2_live_surfaces.py::test_c6b_frozen_non_positive_allowance_returns_null_percent`; no removals |
| C6b E-B boundary mutation, L1 | Same positive fallback at E-B reconstruction site | 1 failed | same C6b ID; no removals |
| Authoritative cycle close, L4 | `PYTHONPATH=. pytest -q --tb=no -o log_cli=false -m 'not e2e'` | 26 failed / 2486 passed / 1 deselected / 2 warnings | baseline 26 IDs unchanged in both directions |
| Changed-file lint | `python3 -m ruff check` on the five changed Python files | passed | ∅ |
| Repository lint comparator | `python3 -m ruff check .` | 136 pre-existing errors | changed files introduce none; full lint is not green repository-wide |

The C5 unions are now explicitly covered by plan 3's coordinator correction: the two
legacy IDs are the external bite class, while C3/C6a/C6b are this phase's required
reconstruction assertions. No other IDs appeared.

## Full write perimeter

Intended changes:

- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/domain/item_economics/serializers.py`
- `app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`
- `app/tests/unit/services/queries/item_economics/test_phase8_serializers.py`
- `app/tests/unit/docs/test_item_economics_handoff_accuracy.py`
- `docs/domains/item_economics/README.md`
- `docs/domains/item_economics/states.md`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/master_plan.md`
- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/plans/plan_3.md`
- this handoff file.

Temporary mutation probes, applied and reverted with no shipped changes:

- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/domain/item_economics/serializers.py`

Tool-recorded state: Architecture Graph status/search/get-node orientation only; no graph
nodes, relationships, source links, review decisions, or maintenance changes were written.
The graph remains at the measured inherited state: 9 pending inferred items and 2 stale
links.

The phase checkpoint commit is required with subject prefix `CHECKPOINT (not approved):`.
