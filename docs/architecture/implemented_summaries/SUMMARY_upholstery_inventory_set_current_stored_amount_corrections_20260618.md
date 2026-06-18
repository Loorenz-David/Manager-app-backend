# SUMMARY_upholstery_inventory_set_current_stored_amount_corrections_20260618

## Metadata

- Summary ID: `SUMMARY_upholstery_inventory_set_current_stored_amount_corrections_20260618`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T15:04:53Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_set_current_stored_amount_corrections_20260618.md`
- Related debug plan (optional): none

## What was implemented

- Added the missing `AsyncSession` annotation to `_load_requirement_candidates(...)` and restored a matching request-model docstring.
- Tightened unit coverage for the stock-setting flow by asserting the `current_amount_in_need_meters` invariant in the promotion test.
- Added a route-specific WORKER rejection test that exercises the actual dependency attached to `route_set_current_stored_amount`.
- Restored the DB-backed integration module on disk with increase, decrease, no-op, and not-found scenarios so pytest can collect it in a real DB environment.

## Files changed

- `backend/app/beyo_manager/services/commands/upholstery/set_current_stored_amount_inventory.py`: added `AsyncSession` import and helper parameter annotation.
- `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: added the missing request-class docstring.
- `backend/app/tests/unit/test_upholstery_inventories_router.py`: added the WORKER-role rejection test for the stored-amount route.
- `backend/app/tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py`: removed the obsolete `# type: ignore`, added the `in_need` assertion, and kept unit command coverage passing.
- `backend/app/tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py`: restored the collectable DB-backed integration scenarios.

## Contract adherence

- `06_commands.md`: the correction did not alter transaction ownership or command flow; the integration module targets the existing command contract.
- `09_routers.md`: the role-gate test validates the route’s attached dependency rather than generic auth behavior.
- `15_testing.md`: the missing coverage items from review are now represented in unit tests and by a collectable integration module.

## Validation evidence

- `/bin/zsh -lc 'cd backend/app && PYTHONPATH=. .venv/bin/pytest tests/unit/test_upholstery_inventories_router.py tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py -v && PYTHONPATH=. .venv/bin/pytest tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py --collect-only -q'`: passed; `9` unit tests passed and `4` integration tests were collected without import errors.

## Known gaps or deferred items

- I did not execute the DB-backed integration tests in this sandbox because the local Postgres port is blocked here. The file is present and collectable, but runtime verification still needs a DB-enabled environment.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_set_current_stored_amount_corrections_20260618.md`
