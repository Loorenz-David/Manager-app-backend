---
plan: maintenance (migration-environment shim follow-up — outside the item-cost pipeline)
role: maintenance
round: 1
date: 2026-08-12
status: FILED — run whenever the owner chooses; blocks nothing in the pipeline
---

# Session prompt — replace the migration-environment shim with a durable fix

Filed from phase-2 re-review notes N10/N11 (2026-08-12) so the items cannot
evaporate. The stall fix (`7e1b11d`) works and is verified; these are its residues.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

## The two residues (reviewer-verified)

- **N10 — a permanent data row in every cold-built database.**
  `_ensure_cold_build_workspace` (in `migrations/env.py`) inserts
  `workspaces('mig_cold_build_workspace', …)` into every database built from
  empty. It is written by the migration *environment* (appears in no revision, no
  history, no downgrade removes it); every future staging/production cold build
  inherits it.
- **N11 — the graph repair mutates Alembic private internals**
  (`script.revision_map._revision_map`, `revision.nextrev`, `revision._all_nextrev`)
  on every alembic invocation (guarded on the on-disk graph shape; verified inert
  at head). `_restore_cold_build_role_enum` additionally executes
  `UPDATE workspace_roles SET name = NULL` (double-guarded). An Alembic upgrade
  renaming those internals breaks every migration run. The shim stands in for the
  real fix: the historical revision graph contains a **cycle**
  (`a3b5c7d9e1f2 → … → a3b5c7d9e1f2`).

## Task

1. Design the durable fix: make the on-disk revision graph **acyclic** without
   rewriting applied migration files (charter rule 7) — e.g. a merge/branch
   revision or an Alembic-sanctioned graph correction; eliminate the need for the
   in-memory reparenting.
2. Remove or shrink the cold-build anchors so no synthetic data row lands in cold
   databases (or convert it to something a revision owns and downgrades).
3. Prove: from-scratch `alembic upgrade head` completes; configured DB no-op at
   head; full suite at baseline; no `mig_cold_build_workspace` row in a fresh
   build; `env.py` free of private-internals mutation (or reduced to a documented,
   version-pinned minimum).
4. If any step requires rewriting an applied migration, STOP and escalate to the
   owner as a decision card — do not do it.

## Constraints

Disposable databases only for destructive verification; perimeter =
`migrations/` (new revision(s) only) + `env.py` + your handoff; nothing in the
item-cost pipeline. Commit as `fix(migrations): <summary>` when proven.

## Closing protocol

Deposit the handoff at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/maintenance/2026-08-12_migration-shim-followup_r1_handoff.md`
(full path) with the standard frontmatter, `⚠ OWNER DECISIONS REQUIRED (n)`, proof,
and full write perimeter incl. the FINAL commit hash.
