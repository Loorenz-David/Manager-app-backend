# SUMMARY_upholsteries_crud_20260527

## Metadata

- Summary ID: `SUMMARY_upholsteries_crud_20260527`
- Status: `summarized`
- Owner agent: `Copilot`
- Created at (UTC): `2026-05-27T06:10:19Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholsteries_crud_20260527.md`
- Related debug plan (optional): _none_

## What was implemented

- Added a dedicated `upholsteries` router at `/api/v1/upholsteries` with create, list, get, update, delete, single favorite toggle, batch favorite toggle, and list-order update endpoints.
- Implemented six new upholstery commands with transaction ownership via `ctx.session.begin()`: create, update, delete, mark favorite (single), mark favorite (batch), and update list order.
- Extended upholstery request parsing with six new request models/parsers, including validators for non-blank names, non-empty batch ids, non-negative stock, and `list_order >= 1` when provided.
- Updated `list_upholsteries` query to support `in_stock` and `favorite` filters and corrected ordering to place explicit `list_order` items first, then `favorite DESC`, then `created_at ASC`.
- Removed misplaced upholstery routes from `item_upholsteries.py` and switched router registration to the new `upholsteries.router`.

## Files changed

- `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: added six new upholstery request models and parsers.
- `backend/app/beyo_manager/services/commands/upholstery/create_upholstery.py`: create upholstery + linked inventory atomically with derived `inventory_condition`.
- `backend/app/beyo_manager/services/commands/upholstery/update_upholstery.py`: partial metadata update with workspace uniqueness checks.
- `backend/app/beyo_manager/services/commands/upholstery/delete_upholstery.py`: soft-delete upholstery and clear `list_order`.
- `backend/app/beyo_manager/services/commands/upholstery/mark_upholstery_favorite.py`: single upholstery favorite toggle.
- `backend/app/beyo_manager/services/commands/upholstery/mark_upholsteries_favorite.py`: batch favorite toggle via single UPDATE.
- `backend/app/beyo_manager/services/commands/upholstery/update_upholstery_list_order.py`: ordered insert behavior with bulk shift for `list_order >= new_value`.
- `backend/app/beyo_manager/services/queries/upholstery/upholsteries.py`: added `in_stock`/`favorite` filters and corrected ordering.
- `backend/app/beyo_manager/routers/api_v1/upholsteries.py`: new dedicated upholstery router.
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: removed embedded upholstery router and handlers.
- `backend/app/beyo_manager/routers/api_v1/__init__.py`: added `upholsteries.router`, removed `item_upholsteries.upholstery_router` registration.

## Contract adherence

- `backend/architecture/06_commands.md`: all new commands parse requests and own DB transactions.
- `backend/architecture/07_queries_local.md`: list query keeps offset pagination with `_MAX_LIMIT = 200` and `_DEFAULT_LIMIT = 50`.
- `backend/architecture/09_routers.md`: static collection routes (`/favorite`) declared before wildcard `/{client_id}`.

## Validation evidence

- `npm run typecheck` in `frontend`: root package had no `typecheck` script.
- `npm run typecheck` in `frontend/apps/managers-app/ManagerBeyo-app-managers`: passed (`tsc -b --force`, no errors).
- VS Code diagnostics check on all changed backend files: no errors found.

## Known gaps or deferred items

- No new backend unit tests were added in this slice for the new upholstery CRUD/favorite/list-order endpoints.

## Handoff notes (if needed)

- Existing `route_create_upholstery_inventory` remains inventory-only; upholstery master creation now belongs to `PUT /api/v1/upholsteries`.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_upholsteries_crud_20260527.md`
