# SUMMARY_update_requirement_quantity_20260523

## Metadata

- Summary ID: `SUMMARY_update_requirement_quantity_20260523`
- Status: `summarized`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-23T19:30:19Z`
- Source plan: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/docs/architecture/archives/implementation/PLAN_update_requirement_quantity_20260523.md`
- Related debug plan (optional): _none_

## What was implemented

- Added a signed inventory-need adjustment helper that re-evaluates upholstery inventory condition after quantity changes.
- Added request validation, a new `update_requirement_quantity` command, and a new `POST /{client_id}/update-quantity` route for mutable requirement states.
- Preserved existing guards so only `AVAILABLE` and `NEEDS_ORDERING` requirements can be updated, with a no-op short-circuit when the quantity is unchanged.

## Files changed

- `backend/app/beyo_manager/services/commands/upholstery/_inventory_mutations.py`: added `adjust_need` to update `current_amount_in_need_meters` by delta and recompute condition.
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py`: added `UpdateRequirementQuantityRequest` and parser-level validation/error wrapping.
- `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`: added the new command to load the active requirement, guard states, adjust inventory need, and re-evaluate requirement state.
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: added the `update-quantity` route and inline request body model.

## Contract adherence

- `backend/architecture/06_commands.md`: kept transaction ownership in the command via `maybe_begin` and left commit boundaries to the service layer.
- `backend/architecture/09_routers.md`: routed through `run_service` and preserved `build_ok` / `build_err` response handling.
- `backend/architecture/21_naming_conventions.md`: used a dedicated command module with the expected command docstring style.

## Validation evidence

- `npm run typecheck` in `frontend/apps/managers-app/ManagerBeyo-app-managers`: passed cleanly.

## Known gaps or deferred items

- No automated backend tests were added in this implementation.
- Freed inventory is not automatically reallocated to other requirements; callers must continue using `resolve-after-stock` when needed.

## Handoff notes (if needed)

- _none_

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_update_requirement_quantity_20260523.md`
