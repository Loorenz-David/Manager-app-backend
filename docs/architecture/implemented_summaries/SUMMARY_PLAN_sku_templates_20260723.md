# SUMMARY_PLAN_sku_templates_20260723

## Metadata

- Summary ID: `SUMMARY_PLAN_sku_templates_20260723`
- Status: `summarized`
- Owner: `Codex`
- Completed at (UTC): `2026-07-23T08:10:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_sku_templates_20260723.md`
- Related debug plan: `none`
- Migration: `261971b16234_create_sku_templates_table.py`

## What was implemented

- Added `SkuTemplate` with `skt` identity, explicit audit columns, workspace/task-type uniqueness, and shared `TaskTypeEnum`.
- Added SKU formatting, preview serialization, and `CREATED`, `UPDATED`, and `SCALAR_RESERVED` realtime events.
- Added validated create, update, and atomic reserve commands using `maybe_begin`; events dispatch only after commit.
- Added offset-paginated workspace-scoped list and by-task-type queries with soft-delete filtering.
- Added the self-contained `/api/v1/sku-templates` router with the approved role split and registered it in API v1.
- Added idempotent `PRE_ORDER` bootstrap seeding (`PRE_ORDER-0001` preview) and wired it after workspace seeding.
- Added command, concurrency, query/isolation, serializer, and router smoke tests.
- Updated the model registry, table overview, and client ID prefix map.

## Deviations and decisions

- The existing task model uses PostgreSQL enum `business_task_type_enum`, not `task_type_enum`. The migration and model reuse `business_task_type_enum`; the migration uses PostgreSQL `ENUM(create_type=False)` and never drops it.
- The referenced intention plan file was not present in the repository, so no intention-plan progress table could be updated.

## Post-review corrections (2026-07-23)

Applied after an architecture review of the merged implementation:

- **Uniqueness changed from a plain `UniqueConstraint(workspace_id, task_type)` to a partial unique index** `uix_sku_templates_workspace_task_type ... WHERE is_deleted = false` (mirrors the `items.sku` pattern). The original plain constraint would have blocked delete-and-recreate once a soft-delete path is added; the partial index keeps one live template per task type while allowing soft-deleted rows to coexist. Migration `261971b16234` and the model `__table_args__` were updated; round-tripped `upgrade`/`downgrade` cleanly.
- **`update_sku_template` now rejects lowering `last_scalar` below its current value** (`ValidationError`). Rewinding the counter would make `reserve` re-issue already-handed-out scalars and collide with existing item SKUs. Added regression test `test_update_rejects_lowering_last_scalar`.
- **`SCALAR_RESERVED` event renamed** `sku_template:scalar_reserved` → `sku_template:scalar-reserved` to match the codebase's kebab-case action convention (`CaseEvent` e.g. `case:state-changed`).
- Focused SKU suite re-run after corrections: 10 passed.

## Validation evidence

- Alembic upgrade head: passed.
- Alembic downgrade -1: passed; only the new table and its indexes were removed.
- Alembic upgrade head restored after the round-trip: passed.
- Focused SKU tests: 11 passed (unit/domain/router plus command/concurrency/query integration).
- Full pytest: 1,024 passed, 30 failed. The failures are in unrelated pre-existing working-section, item, task, upholstery, audit, Shopify, and serializer/router tests in the already-dirty worktree; no SKU template test failed.
- Full `bootstrap_app` execution was not run because the configured environment has no bootstrap admin credentials; the wired `seed_sku_templates` phase was integration-tested for `PRE_ORDER` creation and idempotent counter preservation.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_sku_templates_20260723.md`

