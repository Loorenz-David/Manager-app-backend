# SUMMARY_workspace_role_wood_worker_20260623

## Metadata

- Summary ID: `SUMMARY_workspace_role_wood_worker_20260623`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-23T07:02:59Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_workspace_role_wood_worker_20260623.md`
- Related debug plan (optional): none

## What was implemented

- Added the `WorkspaceRoleNameEnum` domain enum and changed `workspace_roles.name` from required `String(64)` to nullable `workspace_role_name_enum`.
- Updated workspace bootstrapping so system workspace roles are keyed by `role_id`, stored with `name=NULL`, and a custom `wood_worker` workspace role is seeded against the base `worker` permission role.
- Assigned `Mykola` to the new `wood_worker` workspace role during worker bootstrap.
- Updated sign-in response building so system roles fall back to the base permission role name while custom workspace roles still return their custom label.
- Added a migration for the new Postgres enum and updated the living workspace-role table documentation.

## Files changed

- `backend/app/beyo_manager/domain/workspaces/__init__.py`: created the new workspace domain package.
- `backend/app/beyo_manager/domain/workspaces/enums.py`: added `WorkspaceRoleNameEnum.WOOD_WORKER`.
- `backend/app/beyo_manager/models/tables/roles/workspace_role.py`: switched `name` to nullable SQLAlchemy enum storage.
- `backend/app/beyo_manager/services/commands/bootstrap/phases/seed_workspace.py`: seeded system roles with `NULL` names and added the custom `wood_worker` row.
- `backend/app/beyo_manager/services/commands/bootstrap/phases/seed_workers.py`: assigned `Mykola` to the `wood_worker` workspace role key.
- `backend/app/beyo_manager/services/commands/auth/sign_in_user.py`: added the sign-in role fallback.
- `backend/app/tests/unit/services/commands/auth/test_sign_in_user.py`: added coverage for fallback and custom-role response behavior.
- `backend/app/migrations/versions/71df9b8c4a2e_add_workspace_role_name_enum.py`: added the schema migration.
- `backend/app/beyo_manager/models/tables/README.md`: updated the living schema doc for `workspace_roles.name`.

## Contract adherence

- `backend/architecture/08_domain.md`: placed the new enum in `domain/workspaces/enums.py` using `StrEnum`.
- `backend/architecture/06_commands.md`: kept the bootstrap/auth changes within existing command-layer structure and transaction patterns.
- `backend/architecture/23_documentation.md`: updated the living schema doc so the current model truth matches the code.
- `backend/task_system/backend_contract_goal_mapping_guide.md`: restricted relational reads to the concrete files named by the implementation plan.

## Validation evidence

- `python3 -m compileall app/beyo_manager`: passed.
- `PYTHONPATH=app SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://test:test@localhost/test REDIS_URL=redis://localhost:6379/0 ./app/.venv/bin/python ...`: passed direct auth validation for manager-scope admin sign-in, system-role fallback to `manager`, custom-role response `wood_worker`, and invalid scope rejection.
- `npm run typecheck` from `frontend/`: passed after rerunning with filesystem escalation so `tsc` could write `.tsbuildinfo` files outside the backend sandbox.

## Known gaps or deferred items

- No live Alembic `upgrade head` execution was run in this turn, so the migration was validated by code inspection and import/compile checks rather than against a real database.
- The new bootstrap behavior was not exercised through the full reset/bootstrap flow in this turn.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_workspace_role_wood_worker_20260623.md`
