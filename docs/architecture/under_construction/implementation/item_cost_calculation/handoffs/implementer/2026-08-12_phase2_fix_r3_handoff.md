---
plan: phase 2 (schema, models & migration)
role: fix
round: 3
date: 2026-08-12
state: IMPLEMENTED
actor: Codex
---

# Phase 2 fix-r3 handoff

Resolved reviewer r2's blocking B5 finding within the declared fix-cycle
perimeter. The schema, migration, and production code are unchanged; the C2
fixture now distinguishes an active section in two production cost groups from
the `removed_at` exclusion case.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## B5 resolution

In the `sections_conflict` / `sections_removed` branch of
`test_partial_unique_indexes_enforce_conflicts_and_exclusions`, the fixture now
creates a second `ProductionCostGroup` in the same workspace. The second
`ProductionCostGroupSection` uses that second group's id and the same
`working_section_id` as the first membership. `sections_conflict` therefore
depends only on the shipped `(workspace_id, working_section_id)` unique key;
`sections_removed` remains the one-clause `removed_at` variant on the second
group.

## Verification

- Focused schema module on the configured development database: **79 passed**.
- B5 named mutation on the disposable from-scratch database: replaced
  `uix_production_cost_group_sections_active` with the widened key
  `(workspace_id, production_cost_group_id, working_section_id)` and preserved
  the index name. Exactly
  `test_partial_unique_indexes_enforce_conflicts_and_exclusions[sections_conflict]`
  reddened with `Failed: DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>`.
  The original `(workspace_id, working_section_id)` definition was restored and
  verified from `pg_indexes`; the full disposable focused module then passed
  **79**.
- Full non-e2e suite on the configured development database: **1684 passed / 23
  failed / 1 deselected**. The 23 failures are the recorded baseline set.
- Configured development database: `90cdd23a828e (head)`; no downgrade or
  mutation performed.
- Disposable database `phase2_b5_r3_20260812`: created from empty with the
  master-plan §10 recipe, used for the mutation, and dropped. No disposable
  database remains.
- Archgraph: read-only status check; **zero delta**. Revision
  `9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e`, 125 nodes,
  161 edges, 15 pending reviews, 0 stale nodes, 0 diagnostics.
- Optional notes N12 and N13 were not taken; no work beyond B5 was added.

## Mutation-probe perimeter

The B5 mutation touched only the disposable database's DDL. No repository file
was applied and reverted by this probe; the migration source remained unchanged.

## Full write perimeter

### Fix changes in checkpoint `e9d6ac6`

- `app/tests/integration/models/item_economics/test_item_economics_schema.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_2_schema_models.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`

### Handoff deposited after the checkpoint

- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-12_phase2_fix_r3_handoff.md`

### Tool-recorded state

- Architecture Graph: read-only status; zero delta.
- Disposable database: all DDL mutations restored before the database was
  dropped.

The checkpoint was not amended; `e9d6ac6` is the final checkpoint hash. Its
subject is `CHECKPOINT (not approved): item-cost phase 2 fix r3 — correct section
group fixture`.
