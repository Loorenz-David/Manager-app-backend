---
plan: maintenance (migration-environment shim follow-up — outside the item-cost pipeline)
role: maintenance
round: 2
date: 2026-08-12
state: COMPLETE
verdict: PASS
actor: Codex
---

# Migration-environment shim follow-up — round 2 handoff

## Summary

The owner-authorized durable correction is proven. The historical Alembic graph
is acyclic on disk, the private-internals graph repair is removed, and the
cold-build workspace is transient and leaves no shim residue.

## Implementation

- `app/migrations/versions/8cf57fa23110_improve_task_notes_and_image_links.py`
  changes only `down_revision` from `a3b5c7d9e1f2` to `183fb6115bd3`, with the
  owner-authorized metadata-only comment.
- `app/migrations/env.py` no longer imports or mutates private Alembic graph
  internals. A genuinely cold build temporarily creates
  `mig_cold_build_workspace`; cleanup in `finally` removes its pause-reason
  rows and the workspace before the migration command returns.
- The owner authorization is recorded in
  `planning/owner_decisions.md` (maintenance card 1, 2026-08-12).

## Proof

### 3a — from-scratch upgrade

On disposable database `beyo_manager_migration_shim_r2`, twice:

- empty database → `90cdd23a828e` in **2 seconds**;
- no migration failure or cycle stall.

### 3b — fresh-database residue

After each cold build, before dropping the disposable database:

- `workspaces`: **0** rows;
- `pause_reasons`: **0** rows;
- `mig_cold_build_workspace` workspace rows: **0**;
- `Migration workspace` rows: **0**;
- pause-reason rows attached to `mig_cold_build_workspace`: **0**;
- dynamic scan of every text column: **0** matches for either
  `mig_cold_build_workspace` or `Migration workspace`.

The disposable database was dropped after verification. The configured
`beyo_manager` database was never downgraded or destructively modified.

### 3c — configured no-op

Configured database `alembic current` remained `90cdd23a828e (head)` before and
after `alembic upgrade head`; the no-op completed in **1 second**.

### 3d — full non-e2e suite

`PYTHONPATH=. .venv/bin/pytest -m 'not e2e'` from `app/` completed in **68.37s**:

**1684 passed / 23 failed / 1 deselected** (1708 collected, 1707 selected).

The 23 failing test identities match the recorded baseline; no new failure or
migration-related regression appeared. The known Shopify ordering-flake note
did not require a retry for this run.

### 3e — private-internals audit

`env.py` is grep-clean for `_revision_map`, `nextrev`, `_all_nextrev`,
`RevisionMap`, `_proxy`, and `revision_map`. Source compilation and
`git diff --check` also pass.

## Architecture Graph

The graph was rechecked before and after the work: initialized and valid, 125
nodes, 161 edges, no diagnostics, no stale nodes, and no migration architecture
node matched by the bounded search. No graph delta was recorded.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Write perimeter

Maintenance perimeter:

- `app/migrations/versions/8cf57fa23110_improve_task_notes_and_image_links.py`
  — authorized metadata line and comment only;
- `app/migrations/env.py` — graph-shim removal and transient-anchor cleanup;
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  — §10 recipe updated to the final verified state;
- this handoff.

The concurrent phase-3 documentation changes were not edited by this session
and were preserved. The migration/env implementation is present in the final
tree from the shared-workspace parent commit `cbdf393c9818cde3a1d81615d44987b17237b93b`.
Final implementation commit: **cbdf393c9818cde3a1d81615d44987b17237b93b**.
The closing maintenance commit carries this handoff and the final §10 recipe
update.
