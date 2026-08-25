---
plan: plan_2
role: implement
round: 1
state: BLOCKED
date: 2026-08-24
actor: Codex
---

# Plan 2 implementation handoff — batched task budget signals

The phase implementation and focused evidence are complete, but Plan 2 is **not ready for
review** because the one closing repository stamp exposed an inherited contract-test perimeter
omission. The new query service returns the fixed flat ten-key signal row for every visible
requested task, including constructed `no_budget` rows, and the serializer extension is
additive. The criterion suite, mutation ledger, and bounded radius are green; the single closing
repository stamp has one added failure.

## ⚠ OWNER DECISIONS REQUIRED (1)

### OD-1 — authorize the inherited allocator-consumer contract-test amendment

- **Decision:** authorize the coordinator to add
  `app/tests/unit/services/queries/item_economics/test_production_time_contract.py` to the
  Plan-2 write perimeter and change C19's expected allocator-consumer set from the two existing
  services to those two plus `get_task_budget_signals`.
- **Why:** the plan explicitly requires the new service to call `divide_production_budget`, and
  C19 is an inherited source scan whose closed set predates this phase. The only added L4 failure
  is that exact set assertion.
- **Recommendation:** approve. This preserves C19's architectural purpose (one allocator; query
  services only consume it) and acknowledges the planned third consumer. Hiding the call through
  an alias would satisfy the text scan while violating the executor doctrine.
- **Effect if deferred:** keep Plan 2 at `PROMPT_READY`; no checkpoint or review dispatch.

## Outcome

- Added `get_task_budget_signals(ctx)` with a raw 50-id pre-query cap, workspace/deletion
  visibility, deterministic `Task.client_id` ordering, batch loads, live worked seconds at
  `ctx.now`, sibling-equivalent status selection, reconciled typicals, the four-argument
  allocator call, and phase-1 signal computation from the committed evaluation snapshot.
- Added `serialize_budget_signal` and `serialize_budget_signals`. All ten fields are copied
  through without defaulting, coercion, nesting, or Decimal serialization.
- Added 28 criterion-local integration tests: exactly one named test for every row C1(a)–C8(d).
- Kept the no-evaluation status-resolution branch structurally equivalent to the sibling even
  though the wire row can only observe the resulting `no_budget` branch.

## Contract resolution

Both the canonical contract set and the repo-local extensions were read. Repo-local rules bind
where they extend the canonical text; no additional contract was needed beyond the master-plan
selection.

| Status | Contract | Application in this phase |
|---|---|---|
| selected | `01_architecture.md` | New query stays in `services/queries`; serializer stays in the domain serializer module. |
| selected | `04_context.md` | `ServiceContext` supplies query params, workspace, session, and the sole clock `ctx.now`. |
| selected | `05_errors.md` + `05_errors_local.md` | Raw-list cap raises `ValidationError`; the stable identity is the message prefix, with no `code` field. |
| selected | `07_queries.md` + `07_queries_local.md` | Batched read-service shape; pagination override does not apply to an id batch. |
| selected | `08_domain.md` | Phase-1 rule remains pure; phase 2 consumes it without moving SQLAlchemy into the domain rule. |
| selected | `09_routers.md` | No route work in phase 2; the service returns the envelope that phase 3 will pass to `build_ok`. |
| selected | `15_testing.md` | Mirrored integration-test location and disposable-database fixture model. |
| selected | `21_naming_conventions.md` | Fixed `get_task_budget_signals` and `serialize_budget_signal(s)` names. |
| selected | `22_performance.md` | C1(b) proves statement count is constant for one versus three tasks. |
| selected | `25_soft_delete.md` | Task and dependent reads apply their fixed workspace/current/deletion predicates. |
| selected | `28_roles_permissions.md` | Fixture identity truthfully uses `manager`; role enforcement remains phase-3 router work. |
| selected | `29_feature_workflow.md` §B | Existing-domain endpoint workflow; this phase implements only its service seam. |
| selected | `46_serialization.md` + `46_serialization_local.md` | Local rule binds: the query service serializes inline and returns its dict envelope. |
| excluded | `29_feature_workflow.md` §B step 6 / README rule 11 | Intention §7A.6 reserves route documentation and the dated frontend handoff for phase 3 and forbids changing `docs/domains/item_economics/*`. |
| excluded | `07_queries_local.md` pagination; contracts `12`, `18`, `37`, `47` | No pagination, cache, rate limit, scheduler, or notification is in scope. |
| local | Pipeline charter and master-plan §9 | Test-first evidence, exact mutation set, cleanup ownership, perimeter, and one L4 stamp. |

No product or architecture judgment was delegated to this implementation. Fresh ids use the
fixture token and scalar values above sibling-reserved values. MUT-06 used the explicitly
delegated arbitrary rate `Decimal("3.7500")` only while the probe was active.

## Task 0 and honest red baseline

The plan-1 pure probe reproduced every P-A–P-K figure. The additional C1(a) derivation through
the real allocator produced allowances A/B = `2400/1200`, B commitment `1200`, remaining pot
`1200`, and therefore `(projected_over_seconds=0, within_budget)`. With typicals removed, the
same task produced the specified `(600, projected_over)` counterfactual.

Reading and exercising the live-time loader confirmed that one user's one open `WORKING`
record adds the full interval share: advancing `ctx.now` by 60 seconds adds exactly **60 live
worked seconds**.

The test file was written before the service. Its first run collected all 28 tests and produced
**28 failures**, each an expected `ModuleNotFoundError` for the absent
`get_task_budget_signals` module. No fixture, collection, import-chain, or environment defect
obscured that baseline.

## Criterion trace map

| Criterion | Exact pytest function |
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

Every test maps to exactly one criterion row; there are no candidate or convenience tests in
the phase file.

## Mutation ledger

The mutation base was `HEAD bd83950355fc5f70806ad2a5971317a7815c6485`. Stable restored
md5 values were service `f3cc04163839ebc2de639ef0283f0cb8`, serializer
`8038b54147b0368f3c9d3f2b46b8dff9`, phase-1 rule
`c94fec7247673c0891769246b5dadf02`, and phase test
`17340f8a50fe18d5dafb9d1ff8bf6767`. Every probe was applied alone at L1 hypothesis scope,
observed, reverted, and md5-verified before the next probe.

| Probe | Site / change | Observed result |
|---|---|---|
| MUT-01 | Allocator receives `None` typicals. | C1(a) failed: actual `(600, projected_over)` instead of `(0, within_budget)`. |
| MUT-02 | Evaluation select moved into the task loop. | C1(b) failed: three-task request executed 15 statements versus 13 for one task. |
| MUT-03 | Local budget statuses contain only `OK`. | C2(b) failed with constructed `no_budget` zeroes instead of the negative-allowance forecast. |
| MUT-04 | Removed current-evaluation superseded predicate. | C2(d) failed: superseded evaluation produced a budget-bearing row. |
| MUT-05 | Removed evaluation deletion predicate. | C2(e) failed: deleted evaluation produced a budget-bearing row. |
| MUT-06 | No-budget task ran the general path with rate `3.7500`. | C3(a) whole-row equality failed; actual worked seconds became 1200 instead of constructed zero. |
| MUT-07 | No-budget currency fell back to item valuation. | C3(b) failed: `swedish_krona` replaced `no_currency`. |
| MUT-08 | Serializer passed allowed seconds through `_decimal`. | C4(b) exact-int assertion failed. |
| MUT-09 | Serializer added `steps: []`. | C4(a) exact ten-key assertion failed. |
| MUT-10 | Removed task deletion visibility predicate. | C5(a) failed with 2 rows instead of 1. |
| MUT-11 | Applied cap to `set(task_ids)`. | C5(e) failed because 51 duplicate raw ids did not raise. |
| MUT-12 | Raised maximum to 51. | C5(d) failed because 51 raw ids did not raise. |
| MUT-13 | Skipped tasks without an evaluation. | C5(f) failed with 1 row instead of 2. |
| MUT-14 | Removed task query ordering. | C6(a) and C6(b) both failed their ascending id assertions. |
| MUT-15 | Live loader used `datetime.now(timezone.utc)`. | C7(b) failed its exact +60 delta under both `TZ=UTC` and `TZ=Europe/Stockholm`. |
| MUT-16 | Phase-1 definition rounded through minute-domain helpers. | C8(b) failed: over seconds became 1 instead of 2. |
| MUT-17 | Service used the loaded live basis rate. | C8(c) failed: ten-thousandths became 99999 instead of snapshot-derived 37500. |
| MUT-18 | Raw-list cap moved after the visibility query. | C5(d) failed because the statement recorder was non-empty before `ValidationError`. |
| EP-01 | Phase-1 money call received `Decimal(over_seconds)`. | C8(a) failed by surfacing calculator `TypeError` through the service, as required; no identity translation was added. |
| EP-02 | Service used `live_seconds.get(step.client_id, 0)`. | Declared blind spot confirmed: the full phase file stayed green, **28 passed**. The strict index was restored. |

MUT-16 and EP-01 temporarily touched `budget_signal.py` only as declared phase-1 definition-site
probes; that file is byte-identical to its pre-session value and is not an implementation
perimeter change.

## Verification

| Level | Command / result |
|---|---|
| Formatting | `ruff check` and `ruff format --check` on the three phase files: passed. |
| L1 | `PYTHONPATH=. pytest tests/integration/services/queries/item_economics/test_budget_signals_query.py -q`: **28 passed**. |
| Mutation | **18/18 named mutations executed and red; 2/2 exception probes executed**, with EP-02 the specified green blind spot; every probe restored. |
| L2 | Master-plan bounded radius: **639 passed** in 6.88s. |
| L4 | Exactly one `PYTHONPATH=. pytest -m 'not e2e'`: **22 failed / 2785 passed / 1 skipped**. Addition: `tests/unit/services/queries/item_economics/test_production_time_contract.py::test_c19_division_has_one_allocator_and_services_only_consume_it`; removals `∅`. |

Redis answered `PONG` immediately before the L4 run. Application and test files were unchanged
after that run; this blocker record and the reverted tracker claim are the only later closeout
documentation edits. The added ID asserted that the allocator-importing services were exactly
`{get_task_budget_allocations, get_task_production_time}`; the actual set also contained the
planned `get_task_budget_signals` service.

## Architecture graph

Read-only close inspection used the initialized valid graph and the existing allocation
projection, allocation endpoint, and admin/manager money-audience decision anchors. The
implemented tree proves a candidate `projection` for the new service, but this session's
prompt also explicitly says not to modify or adjudicate the graph. No graph write, review
promotion, rejection, or adjudication was performed. The coordinator/reviewer can route the
candidate delta under the normal graph approval workflow.

## Write perimeter and checkpoint

Implementation perimeter:

1. new `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py`;
2. modified `app/beyo_manager/domain/item_economics/division_serializers.py`;
3. new `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py`;
4. modified phase-2 tracker row in `master_plan.md`;
5. appended implementation entry in `plans/plan_2.md`;
6. new this handoff.

Probe-only, fully restored file: `app/beyo_manager/domain/item_economics/budget_signal.py`.
Unrelated pre-existing worktree content in `.archgraph/`, `docs/archgraph-anchor-observations.md`,
the ratified intention and coordinator artifacts, the frontend-to-backend handoff, and
`remaining_production_pressure/` was preserved and excluded from the checkpoint.

No checkpoint was made: the prompt authorizes the `IMPLEMENTED` tracker transition and required
checkpoint only on success, and the added L4 ID blocks success.

Next step after OD-1 approval: coordinator folds the single inherited-test perimeter amendment
and dispatches a bounded continuation/fix cycle. Until then, Plan 2 remains `PROMPT_READY` and
the implementation stays uncommitted for inspection.
