---
plan: 2
role: implement
round: 1c
date: 2026-08-19
state: IMPLEMENTED
actor: Codex
---

# Phase 2 implement r1c handoff — task price-scenario read model

Phase 2 is implemented. The manager-only endpoint now publishes the task's saved valuation,
live cost model, median-substituted task typical, break-even anchors, and slider domain. The
implementation touched all **11 of 11** application/test/documentation files in plan 2 §2's
roster, plus this required handoff and the required additive Architecture Graph record.

## ⚠ OWNER DECISIONS REQUIRED (0)

No owner decision is required.

## What was built

- `get_task_price_scenario.py` composes the existing task budget status and task/item
  resolution with the current valuation, live configuration, the shared typical-time
  statement, phase 1's pure price helpers, the status/binding branches, `can_commit`, and
  the configuration fingerprint.
- `serialize_task_price_scenario` publishes the exact manager payload service-side.
- `GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario` is ADMIN/MANAGER only
  and delegates by service identity through the shared runner.
- All four route-mirror artifacts moved together; the registry count is **25 → 26**.
- The new integration suite enumerates the phase's status, admission, typical-time,
  binding, byline, fingerprint, task-boundary, and suggestion contracts.
- All four carried exceptions landed. No executable line changed in
  `price_scenario.py`, `calculator.py`, or `cases/serializers.py`.

## Delegations

### D-5 — participating set and median

Chosen: import private `_median` and `_step_state_is_excluded`, and use public
`group_steps_by_section`. This preserves the single implementation of median and the exact
state-value semantics, including plain-string states. `divide_production_budget` is never
called.

### D-6 — committed evaluation/status

Chosen: call `get_task_budget_status`, following the production-time read-model precedent.
This reuses the existing committed-evaluation, item-binding, status, and workspace boundary.

### D-7 — serialization site

Chosen: service-side serialization, following `get_task_production_time`. The router remains
a simple `_run(get_task_price_scenario, ...)` mount and the declared perimeter remains exact;
the router-side STOP was not entered.

## Criterion → test map

| Criterion | Automated test(s) |
|---|---|
| C1 | `test_c1_status_matrix_has_twelve_exact_rows` (12 rows); `test_c1_b6_b7_purchase_term_without_cost_collapses_all_blocks` (2 rows) |
| C2 | `test_c2_can_commit_uses_each_live_admission_condition` (10 rows, including null-price/no-valuation and committed-status/live-expired asymmetries) |
| C3 | `test_c3_zero_typical_is_not_usable_and_uses_the_median` |
| C4 | `test_c4_even_median_is_quantised_once_per_substituted_section` |
| C5 | `test_c5_each_excluded_state_removes_its_section` (SKIPPED/CANCELLED/FAILED); `test_c5_deleted_steps_do_not_create_a_participating_section` |
| C6 | `test_c6_nonempty_no_evidence_is_estimated_zero`; `test_c6_empty_participating_set_is_estimated_zero`; `test_c6_no_evidence_keeps_null_anchor_members_and_no_domain` (non-empty and empty rows) |
| C7 | `test_c7_saved_absence_null_price_and_missing_author` |
| C8 | `test_c8_fingerprint_uses_full_ids_fixed_order_and_changes_by_model` |
| C9 | `test_c9_non_bound_binding_governs_the_full_payload` (detached/mismatched) |
| C10 | `test_c10_task_resolution_is_workspace_scoped_and_hides_deleted` (unknown/deleted/cross-workspace) |
| C11 | `test_every_item_economics_route_rejects_worker_and_seller` (the new route contributes WORKER and SELLER 403 rows) |
| C12 | `test_readme_quick_index_mirrors_every_shipped_route`; `test_router_source_matches_the_hand_written_route_and_role_set`; `test_the_registry_ships_twenty_six_routes` |
| C13 | `test_price_scenario_route_mounts_the_price_scenario_service` |
| C14 | `test_c14_query_service_does_not_call_the_budget_divider` |
| C15 | `test_c10_task_resolution_is_workspace_scoped_and_hides_deleted` owns `try/finally` cleanup and verifies zero `tasks`/`workspaces` residue |
| C16 | `test_quantity_zero_falls_back_to_a_divisor_of_one`; `test_c16_discriminating_literal_is_exact`; `test_c16_reciprocal_comment_pairs_are_present` |
| C17 | No test by design: purity was **not** extended to the I/O query service, as C17 decides. Relative-import handling remains closed rather than carried forward. |
| C18 | `test_c18_suggested_price_rounds_to_the_domain_step`; `test_c18_null_domain_forces_null_suggestion_with_break_even` |
| C19 | `test_c19_missing_typical_statement_row_uses_defensive_lookup` |

## Mutation ledger

One named mutation exists in plan 2. It was applied at the definition site and measured by
running the whole unit file, never `-k` or a node id.

| Site | Contract side | Mutation side | Complete observed-red set | Revert SHA-256 |
|---|---|---|---|---|
| `price_scenario.py:slider_domain` definition, `max(1, quantity) → max(6, quantity)` | `slider_domain(8_919, 0, 0) = SliderDomain(step_minor=110, min_minor=3_080, max_minor=12_100)` | `SliderDomain(step_minor=114, min_minor=3_078, max_minor=12_084)` | `test_quantity_zero_falls_back_to_a_divisor_of_one` only; 52 other tests passed | `948a7a0f990ad409f26ff97a173fc0eeb2211970d0c9d5e7e1059277aba04542` |

After the hash-matching revert, the whole file passed **53/53**.

## Reciprocal pairs and carried exceptions

Both pairs land together in this handoff's single checkpoint commit, whose subject is
`CHECKPOINT (not approved): implement task price scenario read model`:

1. `_shape_error`:
   `app/beyo_manager/domain/item_economics/price_scenario.py` ↔
   `app/beyo_manager/domain/item_economics/calculator.py`.
2. `serialize_user_light`'s three-key shape:
   `app/beyo_manager/domain/item_economics/serializers.py` ↔
   `app/beyo_manager/domain/cases/serializers.py`.

The remaining exception replaces the inert quantity-zero assertion with the exact
`SliderDomain(110, 3_080, 12_100)` literal. The three exception production files contain
comment-only diffs; no executable line changed.

## Verification

Focused phase suite from `app/`:

```text
PYTHONPATH=. JWT_SECRET_KEY=<test value> .venv/bin/pytest -q \
  tests/integration/services/queries/item_economics/test_price_scenario_query.py \
  tests/unit/domain/item_economics/test_price_scenario.py \
  tests/unit/routers/api_v1/test_item_economics_router.py \
  tests/unit/routers/test_phase9_item_economics_route_mirror.py
215 passed in 1.61s
```

Full non-E2E suite:

```text
Baseline: 2373 passed, 26 failed, 1 deselected
After:    2425 passed, 26 failed, 1 deselected, 2 warnings in 138.40s
Delta:      +52 passed, 0 new failures
```

The inherited failure count stayed exactly 26, so no failure-ID repeat was required. An
initial run against the explicitly selected `.env.testing` profile was discarded because
that database is schema-stale (`user_shift_state_records.transition_reason` is absent); the
prompt's prescribed default profile produced the baseline-matching result above.

Lint and formatting:

```text
.venv/bin/ruff check <all 10 Python files in the roster>
All checks passed!

.venv/bin/ruff format --check \
  beyo_manager/services/queries/item_economics/get_task_price_scenario.py \
  tests/integration/services/queries/item_economics/test_price_scenario_query.py
2 files already formatted
```

The seven pre-existing modified Python files are not globally Ruff-formatted at baseline.
Formatting them would rewrite executable lines outside the additive/one-row/comment-only
authorizations (including `calculator.py`), so the stronger line-scoped perimeter was
preserved. The new files are fully formatted and Ruff lint is clean across every touched
Python file.

## Architecture Graph delta

The graph was valid at revision
`42c184f31791458db8fb85fcd927eb790bbe2320486237186ef2cac10492f485`.
Duplicate preflight found all candidates new. One dry-run-clean additive batch then applied:

- inferred projection `projection-item-economics-task-price-scenario`;
- inferred endpoint `endpoint-item-economics-task-price-scenario`;
- inferred `endpoint --accepts--> projection` relationship;
- four source links covering the query service/integration contract and route/identity test.

The deliberately separate phase-1 node
`source-file-item-economics-price-scenario` was not reused. Closing revision is
`ea100e058ff2be39b77ca71dc44c52976cbed24644b3bb31204a9ca91ecba5c8`:
186 nodes, 277 edges, 0 diagnostics, 0 stale nodes, and 9 pending review items. No review,
promotion, rejection, maintenance mutation, or context artifact was attempted.

## STOPs and scope

No STOP was hit. In particular, D-7's router-side STOP was avoided by the service-side
choice. No purity assertion was extended to the query service. The master-plan tracker and
plan 2 Review log were not edited, as required.

## Full write perimeter

Closeout used repository-root `git status --porcelain --untracked-files=all` and
`git diff --name-only`. The implementation roster is exactly **11/11**:

1. `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py`
2. `app/beyo_manager/domain/item_economics/serializers.py`
3. `app/beyo_manager/routers/api_v1/item_economics.py`
4. `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py`
5. `app/beyo_manager/routers/README.md`
6. `app/tests/unit/routers/api_v1/test_item_economics_router.py`
7. `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py`
8. `app/tests/unit/domain/item_economics/test_price_scenario.py`
9. `app/beyo_manager/domain/item_economics/calculator.py`
10. `app/beyo_manager/domain/item_economics/price_scenario.py`
11. `app/beyo_manager/domain/cases/serializers.py`

Required closeout artifacts outside that application roster:

12. `.archgraph/architecture.yml`
13. `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase2_implement_r1c_handoff.md`

The same status command reported two concurrent, unrelated untracked files under
`live_clock_for_working_time_economics/planning/`. This session did not create, read, edit,
stage, or commit them.
