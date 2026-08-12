---
plan: maintenance (migration-environment shim follow-up — outside the item-cost pipeline)
role: maintenance
round: 1
date: 2026-08-12
state: BLOCKED — owner decision required
verdict: ESCALATE
actor: Codex
---

# Migration-environment shim follow-up — round 1 handoff

## Summary

The requested durable repair cannot be completed within the prompt's rule-7
perimeter without rewriting an applied migration's revision metadata. No code,
migration, configured database, or item-cost artifact was changed.

## Findings

The repository contains 114 revision files with one root and one apparent head,
but the on-disk graph contains this cycle:

`a3b5c7d9e1f2 → 4f2e9a7b6c1d → 26d4b7f0c3aa → 71df9b8c4a2e → 7e1c3b4a9d2f → 6f4d2c1b9a7e → 8cf57fa23110 → a3b5c7d9e1f2`

The current workaround confirms the required edge correction: `env.py:88`
reparents `8cf57fa23110` from `a3b5c7d9e1f2` to `183fb6115bd3`, then rebuilds
Alembic's map. The same function mutates private Alembic internals at
`env.py:68-92`. A new merge or branch revision cannot remove this cycle: Alembic
loads the existing revision files and detects/traverses the cycle before a new
head revision can make it relevant. A new revision after `90cdd23a828e` would
leave the old SCC in the loaded map.

The cold-build workspace row is a separate residue. Removing
`_ensure_cold_build_workspace` immediately would make the existing chain fail:
`49bd666da846` reads the first workspace to seed pause reasons, and
`fb10ac7fd439` requires all six seeded rows before its backfill. The row is not
owned by a revision and no later revision currently removes it.

## Proof gathered

- Architecture Graph status: initialized and valid; 125 nodes, 161 edges, no
  diagnostics, no stale nodes; no matching migration architecture node was
  found, so no graph delta was available to record.
- Static source declaration walk: 114 revisions, root `a1312183fdfb`, head
  `90cdd23a828e`, and the cycle listed above.
- `architecture/30_migrations.md:311-318` prohibits modifying a migration
  already applied to any environment.
- The current configured database and worktree were left untouched.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Authorize the only durable graph correction

May the maintenance owner authorize a one-line historical metadata correction in
`app/migrations/versions/8cf57fa23110_improve_task_notes_and_image_links.py`
(`down_revision: 'a3b5c7d9e1f2'` → `'183fb6115bd3'`), followed by removal of the
private-internals graph repair and a fresh disposable-database proof? This is the
minimal correction that makes the loaded Alembic graph acyclic, but it rewrites
an applied migration's metadata and therefore violates rule 7 without explicit
owner authorization.

The authorization should also specify the acceptable replacement for the
workspace anchor: either a transient, documented environment-only compatibility
anchor that is removed before `upgrade head` returns, or a revision-owned,
reversible mechanism. Simply deleting the current insert is not safe because the
existing `49bd666da846`/`fb10ac7fd439` chain depends on those rows.

## Deferred proof

The following acceptance checks were not run because the required graph
correction is unauthorized and the current implementation is already known to
depend on the shim:

- from-scratch `alembic upgrade head` with no `mig_cold_build_workspace` row;
- configured database no-op at head;
- full baseline suite;
- final audit that `env.py` has no private-internals mutation;
- final handoff commit hash.

## Write perimeter

The only file written in this session is this handoff. No migration or
`env.py` change was made. Final commit: **none — blocked pending Card 1**.
