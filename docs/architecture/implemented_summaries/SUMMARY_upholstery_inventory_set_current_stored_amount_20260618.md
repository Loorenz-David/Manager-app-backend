# SUMMARY_upholstery_inventory_set_current_stored_amount_20260618

## Metadata

- Summary ID: `SUMMARY_upholstery_inventory_set_current_stored_amount_20260618`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T14:00:54Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_set_current_stored_amount_20260618.md`
- Related debug plan (optional): none

## What was implemented

- Added `PATCH /api/v1/upholstery-inventories/{client_id}/current-stored-amount` to set absolute stored stock without changing planning fields.
- Added `SetCurrentStoredAmountInventoryRequest` and a new command that updates `current_stored_amount_meters`, recomputes `inventory_condition`, demotes low-priority `AVAILABLE` requirements when stock decreases, and re-promotes eligible `ORDERED` or `NEEDS_ORDERING` requirements through the existing stored-pool allocator.
- Moved the shared `ready_by_at` lookup into `_pooled_requirement_allocation.py` so the new command and the order-receipt flow use the same ordering input.
- Emitted `item:upholstery-requirement-state-changed` workspace events for both promotion and demotion buckets.

## Files changed

- `backend/app/beyo_manager/routers/api_v1/upholstery_inventories.py`: added the new absolute-stock route and request body.
- `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: added the request parser and non-negative meters validation.
- `backend/app/beyo_manager/services/commands/upholstery/set_current_stored_amount_inventory.py`: implemented the stored-amount command, demotion pass, forward allocation pass, and event dispatch.
- `backend/app/beyo_manager/services/commands/upholstery/_pooled_requirement_allocation.py`: extracted the shared `fetch_earliest_ready_by_at(...)` helper.
- `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py`: switched to the shared `ready_by_at` helper.
- `backend/app/tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py`: added parser and command behavior coverage for increase, decrease, no-op, and not-found cases.
- `backend/app/tests/unit/test_upholstery_inventories_router.py`: added route wiring coverage for the new endpoint.

## Contract adherence

- `06_commands.md`: the new write flow parses first, owns its transaction, and dispatches events after commit.
- `09_routers.md`: the router remains thin and only builds `ServiceContext` plus `run_service(...)`.
- `08_domain.md`: inventory condition recalculation continues to use the pure `evaluate_inventory_condition(...)` function.
- `15_testing.md`: the new behavior is covered with focused unit tests for parser, command logic, router wiring, and pooled allocation regression coverage.

## Validation evidence

- `/bin/zsh -lc 'cd backend/app && PYTHONPATH=. .venv/bin/pytest tests/unit/test_upholstery_inventories_router.py tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py tests/unit/test_upholstery_pooled_requirement_allocation.py'`: passed, `12 passed`.

## Known gaps or deferred items

- The linked intention plan path referenced by the implementation plan does not currently exist in `backend/docs/architecture/under_construction/intention/`, so no intention-plan status/table update was possible in this turn.
- I did not run DB-backed integration tests in this sandbox because the local Postgres port is blocked here (`PermissionError` on `::1:5433`). The command behavior is covered with unit tests instead.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_set_current_stored_amount_20260618.md`
