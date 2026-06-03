# SUMMARY_PLAN_working_section_order_list_20260602

## Metadata

- Summary ID: `SUMMARY_PLAN_working_section_order_list_20260602`
- Status: `summarized`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T12:44:57Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_working_section_order_list_20260602.md`
- Related debug plan (optional): —

## What was implemented

- Added `order_list` to the `WorkingSection` ORM model as a nullable integer column.
- Updated create and edit request bodies plus command handlers so clients can set or clear `order_list` on `POST /working-sections` and `PATCH /working-sections`.
- Exposed `order_list` through compact and full working-section serialization and threaded the compact serializer change through every caller.
- Updated working-section list queries to sort by `order_list` first, with existing secondary keys preserved, and added the Alembic migration for the new column.

## Files changed

- `backend/app/beyo_manager/models/tables/working_sections/working_section.py`: added the nullable `order_list` column.
- `backend/app/beyo_manager/domain/working_sections/serializers.py`: included `order_list` in compact and full serializers.
- `backend/app/beyo_manager/services/commands/working_sections/requests/create_working_section_request.py`: accepted `order_list` on create.
- `backend/app/beyo_manager/services/commands/working_sections/requests/edit_working_section_request.py`: accepted `order_list` on edit and updated the one-field guard.
- `backend/app/beyo_manager/services/commands/working_sections/create_working_section.py`: persisted `order_list` on insert.
- `backend/app/beyo_manager/services/commands/working_sections/edit_working_section.py`: persisted `order_list` on update.
- `backend/app/beyo_manager/services/queries/working_sections/list_working_sections.py`: sorted by `order_list ASC NULLS LAST, created_at ASC`.
- `backend/app/beyo_manager/services/queries/working_sections/get_worker_working_sections.py`: sorted by `order_list ASC NULLS LAST, name ASC`.
- `backend/app/beyo_manager/services/queries/users/list_users.py`: threaded the compact serializer’s new argument through the user list response.
- `backend/app/beyo_manager/routers/api_v1/working_sections.py`: exposed `order_list` on the request bodies.
- `backend/app/migrations/versions/5ad879ec99d9_add_order_list_to_working_sections.py`: added the new nullable database column.
- `backend/docs/architecture/under_construction/implementation/PLAN_working_section_order_list_20260602.md`: updated lifecycle metadata before archival.

## Contract adherence

- `backend/architecture/03_models.md`: the new ORM field follows the existing column declaration pattern and remains nullable.
- `backend/architecture/06_commands.md`: create/edit command mutation logic stays inside the command layer.
- `backend/architecture/07_queries.md`: ordering changes were kept in the query layer and preserve deterministic secondary ordering.
- `backend/architecture/46_serialization.md`: serializers remain pure and now emit the new field explicitly.

## Validation evidence

- `get_errors` on the touched backend Python files: no errors found.
- `alembic upgrade head` in `backend/app`: passed.
- `alembic downgrade -1` in `backend/app`: passed.
- `npm run typecheck` in `frontend/apps/managers-app/ManagerBeyo-app-managers`: passed.

## Known gaps or deferred items

- No uniqueness or auto-reindex behavior was added for `order_list`, by design.

## Handoff notes (if needed)

- To frontend: none required for the backend data-shape change, unless the UI wants to start sending or displaying `order_list`.
- From frontend dependency: none.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_working_section_order_list_20260602_1244.md`