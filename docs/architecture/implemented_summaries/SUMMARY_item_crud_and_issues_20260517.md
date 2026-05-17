# SUMMARY_item_crud_and_issues_20260517

## Metadata

- Summary ID: `SUMMARY_item_crud_and_issues_20260517`
- Status: `summarized`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Created at (UTC): `2026-05-17T18:25:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_item_crud_and_issues_20260517.md`

## What was implemented

- Added snapshot columns to `items` and updated partial unique index predicates to include `is_deleted = false`.
- Created and applied migration `3a5532f8f0a7_item_snapshot_columns_and_fix_unique_` including manual index drop/recreate operations Alembic did not autogenerate.
- Added item command request models and parser functions for CMD-1 through CMD-4.
- Implemented item commands: create item (with embedded issues + optional upholstery), create item issue, update item with `model_fields_set`, and soft delete item.
- Refactored `create_item_upholstery` to expose `_create_item_upholstery_in_session` helper for composition in CMD-1.
- Extended serializers with `serialize_item_list`, `serialize_item_detail`, `serialize_item_issue`, and updated `serialize_item_upholstery` to include requirements.
- Updated item upholstery queries to batch-load requirements and pass them to the updated serializer signature.
- Added item queries (`list_items`, `get_item`) and new items router with CRUD + nested issue endpoint.
- Registered `/api/v1/items` router in API v1 router registry.

## Files changed

- `backend/app/beyo_manager/models/tables/items/item.py`: added snapshot columns and updated partial unique index predicates.
- `backend/app/migrations/versions/3a5532f8f0a7_item_snapshot_columns_and_fix_unique_.py`: added columns plus index drop/create in upgrade/downgrade.
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py`: added item CRUD request models and parsers.
- `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`: extracted `_create_item_upholstery_in_session` helper and reused it.
- `backend/app/beyo_manager/services/commands/items/create_item.py`: added CMD-1 implementation.
- `backend/app/beyo_manager/services/commands/items/create_item_issue.py`: added CMD-2 implementation and helper.
- `backend/app/beyo_manager/services/commands/items/update_item.py`: added CMD-3 implementation.
- `backend/app/beyo_manager/services/commands/items/delete_item.py`: added CMD-4 implementation.
- `backend/app/beyo_manager/domain/items/serializers.py`: added item serializers and breaking change update.
- `backend/app/beyo_manager/services/queries/items/item_upholsteries.py`: updated serializer call sites with batched requirements.
- `backend/app/beyo_manager/services/queries/items/items.py`: added QUERY-1 and QUERY-2.
- `backend/app/beyo_manager/routers/api_v1/items.py`: added items router.
- `backend/app/beyo_manager/routers/api_v1/__init__.py`: registered items router.

## Contract adherence

- `backend/architecture/06_commands_local.md`: all new/refactored commands use `maybe_begin`; no manual commit/rollback added.
- `backend/architecture/07_queries_local.md`: list queries use offset pagination and `limit + 1` has_more detection.
- `backend/architecture/09_routers.md`: thin router handlers, path params injected via `incoming_data`, and PATCH uses `model_dump(exclude_unset=True)`.
- `backend/architecture/46_serialization.md`: serialization remains pure in `domain/items/serializers.py`.

## Validation evidence

- `cd backend/app && ./.venv/bin/alembic upgrade head`: passed.
- `cd backend/app && ./.venv/bin/alembic current`: `3a5532f8f0a7 (head)`.
- `cd backend/app && ./.venv/bin/python -c "from beyo_manager import create_app; create_app(); print('OK')"`: `OK`.
- `cd backend/app && rg -n "ctx\.session\.begin" beyo_manager/services/commands/items/ || true`: zero matches.
- `cd backend/app && rg -n "serialize_item_upholstery\(" beyo_manager`: all call sites pass requirements argument.

## Known gaps or deferred items

- Endpoint-level integration tests for CMD-1..CMD-4 and QUERY-1..QUERY-2 were not executed in this run; behavioral acceptance at HTTP level remains to be validated.
- Intention success criteria remain in `active` status until endpoint test evidence is collected.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_item_crud_and_issues_20260517.md`
