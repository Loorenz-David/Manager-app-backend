# PLAN_declared_worker_states_phase1_model_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase1_model_20260729`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T12:00:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (master plan plays the intention role; read it first — decisions D1–D10 are binding)

## Goal and intent

- Goal: Create the `user_declared_state_records` source table (model + Alembic migration + docs registration) — the append-style record of what a worker declared they were doing outside task steps. **Inert in this phase**: no service reads or writes it.
- Business/user intent: Foundation for explainable non-task time. The table must be a *source* table (like `StepStateRecord`), never rebuilt, so declarations survive the clock-out reconstruction of the derived `UserShiftStateRecord` table.
- Non-goals: Any command, query, route, reconcile, or reconstruction change (Phases 2–3). Any data migration of legacy `manually_recorded` rows (master D7: frozen, none ever).

## Scope

- In scope:
  1. New model `app/beyo_manager/models/tables/users/user_declared_state_record.py` — `UserDeclaredStateRecord`, `CLIENT_ID_PREFIX = "uds"`, `__tablename__ = "user_declared_state_records"`.
  2. Alembic migration creating the table with all constraints/indexes; clean downgrade (drop table).
  3. Registration: model import in `models/__init__.py`; prefix added to `models/tables/client_id_prefix_map.md` (verify `uds` is unused first — if taken, pick the nearest free prefix and record the deviation in the Review log); table row + boundary rules added to `models/tables/users/README.md`.
- Out of scope: everything else (see master phase table).
- Assumptions:
  - Column set (mirrors `UserShiftStateRecord` / `StepStateRecord` pause conventions; `IdentityMixin` supplies `client_id`):
    - `user_id`: `String(64)` FK `users.client_id` `ondelete="RESTRICT"`, not null, indexed
    - `workspace_id`: `String(64)` FK `workspaces.client_id` `ondelete="RESTRICT"`, not null, indexed
    - `pause_reason_id`: `String(64)` FK `pause_reasons.client_id` `ondelete="RESTRICT"`, not null, indexed
    - `description`: `String(512)`, nullable (required-iff-`requires_description` is a command-layer rule, Phase 3 — not a DB constraint)
    - `entered_at`: `DateTime(timezone=True)`, not null
    - `exited_at`: `DateTime(timezone=True)`, nullable — `NULL` = currently open
    - `created_by_id`: `String(64)` FK `users.client_id` `ondelete="RESTRICT"`, not null (the declaring actor)
    - `closed_by_id`: `String(64)` FK `users.client_id` `ondelete="RESTRICT"`, nullable (`NULL` when closed by the system: reconcile auto-close or clock-out clamp)
  - Constraints / indexes (mirror `user_shift_state_records` naming style):
    - `CheckConstraint("exited_at IS NULL OR exited_at >= entered_at", name="ck_user_declared_state_records_exited_after_entered")`
    - Partial unique index `uix_user_declared_state_records_active` on `(user_id, workspace_id)` `WHERE exited_at IS NULL` — **at most one open declaration per worker per workspace**
    - `Index("ix_user_declared_state_records_user_workspace_entered", "user_id", "workspace_id", "entered_at")`
    - `Index("ix_user_declared_state_records_workspace_reason", "workspace_id", "pause_reason_id")`
  - No `state` enum column: the row *is* the state; its meaning comes from `pause_reason_id`.
  - No soft-delete columns: like `user_shift_state_records`, lifecycle is fully expressed by `entered_at`/`exited_at`; rows are never deleted.

## Clarifications required

- [x] Prefix `uds` — resolved: use it if free in `client_id_prefix_map.md`; otherwise nearest free prefix + Review-log note.
- [x] Soft delete — resolved: none (matches `user_shift_state_records`; rows are history, closing = `exited_at`).

## Acceptance criteria

1. `alembic upgrade head` applies cleanly on a fresh DB and on a DB at current head; `alembic downgrade -1` drops the table cleanly.
2. Model imports without circulars; `models/__init__.py` registers it; app boots.
3. DB-level invariants proven by integration test: (a) inserting a second open row for the same `(user_id, workspace_id)` raises `IntegrityError`; (b) two open rows for the *same user in different workspaces* are allowed; (c) `exited_at < entered_at` is rejected; (d) closing the open row then inserting a new open row succeeds.
4. `client_id_prefix_map.md` and `models/tables/users/README.md` updated (README documents: source table, never rebuilt, one-open-row rule, close-don't-delete).
5. `ruff check` clean on touched files; full test suite green.

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md`: model conventions (mapped_column style, FK/ondelete, naming).
- `backend/architecture/30_migrations.md`: Alembic authoring, upgrade/downgrade discipline.
- `backend/architecture/21_naming_conventions.md`: table/index/constraint names.
- `backend/architecture/24_multi_tenancy.md`: workspace scoping column requirements.
- `backend/architecture/15_testing.md`: integration-test placement for DB-constraint tests.

### Local extensions loaded

- None required for a pure model phase.

### File read intent — pattern vs. relational

Permitted relational reads:
- `models/tables/users/user_shift_state_record.py` — the sibling this model mirrors (constraint/index naming, partial-index recipe).
- `models/tables/pause_reasons/pause_reason.py` — exact FK target column name.
- `models/base/identity.py` — what `IdentityMixin` supplies.
- `models/__init__.py`, `models/tables/client_id_prefix_map.md` — registration points.
- Latest migration under `app/migrations/versions/` — current head revision id only.

Prohibited pattern reads: other models to learn "how to write a model" → `03_models.md`; other migrations to learn migration shape → `30_migrations.md`.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md` (lifecycle only — no dedicated model skill).
- Router trigger terms: `model`, `migration`.
- Excluded alternatives: none applicable.

## Implementation plan

1. Verify `uds` is free in `models/tables/client_id_prefix_map.md`; claim it.
2. Write `user_declared_state_record.py` exactly per the Assumptions column/constraint spec.
3. Register the model in `models/__init__.py`.
4. Autogenerate + hand-verify the Alembic migration (constraints, partial index `postgresql_where`, index names); write the downgrade (drop table).
5. Update `client_id_prefix_map.md` and `models/tables/users/README.md` (add table row + boundary rules: source table, one open row, never deleted, closed via `exited_at`, `closed_by_id NULL` = system-closed).
6. Integration test `tests/integration/models/test_user_declared_state_record.py` (or the project's established location for constraint tests — check where `uix_user_shift_state_records_active` is tested and co-locate): the four invariants from acceptance 3.
7. Run validation plan.

## Risks and mitigations

- Risk: autogenerate misses the partial unique index (`postgresql_where`).
  Mitigation: hand-verify migration against the model; acceptance 3(a) proves it at the DB level.
- Risk: prefix collision.
  Mitigation: step 1 checks the map first.
- Risk: FK to `pause_reasons` blocks hard-deleting reasons.
  Mitigation: intended — the catalog is soft-delete (`is_deleted`); RESTRICT protects history.

## Validation plan

- `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`: applies/reverts/reapplies cleanly.
- `pytest <constraint test path> -q`: all invariants pass.
- `pytest app/tests -q` (full suite): green — proves the phase is inert.
- `ruff check`: clean.

## Review log

- (empty — filled by implementer and reviewer)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
