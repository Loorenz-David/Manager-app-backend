# SUMMARY_PLAN_issue_mode_20260603

## Metadata

- Summary ID: `SUMMARY_PLAN_issue_mode_20260603`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-03T12:40:54Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_issue_mode_20260603.md`
- Related debug plan (optional): `—`

## What was implemented

- Added `IssueModeEnum` with values `graded` and `switch`.
- Added `issue_mode` to `IssueType` with non-null ORM default `graded`.
- Added `issue_mode_snapshot` to `ItemIssue` for immutable creation-time snapshot.
- Extended issue type serializers and item issue serializers to expose mode fields.
- Updated create/update issue type request contracts and API router bodies to accept `issue_mode`.
- Updated issue type create/update commands to persist and update mode.
- Updated batch item issue creation flow to resolve issue type mode once and snapshot it per row.
- Added migration to create `issue_mode_enum`, add/backfill/enforce `issue_types.issue_mode`, and add `item_issues.issue_mode_snapshot`.

## Files changed

- `backend/app/beyo_manager/domain/issue_types/enums.py`: added `IssueModeEnum`.
- `backend/app/beyo_manager/models/tables/issue_types/issue_type.py`: added `issue_mode` mapped enum column.
- `backend/app/beyo_manager/models/tables/items/item_issue.py`: added `issue_mode_snapshot` column.
- `backend/app/beyo_manager/domain/issue_types/serializers.py`: added `issue_mode` to serialized output.
- `backend/app/beyo_manager/domain/items/serializers.py`: added `issue_mode_snapshot` to serialized item issue output.
- `backend/app/beyo_manager/services/commands/issue_types/requests/__init__.py`: added create/update request fields for `issue_mode`.
- `backend/app/beyo_manager/services/commands/issue_types/create_issue_type.py`: persisted `issue_mode` on create.
- `backend/app/beyo_manager/services/commands/issue_types/update_issue_type.py`: applied optional `issue_mode` updates.
- `backend/app/beyo_manager/routers/api_v1/issue_types.py`: added request body fields for `issue_mode`.
- `backend/app/beyo_manager/services/commands/items/batch_create_item_issues.py`: changed issue validation helper to return mode map and set `issue_mode_snapshot` when creating rows.
- `backend/app/migrations/versions/0f7d4c2b1e9a_add_issue_mode_to_issue_type.py`: migration for schema and enum changes.

## Contract adherence

- `backend/architecture/03_models.md`: model changes are declarative, typed, and follow SA enum configuration pattern.
- `backend/architecture/06_commands.md`: command logic remains in services with request parsing and transaction boundaries unchanged.
- `backend/architecture/09_routers.md`: router remains thin and delegates to command layer.
- `backend/architecture/30_migrations.md`: migration includes explicit upgrade and downgrade paths and safe backfill before not-null.
- `backend/architecture/46_serialization.md`: serializers include new fields without changing existing response envelope conventions.

## Validation evidence

- `cd backend/app && source .venv/bin/activate && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic heads`: passed; head is `0f7d4c2b1e9a`.
- `cd frontend && npm run typecheck`: root script missing by project setup.
- `cd frontend/apps/managers-app/ManagerBeyo-app-managers && npm run typecheck`: passed (`tsc -b --force`).
- `cd frontend/apps/workers-app/ManagerBeyo-app-workers && npm run typecheck`: passed (`tsc -b --noEmit`).

## Known gaps or deferred items

- Root `frontend/package.json` does not define a `typecheck` script; typechecks were executed in app packages where scripts exist.
- No additional endpoint integration tests were added in this iteration.

## Handoff notes (if needed)

- To frontend: `—`
- From frontend dependency: `—`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_issue_mode_20260603.md`
