# SUMMARY_PLAN_case_reference_number_20260628

## Metadata

- Summary ID: `SUMMARY_PLAN_case_reference_number_20260628`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-28T07:44:17Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_case_reference_number_20260628.md`
- Related debug plan (optional): none

## What was implemented

- Added `scalar_id` and `reference_number` columns to the `Case` ORM model and exposed both fields in single-case and case-list serializers.
- Updated `create_case` to allocate a global sequential `scalar_id` under a PostgreSQL advisory lock and derive a human-readable `reference_number` from the linked entity prefix or `N`.
- Added an Alembic migration that backfills existing rows in `cases` with ordered scalar ids and `N-####` reference numbers before enforcing `NOT NULL` and indexes.
- Added focused unit and integration coverage for serializer output and end-to-end case creation/reference-number behavior.

## Files changed

- `backend/app/beyo_manager/models/tables/cases/case.py`: added `scalar_id` and `reference_number` columns.
- `backend/app/beyo_manager/services/commands/cases/create_case.py`: added advisory-lock-backed scalar allocation and reference-number generation.
- `backend/app/beyo_manager/domain/cases/serializers.py`: exposed the new fields in `serialize_case` and `serialize_case_list_item`.
- `backend/app/migrations/versions/d1e2f3a4b5c6_add_scalar_id_reference_number_to_cases.py`: added schema/backfill migration.
- `backend/app/tests/unit/test_case_serializers.py`: covered new serializer fields.
- `backend/app/tests/integration/services/commands/cases/test_case_reference_number_integration.py`: covered creation and serialization behavior against Postgres.

## Contract adherence

- `backend/architecture/03_models.md`: model fields are declared directly on the ORM table with explicit types and indexes.
- `backend/architecture/06_commands.md`: the command computes authoritative write-time values inside the transaction before flush.
- `backend/architecture/30_migrations.md`: the migration adds nullable columns, backfills, then enforces constraints and indexes.
- `backend/architecture/46_serialization.md`: serializers return plain dict fields directly from the loaded case entity.

## Validation evidence

- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt-secret PYTHONPATH=. .venv/bin/python -m py_compile beyo_manager/services/commands/cases/create_case.py beyo_manager/domain/cases/serializers.py tests/unit/test_case_serializers.py tests/integration/services/commands/cases/test_case_reference_number_integration.py migrations/versions/d1e2f3a4b5c6_add_scalar_id_reference_number_to_cases.py`: passed.
- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt-secret PYTHONPATH=. .venv/bin/alembic upgrade head`: passed.
- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt-secret PYTHONPATH=. .venv/bin/alembic downgrade -1` then `... alembic upgrade head`: passed.
- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt-secret PYTHONPATH=. .venv/bin/alembic current`: returned `d1e2f3a4b5c6 (head)`.
- `APP_ENV=testing SECRET_KEY=test-secret JWT_SECRET_KEY=test-jwt-secret PYTHONPATH=. .venv/bin/pytest tests/unit/test_case_serializers.py tests/integration/services/commands/cases/test_case_reference_number_integration.py -q`: passed (`4 passed`).

## Known gaps or deferred items

- The plan's non-goals remain unchanged: there is still no case filtering or sorting by `reference_number`.
- Existing event payloads and socket frames were intentionally left unchanged.
- The local test profile required creating the missing `app_test` database before DB-backed validation could run.

## Handoff notes (if needed)

- Frontend/API consumers can now rely on `scalar_id` and `reference_number` being present in case detail and case list payloads.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_case_reference_number_20260628.md`
