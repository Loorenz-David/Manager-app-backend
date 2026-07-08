# SUMMARY_shopify_foundation_schema_config_20260708

## Metadata

- Summary ID: `SUMMARY_shopify_foundation_schema_config_20260708`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-08T06:35:34Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md`
- Related debug plan (optional): `none`

## What was implemented

- Added Shopify settings fields to the existing `Settings` class without making them critical startup requirements.
- Added pure Shopify domain foundation modules for enums, scope normalization/comparison, shop-domain normalization/validation, and the initial webhook registry.
- Added five Shopify SQLAlchemy foundation tables, model registration, reserved `CLIENT_ID_PREFIX` entries, and an Alembic migration for the new schema and partial unique indexes.
- Added focused unit and integration tests for Shopify domain helpers, webhook registry definitions, and core schema constraints.

## Files changed

- `backend/app/beyo_manager/config.py`: added Shopify config/env fields under the existing settings class.
- `backend/app/beyo_manager/domain/shopify/`: added foundation domain modules and package init.
- `backend/app/beyo_manager/models/tables/shopify/`: added Shopify foundation table models and package init.
- `backend/app/beyo_manager/models/__init__.py`: registered the new Shopify models for metadata loading and Alembic autogenerate.
- `backend/app/beyo_manager/models/tables/client_id_prefix_map.md`: reserved the approved Shopify client ID prefixes.
- `backend/app/migrations/versions/677ed7131bb2_create_shopify_integration_foundation.py`: added the Shopify foundation migration and removed unrelated autogenerate drift.
- `backend/app/tests/unit/domain/shopify/`: added domain helper and webhook registry tests.
- `backend/app/tests/integration/models/shopify/test_shopify_foundation_constraints.py`: added focused schema constraint coverage.
- `backend/docs/architecture/under_construction/intention/shopify_integration_intention.txt`: added a minimal lifecycle progress note for the completed child plan.

## Contract adherence

- `backend/architecture/08_domain.md`: kept Shopify normalization, scope comparison, and registry logic pure under `domain/shopify/`.
- `backend/architecture/03_models.md`: implemented Shopify tables in SQLAlchemy 2.x model files and registered them in `models/__init__.py`.
- `backend/architecture/30_migrations.md`: generated the migration through Alembic autogenerate, then reviewed and trimmed it to Shopify-only schema changes.
- `backend/architecture/24_multi_tenancy.md`: kept Shopify integration rows workspace-owned while also enforcing the approved global shop-domain uniqueness rule.
- `backend/architecture/25_soft_delete.md`: added `is_deleted` and `deleted_at` to the soft-deletable integration table and validated the active-like partial-index behavior.

## Validation evidence

- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. ./.venv/bin/alembic upgrade head`: passed; applied `677ed7131bb2_create_shopify_integration_foundation`.
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. ./.venv/bin/alembic current`: passed; database reported `677ed7131bb2 (head)`.
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. ./.venv/bin/pytest tests/unit/domain/shopify -q`: passed; `16 passed`.
- `APP_ENV=testing SECRET_KEY=test JWT_SECRET_KEY=test PYTHONPATH=. ./.venv/bin/pytest tests/unit/domain/shopify tests/integration/models/shopify/test_shopify_foundation_constraints.py -q`: passed; `22 passed`.
- `./app/.venv/bin/python -m py_compile ...`: passed for the new Shopify domain/model/test files and migration.

## Known gaps or deferred items

- OAuth routes, token exchange, webhook HTTP handling, subscription sync, workers, admin routes, serializers/results, and imports remain intentionally deferred to later Shopify child plans.
- Alembic autogenerate surfaced pre-existing unrelated drift in `workspace_roles` and `email_sync_states`; that drift was explicitly excluded from the Shopify migration and not modified in this phase.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_shopify_foundation_schema_config_20260707.md`
