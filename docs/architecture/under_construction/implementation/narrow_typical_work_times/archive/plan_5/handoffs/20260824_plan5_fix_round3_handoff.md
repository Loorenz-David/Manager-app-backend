---
plan: plan_5
role: fix
state: IMPLEMENTED
date: 2026-08-24
actor: Codex
---

# Plan 5 fix round 3 handoff

## Summary

Implemented the two blocking review findings and the requested one-line note closures. The
application fix perimeter is one test file; production code is unchanged. C8 now drives
`get_task_price_scenario` end to end on `seed_divergent_category_task` and asserts the served
payload. C1(b) now uses a real SQL-backed boundary fixture and the prescribed fake datetime.

## Gate and baseline

- Plan 5 opened at `CHANGES_REQUESTED`; master tracker row 5 was `CHANGES_REQUESTED`.
- `planning/intention.md` header was `RATIFIED`.
- `git status --porcelain -- app/` was empty before the first edit.
- `redis-cli ping` returned `PONG`.
- Pre-edit phase baseline, from `app/` with `BEYO_TEST_SLOT=main PYTHONPATH=.`:
  the three phase files (`test_narrowed_price_scenario.py`, `test_price_scenario_query.py`,
  `test_narrowed_task_economics.py`) passed **83** with no failures.
- The full-suite pre-edit red baseline is honestly carried by citation from the round-2 handoff:
  **2707 passed / 21 failed / 1 skipped**, with the same 21-ID set used for the closing delta.
  No pre-edit L4 was rerun because the charter permits one authoritative L4 at close and this
  round made no production edit.

## B1 and B2

### B1 — C8(c), the upstream spec edge

The former direct `_typical_block` calls in C8 were replaced with end-to-end
`module.get_task_price_scenario(context(task_id))` calls for both the categorized and plain tasks.
The narrowed assertion is now on the served payload: `narrowed["typical"]["total_seconds"] == 600`;
the same served payload proves the plain section-wide value is `375`.

Named mutation: `get_task_price_scenario.py`, **call site** at the third argument, replacing
`budget_status.typical_filter_spec` with `None`.

Observed red on the new C8 test: `assert 375 == 600` at the served payload assertion. This is the
required numeric red, and the row is alone in the test's narrowing assertion path.

### B2 — C1(b), the composed clock/boundary contract

The test now uses `seed_divergent_category_task` and the real database session. It freezes
`ctx.now` at `2026-10-30 00:00 UTC`; the fixture's completed history has
`max(closed_at) == 2026-08-01 00:00 UTC`, exactly `ctx.now - 90 days`. It monkeypatches
`beyo_manager.services.queries.working_sections.get_working_section_typical_times.datetime` with
the prescribed fake whose successive `now()` values are `ctx.now - 1 second` and
`ctx.now + 1 second`.

The contract assertions are byte-identical serialized typical blocks and exact total `600` on
both calls. With the named mutation at the price-scenario call site (dropping `now=ctx.now`), the
first call includes the boundary group and returns `600`; the second excludes it and returns `0`.
Observed red: `assert 600 == 0` on the exact numeric assertion, not on the kwargs/spy list.

Prescribed C1(b) elements, declared one by one:

- fake `datetime`: implemented on the working-sections module attribute;
- boundary group: supplied by the divergent fixture at `2026-08-01 00:00 UTC`, with frozen
  `ctx.now` at `2026-10-30 00:00 UTC`;
- exact contract literals: `600` and `600`;
- exact mutation literals: `600` then `0`.

## Note dispositions

- **N1:** C4 now asserts both `total_seconds` and `is_estimated`. The mixed `600/900/None` case
  is explicitly estimated because one selected value is unusable.
- **N2:** no new C6 coverage. Row (c) remains a hand-built `TaskTypicalSelection` and therefore
  reads constants supplied by that test (`icat_chair`-shaped category and count). Rows (a)/(b)
  remain the genuine serializer-shape guards; phase 4's approved count-only guard owns the
  participating-count class.
- **N3:** C8 now asserts the served price-scenario payload, resolving the wire-reach portion.
  The row's named production-time `sections[].typical` triple is still not asserted by C8(b); this
  residual surface divergence is declared rather than adding coverage in a fix round.
- **N4:** C1(c) now asserts the delegating spy was invoked before asserting that no `now` kwarg was
  captured.
- **N5:** `section_ids` is intentionally built from `groups`, not `steps`. The production path is
  behaviourally identical because deleted steps are filtered before grouping, and the groups form
  is safer against the phase's fake sessions. This divergence is declared.
- **S1:** no test was added. §2B S-7 SQL scoping remains a query-cost property with no wire
  observable and no owner; the plan's no-owner disposition is preserved.

## Task 0 coverage map — criterion row to test

Each criterion row is listed separately. “Exact” means the assertion shape matches the plan row;
“weaker/deviation” is declared rather than silently presented as exact.

| criterion row | discharging test | assertion shape |
|---|---|---|
| C1(a) | `test_c1a_typical_block_passes_the_request_clock_to_the_statement` | exact `now=ctx.now` and `specs=()` through a delegating spy |
| C1(b) | `test_c1b_same_frozen_context_produces_byte_identical_typicals` | exact boundary fixture, fake clock, exact numeric totals, byte-identical served typical |
| C1(c) | `test_c1c_working_section_typicals_keep_the_default_statement_clock` | exact no-`now` kwarg plus spy-invoked guard |
| C2(a) | `test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals[steps0-rows0-expected0]` | exact `true`, `0`, `0` |
| C2(b) | same parametrized test, `steps1/rows1/expected1` | exact `true`, one `None`, `sections_without_sample == 1` |
| C2(c) | same parametrized test, `steps2/rows2/expected2` | exact `true`, one zero, `sections_without_sample == 1` |
| C2(d) | `test_c2d_section_wide_uniform_does_not_make_is_estimated_true` | exact `false` and count `0` |
| C3 | `test_c3_counts_only_participating_selected_typicals` | exact participating count `3` and unusable count `2` |
| C4(a) | `test_c4_price_terminal_and_median_are_duration_values[rows0-0-True]` | exact terminal `0` and `is_estimated: true` |
| C4(b) | same parametrized test, `rows1-2250-True` | exact `2250`; `is_estimated` is also asserted true because the `None` section fires the estimate flag |
| C5(a) | `test_c5_three_surfaces_use_the_same_published_literal` | exact production-time triple `(600, item_narrowed, 5)` |
| C5(b) | same C5 test | exact price total `600`, asserted against a literal and participating fixture |
| C5(c) | same C5 test | exact budget-allocation triple `(600, item_narrowed, 5)` |
| C6(a) | `test_c6_price_and_production_resolution_have_the_exact_six_key_shape` | exact six-key price serializer set |
| C6(b) | same C6 test | exact six-key production serializer set |
| C6(c) | same C6 test | exact values; hand-built selection constants declared under N2 |
| C7(a) | `test_c7_typical_block_delegates_statistics_and_has_no_private_terms` | exact one-call spy plus source-term absence |
| C7(b) | `test_c7_item_economics_fork_sweep_finds_only_the_shared_median` | exact root/term equality and non-empty walk |
| C7(c) planted proof | same C7 sweep with temporary private ladder | observed red: extra `_mutation_probe_private_ladder.py` hit |
| C7(d) planted proof | `test_c13c_excluded_state_logic_has_one_shared_production_owner` with temporary enum copy | observed red: extra `_mutation_probe_excluded_states.py` hit |
| C8(a) | `test_c8_divergent_fixture_measures_narrowed_600_against_section_375` | exact served narrowed total `600` |
| C8(b) | same C8 test | served section-wide total `375`; weaker than the row's named production-time triple, declared under N3 |
| C8(c) | same C8 test | exact end-to-end edge observation; call-site `None` mutation reddens `375 == 600` |

Reverse map: the 15 test functions in `test_narrowed_price_scenario.py` all appear above against
at least one row; the only test in `test_narrowed_task_economics.py` used this round is the C7(d)
planted proof. No orphan test was added.

## Mutation ledger

Summands: `C1 2 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 2 = 15` named mutations;
`C7(c) 1 + C7(d) 1 = 2` planted-defect probes; **17 total**.

| row | site and probe | observed red |
|---|---|---|
| C1(i) | `get_task_price_scenario.py` call site: drop `now=ctx.now`; C1(a) and C1(b) | C1(a) `KeyError: 'now'`; C1(b) numeric `assert 600 == 0` |
| C1(ii) | `get_working_section_typical_times.py:192` call site: pass `now=ctx.now`; C1(c) | `assert 'now' not in captured` |
| C2(i) | `_typical_block` definition: remove empty-set disjunct; C2(a) | `(0, False, 0, 0) != (0, True, 0, 0)` |
| C2(ii) | `_typical_block` definition: flag section-wide basis as estimated; C2(d) | `assert True is False` |
| C2(iii) | `_typical_block` definition: change `<= 0` to `< 0`; C2(c) | `is_estimated`/count tuple differed: `(1200, False, 0, 2)` vs expected |
| C3(i) | `_typical_block` definition: `sections_total = len(selection.selected)`; C3 | `assert 4 == 3` |
| C3(ii) | `_typical_block` definition: count narrowed-thin evidence; C3 | `assert 3 == 2` |
| C4(i) | `_typical_block` fallback call site: `terminal=Fraction(1, 1)`; C4(a) | `assert 3 == 0` |
| C4(ii) | `typical_filters.apply_business_fallback` definition: `fallback = terminal`; C4(b) | `assert 1500 == 2250` |
| C5(i) | `_typical_block` call site: use all grouped sections instead of `participating_sections`; C5(b) | `assert 750 == 600` |
| C5(ii) | `_typical_block` definition: resolve from section-wide evidence; C5(b) | `assert 375 == 600` |
| C6(i) | `serializers.py` definition: omit `comparability_profile` from price resolution; C6(a) | expected six-key set missing `comparability_profile` |
| C7(i) | `_typical_block` definition: replace fallback delegation with private ladder; C7(a) | spy calls `[]` vs expected ` [([600], Fraction(0, 1))]` |
| C8(i) | `_typical_block` definition: `specs = ()`; C8(a) | served `assert 375 == 600` |
| C8(ii) / B1 | `get_task_price_scenario.py` call site: pass `None` for status-derived spec; C8(c) | served `assert 375 == 600` |
| C7(c) planted | temporary private `_median` ladder under the swept root; C7(b) | extra `_mutation_probe_private_ladder.py` hit |
| C7(d) planted | temporary enum-member excluded-state copy under `app/beyo_manager`; C13(c) | extra `_mutation_probe_excluded_states.py` hit |

Every probe was applied, run at L1/L2, observed red, reverted, and checked. No probe touched the
database outside the test transaction/fixture cleanup.

## Perimeter and md5

Fix writes this round:

- `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_5.md`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- this handoff

Mutation-probe files, applied and reverted, separate from the fix writes:

- `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` — final md5
  `213a38a03f7ffaafe954bae68d4da16a`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` —
  final md5 `48833e4438348f2d01bcf2d00f64bb20`
- `app/beyo_manager/domain/item_economics/typical_filters.py` — final md5
  `c888e3d24748edfa6fe22a0c24605b45`
- `app/beyo_manager/domain/item_economics/serializers.py` — final md5
  `e4e01db8c82421d7d00ce9e049441aaa`
- temporary planted probe `app/beyo_manager/services/queries/item_economics/_mutation_probe_private_ladder.py` —
  deleted after red; absent from the final tree
- temporary planted probe `app/beyo_manager/services/queries/item_economics/_mutation_probe_excluded_states.py` —
  deleted after red; absent from the final tree

Final application diff: only the intended test file. `.archgraph/` was not read for state and was
not touched; it remains the owner's closed perimeter under D31.

## Verification and closing stamp

- L2 `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -q tests/integration/services/queries/item_economics`:
  **159 passed**.
- Focused Ruff on the changed test file: **All checks passed**.
- Authoritative L4, `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'`:
  **2707 passed / 21 failed / 1 skipped / 2 warnings** in 51.95s.
- Failure-ID delta against the round-2 baseline: **∅/∅**. The 21 unchanged IDs are:
  `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_seat_height_without_height_maps_without_zero_values`,
  `tests/unit/domain/shopify/test_dimension_migration.py::test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values`,
  `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`,
  `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_promotes_expected_candidates`,
  `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_demotes_low_priority_available_first`,
  `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py::test_set_current_stored_amount_inventory_noop_emits_no_events`,
  `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py::test_seed_item_economics_creates_requested_configuration_and_updates_owned_values`,
  `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`,
  `tests/unit/test_items_router.py::test_route_list_item_issues_forwards_client_id`,
  `tests/unit/test_items_router.py::test_route_delete_item_issues_forwards_ids`,
  `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rewrites_sort_order_and_worker_view_follows_it`,
  `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py::test_reorder_rejects_payload_not_matching_active_set`,
  `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_batch_flag_round_trips_and_new_step_snapshots_follow_section_value`,
  `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events`,
  `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py::test_worker_working_sections_excludes_counts_for_deleted_parent_tasks`,
  `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`,
  `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py::test_batch_update_item_positions_rolls_back_when_any_item_is_missing`,
  `tests/integration/test_audit_log.py::test_write_audit_from_event_inserts_row`,
  `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`,
  `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`,
  `tests/integration/test_audit_log.py::test_detail_defaults_to_empty_dict`.

## Architecture graph and owner decisions

No architectural boundary changed, so no graph delta was recorded and `.archgraph/` remains closed.

⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required. The residual C8(b) surface divergence and the N2/N5 declarations
are coordinator-fold items, not blockers for this fix cycle.

State: `IMPLEMENTED`.
