# SUMMARY_declared_worker_states_phase1_model_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase1_model_20260729`
- Status: `summarized`
- Owner agent: `Codex` (implementation) / `claude-fable-5` (lifecycle finalization) / `Opus` (review)
- Created at (UTC): `2026-07-29T16:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase1_model_20260729.md`
- Master plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 1 of 7)
- Related debug plan: none

## What was implemented

- `UserDeclaredStateRecord` model (`user_declared_state_records`, prefix `uds`) — the inert source
  table for worker-declared states: `user_id`, `workspace_id`, `pause_reason_id` (FK to the
  manager-editable catalog), `description`, `entered_at`/`exited_at` (NULL = open),
  `created_by_id`, `closed_by_id` (NULL = system-closed). All FKs `ondelete="RESTRICT"`.
- DB-level invariants: partial unique index `uix_user_declared_state_records_active` on
  `(user_id, workspace_id) WHERE exited_at IS NULL` (one open declaration per worker per
  workspace) and check `exited_at IS NULL OR exited_at >= entered_at`; two supporting indexes.
- Alembic revision `595e7b840926` (single head) with clean downgrade; verified
  upgrade→downgrade→upgrade.
- Four PostgreSQL constraint tests proving the invariants against the migrated schema (the test
  schema comes from Alembic, so the tests prove the migration, not just the model).
- Registration: `models/__init__.py`, `uds` claimed in `client_id_prefix_map.md`, boundary rules
  documented in `models/tables/users/README.md` (source table, never rebuilt, one-open-row rule,
  close-don't-delete, `closed_by_id IS NULL` = system-closed).
- **Inert by design**: no service, command, query, router, or worker references the table yet
  (Phase 2 wires the derivation read path; Phase 3 the write path).

## Files changed

- `app/beyo_manager/models/tables/users/user_declared_state_record.py`: new model.
- `app/migrations/versions/595e7b840926_create_user_declared_state_records_table.py`: new revision.
- `app/tests/integration/models/users/test_user_declared_state_record.py`: 4 constraint tests.
- `app/beyo_manager/models/__init__.py`: registration.
- `app/beyo_manager/models/tables/client_id_prefix_map.md`: `uds` claimed.
- `app/beyo_manager/models/tables/users/README.md`: table row + boundary rules.

## Contract adherence

- `03_models.md` / `21_naming_conventions.md`: mirrors `user_shift_state_records` conventions
  (constraint/index naming, partial-index recipe, mapped_column style).
- `30_migrations.md`: hand-verified autogenerate output (partial index `postgresql_where`
  preserved); clean downgrade.
- `24_multi_tenancy.md`: workspace-scoped with indexed `workspace_id`.
- `15_testing.md`: constraint tests co-located under `tests/integration/models/users/`.

## Validation evidence

- Reviewer (Opus) independently re-ran every gate and `APPROVED` (review log in the plan):
  constraint suite 4/4; index confirmed live in `app_test`; upgrade→downgrade→upgrade clean;
  imports clean; table registered with expected 9 columns.
- **Baseline-diff proof of inertness** (reviewer, detached worktrees at `091c0db` vs `a84610c`,
  same DB): 25 failed/1157 passed vs 25 failed/1161 passed — failure lists identical
  test-for-test; delta = the 4 new tests, all passing. Zero failures attributable to Phase 1.
- Ruff: touched files clean; repo-wide 149 errors identical to the pre-phase baseline.
- **Validation waiver** (operator, recorded in the plan's Review log): the full-suite-green and
  fresh-empty-DB gates were waived for the pre-existing repository baseline only (22–25 failing
  tests incl. flaky non-idempotent cases, 149 ruff errors, historical migration-graph
  topological-sort stall on empty DBs). Binding no-new-failures rule added to the master plan for
  all remaining phases.

## Known gaps or deferred items

- Repo-health (explicitly out of feature scope, tracked in the master plan's baseline note):
  pre-existing failing tests (incl. two in `test_worker_shift_commands` — this feature's own
  domain; Phase 2/3 implementers and reviewers must treat those two as baseline, not regressions),
  the non-idempotent shopify metafield test, 149 baseline ruff errors, empty-DB Alembic
  topological-sort stall, and a pre-existing `client_id_prefix_map.md` typo (`ussr` recorded for
  `UserShiftStateRecord` whose real prefix is `uss`).

## Handoff notes

- Frontend contract unaffected by this phase (tables only). Build-ahead contract:
  `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 1 status → `archived`; next phase to launch: Phase 2 (derivation integration).
