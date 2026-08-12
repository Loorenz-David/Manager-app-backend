---
plan: maintenance (migration-chain stall — outside the item-cost pipeline)
role: maintenance
round: 1
date: 2026-08-12
state: COMPLETE
verdict: PASS
actor: Codex
---

# Migration-chain stall — round 1 handoff

## Root cause

The cold upgrade did not hang on a PostgreSQL lock or on async connection cleanup.
On the empty `beyo_manager_stall_probe`, Alembic created `alembic_version` and then
stalled before the first revision. `pg_stat_activity` showed the expected
`idle in transaction` / `ClientRead` state with the last query being
`CREATE TABLE alembic_version`; interrupting the client showed it looping in
Alembic's `RevisionMap._topological_sort`.

The historical revision graph contains a cycle:

`a3b5c7d9e1f2 → 8cf57fa23110 → 6f4d2c1b9a7e → 7e1c3b4a9d2f → 71df9b8c4a2e → 26d4b7f0c3aa → 4f2e9a7b6c1d → a3b5c7d9e1f2`.

Static inspection found 114 revision files, one root, no unknown parents, and
the runtime graph reported `90cdd23a828e` as head. A bounded reproduction of the
topological sorter emitted 69 revisions and then repeatedly switched between
`a3b5c7d9e1f2` and `7e1c3b4a9d2f`.

## Fix

`app/migrations/env.py` now performs a guarded, in-memory compatibility repair:

- reparent the image/task-note revision `8cf57fa23110` from `a3b5c7d9e1f2` to
  the earlier predecessor `183fb6115bd3`, then rebuild Alembic's `RevisionMap`;
- after the initial schema migration on a genuinely cold database, create the
  minimal migration workspace and restore the superseded role-enum shape that
  the later rename revision expects.

The guards match the exact legacy graph and only act when the expected enum/table
shape is absent. Existing databases and already-partially-migrated databases are
left alone. No historical migration file, model, test, or item-cost pipeline file
was rewritten.

## Proof

- Disposable database: `beyo_manager_stall_probe`, created with
  `PYTHONPATH=. APP_ENV=development DATABASE_URL=… python3 -m scripts.create_db`.
- Before the fix, `alembic upgrade 7758ea23764e` reproduced the stall; the session
  was `idle in transaction` / `ClientRead` and the client was in Alembic's
  topological sorter.
- After the fix, an empty database completed
  `PYTHONPATH=. APP_ENV=development DATABASE_URL=… python3 -m alembic upgrade head`
  to `90cdd23a828e` in **1.80s**. Verification found 106 public tables and the
  expected `workspace_role_specialization_enum`.
- Configured database safety check: `make db-migrate` completed as a no-op at head
  in **0.68s**. The configured `beyo_manager` database was not destructively
  modified and remained at `90cdd23a828e`.
- Non-e2e suite: the full invocation is currently blocked by a pre-existing phase-2
  test collection error in
  `tests/integration/models/item_economics/test_item_economics_schema.py` (three
  parametrization names, four supplied values). With that file excluded, the
  remainder completed at the recorded baseline: **1605 passed, 23 failed, 1
  deselected**. No new test failures were attributable to this change.
- The disposable database was dropped after verification.

## Write perimeter

Changed files:

- `app/migrations/env.py` — guarded runtime graph repair and cold-build anchors;
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` §10 — verified recipe replacing the clone workaround;
- `handoffs/maintenance/2026-08-12_migration-chain-stall_r1_handoff.md` — this handoff.

No test-suite, model, historical migration, or item-cost pipeline files were
changed. Commit hash: `2875320`.

⚠ OWNER DECISIONS REQUIRED (0)
