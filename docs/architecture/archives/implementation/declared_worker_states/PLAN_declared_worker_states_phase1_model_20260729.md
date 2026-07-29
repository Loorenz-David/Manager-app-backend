# PLAN_declared_worker_states_phase1_model_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase1_model_20260729`
- Status: `archived` (reviewed and APPROVED by Opus at commit `a84610c`; summarized and archived)
- Owner agent: `claude-fable-5` (plan) → `Codex` (implementation) → `Opus` (review)
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-29T16:00:00Z`
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

- `2026-07-29T14:04:55Z` — Codex (implementer)
  - Implemented `UserDeclaredStateRecord`, model registration, autogenerated revision
    `595e7b840926`, prefix/table documentation, and four PostgreSQL constraint tests.
  - Verified `uds` was unclaimed before registration.
  - Green evidence:
    - Development DB: `alembic upgrade head` → `alembic downgrade -1` →
      `alembic upgrade head` all completed successfully.
    - Focused constraint suite: `4 passed`.
    - Touched-file `ruff check`: clean.
    - Model registration/import check: clean.
    - Inertness scan: runtime references are limited to the model module and
      `models/__init__.py`; all other references are documentation or tests.
  - Repository-level validation blockers outside this phase's touched scope:
    - Fresh empty DB: the existing historical Alembic graph remains CPU-bound in
      `RevisionMap._topological_sort` before the first revision executes; the run was
      terminated after PostgreSQL confirmed only an uncommitted
      `CREATE TABLE alembic_version`.
    - Full suite: `1161 passed, 25 failed`; failures are in existing bootstrap,
      worker-shift, Shopify, router, audit, and other tests that do not reference
      `UserDeclaredStateRecord`.
    - Full-repository Ruff: `142` existing errors; none are in the touched files.
  - Lifecycle decision: implementation is complete, but summary/archive and the
    master Phase 1 status transition are held pending operator direction because the
    required fresh-DB, full-suite, and repository-wide Ruff gates are not green.
- `2026-07-29` — operator (David) via claude-fable-5: **VALIDATION WAIVER — blockers verified
  pre-existing; scope expansion declined; lifecycle unblocked.**
  - Verification method: `git stash -u` (Phase 1 is uncommitted), re-run gates on the
    pre-phase baseline, restore, compare.
  - **Ruff**: `ruff check .` = **149 errors on baseline and 149 with Phase 1** — identical;
    Phase 1 adds zero. (Implementer's 142 vs 149 = invocation difference; the equality is
    the evidence.)
  - **Full suite**: baseline (no Phase 1) = **22 failed / 1160 passed**; with Phase 1 =
    **23 failed / 1163 passed** — the same 22 failures plus the 4 new constraint tests
    (all passing) plus `test_create_shopify_metafield_preferences::test_create_uses_client_supplied_id_for_new_preference`,
    which was **reproduced failing on the baseline as well** (non-idempotent test: hardcoded
    client_id + no cleanup → "Provided client_id is already in use" on any re-run against a
    dirty test DB). Run-to-run variance (22/23/25) is dirty-shared-DB flakiness in
    pre-existing tests. **Zero failures are attributable to Phase 1.**
  - **Fresh-DB Alembic stall**: occurs in the historical revision graph's topological sort
    before any revision executes; the new revision appends at head and
    upgrade→downgrade→upgrade passed on dev and testing DBs. Pre-existing by construction.
  - Ruling: acceptance 1's fresh-DB clause and acceptance 5's "full test suite green" are
    **waived for the pre-existing baseline only**, re-interpreted as "no NEW failures/errors
    relative to the recorded baseline" — which is met. The repository-health items (22
    failing tests, the non-idempotent shopify test, 149 ruff errors, the migration-graph
    topological-sort stall) are logged as **separate repo-health work outside this feature
    set** and must not be absorbed into any phase.
  - Lifecycle: proceed to reviewer; on approval, complete summary/archive/master-table
    transition as normal.
- `2026-07-29` — reviewer (`claude-opus-5`, adversarial verification of commit `a84610c`):
  **APPROVED — 0 blocking findings, 0 minor findings against this phase.**
  - Scope reviewed: commit `a84610c` (working tree clean; no uncommitted drift). 9 files —
    model, `models/__init__.py`, migration `595e7b840926`, prefix map, users README,
    constraint tests, master plan, this plan, review prompt.
  - **Column spec**: model matches the Assumptions block exactly — 8 declared columns +
    `client_id` from `IdentityMixin`, correct types/nullability, all four FKs
    `ondelete="RESTRICT"`. No extra columns, none dropped. No `state` enum column, no
    soft-delete columns (both correctly excluded).
  - **Migration**: `postgresql_where=sa.text('exited_at IS NULL')` present on
    `uix_user_declared_state_records_active` in the migration itself (line 44) — not lost by
    autogenerate. Check constraint present in both model and migration. Single Alembic head
    confirmed (`595e7b840926`; the two apparent orphan revisions `183fb6115bd3` /
    `3c2d4e5f6a7b` are absorbed by existing merge revisions).
  - **Re-run validation (not trusted from the implementer's report)**, `APP_ENV=testing`:
    - `pytest tests/integration/models/users/test_user_declared_state_record.py -q` →
      **4 passed**.
    - Live DB introspection of `app_test` (`\d+ user_declared_state_records`): partial unique
      index materialized as
      `UNIQUE, btree (user_id, workspace_id) WHERE exited_at IS NULL`; check constraint
      `CHECK (exited_at IS NULL OR exited_at >= entered_at)`; all five RESTRICT FKs present.
      Schema comes from Alembic (no `create_all` in `init_db`), so the tests prove the
      *migration*, not just the model.
    - `alembic downgrade -1` → table gone (`to_regclass` NULL) → `alembic upgrade head` →
      table + partial index recreated. Full upgrade→downgrade→upgrade cycle verified on an
      existing-head DB.
    - `ruff check` on the four touched source files → **All checks passed**.
      `ruff check .` from repo root → **149 errors**, identical to the recorded baseline
      (the implementer's 142 is the same run from `backend/app/`; both counts reproduced).
  - **Baseline diff (definitive, not variance-based)**: ran the full suite on a detached
    worktree at the parent commit `091c0db` and on `a84610c` against the same DB.
    Baseline = **25 failed / 1157 passed**; Phase 1 = **25 failed / 1161 passed**. The failure
    lists are **identical test-for-test** (including both
    `test_worker_shift_commands` clock-out failures, which are pre-existing and unrelated).
    Delta = the 4 new constraint tests, all passing. **Zero new failures, zero new ruff errors.**
  - **Inertness**: `grep -rn "UserDeclaredStateRecord\|user_declared_state_records"
    app/beyo_manager/` hits only the model module, `client_id_prefix_map.md`, and
    `users/README.md` (both documentation, both required by the plan). Registration in
    `models/__init__.py:46` is by module name (`user_declared_state_record`), which is why it
    does not appear in that grep — verified separately. **No service, router, worker, query,
    or schema references the table.**
  - **Prefix**: `uds` is the only `CLIENT_ID_PREFIX = "uds"` in the codebase and has no
    duplicate in `client_id_prefix_map.md`; claimed correctly.
  - **Docs**: `users/README.md` documents all four required rules (source table / never
    rebuilt / one-open-row / close-don't-delete) plus `closed_by_id IS NULL` = system-closed.
  - **Acceptance 2**: `beyo_manager.models` + `beyo_manager.asgi` import cleanly; table
    registered in `Base.metadata` with the expected 9 columns.
  - Out-of-scope observation (repo-health, **not** a Phase 1 finding, do not fix here):
    `client_id_prefix_map.md` records `UserShiftStateRecord | ussr` while the model's actual
    prefix is `uss`. Pre-existing since commit `3fcfbe5`; the Phase 1 diff only added the
    `uds` row adjacent to it.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `David` (finalized by `claude-fable-5` post-approval)
