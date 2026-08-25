---
plan: plan_3
role: implement
state: IMPLEMENTED
date: 2026-08-25
actor: Codex
---

# Plan 3 implementation handoff — route, HC-2a artifacts, and frontend handoff

Implemented the manager-only budget-signals route, the four HC-2a artifacts, the new dated
frontend handoff, and the phase-3 endpoint graph delta. The Phase 2 service and serializer were
not changed. The only production route judgment was to move the existing fixed
`budget-allocations` route together with the new fixed route ahead of every parameterized task
route: Plan 3 C1(b) requires both fixed routes to precede every `/tasks/{...}` route, while the
pre-existing evaluation routes were previously above the fixed batch route.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The phase is implemented under the ratified intention and recorded projection waiver.

## Gate and read-order evidence

- Intention header: `RATIFIED` in `planning/intention.md`.
- Plan 2 tracker state: `APPROVED` in `master_plan.md`; Phase 2 gate commit: `18f774f`.
- Plan 3 tracker state on close: `IMPLEMENTED`; projection waiver is recorded in Plan 3 §9.
- Architecture graph: initialized and valid at entry (`205` nodes, `314` edges); no context build
  was called, and no review or maintenance decision was enacted.
- Task 0 pre-production baseline was captured after writing the executable phase tests and before
  production route/README/handoff implementation:
  `PYTHONPATH=. pytest tests/unit/routers/api_v1/test_budget_signals_route.py tests/unit/routers/api_v1/test_item_economics_router.py tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs/test_budget_signals_handoff.py -q` → **16 failed / 112 passed**. The failures were the expected absent-route, absent-artifact, and absent-handoff reds; the README-path failure in that pre-production test draft was corrected before implementation evidence. This was a dirty test-only tree derived from `18f774f`; no fabricated clean-tree digest is claimed.
- Task 0 derived counts: mirror registry `26 → 27`; README Quick Index item-economics rows `26 → 27`; router `_ROUTES` `23 → 24`; HC-2a route artifacts exactly `4`; Plan 3 write table `4 MOD + 3 NEW = 7` paths.

## Contract resolution re-emitted

| Resolution | Contracts and application |
|---|---|
| selected | `01_architecture.md`, `04_context.md`, `05_errors.md` + `05_errors_local.md`, `07_queries.md` + `07_queries_local.md`, `08_domain.md`, `09_routers.md`, `15_testing.md`, `21_naming_conventions.md`, `22_performance.md`, `25_soft_delete.md`, `28_roles_permissions.md`, `29_feature_workflow.md` §B |
| selected | `46_serialization.md` + `46_serialization_local.md`: item-economics query services serialize inline and return dicts; the router passes the result through `build_ok` |
| excluded | `29_feature_workflow.md` §B step 6 and `docs/domains/item_economics/*`: Plan 3 §7A.6 explicitly makes `routers/README.md` plus the dated frontend handoff the documentation home |
| excluded | pagination, cache, rate-limit, scheduler, notification contracts: this endpoint is a capped id-batch read with no side effects |
| standing | fixed routes precede parameterized routes; ADMIN/MANAGER role gate; standard `build_ok`/FastAPI validation envelopes; frontend source handoffs are immutable |

## Row-by-row coverage map

Each criterion row is mapped to the executable assertion or the required gate evidence. The
assertion-shape column distinguishes an exact row assertion from a weaker collateral check.

| Row | Test/evidence | Assertion shape |
|---|---|---|
| C1(a) | `test_budget_signals_dispatches_batch_ids_and_uses_the_signal_service` | Exact: 200, callable identity, and ordered `query_params` list |
| C1(b) | `test_budget_signals_fixed_route_precedes_parameterized_task_routes` | Exact: signal immediately follows allocations and both precede every parameterized task route |
| C2(a) | `test_every_item_economics_route_retains_admin_and_manager_access` with the `_ROUTES` signal row | Exact parametrized 200 and one service call for ADMIN/MANAGER |
| C2(b) | `test_every_item_economics_route_rejects_worker_and_seller` with the `_ROUTES` signal row | Exact parametrized 403 and zero service calls for WORKER/SELLER |
| C2(c) | `test_router_route_pairs_match_the_authoritative_route_table` plus `_ALL_ROLE_ROUTES` remaining unchanged | Exact route-pair equality; the absent all-role row is represented by the unchanged table and the green all-role regression set |
| C3(a) | `test_budget_signals_rejects_more_than_fifty_ids_with_registered_identity` | Exact 422 `error`/`ok` envelope, stable prefix, no `detail`, and service entry before the service raises |
| C3(b) | `test_budget_signals_at_fifty_enters_the_service_once` | Exact 200 and one signal-service entry at the cap |
| C3(c) | `test_budget_signals_missing_ids_uses_fastapi_validation_envelope` | Exact 422 `detail[]`, no `error`, and zero service calls |
| C4(a) | `test_readme_quick_index_mirrors_every_shipped_route` | Exact README Quick Index set including the operation id row |
| C4(b) | `test_router_source_matches_the_hand_written_route_and_role_set` | Exact decorator/role pair, ADMIN/MANAGER only |
| C4(c) | `test_the_registry_ships_twenty_seven_routes` | Exact derived count and distinct-pair count, both 27 |
| C4(d) | `test_budget_signals_readme_detail_documents_the_ten_field_contract` | Exact heading once and all ten field rows, required markers, types, and enum prefixes |
| C5(a) | Final L4 stamp and its failure-ID delta | Gate evidence: full non-e2e suite compared with the durable 21-ID baseline; sibling route/query/doc surfaces included in the L2 and L4 commands |
| C5(b) | Checkpoint perimeter plus `git diff --name-only 18f774f..phase-3 checkpoint` | Gate evidence: phase implementation paths are the seven Plan 3 paths plus required tracker/plan/handoff closeout records; unrelated dirty bootstrap graph work is not staged |
| C6(a) | `test_budget_signals_handoff_has_metadata_and_five_answers` | Exact one dated handoff glob, intention path, and plan path |
| C6(b) | `test_budget_signals_handoff_pins_the_three_request_corrections` | Exact three required correction sentences |
| C6(c) | `test_budget_signals_handoff_has_metadata_and_five_answers` | Exact five headings with non-empty answer paragraphs |
| C6(d) | `test_budget_signals_handoff_records_the_served_contract` | Exact required D9/D10 and infeasible-production-time phrases |
| C6(e) | `test_budget_signals_handoff_records_the_served_contract` | Exact ten-field table header, four state members, four currency members, role, ordering, and timestamp wording |
| C6(f) | Pre-existing `test_retired_inline_refusal_identity_is_absent_from_live_sources` in `test_item_economics_handoff_accuracy.py` | Exact repository-wide absence guard; it remains green in the docs guard |

Reverse map: every test in the phase files is declared above or is an inherited collateral guard.
The four mirror tests map to C4(a–c) and the route-registration perimeter; the inherited router
tests map to C2(a–c), C5(a), and the standing route-surface contract. The six new route tests map
to C1/C3/C4(d); the three new handoff tests map to C6(a–e). No orphan test was added.

## Implemented perimeter

Plan 3 §4 seven paths, all changed as authorized:

1. `app/beyo_manager/routers/api_v1/item_economics.py` — import, fixed-route ordering, and new ADMIN/MANAGER route.
2. `app/beyo_manager/routers/README.md` — Quick Index row and endpoint detail section.
3. `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` — route row, count 27, and truthful test name.
4. `app/tests/unit/routers/api_v1/test_item_economics_router.py` — `_ROUTES` row only; `_ALL_ROLE_ROUTES` remains unchanged.
5. `app/tests/unit/routers/api_v1/test_budget_signals_route.py` — new route, precedence, cap/envelope, and README tests.
6. `app/tests/unit/docs/test_budget_signals_handoff.py` — new handoff contract tests.
7. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_budget_overrun_signal_20260825.md` — new dated handoff.

Required closeout records: Plan 3 tracker/review log, this implementer handoff, and the one graph
delta described below. No service, serializer, domain, migration, worker/seller route,
`_ALL_ROLE_ROUTES`, `from_frontend`, or `docs/domains/item_economics` file was changed.

## Named mutation ledger — closed set 9/9

Every probe ran at L1 on its named site, observed the red assertion below, and was immediately
reverted. Probe-only files are listed separately from the fix perimeter.

| Mutation | Site | Command/result | Observed red |
|---|---|---|---|
| MUT-01 | `item_economics.py`, move `route_get_task_budget_signals` below `route_get_task_price_scenario` | Two C1 tests: `1 passed / 1 failed` | C1(b) first assertion `signal_index == allocation_index + 1`: `22 == 17` failed; C1(a) stayed green as the plan predicted |
| MUT-02 | `item_economics.py`, new route dependency | `test_every_item_economics_route_rejects_worker_and_seller -k get-budget-signals`: `2 failed` | Both WORKER and SELLER expected 403, observed 200 |
| MUT-03 | `test_item_economics_router.py`, add signal to `_ALL_ROLE_ROUTES` | all-role signal parametrization: `4 failed` | ADMIN/MANAGER service identity assertions expected the budget-status service; WORKER/SELLER expected 200, observed 403 |
| MUT-04 | Phase 2 `get_task_budget_signals.py`, `_MAX_TASK_IDS = 51` | C3(a): `1 failed` | Expected 422, observed 200 for 51 ids |
| MUT-05 | `item_economics.py`, signal `task_ids: list[str] \| None = Query(None)` | C3(c): `1 failed` | Expected 422 FastAPI `detail[]`, observed 200 |
| MUT-06 | `routers/README.md`, delete Quick Index signal row | C4(a): `1 failed` | README set was missing `GET /api/v1/item-economics/tasks/budget-signals` |
| MUT-07 | mirror test `_EXPECTED_ROUTES`, signal role `_ALL_ROLES` | C4(b): `1 failed` | Router had ADMIN/MANAGER; hand-written table expected all four roles |
| MUT-08 | `routers/README.md`, delete `projected_over_cost_minor` detail row | C4(d): `1 failed` | Ten-field loop found zero `data.budget_signals[].projected_over_cost_minor` rows |
| MUT-09 | dated frontend handoff, delete correction (2) | C6(b): `1 failed` | Required `N rows means one row per **distinct** visible requested id` was absent |

Probe-only file list, each applied and reverted: `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py` (MUT-04), `app/beyo_manager/routers/api_v1/item_economics.py` (MUT-01/MUT-02/MUT-05), `app/tests/unit/routers/api_v1/test_item_economics_router.py` (MUT-03), `app/beyo_manager/routers/README.md` (MUT-06/MUT-08), `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` (MUT-07), and the dated frontend handoff (MUT-09). The final diff contains no probe mutation.

## Validation evidence

- L1 final targeted command: `PYTHONPATH=. pytest tests/unit/routers/api_v1/test_budget_signals_route.py tests/unit/routers/api_v1/test_item_economics_router.py tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs/test_budget_signals_handoff.py -q` → **128 passed**.
- Docs guard: `PYTHONPATH=. pytest tests/unit/docs/ -q` → **70 passed**.
- L2 command: `PYTHONPATH=. pytest tests/unit/domain/item_economics tests/integration/services/queries/item_economics tests/unit/routers/api_v1 tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/unit/docs -q` → **653 passed**.
- Final L4 command: `PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/` on checkpoint tree
  `c83c815` → **21 failed / 2800 passed / 1 skipped / 2 warnings**. The 21 failing IDs exactly
  match the durable baseline in `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7:
  `test_legacy_seat_height_without_height_maps_without_zero_values`,
  `test_legacy_multiline_rerun_is_idempotent_and_protects_existing_values`,
  `test_sign_in_user_preserves_custom_workspace_role_name`,
  the three `test_set_current_stored_amount_inventory_*` tests,
  `test_seed_item_economics_creates_requested_configuration_and_updates_owned_values`,
  `test_route_list_item_issues_forwards_client_id`,
  `test_route_delete_item_issues_forwards_ids`,
  `test_route_list_upholstery_inventories_passes_filter_query_params`,
  the two `test_batch_update_item_positions_*` tests,
  the two `test_batch_working_section_integration` tests,
  `test_worker_working_sections_excludes_counts_for_deleted_parent_tasks`,
  the two `test_working_section_ordering_*` tests,
  `test_split_services_return_disjoint_worker_shapes`,
  `test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`,
  `test_serialize_case_type_entry_returns_contract_fields`, and the two `test_audit_log` tests.
  Failure-ID delta against the 21-ID baseline: **additions ∅ / removals ∅**. Tree identity is
  checkpoint `c83c815` plus dirty tracked-tree diff digest
  `dc386467bd7d0653975786c52773a6c9ecf40dee0d8715219299978d09612d99`; phase files are clean
  relative to that checkpoint. The remaining dirty paths are pre-existing architecture/bootstrap
  work and were not staged by this session.
- No formatter/linter mutation was required; `git diff --check` is clean.

## Architecture graph delta

After read-only orientation and duplicate preflight, one `archgraph_apply_changes` batch applied:

- 1 inferred endpoint node: `endpoint-item-economics-task-budget-signals`.
- 1 `accepts` edge from that endpoint to the existing Phase 2 projection
  `projection-item-economics-task-budget-signals`.
- 1 `governed_by` edge to `decision-money-audience-admin-manager-only`.

No source links were recorded; evidence is symbol-anchored to
`route_get_task_budget_signals`. The existing pending Phase 2 projection node was reused and no
graph item was promoted, rejected, edited, deprecated, removed, or maintained. The graph write
was separate from unrelated dirty `.archgraph` bootstrap work, which was not staged or edited by
this session.

## Judgment calls and observations

- The Plan 3 C1(b) assertion is stronger than the pre-existing source layout: the two fixed batch
  routes must precede parameterized evaluation routes as well as the later budget-status,
  production-time, and price-scenario routes. The existing budget-allocation route was moved with
  the new route so the pair remains contiguous; endpoint semantics and the README route order are
  unchanged.
- The frontend handoff uses the exact three correction sentences and the five requested answers;
  it does not alter either published `from_frontend` handoff and does not name the retired inline
  identity.
- The service's 50-id behavior is tested through the real Phase 2 service with an empty session
  stub for the cap boundary; no Phase 2 production change was needed.

## Checkpoint and closeout

The required checkpoint commit is prefixed `CHECKPOINT (not approved):`. The final L4 tree
identity, clean-status assertion, failing-ID delta, and commit SHA are appended here immediately
after the final stamp.
