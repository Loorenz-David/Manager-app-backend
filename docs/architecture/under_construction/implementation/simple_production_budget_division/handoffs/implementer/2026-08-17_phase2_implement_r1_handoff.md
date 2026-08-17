---
plan: 2
role: implementer
round: 1
state: IMPLEMENTED
actor: Codex (GPT-5)
date: 2026-08-17
---

# Phase 2 implementation handoff

## Result

E3 is implemented: a task-scoped, all-role, time-only production-time projection
with section rows, deterministic section ordering, exact per-step allowance
allocation, live state snapshots, and the existing manager budget-status
degradation/frozen-final behavior. No owner decisions remain open.

The implementation keeps arithmetic in the single allocator
`budget_division.divide_production_budget`. E3 performs no money serialization,
does not read persisted calculation results for the final view, and makes no
migration, index, persisted-state, or `CALCULATION_VERSION` change.

## Files in the implementation perimeter

- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
- `app/beyo_manager/routers/api_v1/item_economics.py`
- `app/beyo_manager/routers/README.md`
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/integration/services/queries/item_economics/test_production_time_query.py`
- `app/tests/unit/services/queries/item_economics/test_production_time_contract.py`
- `app/tests/unit/routers/api_v1/test_production_time_routes.py`
- `app/tests/unit/routers/api_v1/test_item_economics_router.py`
- `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/master_plan.md`
- `docs/architecture/under_construction/implementation/simple_production_budget_division/plans/plan_2.md`

The prompt, projection handoff, and reviewer prompt files were pre-existing
working artifacts and were not altered by the implementation.

## T7b closure

Exactly two phase-1 value rows changed in
`test_live_partition_includes_working_paused_and_completed_steps`:

| Fixture | pending / working / paused | completed | new |
|---|---:|---:|---:|
| base | 20 / 20 / 20 | 0 | — |
| with_new | 15 / 15 / 15 | 0 | 15 |

The causes are removal of double-weighting and the fallback-median multiset
change: a two-step section contributes its typical once. The shared typical-ratio
test was unchanged in value and now verifies the section-level invariant.

## Criterion ledger

| Criteria | Passing test/evidence |
|---|---|
| C1–C2 | `test_c1_c2_section_order_is_total_and_nulls_last` |
| C3 | `test_c3_section_sort_key_uses_id_as_final_backstop` |
| C4, C6, C25 | `test_c4_c6_c25_grouped_row_preserves_state_and_snapshot` |
| C5 | `test_c5_section_unit_weights_a_reassigned_section_once` |
| C7 | `test_c7_multi_open_governing_step_and_equal_remainder_tie_are_deterministic` |
| C8–C9 | `test_c8_c9_excluded_and_mixed_sections_keep_task_charge` |
| C10 | `test_c10_section_allowances_sum_exactly_on_indivisible_budget` |
| C11–C12, C20, C24 | `test_c11_c12_c20_c24_e2_and_e3_agree_and_keep_e2_shape` |
| C13 | `test_c13_negative_open_residual_is_not_clamped` |
| C14–C16 | `test_c14_c16_flat_time_only_degradation_and_tenant_boundary` |
| C17 | `test_c17_frozen_final_uses_live_percent_without_money` |
| C18 | route contract, item-economics router, mirror, and README checks |
| C19 | `test_c19_division_has_one_allocator_and_services_only_consume_it` |
| C21–C22 | `test_c15_c21_c22_task_scope_and_soft_deleted_section_outer_join` |
| C23 | `test_c23_leftover_section_tie_uses_section_id_for_both_surfaces` |
| C26 | `test_budget_allocation_constant_query_count_for_one_and_three_tasks` |

Property checks were explicitly verified: P-SUM3 exact allowance sum, P-ORDER
total section order with nulls last, P-COVER agreement between SQL actual seconds
and E3 section worked seconds, P-AGREE section allowance agreement across E2/E3,
and P-FLAT byte-identical time-only bodies across roles.

## Mutation probes

All seven required probes produced a red output and were reverted:

| Probe | Mutation | Observed red result |
|---|---|---|
| C5 | restored per-step weighting | expected 4320/2160/4320, got 3086/1543/6171 |
| C6 | removed governing-step rule | expected `pending`, got `completed` |
| C14 | returned `serialize_item_cost_result(result)` | recursive money-key assertion failed |
| C15 | removed workspace filter | tenant `pytest.raises(Task not found)` failed |
| C22 | changed section attributes to inner-join behavior | expected one section, got zero |
| C23 | changed one caller's remainder tie key | E2/E3 section allowance equality failed |
| C25 | emitted snapshot as live section name | expected `Renamed`, got `Upholstery` |

The temporary C15 probe touched
`get_task_budget_status.py` but was fully reverted; its SHA matched the
pre-probe baseline. The final production-file SHAs were also checked after each
reversion, with no mutation residue.

## Verification

- Baseline reproduced before edits: **2287 passed, 26 failed, 1 deselected**.
- Targeted phase suite: **164 passed**.
- Full suite: **2337 selected, 2311 passed, 26 failed, 1 deselected**.
- The 26 full-suite failure IDs are byte-identical to the approved start baseline;
  there are zero added or removed failures.
- `git diff --check` is clean.

The inherited failure set is the documented bootstrap, working-section, audit,
Shopify, inventory, task-step/date, worker-stats, serializer, and router set; it
does not include any phase-2 test.

## Architecture graph

The graph delta was recorded in one additive `archgraph_apply_changes` batch
after status and duplicate checks. It added the inferred projection and endpoint
nodes plus `implements` and `accepts` relationships. Resulting graph revision:
`1ed6696044c0e8ce6ee016656724700fd4f7570b12789ceed1d2967f5f2638d8`.

## Checkpoint

The implementation checkpoint commit is recorded below after the commit is made.
