# SUMMARY_models_tables_20260515

## Metadata

- Summary ID: `SUMMARY_models_tables_20260515`
- Status: `archived`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Created at (UTC): `2026-05-15T10:00:01Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_models_tables_20260515.md`
- Related debug plan (optional): N/A

## What was implemented

- Created all planned domain enum modules for users, working_sections, customers, issue_types, items, upholstery, static_costs, tasks, and task_steps.
- Added aggregate metrics mixins at `models/base/aggregate_metrics.py`.
- Implemented all planned new model tables across users, working_sections, issue_types, items, upholstery, customers, static_costs, and tasks domains.
- Registered all new table modules in `models/__init__.py` in dependency-safe import order.
- Added package `__init__.py` stubs for all new `domain/` and `models/tables/` folders.
- Updated local identity extension notes with all new prefix reservations and conflict-avoidance decisions.
- Applied one compatibility safeguard: task business enum type name set to `business_task_type_enum` to avoid collision with existing execution `task_type_enum`.
- Hardened enum persistence so SQLAlchemy now stores enum `.value` strings via `models/base/sa_enum.py`; the wrapper was injected into all SAEnum-using model modules, including the shared event base mixin.
- Added a PostgreSQL enum-label migration to rename existing labels from uppercase member names to lowercase values and corrected the affected check constraint / partial index literals.
- Added a follow-up migration to materialize the missing circular foreign keys that Alembic autogenerate identified after the initial table build.

## Files changed

- `backend/app/beyo_manager/models/__init__.py`: appended import registrations for all new table modules in the planned order.
- `backend/app/beyo_manager/models/base/aggregate_metrics.py`: added aggregate metrics mixins used by task steps.
- `backend/app/beyo_manager/models/base/sa_enum.py`: added helper that configures SAEnum to persist enum `.value` strings.
- `backend/app/beyo_manager/models/base/event.py`: applied the shared SAEnum value wrapper for event-record enums.
- `backend/app/beyo_manager/domain/users/enums.py`: added `UserShiftStateEnum`.
- `backend/app/beyo_manager/domain/working_sections/enums.py`: added placeholder module.
- `backend/app/beyo_manager/domain/customers/enums.py`: added customer enums.
- `backend/app/beyo_manager/domain/issue_types/enums.py`: added issue source enum.
- `backend/app/beyo_manager/domain/items/enums.py`: added item, item issue, and item upholstery enums.
- `backend/app/beyo_manager/domain/upholstery/enums.py`: added upholstery inventory and threshold enums.
- `backend/app/beyo_manager/domain/static_costs/enums.py`: added static cost currency enum.
- `backend/app/beyo_manager/domain/tasks/enums.py`: added task, note, event, and lifecycle enums.
- `backend/app/beyo_manager/domain/task_steps/enums.py`: added task-step state/readiness/reason/accuracy enums.
- `backend/app/beyo_manager/models/tables/users/user_work_profile.py`: added user work profile table.
- `backend/app/beyo_manager/models/tables/users/user_shift_state_record.py`: added shift state history table.
- `backend/app/beyo_manager/models/tables/working_sections/working_section.py`: added working section table.
- `backend/app/beyo_manager/models/tables/working_sections/working_section_membership.py`: added membership bridge/history table.
- `backend/app/beyo_manager/models/tables/working_sections/working_section_dependency.py`: added section dependency graph table.
- `backend/app/beyo_manager/models/tables/working_sections/working_section_item_category.py`: added section-item-category bridge table.
- `backend/app/beyo_manager/models/tables/working_sections/working_section_supported_issue_type.py`: added section-issue-type bridge table.
- `backend/app/beyo_manager/models/tables/issue_types/issue_type.py`: added issue type registry table.
- `backend/app/beyo_manager/models/tables/issue_types/issue_severity.py`: added issue severity registry table.
- `backend/app/beyo_manager/models/tables/issue_types/issue_category_config.py`: added issue-category timing config table.
- `backend/app/beyo_manager/models/tables/items/item_category.py`: added item category table.
- `backend/app/beyo_manager/models/tables/items/item.py`: added item table.
- `backend/app/beyo_manager/models/tables/items/item_issue.py`: added item issue table.
- `backend/app/beyo_manager/models/tables/items/item_upholstery.py`: added item upholstery table.
- `backend/app/beyo_manager/models/tables/items/item_upholstery_requirement.py`: added item upholstery requirement table.
- `backend/app/beyo_manager/models/tables/upholstery/upholstery.py`: added upholstery registry table.
- `backend/app/beyo_manager/models/tables/upholstery/upholstery_inventory.py`: added upholstery inventory table.
- `backend/app/beyo_manager/models/tables/upholstery/upholstery_inventory_threshold_policy.py`: added threshold policy table.
- `backend/app/beyo_manager/models/tables/customers/customer.py`: added customer table with circular FK handling.
- `backend/app/beyo_manager/models/tables/customers/customer_history_record.py`: added customer history table.
- `backend/app/beyo_manager/models/tables/static_costs/static_cost.py`: added static costs table.
- `backend/app/beyo_manager/models/tables/tasks/task.py`: added task table (including enum collision safeguard).
- `backend/app/beyo_manager/models/tables/tasks/task_history_record.py`: added task history table.
- `backend/app/beyo_manager/models/tables/tasks/task_event.py`: added task event table.
- `backend/app/beyo_manager/models/tables/tasks/task_note.py`: added task note table.
- `backend/app/beyo_manager/models/tables/tasks/task_item.py`: added task-item bridge table.
- `backend/app/beyo_manager/models/tables/tasks/task_step.py`: added task step table with aggregate mixins.
- `backend/app/beyo_manager/models/tables/tasks/step_state_record.py`: added step state records table.
- `backend/app/beyo_manager/models/tables/tasks/task_step_dependency.py`: added task-step dependency table.
- `backend/app/beyo_manager/models/tables/tasks/task_step_assignment_record.py`: added assignment history table.
- `backend/app/migrations/versions/ddc5bf50153b_rename_enum_labels_to_lowercase.py`: renamed existing PostgreSQL enum labels to lowercase and fixed enum-dependent literals.
- `backend/app/migrations/versions/243e62bcd858_add_missing_circular_fks.py`: added the missing circular foreign keys for customers, tasks, and task steps.
- `backend/architecture/40_identity_local.md`: documented newly reserved prefixes and collision-avoidance decisions.

## Contract adherence

- `backend/architecture/03_models.md`: used SQLAlchemy 2.x `Mapped`/`mapped_column`, FK indexing, UTC DateTime columns, and named constraints/indexes.
- `backend/architecture/08_domain.md`: all enums placed under `domain/<domain>/enums.py` and imported into model files.
- `backend/architecture/21_naming_conventions.md`: naming patterns applied for table, index, and unique/check constraints.
- `backend/architecture/30_migrations.md`: circular FK links modeled with `use_alter=True`, explicit names were retained, and the final DB state was corrected with a follow-up migration where Alembic had not emitted the circular constraints.
- `backend/architecture/40_identity.md`: each new addressable model defines `CLIENT_ID_PREFIX`; local companion updated for app-specific prefix registry.

## Validation evidence

- `APP_ENV=development ./.venv/bin/python -c "from beyo_manager.models import Base; print('OK_BASE_IMPORT')"` (run in `backend/app`): `OK_BASE_IMPORT`.
- `./.venv/bin/python -m compileall -q beyo_manager && echo COMPILE_OK` (run in `backend/app`): `COMPILE_OK`.
- `APP_ENV=development ./.venv/bin/alembic upgrade head` (run in `backend/app`): applied both follow-up migrations successfully.
- `APP_ENV=development ./.venv/bin/alembic revision --autogenerate -m "final_drift_check"`: no detected schema drift after the follow-up migration.

## Known gaps or deferred items

- None currently tracked.

## Handoff notes (if needed)

- To frontend: N/A
- From frontend dependency: N/A

## Lifecycle transition

- Current state: `archived`
- Next state: `N/A`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_models_tables_20260515_1000.md`
