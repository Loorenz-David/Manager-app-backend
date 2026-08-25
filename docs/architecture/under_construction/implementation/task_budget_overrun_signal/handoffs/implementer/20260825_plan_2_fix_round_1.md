---
plan: plan_2
role: fix
round: 1
state: IMPLEMENTED
date: 2026-08-25
actor: Codex
---

# Plan 2 fix round 1 handoff

## Summary

The bounded review fix is complete. C8(e) now distinguishes the two non-zero money
operands, MUT-19 proves that transposing their row keys is observable, and C4(b)/C4(c)
cannot pass their flatness checks on an empty result. Production code was not changed.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs owner attention before re-review.

## Outcome

- Plan 2 moved from `CHANGES_REQUESTED` to `IMPLEMENTED`.
- The only executable-file delta is
  `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py`.
- Focused evidence is 29 passed; the declared layer-2 suite is 640 passed.
- All 19 named mutations were applied alone, observed red, and restored after the final
  test-file edit.
- The one authorized repository-wide stamp is 21 failed / 2787 passed / 1 skipped, with
  additions `∅` and removals `∅` against the durable 21-ID baseline.

## Gate and contract resolution

| Gate | Result |
|---|---|
| Intention | `RATIFIED`, round 12; owner-approved seven-numeric correction already folded |
| Dependency | Plan 1 `APPROVED` |
| Review input | Plan 2 `CHANGES_REQUESTED`; exact B1 and N2 corrections selected |
| Repository base | `8a6340275a83e3e4de8edcde137aa94480851377` |
| Selected contract | C8(e), MUT-19, C4(b) two-row non-vacuity, C4(c) non-empty list |
| Excluded findings | N3/N4 remain coordinator notes; no production redesign or adjacent cleanup |
| Local authority | Plan 2 §9 mutation protocol and §10 verification ladder |

The service remains the single projection of the existing allocation/economics contracts:
the reconciled allocation output is consumed, evaluation eligibility stays batch-loaded,
money continues through `calculate_consumed_cost_minor`, and the serializer remains a flat
ten-key envelope. No contract ambiguity or product judgment was encountered.

## Task 0 derivation

For C8(e), the independently exercised production helpers used an allowance of
`Decimal("-12.50")`, rate `Decimal("3.7500")`, 60 worked seconds in section A, and a
pending zero-second section-B step. With no open record, the derived witness is:

`(over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor, budget_state)`
`= (60, 4, 810, 51, "over")`.

The unequal, non-zero pairs make both source operands and both destination keys observable.

## Acceptance-to-test bijection

The coverage map is exactly 29 acceptance rows to 29 test functions; no test is orphaned.

| Row | Test function |
|---|---|
| C1(a) | `test_c1_a_allocator_uses_reconciled_unequal_typicals` |
| C1(b) | `test_c1_b_query_count_is_constant_for_one_and_three_tasks` |
| C2(a) | `test_c2_a_current_committed_evaluation_is_budget_bearing` |
| C2(b) | `test_c2_b_negative_allowance_is_a_forecast_on_the_service_path` |
| C2(c) | `test_c2_c_missing_evaluation_is_no_budget` |
| C2(d) | `test_c2_d_superseded_evaluation_is_no_budget` |
| C2(e) | `test_c2_e_deleted_evaluation_is_no_budget` |
| C3(a) | `test_c3_a_no_budget_row_is_constructed_with_all_zeroes` |
| C3(b) | `test_c3_b_no_budget_currency_ignores_item_valuation` |
| C3(c) | `test_c3_c_evaluated_currency_is_the_enum_value_string` |
| C4(a) | `test_c4_a_every_row_has_exactly_the_ten_contract_keys` |
| C4(b) | `test_c4_b_row_values_have_closed_types_and_vocabularies` |
| C4(c) | `test_c4_c_envelope_is_exact_and_rows_are_flat` |
| C5(a) | `test_c5_a_visibility_omits_deleted_foreign_and_unknown_tasks` |
| C5(b) | `test_c5_b_duplicate_ids_collapse_to_one_row` |
| C5(c) | `test_c5_c_fifty_raw_ids_are_accepted` |
| C5(d) | `test_c5_d_fifty_one_ids_raise_before_any_statement` |
| C5(e) | `test_c5_e_cap_is_applied_before_deduplication` |
| C5(f) | `test_c5_f_unevaluated_visible_task_is_present` |
| C6(a) | `test_c6_a_rows_are_sorted_independently_of_request_order` |
| C6(b) | `test_c6_b_second_request_order_returns_the_same_sorted_rows` |
| C7(a) | `test_c7_a_fixed_rows_are_equal_across_clock_advance` |
| C7(b) | `test_c7_b_open_record_moves_only_live_time_fields` |
| C7(c) | `test_c7_c_over_is_absorbing_and_non_decreasing` |
| C8(a) | `test_c8_a_half_tie_money_uses_the_shipped_calculator` |
| C8(b) | `test_c8_b_second_domain_operand_does_not_round_through_minutes` |
| C8(c) | `test_c8_c_orm_snapshot_rate_wins_over_live_basis_rate` |
| C8(d) | `test_c8_d_nonzero_overrun_can_legitimately_cost_zero` |
| C8(e) | `test_c8_e_money_fields_map_to_distinct_nonzero_operands` |

## Fresh mutation ledger

Each mutation was run alone against the same final normal-side tree, whose app diff SHA-256
was `44a644dc73a6225551a7af606f772faaf91eb3bd725ace7801a1ce702a1a85fb` relative to the
base commit. `F` below means
`app/tests/integration/services/queries/item_economics/test_budget_signals_query.py`; commands
were `PYTHONPATH=. pytest F::<named test(s)> -q` (with the two named `TZ` environments for
MUT-15). A clean 29-pass focused run established the normal side. After every red, the probe
was reverted before the next mutation.

| ID | Isolated mutation | Mutant command scope | Observed red evidence | Restored |
|---|---|---|---|---|
| MUT-01 | Pass `None` instead of `selection.selected` at the allocator call site | C1(a) | tuple was `(600, projected_over)` instead of `(0, within_budget)` | yes |
| MUT-02 | Move evaluation loading from the batch before the loop into the task loop | C1(b) | statement count changed from 13 to 15 | yes |
| MUT-03 | Restrict local budget statuses to `OK` | C2(b) | negative-allowance row became `no_budget` | yes |
| MUT-04 | Drop the superseded-evaluation predicate | C2(d) | state became `within_budget`, not `no_budget` | yes |
| MUT-05 | Drop the evaluation deletion predicate | C2(e) | state became `within_budget`, not `no_budget` | yes |
| MUT-06 | Remove the no-budget short circuit and compute a general row | C3(a) | whole-row zero contract failed; non-zero time/rate fields appeared | yes |
| MUT-07 | Fall back to item-valuation currency for no-budget rows | C3(b) | `swedish_krona` appeared instead of `no_currency` | yes |
| MUT-08 | Serialize `allowed_seconds` as `Decimal` | C4(b) | exact integer-type assertion failed | yes |
| MUT-09 | Add nested `steps: []` to each serialized row | C4(a), C4(c) | exact keys and flat-envelope assertions both failed | yes |
| MUT-10 | Remove `Task.is_deleted` visibility filtering | C5(a) | two rows returned instead of one | yes |
| MUT-11 | Apply the request cap after deduplication | C5(e) | expected exception was not raised | yes |
| MUT-12 | Raise the request cap to 51 | C5(d) | expected exception was not raised | yes |
| MUT-13 | Skip rows with no evaluation | C5(f), C2(c) | one row returned instead of two; missing row lookup failed | yes |
| MUT-14 | Remove deterministic task ordering | C6(a), C6(b) | both ascending-order assertions failed | yes |
| MUT-15 | Use `datetime.now(timezone.utc)` instead of `ctx.now` | C7(b), once under `TZ=UTC` and once under `TZ=Europe/Stockholm` | both runs observed a 0-second rather than 60-second delta | yes |
| MUT-16 | Round the second-domain operand through minute-domain calculator helpers | C8(b) | `over_seconds` was 1 instead of 2 | yes |
| MUT-17 | Use the live matching basis-version rate instead of the loaded ORM snapshot | C8(c) | rate was 99999 instead of 37500 | yes |
| MUT-18 | Move the 50-ID cap check after the visibility query | C5(d) | one SQL statement executed instead of none | yes |
| MUT-19 | Transpose `over_cost_minor` and `projected_over_cost_minor` in the row dict | C8(e) | tuple was `(60, 51, 810, 4, over)`, not `(60, 4, 810, 51, over)` | yes |

Closed-set count: C1 `2` + C2 `3` + C3 `2` + C4 `2` + C5 `5` + C6 `1` +
C7 `1` + C8 `3` = **19**.

## Verification evidence

| Check | Command / result |
|---|---|
| Focused L1 | `PYTHONPATH=. pytest app/tests/integration/services/queries/item_economics/test_budget_signals_query.py -q` → **29 passed** |
| Declared L2 | `PYTHONPATH=. pytest tests/unit/domain/item_economics tests/integration/services/queries/item_economics tests/unit/routers/api_v1 tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs -q` from `app/` → **640 passed** |
| Repository L4 | Exactly one `PYTHONPATH=. pytest -m 'not e2e'` from `app/` → **21 failed / 2787 passed / 1 skipped** |
| L4 comparison | Durable 21-ID baseline additions `∅`; removals `∅` |
| Redis precondition | `PONG` |
| Static checks | Ruff check passed; Ruff format check reported already formatted; `git diff --check` clean |

The L4 run was authorized before execution because narrower evidence cannot establish the
repository-wide failing-ID delta. No retry or second L4 run occurred.

Final probe-restoration SHA-256 identities:

- service: `41934cd4491ab259edf8f87e232f4ecc91ec3f99eba27065f49b2d5895aff453`
- serializer: `bc1f56cc057317211a1298c2bac9387d754c6530fac29fffb7604cf6ce4ff577`
- budget-signal domain module: `1c0018ee84a4772f7a996eec9f0c2244f10a1ba21653f7fcce24a6e9d65ff070`
- final integration test: `0b4689f0a40411bd39b655a78cfccdb1ab9338b4efca4e27e7a5e51d032693d0`

## Architecture Graph assessment

The initialized graph was inspected under the architecture-graph operating policy. The
existing pending inferred node `projection-item-economics-task-budget-signals` already records
the capability, with four `reads_from` relationships plus its `contains` and `implements`
relationships. The fix changes test observability only, not architecture meaning, boundaries,
or impact. Therefore:

- reused nodes: `projection-item-economics-task-budget-signals` and its existing neighbors;
- created nodes: 0;
- new or changed relationships: 0;
- unresolved graph gaps relevant to this fix: 0;
- graph review or maintenance mutations: 0;
- architecture context writes: 0;
- decomposition budget depth: 0.

Graph permissions remain `review`; no inferred item was promoted, rejected, edited, deprecated,
or removed.

## Write and probe perimeter

Final session writes:

- `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py`
- Plan 2 tracker row in `master_plan.md`
- this Plan 2 review-log entry in `plans/plan_2.md`
- this handoff
- the required checkpoint commit

The checkpoint also carries the pre-existing, same-pipeline coordinator fold that this fix was
required to consume: `planning/intention.md`, `plans/plan_1.md`, `plans/plan_3.md`, the
coordinator portions already present in `master_plan.md` and `plans/plan_2.md`, the review-r1
prompt and handoff, and this fix prompt. Those contents were not authored or altered by this
fix session. The older waived re-projection queue prompt remains unstaged, as do all unrelated
graph, backfill, remaining-production-pressure, and frontend-handoff worktree changes.

Probe-only and byte-restored files:

- `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py`
- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/domain/item_economics/budget_signal.py`

No production file or graph file has a final fix-cycle delta. Pre-existing coordinator and
unrelated worktree changes were preserved.

## Divergences and judgment calls

None. The owner-approved reviewer correction was implemented exactly as folded; no new product,
contract, architecture, or scope decision was taken.
