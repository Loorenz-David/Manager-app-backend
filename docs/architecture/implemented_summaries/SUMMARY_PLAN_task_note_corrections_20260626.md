# SUMMARY_PLAN_task_note_corrections_20260626

## Metadata

- Summary ID: `SUMMARY_PLAN_task_note_corrections_20260626`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-26T12:23:27Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_note_corrections_20260626.md`
- Related debug plan (optional): `—`

## What was implemented

- Corrected the `TaskNote.users_read_list` model default to `text("'[]'::jsonb")` so the model matches the live schema and `alembic check` stays clean.
- Filtered soft-deleted task notes out of `GET /api/v1/tasks/{task_id}/notes`.
- Restored task-note history record username capture to `ctx.identity.get("username")` in both create and update note commands.
- Added `task_id` validation to the note read-by command so a note cannot be marked read through a different task route in the same workspace.
- Changed the standalone task-note create route to batch semantics: `POST /api/v1/tasks/{task_id}/notes` now accepts an array of notes and returns `client_ids`.
- Aligned router body `content` typing with the canonical request model and updated the frontend handoff to document batch note creation, deleted-note shape, and inline note creation during `POST /api/v1/tasks`.

## Files changed

- `backend/app/beyo_manager/models/tables/tasks/task_note.py`: fixed the JSONB server default expression.
- `backend/app/beyo_manager/services/queries/tasks/get_task_notes.py`: excluded soft-deleted notes.
- `backend/app/beyo_manager/services/commands/tasks/create_task_note.py`: switched to batch note creation, empty-list validation, and identity-based username snapshots.
- `backend/app/beyo_manager/services/commands/tasks/update_task_note.py`: switched username snapshot back to `ctx.identity.get("username")`.
- `backend/app/beyo_manager/services/commands/tasks/append_note_read_by.py`: enforced `task_id` ownership checks.
- `backend/app/beyo_manager/services/commands/tasks/requests/__init__.py`: added `CreateBatchTaskNotesRequest`, added `task_id` to `MarkNoteReadByRequest`, and kept note request parsing aligned.
- `backend/app/beyo_manager/routers/api_v1/tasks.py`: changed the standalone create-note route body from one note object to a list and aligned note content typing.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`: documented deleted-note shape, batch standalone note creation, and inline note creation via task create.
- `backend/app/tests/unit/test_task_note_requests.py`: extended request-model coverage.
- `backend/app/tests/unit/test_task_note_routes.py`: added route forwarding coverage for batch note creation.
- `backend/app/tests/unit/services/commands/tasks/test_task_note_command_corrections.py`: added empty-batch validation and read-by task mismatch coverage.

## Contract adherence

- `backend/architecture/03_models.md`: kept the schema correction in the model layer only and avoided creating a fake migration for an already-correct DB default.
- `backend/architecture/06_commands.md` and `backend/architecture/06_commands_local.md`: kept validation and ownership checks in command services under `maybe_begin`.
- `backend/architecture/07_queries.md`: kept the deleted-note filter in the dedicated note query service.
- `backend/architecture/09_routers.md`: kept the router thin and limited it to body-shape adaptation for the new batch endpoint.
- `backend/architecture/23_documentation.md`: updated the frontend handoff so the delivered API contract reflects current backend behavior.

## Validation evidence

- `python3 -m compileall app/beyo_manager`: passed.
- `PYTHONPATH=. ./.venv/bin/pytest tests/unit/test_task_note_requests.py tests/unit/test_task_note_routes.py tests/unit/services/commands/tasks/test_task_note_command_corrections.py tests/unit/test_image_confirm_upload.py tests/unit/test_image_create_from_url.py tests/unit/test_task_serializers.py`: passed (`26 passed`).
- `./.venv/bin/alembic check`: passed with `No new upgrade operations detected.`

## Known gaps or deferred items

- No integration test was added for the full batch note creation HTTP flow or for read-by against real DB rows; current validation is through unit coverage plus compile and Alembic drift checks.
- `PATCH /api/v1/tasks/{task_id}/notes/{note_id}` still does not validate `task_id` ownership. That gap predates this correction plan and remains out of scope here.

## Handoff notes (if needed)

- Updated frontend handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_task_note_corrections_20260626.md`
