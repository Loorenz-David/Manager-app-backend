# SUMMARY_merge_set_update_quantity_20260523

## Metadata

- Summary ID: `SUMMARY_merge_set_update_quantity_20260523`
- Status: `summarized`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-23T19:47:25Z`
- Source plan: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/docs/architecture/archives/implementation/PLAN_merge_set_update_quantity_20260523.md`
- Related debug plan (optional): _none_

## What was implemented

- Merged the old set-quantity behavior into `update_requirement_quantity` so `MISSING_QUANTITY`, `AVAILABLE`, and `NEEDS_ORDERING` now share one endpoint and command.
- Removed the redundant `set_requirement_quantity` command, `SetQuantityRequest` parser model, and `POST /{client_id}/set-quantity` route.
- Preserved the existing delta-adjust path for `AVAILABLE` and `NEEDS_ORDERING`, including the no-op short-circuit when the quantity is unchanged.

## Files changed

- `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`: added the `MISSING_QUANTITY` branch using `check_and_inject_need` and broadened the mutable-state guard.
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py`: removed `SetQuantityRequest` and `parse_set_quantity_request`; retained the shared update parser.
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: removed the `set-quantity` import, body model, and route while keeping `update-quantity` unchanged.
- `backend/app/beyo_manager/services/commands/items/set_requirement_quantity.py`: deleted because the behavior now lives entirely in `update_requirement_quantity`.

## Contract adherence

- `backend/architecture/06_commands.md`: kept the transactional command pattern under `maybe_begin` and continued using inventory helper functions for mutation boundaries.
- `backend/architecture/09_routers.md`: preserved the router/service wiring through `run_service` with standard `build_ok` / `build_err` handling.
- Plan risk gate: verified all old consumers with repository grep before deleting the old command and parser symbols.

## Validation evidence

- `rg -n "set_requirement_quantity" backend/app -g '*.py'`: only expected files referenced the old command before deletion.
- `rg -n "SetQuantityRequest|parse_set_quantity_request" backend/app -g '*.py'`: only expected files referenced the old request model/parser before deletion.
- `npm run typecheck` in `frontend/apps/managers-app/ManagerBeyo-app-managers`: passed cleanly.

## Known gaps or deferred items

- No automated backend tests were added in this implementation.
- Any callers still using `POST /set-quantity` must migrate to `POST /update-quantity`; the old route is removed rather than redirected.

## Handoff notes (if needed)

- _none_

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_merge_set_update_quantity_20260523.md`
