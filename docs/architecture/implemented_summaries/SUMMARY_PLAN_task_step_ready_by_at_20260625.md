# SUMMARY_PLAN_task_step_ready_by_at_20260625

## Metadata

- Summary ID: `SUMMARY_PLAN_task_step_ready_by_at_20260625`
- Status: `summarized`
- Owner agent: `Codex`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_step_ready_by_at_20260625.md`
- Related debug plan (optional): `—`

## What was implemented

- Added nullable `ready_by_at` to `TaskStep` and created a matching Alembic migration.
- Extended task-create and task-step-add request models and router bodies so step inputs can carry `ready_by_at`.
- Applied fallback assignment logic so a step inherits the task deadline when its own `ready_by_at` is omitted.
- Added `update_task_step_ready_by_at` plus `PATCH /api/v1/tasks/{task_id}/steps/ready-by-at` for batch deadline updates.
- Exposed `ready_by_at` in task-step serializers used by task and working-section read paths.
- Wrote a frontend handoff document for the new request/response contract.

## Files changed

- `app/beyo_manager/models/tables/tasks/task_step.py`: added the new column on `TaskStep`.
- `app/migrations/versions/4f2e9a7b6c1d_add_ready_by_at_to_task_steps.py`: migration to add/drop the column.
- `app/beyo_manager/services/commands/tasks/requests/__init__.py`: extended `TaskStepInput`.
- `app/beyo_manager/services/commands/task_steps/requests/__init__.py`: extended `StepInputItem` and added the batch-update request parser.
- `app/beyo_manager/services/commands/tasks/create_task.py`: applied create-time fallback assignment.
- `app/beyo_manager/services/commands/task_steps/add_task_steps.py`: applied add-time fallback assignment.
- `app/beyo_manager/services/commands/task_steps/update_task_step_ready_by_at.py`: added the new batch update command.
- `app/beyo_manager/routers/api_v1/tasks.py`: added the new route and body models.
- `app/beyo_manager/domain/task_steps/serializers.py`: exposed `ready_by_at` in compact step serialization.
- `app/beyo_manager/domain/tasks/serializers.py`: exposed `ready_by_at` in task detail step serialization.
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_step_ready_by_at_20260625.md`: frontend contract handoff.

## Contract adherence

- `architecture/03_models.md`: kept the new field as a plain SQLAlchemy column with `DateTime(timezone=True)`.
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: used command-local parsing and `maybe_begin`, with event dispatch after the write transaction.
- `architecture/09_routers.md`: kept the router thin and wired path/body data into `ServiceContext`.
- `architecture/30_migrations.md`: added a reversible migration file for the schema change.
- `architecture/46_serialization.md`: limited serializer changes to presentation-layer field exposure.

## Validation evidence

- `python3 -m py_compile ...`: passed for the touched Python files, including the new command, router, request models, model, serializers, and migration.
- `alembic revision --autogenerate` / `alembic upgrade head`: not run because no local `alembic` executable or project virtualenv was available in this workspace.
- Manual review of impacted read/write paths: completed against task creation, step add, task step list, task detail, working-section step list, and last-active-step payload assembly.

## Known gaps or deferred items

- Migration was written manually rather than auto-generated because Alembic was unavailable locally in this workspace.
- No automated test suite was run in this turn, so runtime verification remains pending.

## Handoff notes (if needed)

- To frontend: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_step_ready_by_at_20260625.md`
- From frontend dependency: `—`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_task_step_ready_by_at_20260625.md`
