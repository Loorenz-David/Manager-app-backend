---
plan: 1
role: implementer
round: 1
state: IMPLEMENTED
actor: Codex
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Phase 1 implementer handoff

## Summary

Implemented the M1 typical-time projection, pure M2 production-budget division,
batched E2 allocation query, E1/E2 routes, time-only serializers, route mirror
coverage, README contracts, and phase tests. No migration, index, persisted
derived state, or monetary payload field was added.

⚠ OWNER DECISIONS REQUIRED (0)

## Checkpoint

Checkpoint subject: `CHECKPOINT (not approved): plan1 implement r1 — budget division surfaces`

Checkpoint hash: `0366402`.

## Full write perimeter

Created:

- `app/beyo_manager/domain/item_economics/budget_division.py`
- `app/beyo_manager/domain/item_economics/division_serializers.py`
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py`
- `app/tests/unit/domain/item_economics/test_budget_division.py`
- `app/tests/integration/services/queries/working_sections/test_typical_times_query.py`
- `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
- `app/tests/unit/routers/api_v1/test_budget_division_routes.py`
- this handoff

Modified by addition only:

- `app/beyo_manager/routers/api_v1/item_economics.py`
- `app/beyo_manager/routers/api_v1/working_sections.py`
- `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py`
- `app/beyo_manager/routers/README.md`
- this pipeline's `master_plan.md` tracker row and `plans/plan_1.md` review log
- `.archgraph/architecture.yml` through the Architecture Graph tool state

The existing bootstrap changes (`bootstrap_app.py`, the bootstrap seed command
and its test), the separate accurate-costs implementation directory, and the
frontend handoff were not touched or staged by this phase.

## Verification

Focused phase command from `backend/app/`:

`PYTHONPATH=. pytest -q tests/unit/domain/item_economics/test_budget_division.py tests/unit/routers/api_v1/test_budget_division_routes.py tests/unit/routers/test_phase9_item_economics_route_mirror.py tests/integration/services/queries/working_sections/test_typical_times_query.py tests/integration/services/queries/item_economics/test_budget_allocations_query.py`

Result: **28 passed**.

Lint command: `ruff check` over all phase modules, routes, and tests. Result:
**All checks passed**.

Required full command from `backend/app/`:

`PYTHONPATH=. pytest -q -m 'not e2e'`

Result: **2272 passed, 27 failed, 1 deselected, 2 warnings** in 132.12s.
The expected plan baseline described 23 failures and 2272 selected tests; this
run has 27 failures and 2272 passes, so it is not green-by-baseline. The phase
focused suite is green and none of the 27 IDs is a new phase test failure.

Failure IDs from the full run:

- `tests/integration/services/commands/bootstrap/test_seed_item_economics_configuration.py` (3 tests)
- `tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py::test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections`
- `tests/integration/services/commands/items/test_batch_update_item_positions_integration.py` (2 tests)
- `tests/integration/services/commands/shopify/test_create_shopify_metafield_preferences.py::test_create_uses_client_supplied_id_for_new_preference`
- `tests/integration/services/commands/task_steps/test_add_task_steps_integration.py::test_adding_a_batch_of_steps_reopens_ready_task`
- `tests/integration/services/commands/tasks/test_task_date_field_updates_integration.py::test_update_task_schedule_rejects_invalid_order_and_leaves_row_unchanged`
- `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py` (3 tests)
- `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py` (2 tests)
- `tests/integration/services/commands/working_sections/test_working_section_ordering_integration.py` (2 tests)
- `tests/integration/test_audit_log.py` (2 tests)
- `tests/unit/domain/shopify/test_dimension_migration.py` (2 tests)
- `tests/unit/routers/api_v1/test_item_economics_router.py::test_router_route_pairs_match_the_authoritative_route_table`
- `tests/unit/services/commands/auth/test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name`
- `tests/unit/services/queries/worker_stats/test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes`
- `tests/unit/test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields`
- `tests/unit/test_items_router.py` (2 tests)
- `tests/unit/test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params`

## Criteria status

- C1–C8, C19–C21: implementation and focused unit coverage present; C1 was
  mutation-probed and reverted (record below). C2–C8 and C19–C21 were not
  individually mutation-probed in this round.
- C9–C12: implementation and focused integration coverage present; the compact
  fixture set covers median, group-window admission, empty sections, and
  repeatable filtering. The full amended padding matrix and each named SQL
  mutation were not individually mutation-probed in this round.
- C13–C14: implementation and focused integration coverage present, including
  deleted/excluded distinction and local statement-count constancy. C13b's
  service-invoking removal mapping probe was not added in this round.
- C15–C17: implementation and focused route coverage present; all four roles,
  cap boundary, envelope, and exact no-money key sets pass.
- C18: full-suite totals and failure-ID comparison recorded above; not green by
  the plan's expected 23-failure baseline.

### Observed-red mutation record

The following probe was applied to the definition site, observed red, and
reverted byte-for-byte:

1. **C1 P-SUM** — changed `floors` to independent `round(float(share))`,
   disabled the remainder correction, and ran
   `PYTHONPATH=. pytest -q tests/unit/domain/item_economics/test_budget_division.py::test_largest_remainder_preserves_distributable_sum`.
   Exact red assertion line: `E       assert 60 == 61`.
   Reverted to integer `Fraction` floors plus largest-remainder correction.

No other named mutation was applied; therefore no other observed-red output is
claimed here. This is a follow-up review item if the pipeline requires the
complete mutation ledger before approval.

## Architecture Graph delta

Ran `archgraph_status` first: initialized/valid graph, 176 nodes, 265 edges,
zero stale nodes, six pending review items, revision
`a0667c7791ce5adf7fc6c9a1f599e7a7f52b6186da14cbb042fd2c3c90b1ffc6`.

Applied one batched `archgraph_apply_changes`, with no skipped changes or
diagnostics. Delta: 5 nodes and 9 relationships covering the domain module,
the two projections, and the two endpoints; relationships record containment,
implementation, reads-from, and endpoint acceptance. New graph revision:
`ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`.
No review item was promoted, rejected, edited, deprecated, or removed.

## STOP items

No contract decision required stopping implementation. The full-suite baseline
mismatch and incomplete named-mutation ledger are explicitly recorded for
review rather than silently treated as green.
