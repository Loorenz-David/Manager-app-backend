# SUMMARY_upholstery_realtime_events_20260619

## Metadata

- Summary ID: `SUMMARY_upholstery_realtime_events_20260619`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T10:30:20Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_realtime_events_20260619.md`
- Related debug plan (optional): none

## What was implemented

- Added post-commit workspace event dispatches for item upholstery create, update, delete, and quantity update flows.
- Added post-commit workspace event dispatches for upholstery update, inventory update, and inventory delete flows.
- Preserved the `update_requirement_quantity` zero-delta early return path so unchanged quantities still emit no events.
- Updated both backend and frontend realtime event catalog handoff copies with item-upholstery and upholstery event sections, TypeScript event signatures, and handler responsibility matrix rows.

## Files changed

- `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`: emits `item:upholstery-created` alongside the existing `item:updated`.
- `backend/app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py`: emits `item:upholstery-updated` and `item:upholstery-deleted` alongside the existing parent item update signal.
- `backend/app/beyo_manager/services/commands/items/update_requirement_quantity.py`: emits `item:upholstery-updated` and `item:upholstery-requirement-state-changed` after successful quantity mutations.
- `backend/app/beyo_manager/services/commands/upholstery/update_upholstery.py`: emits `upholstery:updated`.
- `backend/app/beyo_manager/services/commands/upholstery/update_upholstery_inventory.py`: emits `upholstery:inventory-updated`.
- `backend/app/beyo_manager/services/commands/upholstery/delete_upholstery_inventory.py`: emits `upholstery:inventory-deleted` and conditionally emits `upholstery:deleted` when the parent upholstery row is soft-deleted.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: documents the new event catalog entries.
- `frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: mirrors the backend handoff catalog updates.

## Contract adherence

- `11_infra_events.md`: all new events are built as `WorkspaceEvent` instances and dispatched after transaction blocks.
- `06_commands.md` and `06_commands_local.md`: command transaction boundaries remain intact; item commands continue to use `maybe_begin`.
- `56_realtime_layer.md`: payloads remain minimal Socket.IO change signals with `client_id` and only required extra fields.
- `23_documentation.md`: the frontend-facing event catalog was updated for the new emitted events.

## Validation evidence

- `python3 -m py_compile app/beyo_manager/services/commands/items/create_item_upholstery.py app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py app/beyo_manager/services/commands/items/update_requirement_quantity.py app/beyo_manager/services/commands/upholstery/update_upholstery.py app/beyo_manager/services/commands/upholstery/update_upholstery_inventory.py app/beyo_manager/services/commands/upholstery/delete_upholstery_inventory.py`: passed.
- `rg -n "item:upholstery-created|item:upholstery-updated|item:upholstery-deleted|item:upholstery-requirement-state-changed|upholstery:updated|upholstery:deleted|upholstery:inventory-updated|upholstery:inventory-deleted" ...`: confirmed the expected event names are present in command code and both handoff catalog copies.

## Known gaps or deferred items

- Runtime Socket.IO verification was not run in this turn because it requires the API server, notification worker, and a browser or socket client driving the seven mutating flows.
- No frontend handler implementation was added; this plan only updates the handoff catalog for frontend follow-up.

## Handoff notes (if needed)

- Frontend should add handlers for the seven newly cataloged events in `features/items/socket-events.ts` and `features/upholstery/socket-events.ts`.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_upholstery_realtime_events_20260619.md`
