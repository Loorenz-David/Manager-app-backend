# SUMMARY_PLAN_create_upholstery_inline_category_20260625

## Metadata

- Summary ID: `SUMMARY_PLAN_create_upholstery_inline_category_20260625`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-25T09:50:50Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_inline_category_20260625.md`
- Related debug plan (optional): —

## What was implemented

- Extended `CreateUpholsteryRequest` with an optional nested `create_category` payload and an after-model validator that rejects requests sending both `create_category` and `upholstery_category_id`.
- Added inline category creation to `create_upholstery`, keeping category creation, upholstery creation, and inventory creation inside the existing single transaction.
- Added the router-local `_InlineCategoryBody` and exposed the new nested field on `PUT /api/v1/upholsteries`.
- Added focused unit coverage for the new request validation and inline category command behavior.

## Files changed

- `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: added `CreateUpholsteryCategoryInlineRequest`, `create_category` on `CreateUpholsteryRequest`, and mutual-exclusion validation.
- `backend/app/beyo_manager/services/commands/upholstery/create_upholstery.py`: added inline category creation, category client ID validation, name conflict handling, and category ID resolution before upholstery creation.
- `backend/app/beyo_manager/routers/api_v1/upholsteries.py`: added `_InlineCategoryBody` and `create_category` to the create request body.
- `backend/app/tests/unit/test_upholstery_request_models.py`: added request-model tests for accepted nested payloads and rejected invalid combinations.
- `backend/app/tests/unit/services/commands/upholstery/test_create_upholstery.py`: added unit tests for successful inline category creation and category-name conflict rollback behavior.
- `backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_inline_category_20260625.md`: updated lifecycle metadata and closure notes before archival.

## Contract adherence

- `backend/architecture/06_commands.md`: kept all inline category work inside the existing command rather than composing another command.
- `backend/architecture/05_errors.md`: surfaced mutual-exclusion failures as validation errors and category conflicts as `ConflictError`.
- `backend/architecture/09_routers.md`: kept the router change limited to request-body shape and `ServiceContext` handoff.
- `backend/architecture/21_naming_conventions.md`: used explicit inline request/body names instead of generic helper naming.

## Validation evidence

- `./.venv/bin/python -m pytest tests/unit/test_upholstery_request_models.py tests/unit/services/commands/upholstery/test_create_upholstery.py tests/unit/test_upholstery_serializers.py`: passed (`10 passed`).
- `./.venv/bin/python -m py_compile beyo_manager/services/commands/upholstery/requests/__init__.py beyo_manager/services/commands/upholstery/create_upholstery.py beyo_manager/routers/api_v1/upholsteries.py tests/unit/test_upholstery_request_models.py tests/unit/services/commands/upholstery/test_create_upholstery.py`: passed.

## Known gaps or deferred items

- No live API smoke call was run against `PUT /api/v1/upholsteries`; validation in this task is limited to targeted unit tests and static compile checks.
- Standalone `PUT /api/v1/upholstery-categories` was intentionally left unchanged.

## Handoff notes (if needed)

- Frontend callers can now either pass `upholstery_category_id` or a nested `create_category` payload, but not both in the same request.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_create_upholstery_inline_category_20260625.md`
