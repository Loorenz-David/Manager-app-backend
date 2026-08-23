---
plan: plan_3
role: implementer
round: 1
date: 2026-08-23
actor: Codex
state: IMPLEMENTED
---

# Plan 3 implementation handoff — `TaskBudgetStatus` carries the derived spec

Phase 3 is implemented as an additive internal carrier: manager and worker query services now derive the typical-filter specification from the loaded active PRIMARY item and carry it through the shared status model. The manager and worker payload contracts remain unchanged, including the existing live-clock goldens. Focused tests and the authoritative non-e2e suite are complete; the full-suite failure set is unchanged from the approved baseline.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs you.

## Task 0 — transcription and red baseline

The §6/§6A contract was transcribed into `app/tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py`. Before implementation, the new file produced **9 failed / 4 passed**. The failures were the expected absent-field/absent-attribute failures; collection, imports, fixtures, and test setup were healthy.

## Implementation result

- Added `typical_filter_spec: TypicalFilterSpec | None = None` after `result` on `TaskBudgetStatus`.
- Derived the carrier immediately after the unchanged two-value `_load_task_and_item` call in both manager and worker services.
- Propagated the carrier through `_empty_status` and `_build_evaluated_status` using required keyword-only parameters.
- Preserved the evaluated path's `item_id=evaluation.item_id`; the carrier always comes from the loaded active PRIMARY item.
- Did not change serializers, routes, consumers, division serializers, or golden files.
- Added 13 contract/integration tests covering field order/default, exact manager and worker key sets, source identity, empty-state distinctions, golden identity, the partial unique index, and the explicit command conflict guard.

## Criteria and mutation ledger

All 14 named mutations were run against the base tree and reverted immediately after observation.

| Criterion | Mutation | Result / failing test ID |
|---|---|---|
| C1 | Move the defaulted field before non-default `result`. | Collection `TypeError`: `non-default argument 'result' follows default argument`. |
| C2 | Add the field inside the manager serializer's monetary mapping. | **3 failed / 125 passed**: `test_C2_manager_budget_status_payload_has_the_existing_exact_key_set`; `test_C2a_and_C2c_existing_live_clock_goldens_are_byte_identical`; `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`. |
| C2(c) | Publish the field from `division_serializers.serialize_task_production_time`. | **2 failed / 126 passed**: the new golden identity test and `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`. |
| C3 | Add the field to the shared serializer payload. | **4 failed / 124 passed**: manager exact keys, worker exact keys, new golden identity, and existing live-clock golden; the worker path also encountered JSON serialization of the leaked spec object. |
| C4 | Reload `Item` by `evaluation.item_id` and derive from that item. | **2 failed**: `test_C4_manager_uses_loaded_primary_item_not_evaluation_item`; `test_C4_worker_uses_loaded_primary_item_not_evaluation_item`; both got X/table instead of Y/chair. |
| C4 item-id consistency | Use the loaded item for evaluated `item_id` instead of `evaluation.item_id`. | **2 failed**: the same two C4 tests; both got Y instead of evaluated X. |
| C5(a) | Pass `TypicalFilterSpec()` to the manager no-item empty call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-a-manager-no-primary]`. |
| C5(b) | Pass `None` to the manager item-present empty call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-b-manager-categoryless-primary]`. |
| C5(c) | Pass `TypicalFilterSpec()` to the worker no-item empty call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-c-worker-no-primary]`. |
| C5(d) | Pass `None` to the worker item-present empty call. | **1 failed**: `test_C5_empty_status_preserves_no_item_vs_categoryless_item[C5-d-worker-categoryless-primary]`. |
| C6 | Remove the dataclass default. | **7 failed / 232 passed**: C1, C2 construction, four role cases in `test_budget_status_route_is_available_to_all_roles[...]`, and `test_budget_status_audience_predicate_fails_closed_for_unknown_role`. |
| C-N1(a) | Drop `uix_task_items_primary_active` before the violating insert. | **1 failed**: `test_CN1a_primary_index_is_partial_and_two_legal_shapes_are_valid` (`DID NOT RAISE IntegrityError`). |
| C-N1(a) | Recreate `uix_task_items_primary_active` without its `WHERE`. | The legal active RELATED and removed PRIMARY shapes failed at their legal flush, proving the partial predicate is required. |
| C-N1(b) | Remove the explicit active-PRIMARY precheck from `add_item_to_task`. | **1 failed**: `test_CN1b_add_item_to_task_has_the_explicit_primary_conflict_guard`; database `IntegrityError` replaced the pinned `ConflictError` message. |

## Verification

- `PYTHONPATH=. pytest tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py tests/unit/routers/api_v1/test_item_economics_router.py`: **124 passed**.
- `PYTHONPATH=. pytest -m 'not e2e'` from `app/` with default `BEYO_TEST_SLOT=main`: **2674 passed, 21 failed, 1 skipped, 2 warnings**, 2696 collected, 48.83s.
- Full-suite failure IDs added relative to baseline: **none**.
- Baseline failure IDs absent from current run: **none**.
- The 21 failures remain the known baseline failures in Shopify migration, auth role shape, upholstery/inventory fixtures, bootstrap, item routers, working sections, worker stats, case-type serialization, and audit log.
- `redis-cli ping`: **PONG**.

## Architecture graph and environment

Read-only graph status at close: initialized/valid, 198 nodes, 298 edges, 0 diagnostics, revision `364223242014a733822256e445824b7160bcda2e1cc4a6e3f9e9d930b5419a47`, 1 pending review, 2 stale nodes. This change does not introduce a new architectural boundary or meaning, so no node/relationship delta was recorded; the pending review item was not touched. An empty `archgraph_apply_changes` attempt was rejected by the tool's required non-empty change array, confirming that a no-op batch cannot be recorded.

## Write perimeter and checkpoint

Expected implementation perimeter at handoff time:

- modified `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
- modified `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`
- new `app/tests/integration/services/queries/item_economics/test_budget_status_filter_spec.py`
- modified `docs/architecture/under_construction/implementation/narrow_typical_work_times/master_plan.md`
- modified `docs/architecture/under_construction/implementation/narrow_typical_work_times/plans/plan_3.md`
- new this handoff file
- expected untracked `?? .archgraph/contexts/` retained and not staged

Checkpoint SHA: **pending the explicit-path checkpoint commit immediately following this handoff**. The final commit SHA will be added to this handoff in the documentation follow-up commit if the self-referential hash changes.

No upstream notes or owner decisions are required.
