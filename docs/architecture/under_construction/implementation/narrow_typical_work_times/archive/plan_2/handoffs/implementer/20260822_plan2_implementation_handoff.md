---
plan: plan_2
role: implementer
round: 1
date: 2026-08-22
actor: Codex (GPT-5)
---

# Plan-2 implementation handoff

Plan 2 is implemented and ready for review. The query now accepts an ordered sequence
of canonical specs and returns one keyed row per live section and spec, while the empty
sequence takes the preserved pre-refactor SQL branch. Item matching is centralized in a
new query-layer module and is attached through the task's active PRIMARY item. The
measurement harness and document contain the required ten cells plus the API-ceiling
row; no consumer payload or call form was changed.

## Task 0 — criteria transcription before production code

Before writing production code, I transcribed the corrected C0, C1, C2, C3, C4, C5,
C6, C7, C8, C9, C10, C11, C12, C13 rows and prose clauses into:

- `test_typical_filters.py` (C0 and inherited C14 rows);
- `test_typical_times_sql_identity.py` (three independently parametrized C1 rows);
- `test_typical_item_filter.py` (predicate tuple, coalesce, recorded-range and absence
  checks);
- `test_typical_times_narrowing.py` (shape, cardinality, populations, joins, all field
  rows, service payload, and the opt-in measurement caller).

The red run was for the intended reasons: malformed parser inputs were accepted, the
new predicate function and `specs` argument were missing, and the explicit no-spec
snapshot row did not compile. No criterion row was untranscribable after §6A; the
fixtures that assert typical values clear the five-group floor, and the removed-primary
and fan-out rows use five or more groups where the mutation must move a result.

## Implementation summary

- Added `_typical_item_filter.build_item_match(spec) -> (needs_category_join, predicate)`.
- Added per-family parser guards for byte-like values, mappings, bare enum strings, and
  non-boolean upholstery values.
- Added the K-spec query path with an outer `VALUES` cross join on `spec_index`, FILTER
  aggregates for narrowed and section-wide populations, and total section cardinality.
- Chose outer attachment. `workspace_id` is supplied as a bound value in the
  `TaskItem`/`Item` ON clauses; no extra grouped-step column was added.
- The active-primary unique-index contract remains a recorded dependency; this phase
  did not add the separate index-enforcement criterion noted in the projection.

## Criteria ledger — both sides and failing mutation ID

| criterion | contract side | named mutation side | failing test ID |
|---|---|---|---|
| C0 | malformed family rows raise `ValidationError`; inherited C14 rows remain green | remove upholstery type guard | `test_parser_rejects_non_boolean_upholstery_value` |
| C1 | all three snapshot rows equal | delete `len(specs) == 0` branch | `test_typical_times_statement_matches_pre_refactor_snapshot_at_both_clock_forms[default-clock]`, `[injected-clock]`, `[explicit-no-spec]` |
| C2 | K=0 has 4 columns; K=1 empty and narrowing have 7 | branch on `is_narrowing` | `test_k_shape_is_keyed_by_spec_count_and_non_narrowing_k1_is_seven_columns` |
| C3 | live sections × K, history-less section materialized | inner join grouped history | `test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized` |
| C4 | caller order gives index 0 chair / index 1 table; no fingerprint terms | reverse specs | `test_spec_index_preserves_input_order_and_section_population_is_constant` |
| C5 | section count/value invariant across specs and K=0 | move match to outer WHERE | `test_spec_index_preserves_input_order_and_section_population_is_constant` |
| C6 | narrowed count 2 has no typical; exact floor has one; one below has none | threshold reads section count | `test_narrowed_threshold_uses_its_own_count` |
| C7 | primary-less task remains section-wide only | inner TaskItem join | `test_primary_less_tasks_stay_in_section_population_and_not_narrowed` |
| C8 | five-group primary + secondaries counts once and median stays 100 | remove PRIMARY ON predicate | `test_primary_join_is_fanout_free_and_secondary_items_do_not_define_membership` |
| C9 | five removed-primary groups remain count 5 / typical 100; K=0 is a control | remove `removed_at IS NULL` from ON | `test_removed_primary_does_not_change_group_sum_and_no_spec_is_a_control` |
| C10 | each field's in/out/NULL rows give exact count 5; zero lower bound is honored | remove range `IS NOT NULL` | `test_recorded_dimension_range_requires_a_non_null_dimension` |
| C11 | compiled narrowing predicate contains `coalesce` | remove coalesce wrapper | `test_narrowing_spec_returns_a_predicate_and_coalesces_unknowns[category]` (and all 9 field parametrizations) |
| C12 | category join count is 0/1/1 for no/one/both major specs | unconditional category join | `test_item_category_join_is_emitted_exactly_when_major_category_is_needed` |
| C13 | explicit seeded no-spec payload matches exact baseline | service passes an empty spec and reads K≥1 row as old shape | `test_service_no_spec_payload_is_explicitly_unchanged` |

All mutation probes were reverted before verification. The measurement harness itself is
covered by the opt-in `test_cost_matrix_harness_is_reproducible` test.

## Query-cost measurements

Source: [query_cost_measurements.md](../../planning/query_cost_measurements.md).
The new statement measured 0.296 / 0.751 / 1.466 ms execution at 20-task pages with
5 / 10 / 20 specs. The 50×20 API-ceiling row measured 2.758 ms. Current/no-spec cells
are explicitly labelled copies; every seed uses one section, one step per task, 20
categories, and one-day-old history inside the 90-day window.

## L4 full-suite stamp

Command: `cd app && PYTHONPATH=. pytest -m 'not e2e'`.

- Redis reachability: checked by the suite's isolated Redis fixture.
- Baseline comparator: the approved 21-ID failure set.
- Result: **2655 passed, 1 skipped, 24 failed, 2 warnings; 2680 collected in 52.58s**.
- Both-direction delta: baseline IDs added **∅**; baseline IDs removed **∅**; observed-only
  IDs added **3** —
  `tests/integration/models/users/test_user_work_profile_clock_in_code.py::test_duplicate_clock_in_code_in_one_workspace_is_rejected`,
  `tests/integration/models/users/test_user_work_profile_clock_in_code.py::test_same_clock_in_code_in_two_workspaces_is_allowed`, and
  `tests/integration/models/users/test_user_work_profile_clock_in_code.py::test_index_is_partial_so_unassigned_codes_never_collide`.
  The 21 approved IDs were all present. Redis was reachable, so the known 23-failure/2-error
  Redis diagnostic does not apply.
- Focused phase verification after final restoration: **87 passed, 1 skipped**.
- Tree identity: checkpoint commit recorded below; the only expected pre-existing dirty path
  remains `.archgraph/contexts/`.

## Full write perimeter

- `app/beyo_manager/domain/item_economics/typical_filters.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py`
- `app/tests/unit/domain/item_economics/test_typical_filters.py`
- `app/tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`
- `app/tests/unit/services/queries/working_sections/test_typical_item_filter.py`
- `app/tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`
- `app/tests/integration/services/queries/working_sections/_narrowing_seed.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_2.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/query_cost_measurements.md`
- this handoff
- `.archgraph/architecture.yml` (the additive graph delta)
- Architecture Graph: one additive batched delta, revision
  `46154ec9d22efb39c02cec11dcb6f334a72196dad37dd2246b7a2855bdbb9291`; `.archgraph/contexts/`
  remains expected untracked state.

Checkpoint SHA: `d07028b` — `CHECKPOINT (not approved): implement plan 2 typical-times statement`.
