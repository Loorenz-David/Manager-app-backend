# SUMMARY_PLAN_internal_upholstery_without_requirement_20260617

## Metadata

- Summary ID: `SUMMARY_PLAN_internal_upholstery_without_requirement_20260617`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-17T13:10:16Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_internal_upholstery_without_requirement_20260617.md`
- Related debug plan (optional): —

## What was implemented

- Allowed internal `ItemUpholstery` creation without `upholstery_id` when positive `amount_meters` is present, while deferring requirement creation until a later upholstery selection.
- Preserved the existing swap behavior for already-linked upholsteries and added a separate first-link activation path when a deferred internal upholstery later receives its first `upholstery_id`.
- Added a specific business error for requirement actions attempted before upholstery selection is completed.
- Kept deferred internal upholsteries visible in the pending seat-task upholstery views by classifying them as `missing_selection`.
- Hardened the item-upholstery PATCH route and update request parsing so omitted optional fields are not treated as implicit null updates.

## Files changed

- `backend/app/beyo_manager/domain/items/upholstery_selection.py`: added pure helper functions for positive-amount checks and deferred internal selection detection.
- `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`: centralized the deferred internal validation rule and skipped initial requirement creation for deferred internal upholsteries.
- `backend/app/beyo_manager/services/commands/items/create_item.py`: allowed embedded deferred internal upholstery and avoided registry lookup when no `upholstery_id` is present.
- `backend/app/beyo_manager/services/commands/tasks/create_task.py`: allowed embedded deferred internal upholstery during task creation when positive `amount_meters` is provided.
- `backend/app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py`: split first-link activation from true swap behavior and added the shared business error guard for requirement actions.
- `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`: now raises the specific selection-required business error before active-requirement lookup.
- `backend/app/beyo_manager/services/commands/items/apply_surplus_to_requirement.py`: now raises the specific selection-required business error before active-requirement lookup.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py`: now validates the parent `ItemUpholstery` first and raises the specific selection-required business error when applicable.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py`: now validates the parent `ItemUpholstery` first and raises the specific selection-required business error when applicable.
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py`: aligned update request validation with create flows by coercing non-positive `amount_meters` to `None` and enforcing non-negative time.
- `backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py`: treated internal upholsteries with `upholstery_id=None` as `missing_selection` in list/count discovery and extracted a small helper for pending-reason resolution.
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: changed PATCH forwarding to `model_dump(exclude_unset=True)` so omitted optional fields stay omitted.
- `backend/app/tests/unit/test_item_upholstery_selection.py`: added coverage for deferred-selection helper behavior and the new business error guard.
- `backend/app/tests/unit/test_item_upholsteries_router.py`: added coverage that the PATCH route excludes unset optional fields.
- `backend/app/tests/unit/test_seat_tasks_pending_upholstery.py`: added coverage for pending upholstery reason resolution, including deferred internal selection.
- `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`: linked this implementation plan and added a progress note for the deferred internal upholstery correction.

## Contract adherence

- `backend/skills/_shared/quality_gate.md`: kept business logic in commands/queries, preserved thin-router behavior, and maintained typed domain error usage.
- `backend/architecture/23_documentation.md`: updated the implementation lifecycle documents so the plan, summary, archive record, and intention note stay trace-linked.
- `backend/architecture/29_feature_workflow.md`: implemented the change in the existing command/query layers without introducing a new cross-layer pattern.

## Validation evidence

- `python3 -m py_compile backend/app/beyo_manager/domain/items/upholstery_selection.py backend/app/beyo_manager/services/commands/items/create_item_upholstery.py backend/app/beyo_manager/services/commands/items/create_item.py backend/app/beyo_manager/services/commands/tasks/create_task.py backend/app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py backend/app/beyo_manager/services/commands/items/apply_surplus_to_requirement.py backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py backend/app/beyo_manager/services/commands/items/requests/__init__.py backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py backend/app/beyo_manager/routers/api_v1/item_upholsteries.py backend/app/tests/unit/test_item_upholstery_selection.py backend/app/tests/unit/test_item_upholsteries_router.py backend/app/tests/unit/test_seat_tasks_pending_upholstery.py`: passed.
- `PYTHONPATH=. .venv/bin/pytest tests/unit/test_item_upholstery_selection.py tests/unit/test_item_upholsteries_router.py tests/unit/test_seat_tasks_pending_upholstery.py` (run from `backend/app`): 10 passed.

## Known gaps or deferred items

- No live HTTP integration flow or DB-backed end-to-end test was run for create-task/create-item followed by later upholstery selection; validation for this change is currently compile-level plus focused unit coverage.
- The `tasks` query filter based on `upholstery_requirement_states` still only matches rows with requirement records; this implementation corrected manager-facing pending seat-task discovery, but it does not add a new filter state for deferred internal selection.

## Handoff notes (if needed)

- —

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_internal_upholstery_without_requirement_20260617.md`
