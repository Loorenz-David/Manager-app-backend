# SUMMARY_PLAN_task_note_system_improvement_20260626

## Metadata

- Summary ID: `SUMMARY_PLAN_task_note_system_improvement_20260626`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-26T10:56:46Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_note_system_improvement_20260626.md`
- Related debug plan (optional): `—`

## What was implemented

- Extended `TaskNote` with nullable `plain_text` and JSONB `users_read_list`, and extended `ImageLink` with `major_entity_type` plus `major_entity_client_id`.
- Added `ImageLinkEntityTypeEnum.NOTE` and `ImageEventTypeEnum.UPLOAD_NOTE_IMAGE`, so note images can be linked and uploaded through the existing image-confirm flow.
- Reworked task-note writes around a shared `write_task_note(...)` helper that validates block-list content, normalizes stored JSON, and maintains note mention links.
- Updated task note requests and router bodies to accept block-list `content`, `plain_text`, and `users_read_list`, and added `POST /api/v1/tasks/{task_id}/notes/{note_id}/read-by`.
- Added `GET /api/v1/tasks/{task_id}/notes` as a dedicated query that returns enriched note payloads with `created_by`, `updated_by`, `plain_text`, `users_read_list`, and `note_images`.
- Removed embedded `task_notes` loading from `get_task`, so the main task detail query no longer includes note data.
- Added a single Alembic migration for the task-note, image-link, and enum changes.

## Files changed

- `backend/app/beyo_manager/models/tables/tasks/task_note.py`: added `plain_text` and `users_read_list`, and widened the Python content annotation to block lists.
- `backend/app/beyo_manager/models/tables/images/image_link.py`: added nullable major-entity linkage columns.
- `backend/app/beyo_manager/domain/images/enums.py`: added `NOTE` image-link support and the `upload_note_image` image event type.
- `backend/app/beyo_manager/services/commands/tasks/note_writes.py`: added the shared task-note write helper with content validation and mention processing.
- `backend/app/beyo_manager/services/commands/tasks/create_task_note.py`: refactored note creation to use the shared write helper.
- `backend/app/beyo_manager/services/commands/tasks/create_task.py`: updated inline note creation during task create to use the shared helper and new note fields.
- `backend/app/beyo_manager/services/commands/tasks/update_task_note.py`: added block-list normalization, `plain_text` updates, and mention replacement.
- `backend/app/beyo_manager/services/commands/tasks/append_note_read_by.py`: added append-only read-by updates with duplicate suppression.
- `backend/app/beyo_manager/services/commands/tasks/requests/__init__.py`: updated note request models and added `MarkNoteReadByRequest`.
- `backend/app/beyo_manager/domain/tasks/serializers.py`: replaced the flat note serializer with note-plus-images serialization and compact user-role payloads.
- `backend/app/beyo_manager/services/queries/tasks/get_task_notes.py`: added the dedicated note query with user-role joins and note-image loading.
- `backend/app/beyo_manager/services/queries/tasks/tasks.py`: removed note querying and the `task_notes` response key from `get_task`.
- `backend/app/beyo_manager/routers/api_v1/tasks.py`: added task-note list and read-by routes and updated note body models.
- `backend/app/beyo_manager/services/commands/images/confirm_upload.py`: mapped note uploads to the new image event type.
- `backend/app/migrations/versions/8cf57fa23110_improve_task_notes_and_image_links.py`: added the schema migration and enum extensions.
- `backend/app/tests/unit/test_task_note_requests.py`: added request-model coverage for list-based note content and read-by payloads.
- `backend/app/tests/unit/test_image_confirm_upload.py`: added coverage for note-image uploads.
- `backend/app/tests/unit/test_image_create_from_url.py`: added coverage for `entity_type="note"` in external image linking.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`: documented the frontend-facing API contract changes.

## Contract adherence

- `backend/architecture/06_commands.md`: kept all note writes in command services and used the app-local `maybe_begin` transaction pattern.
- `backend/architecture/07_queries.md` and `backend/architecture/07_queries_local.md`: moved note retrieval into a dedicated query service that enforces workspace scope and returns serialized dict data.
- `backend/architecture/09_routers.md`: kept the router thin and delegated all note logic to services.
- `backend/architecture/03_models.md` and `backend/architecture/30_migrations.md`: implemented schema changes through model edits plus a reviewed Alembic migration.
- `backend/task_system/backend_contract_goal_mapping_guide.md`: used contracts for structure and limited relational reads to the concrete task-note, image, serializer, and router files named by the plan.

## Validation evidence

- `python3 -m compileall app/beyo_manager`: passed.
- `PYTHONPATH=. ./.venv/bin/pytest tests/unit/test_task_note_requests.py tests/unit/test_image_confirm_upload.py tests/unit/test_image_create_from_url.py tests/unit/test_task_serializers.py`: passed (`22 passed`).
- `./.venv/bin/alembic upgrade head`: passed and applied `8cf57fa23110_improve_task_notes_and_image_links`.

## Known gaps or deferred items

- No dedicated integration test was added for `GET /api/v1/tasks/{task_id}/notes` or `POST /api/v1/tasks/{task_id}/notes/{note_id}/read-by`; validation for those paths is currently through compile, request-model tests, and migration/runtime consistency.
- The existing `GET /api/v1/tasks/{task_id}` response contract changed by removing `task_notes`, so the frontend must switch note loading to the new dedicated endpoint before depending on updated backend behavior.

## Handoff notes (if needed)

- To frontend: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626.md`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_task_note_system_improvement_20260626.md`
