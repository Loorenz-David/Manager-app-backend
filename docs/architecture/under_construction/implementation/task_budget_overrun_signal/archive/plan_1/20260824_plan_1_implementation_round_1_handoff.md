---
plan: plan_1
role: implement
round: 1
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Phase 1 implementation handoff

Phase 1 is implemented and ready for review. The pure budget rule, allocator-derived unit
tests, tracker state, review log, and evidence ledgers are complete. No owner decision is
open in this handoff.

⚠ OWNER DECISIONS REQUIRED (0)

## Outcome

`budget_signal.py` now computes the incurred and projected budget figures, their shipped
money conversions, the four-state verdict, and the fixed frozen `BudgetSignal` surface. The
module is pure: no service, serializer, route, ORM, SQL, migration, or frontend change was
made. The unit suite constructs every section row through `divide_production_budget`.

## Changed-file perimeter

Files changed by this phase:

1. `app/beyo_manager/domain/item_economics/budget_signal.py` — new production rule.
2. `app/tests/unit/domain/item_economics/test_budget_signal.py` — new criterion and mutation suite.
3. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/master_plan.md` — phase 1 tracker row only, advanced to `IMPLEMENTED`.
4. `docs/architecture/under_construction/implementation/task_budget_overrun_signal/plans/plan_1.md` — append-only Review log entry.
5. This handoff file.

Unrelated pre-existing worktree changes were not staged or modified: `.archgraph/` changes,
the intention file, archive/planner/reviewer artifacts, and the frontend handoff remain outside
this implementation perimeter.

### Mutation-probe file list

The 35 probes were applied one at a time and reverted with an md5 check after each probe. The
probe perimeter was only:

- `app/beyo_manager/domain/item_economics/budget_signal.py`
- `app/tests/unit/domain/item_economics/test_budget_signal.py` (edited once to close the C4(e) criterion gap before the final rerun)

## Contract resolution and judgments

No unresolved judgment was delegated to the implementer. The ratified contract was applied as
written:

- terminal membership is derived from `TERMINAL_STEP_STATES`, and the module does not quote
  persisted task-step values;
- commitment clamps each contributing section before summing, while the served pot and
  incurred seconds use their specified independent clamps;
- the `over` verdict wins over `projected_over`, with the 60-second floor and the
  `has_work_ahead` guard;
- both cost fields call `calculate_consumed_cost_minor`, exactly once each, in incurred then
  projected order;
- currency values are derived from `ItemCurrencyEnum`, with the single `NO_CURRENCY`
  sentinel and exact four-member vocabulary;
- `BudgetSignal` is frozen with exactly eight fields and the four public callable signatures
  are closed.

Task 0 reproduced all planner figures: P-A `(0, 0, 600, 38, projected_over)`, P-B
`(0, 0, 0, 0, within_budget)`, P-C `(0, 0, 750, 47, projected_over)`, P-D
`(60, 4, 810, 51, over)`, P-E/P-F `(0, 0, 750, 47, within_budget)`, P-G59
`(0, 0, 59, 4, within_budget)`, P-G60 `(0, 0, 60, 4, projected_over)`, P-H2
`(100, 6, 1900, 119, over)`, P-H3 `(20, 1, 30, 2, over)`, P-H4 `(1, 0, 1, 0, over)`,
P-H6 `(0, 0, 30, 2, within_budget)`, P-H7 `(0, 0, 0, 0, within_budget)`, P-J
`(136, 9, 136, 9, over)`, P-K `(8, 0, 8, 0, over)`, plus the eight-state partition,
money figures `8→0`, `9→1`, `40→2`, `136→9`, `152→9`, and the P3/C5(f) independent
derivations. The first criterion pass exposed that C4(e) needed an explicit test; that test
was added, then the full L1 and all mutations were rerun. MUT-07 initially used the wrong
textual site and was a false green; the probe was re-sited to the specified remaining-pot
expression and then reddened as required.

## Criterion coverage map

Every criterion sub-row has a test, and every test is mapped below. C5(a)/(b) and C5(f) use
the parametrization specified by the plan.

| Criterion | Test id | Discharge |
|---|---|---|
| C1(a) | `test_c1a_contributes_partitions_all_step_states` | eight-state contribution partition and integer left seconds |
| C1(b) | `test_c1b_has_work_ahead_uses_the_contributing_set` | with/without the pending second row |
| C1(c) | `test_c1c_terminal_values_are_derived_strings` | derived terminal set and exact string types |
| C1(d) | `test_c1d_module_does_not_spell_step_state_values` | quoted-state source sweep |
| C2(a) | `test_c2a_remaining_commitment_clamps_each_section_before_summing` | per-section clamp |
| C2(b) | `test_c2b_projection_uses_clamped_commitment` | projected seconds and cost |
| C2(c) | `test_c2c_projection_is_signalled_after_the_clamp` | projected verdict |
| C3(a) | `test_c3a_negative_pot_is_forecast_but_not_incurred` | negative allowance operand clamps |
| C3(b) | `test_c3b_first_logged_seconds_on_negative_pot_are_incurred` | incurred seconds precedence |
| C3(c) | `test_c3c_projection_uses_the_task_pot_operand` | task-pot projection, not section sum |
| C3(d) | `test_c3d_numeric_signal_fields_are_exact_ints` | all numeric field types |
| C4(a) | `test_c4a_projection_below_the_floor_is_served_not_signalled` | 59-second floor boundary |
| C4(b) | `test_c4b_projection_at_the_floor_is_signalled` | 60-second floor boundary |
| C4(c) | `test_c4c_infeasible_all_excluded_has_no_forecast` | excluded rows and guard |
| C4(d) | `test_c4d_infeasible_without_steps_has_no_forecast` | empty rows and guard |
| C4(e) | `test_c4e_excluded_allocator_rows_have_no_commitment_or_work_ahead` | P3 excluded-allocation shape |
| C5(a) | `test_c5ab_money_call_matches_shipped_rounding` | 136-second shipped conversion |
| C5(b) | `test_c5ab_money_call_matches_shipped_rounding` | 152-second shipped conversion |
| C5(c) | `test_c5c_money_call_is_not_the_two_step_inverse` | 40-second shipped conversion |
| C5(d) | `test_c5d_nonzero_overrun_may_cost_zero` | 8/9-second cost boundary |
| C5(e) | `test_c5e_incurred_money_never_goes_negative` | non-negative incurred money |
| C5(f) | `test_c5f_rate_scaling_is_exact` | three pure Decimal scale conversions |
| C5(g) | `test_c5g_money_calls_receive_ordered_exact_arguments` | exactly two typed ordered calls |
| C6(a) | `test_c6a_no_budget_signal_is_the_constructed_zero_row` | sentinel row |
| C6(b) | `test_c6b_over_state_keeps_both_pairs` | over with both pairs populated |
| C6(c) | `test_c6c_over_state_keeps_sub_floor_projection_pair` | over below-floor projection |
| C6(d) | `test_c6d_projected_over_state_requires_the_floor` | projected-over row |
| C6(e) | `test_c6e_within_budget_can_serve_a_sub_floor_projection_pair` | within-budget sub-floor pair |
| C6(f) | `test_c6f_within_budget_has_zero_overrun_figures_when_not_heading_over` | ordinary within-budget row |
| C6(g) | `test_c6g_over_precedes_competing_projection` | precedence competition |
| C6(h) | `test_c6h_over_implies_projection_is_at_least_the_incurred_seconds` | F1 invariant and unreachable row |
| C7(a) | `test_c7a_currency_sentinel_and_derived_vocabulary` | sentinel and vocabulary |
| C7(b) | `test_c7b_currency_sentinel_is_not_persisted` | persisted enum plus rule-15 local probe |
| C7(c) | `test_c7c_currency_sentinel_literal_occurs_once_in_application_sources` | one application literal |
| C7(d) | `test_c7d_currency_values_are_not_quoted_in_the_domain_module` | unquoted derived currency values |
| C8(a) | `test_c8a_budget_state_public_constants_are_closed` | four constants and set |
| C8(b) | `test_c8b_projection_floor_is_an_int` | floor type and value |
| C8(c) | `test_c8c_budget_signal_dataclass_surface_is_exact` | exact eight-field surface |
| C8(d) | `test_c8d_budget_signal_is_frozen` | frozen dataclass behavior |
| C8(e) | `test_c8e_public_callable_signatures_are_closed` | exact signatures and resolved hints |

## Evidence

Tree identity at the final application-test evidence run:

- base `HEAD`: `f376928b94d63307b0d73268a74551f799aea906`;
- production module md5: `c94fec7247673c0891769246b5dadf02`;
- test module md5: `25a11b845ae4dd071ef886fe7491645e`;
- application/test files were unchanged after the L4 run; closeout docs are the only later
  perimeter changes.

| Level | Command/result |
|---|---|
| L1 | `test_domain_purity.py`, `test_budget_division.py`, and `test_budget_signal.py` with `-q -n 0`: **63 passed**. Ruff check and `ruff format --check` passed for both new files. |
| Mutations | **35 executed / 35 declared**, one at a time, each restored and md5-verified; all required probes reddened at their own criterion assertion. |
| L2 | Master item-economics radius command: **611 passed** in 6.49s. |
| L4 | Exactly one `PYTHONPATH=. .venv/bin/pytest -m 'not e2e'` run: **21 failed / 2758 passed / 1 skipped**. Failing-ID additions: `∅`; removals: `∅`; the documented 21-ID baseline is unchanged. |

## Mutation ledger

All rows below are red observations from the final-tree rerun. The listed application/test
files were restored and md5-checked after each mutation.

| # | Probe site | Observed red |
|---:|---|---|
| MUT-01 | assign the enum itself to `_TERMINAL_STATE_VALUES` | C1(a) completed sub-row and C1(c) |
| MUT-02 | type out the four terminal strings | C1(d) source sweep |
| MUT-03 | clamp after summing commitment | C2(a), C2(b), C2(c) |
| MUT-04 | clamp allowed seconds before subtracting actual | C3(a) projected seconds/state |
| MUT-05 | drop the inner allowed-seconds clamp for incurred seconds | C3(a) incurred seconds/state |
| MUT-06 | return raw allowed seconds | C3(a) allowed seconds |
| MUT-07 | derive projection from section-left sum | C3(c) projected seconds/state |
| MUT-08 | pass Decimal incurred seconds to money helper | C5(g) first seconds type |
| MUT-09 | construct Decimal `over_seconds` in signal | C3(d) exact-int field loop |
| MUT-10 | change floor `>= 60` to `> 60` | C4(b) floor boundary |
| MUT-11 | change floor to `>= 0` | C4(a) sub-floor boundary |
| MUT-12 | remove `has_work_ahead` conjunct | C4(c), C4(d) |
| MUT-13 | use positive commitment as work-ahead test | C3(a) projected state |
| MUT-14 | remove outer incurred-seconds clamp | C5(e) non-negative seconds/cost |
| MUT-15 | pass Decimal projected seconds to money helper | C5(g) second seconds type |
| MUT-16 | replace incurred money call with half-even transform | C5(a), C5(b) incurred cost |
| MUT-17 | replace projected money call with half-even transform | C5(a), C5(b) projected cost |
| MUT-18 | use two-step inverse for incurred money | C5(c) incurred cost |
| MUT-19 | use two-step inverse for projected money | C5(c) projected cost |
| MUT-20 | scale rate with `rate * 1000` | C5(f), all three parameters |
| MUT-21 | check projected state before over state | C6(b), C6(g) |
| MUT-22 | zero projection pair for over state | C6(b), C6(c), C6(h) |
| MUT-23 | zero projection pair below floor | C6(c), C6(e) |
| MUT-24 | add a second sentinel literal | C7(c) occurrence count |
| MUT-25 | quote the three currency values in vocabulary | C7(d) source sweep |
| MUT-26 | omit within-budget from public state set | C8(a) exact set |
| MUT-27 | change the over constant to uppercase | C8(a) exact string |
| MUT-28 | change floor to 61 | C8(b) exact value |
| MUT-29 | add defaulted `task_id` field | C8(c) exact dataclass surface |
| MUT-30 | remove dataclass frozen flag | C8(d) assignment/frozen assertion |
| MUT-31 | add `extra` parameter to contributes | C8(e) contributes signature |
| MUT-32 | annotate remaining commitment as bool | C8(e) remaining annotation |
| MUT-33 | annotate has-work-ahead sections as `Sequence[object]` | C8(e) parameter annotation |
| MUT-34 | remove keyword-only marker from compute function | C8(e) parameter kind |
| MUT-35 | change sentinel value to `wrong_currency` | C7(a) sentinel value and C7(c) count |

## Architecture graph

No graph mutation was warranted. The completed module is a pure, new phase-1 leaf and is not
yet reachable from the mapped endpoint/service path; no existing anchor meaning or boundary
changed. The reused anchors were the allocation source, task-budget allocation projection,
endpoint allocation node, and admin/manager decision node. Expected phase-1 delta: **none**
(within the master-plan allowance of none or one `source_file` node).

## Checkpoint and upstream item

- checkpoint commit: `6b84ef0e3b89c2c4da7cba9fd33f064044c8ee3c` (`CHECKPOINT (not approved): implement task budget signal phase 1`);
- closeout commit: recorded after the checkpoint SHA was placed in this handoff;
- upstream item: none;
- next handoff: plan-reviewer, phase 1 review against the commit perimeter.
