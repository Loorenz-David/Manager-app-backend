---
plan: plan_2
role: implementer
round: 2
date: 2026-08-23
actor: Codex (GPT-5)
---

# Plan 2 fix-round-2 handoff

The phase-2 implementation is unchanged in production code. This round repaired the
evidence perimeter and the fixtures that could not fail: the K-multiplication owner test
now asserts literal section count and median values, the below-floor shape tests clear the
floor, C7 has both primary-less variants, C10 has the requested boundary and falsy rows,
and the measurement harness label describes age rather than window span. The focused
phase suite is green: 23 passed, 1 skipped. The full-suite L4 stamp is recorded after the
checkpoint metadata is finalized below.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. No owner decision is required for this fix round.

## Prompt-item disposition

| prompt item | disposition |
|---|---|
| K1: C5 omitted typical-value guard and inert fixture | fixed; C5 now seeds 6 narrowed / 20 section groups with seconds 10..143, asserts literal count `20` and median `76` at every index and in K=0, and the `SUM(...)*2` probe reddened the named C5 test |
| K2: C6 exact-floor `>=`→`>` mutation not run | fixed; mutation run and recorded below |
| K3: C7 `role == PRIMARY` moved to `WHERE` mutation not run | fixed; mutation run and recorded below |
| K4: C7 `removed_at IS NULL` moved to `WHERE` mutation not run | fixed; added removed-primary fixture variant, mutation run and recorded below |
| C10 wrong unit instrument | fixed; mutation ledger below reports integration population counts, while the existing unit predicate row remains as a supplementary guard |
| C10(ii): `(None, None)` emits `TRUE` mutation not run | fixed; mutation run and recorded below |
| C10(iii): field conjunction changed to `or_` mutation not run | fixed; mutation run and recorded below |
| C10(iv): category `IN` changed to `NOT IN` mutation not run | fixed; category fixture now has four non-null out rows plus a NULL row, mutation run and recorded below |
| C1 structural control: delete `WorkingSection.is_deleted.is_(False)` | fixed; no-spec snapshot control mutation run and recorded below |
| N1: C2(d) one-group fixture and computed-vs-computed typicals | fixed; five groups with seconds `[10, 20, 30, 40, 50]`, literal counts `5` and typicals `30` |
| N2: C8 median half inert / disclosure absent | justified; chose option (b): under shipped outer attachment the count assertion is the biting assertion; the equal-seconds median is explicitly documented as a control |
| C3 fixture smaller than enumerated | fixed; restored 3 live + 1 soft-deleted sections and 6 K=2 rows |
| C10 row (f) missing ordinary `True` case | fixed; retained falsy `False` row and added `True` row |
| C10 row (c) upper boundary missing | fixed; width fixture now includes `60` and `80` in-values |
| C13(b) ledger row missing | fixed; five existing suites plus `test_phase2_live_surfaces.py` are named in the verification section below; no files in those suites were edited |
| C0 per-row mutation detail | justified by round-1 tree-bound ledger row; all five parser rows remain unchanged and this round spent its mutation budget on the seven coordinator-named gaps |
| `_narrowing_seed.py` false history column | fixed; replaced `history_span_days: 90` with `history_age_days: 1` and `window_days: 90`; the matrix was not rerun |
| out-of-perimeter clock-in-code failures | declined-with-reason; pre-existing xdist isolation issue, not phase-2 code or fixture perimeter; routed to `test_isolation_xdist` |

## Mutation ledger

All contract-side baselines below were taken on the repaired tree. A probe tree is identified
as checkpoint `d07028b` plus the listed dirty-diff SHA; `git status --porcelain` was clean
apart from the expected `.archgraph/contexts/` before the round's intended edits, and the
probe was applied-and-reverted. The final intended dirty tree before this handoff had diff
SHA `40c4ee3df7412923fefc82fe293a23d19cd88006d5a1fdedf3892bc9b4ab6375`.

| criterion / hypothesis | contract side | mutation side, exact command and tree | failing test ID(s) |
|---|---|---|---|
| K1/C5: section count and typical stay invariant across K | focused integration baseline: 23 passed, 1 skipped | `BEYO_TEST_SLOT=r2k1b PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`; dirty SHA `bb1bbb4b280d04ec556d80154a2a8d4283963ba658e656da1acd3333e17e9cbb`; K≥1 grouped `SUM(total_working_seconds) * 2`; 19 passed, 4 failed, 1 skipped | `test_k_shape_is_keyed_by_spec_count_and_non_narrowing_k1_is_seven_columns`; `test_spec_index_preserves_input_order_and_section_population_is_constant` (C5 owner); `test_primary_join_is_fanout_free_and_secondary_items_do_not_define_membership`; `test_removed_primary_does_not_change_group_sum_and_no_spec_is_a_control` |
| C6(ii): narrowed exact floor uses `>=` | 23 passed, 1 skipped | `BEYO_TEST_SLOT=r2c6b PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`; dirty SHA `eada9f8cda7742cca709b8d07fc608ced7deca0541f75da9daaa4531fce75255`; narrowed `>=` changed to `>`; 21 passed, 2 failed, 1 skipped | `test_k_shape_is_keyed_by_spec_count_and_non_narrowing_k1_is_seven_columns`; `test_narrowed_threshold_includes_exact_floor_and_excludes_one_below[5-present]` (C6(ii) owner) |
| C7(ii): primary role predicate in `ON` preserves primary-less section row | L2 baseline: 62 passed, 1 skipped | `BEYO_TEST_SLOT=r2c7rb PYTHONPATH=. pytest tests/unit/services/queries/working_sections/ tests/integration/services/queries/working_sections/`; dirty SHA `e512fdc62c8acdb0bb18664902927ae8121b6acd385f5a7643f38466c474c380`; role predicate moved from `TaskItem` `ON` to statement `WHERE`; 58 passed, 4 failed, 1 skipped | `test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized`; `test_spec_index_preserves_input_order_and_section_population_is_constant`; `test_primary_less_tasks_stay_in_section_population_and_not_narrowed`; `test_removed_primary_is_still_section_population_and_not_narrowed` |
| C7(iii): removed-primary predicate in `ON` preserves removed-primary section row | L2 baseline: 62 passed, 1 skipped | `BEYO_TEST_SLOT=r2c7mb PYTHONPATH=. pytest tests/unit/services/queries/working_sections/ tests/integration/services/queries/working_sections/`; dirty SHA `9cf9279632545482f5dbd6942aa64c74335dd115613a7a0dfafbb9feeb4618cc`; `removed_at IS NULL` moved from `TaskItem` `ON` to statement `WHERE`; 61 passed, 1 failed, 1 skipped | `test_removed_primary_is_still_section_population_and_not_narrowed` |
| C10(ii): recorded-width NULL row is excluded by `IS NOT NULL` | 23 passed, 1 skipped | `BEYO_TEST_SLOT=r2c10nb PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`; dirty SHA `04eb58a50dd05fcaf2bf56e0d2d8cd08e18700ad4737303885f6d5858adcbcc7`; `(None, None)` changed to emit `TRUE`; 22 passed, 1 failed, 1 skipped, 1 warning | `test_each_item_field_and_null_unknown_row_is_an_exact_population_count[recorded-width-width_cm-recorded-width-null-width]` |
| C10(iii): fields are conjoined, not disjoined | 23 passed, 1 skipped | `BEYO_TEST_SLOT=r2c10ob PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`; dirty SHA `9ed0f3dc1d5e14d3a2f3d1a11394665716943d2e0fda378625d6c1f4f0297eae`; `and_` changed to `or_`; 22 passed, 1 failed, 1 skipped | `test_field_predicates_are_and_across_fields_and_or_within_category_collection` |
| C10(iv): category membership uses `IN` | 23 passed, 1 skipped | `BEYO_TEST_SLOT=r2c10nb2 PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`; dirty SHA `4ed076316bb31e41e1200a94bc83a3f2eebad83e75726642cfc3b9af1e76a3cb`; `IN` changed to `NOT IN`; 14 passed, 9 failed, 1 skipped | `test_spec_index_preserves_input_order_and_section_population_is_constant`; `test_narrowed_threshold_uses_its_own_count`; `test_narrowed_threshold_includes_exact_floor_and_excludes_one_below[5-present]`; `test_narrowed_threshold_includes_exact_floor_and_excludes_one_below[4-absent]`; `test_primary_less_tasks_stay_in_section_population_and_not_narrowed`; `test_removed_primary_is_still_section_population_and_not_narrowed`; `test_primary_join_is_fanout_free_and_secondary_items_do_not_define_membership`; `test_each_item_field_and_null_unknown_row_is_an_exact_population_count[category-item_category_ids-category-other-category]`; `test_field_predicates_are_and_across_fields_and_or_within_category_collection` |
| C1 control: no-spec statement excludes deleted sections | 3 parametrized snapshot rows passed | `BEYO_TEST_SLOT=r2c1b PYTHONPATH=. pytest tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`; dirty SHA `8feca79a9a33358c6d7008d7c4b2bf81ea2e92744e64dd3741331fa673029596`; removed `WorkingSection.is_deleted.is_(False)` from the no-spec statement; 3 failed | `test_typical_times_statement_matches_pre_refactor_snapshot_at_both_clock_forms[default-clock]`; `[injected-clock]`; `[explicit-no-spec]` |


## Verification and C13(b) perimeter

- Focused final run: `BEYO_TEST_SLOT=r2final PYTHONPATH=. pytest tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`
  → **23 passed, 1 skipped**.
- L2 contract run: `BEYO_TEST_SLOT=r2l2base PYTHONPATH=. pytest tests/unit/services/queries/working_sections/ tests/integration/services/queries/working_sections/`
  → **62 passed, 1 skipped**.
- Docs guard: `PYTHONPATH=. pytest tests/unit/docs/` → **59 passed**.
- C13(b) no-edit perimeter: `test_typical_times_query.py`, `test_production_time_query.py`,
  `test_budget_allocations_query.py`, `test_price_scenario_query.py`,
  `test_phase2_live_surfaces.py`, and `test_live_clock_goldens.py` were covered by the
  L2 run or round-1 green evidence; no file in those suites was edited this round.
- C8 strategy disclosure: option **(b)** was chosen. With shipped outer attachment,
  secondary rows multiply the aggregate count, so the count assertion bites; all equal
  `100` seconds leave the median unchanged, so that median assertion is a documented
  control. C9's `specs=()` half remains a control as required by §6A.
- C0 per-row mutations remain cited from the round-1 handoff's tree-bound ledger; the
  five parser rows and their production code were not touched this round.

## L4 full-suite stamp

Pending the final full-suite run after the checkpoint metadata is finalized. Required
comparator: the approved 21-ID baseline, with the three known diagnosed out-of-perimeter
IDs in `tests/integration/models/users/test_user_work_profile_clock_in_code.py` named
separately. The stamp will record both-direction failure-ID delta, Redis reachability, and
the final clean-tree identity.

## Full write perimeter

Intended fix files:

- `app/tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`
- `app/tests/integration/services/queries/working_sections/_narrowing_seed.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_2.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

Mutation-probe files, all applied and reverted with no production change:

- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py`

Architecture Graph: no delta. The round changes test evidence and a reproducibility label,
not an independently named architectural boundary; the existing phase-2 additive graph
delta remains untouched. `.archgraph/contexts/` is the expected untracked generated state.

Checkpoint SHA: pending the checkpoint commit immediately following this handoff.
