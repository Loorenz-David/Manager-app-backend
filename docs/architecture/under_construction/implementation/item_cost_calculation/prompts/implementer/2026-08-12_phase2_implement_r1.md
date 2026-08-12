---
plan: phase 2 (schema, models & migration)
role: implementer
round: 1
date: 2026-08-12
---

# Session prompt — implement phase 2: schema, models & migration

You are the **implementing agent** for phase 2 of the item-cost-calculation pipeline.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — shared charter.
2. `/Users/davidloorenz/agent-skills/implementation-executor.md` — your session
   doctrine. Follow it end to end.

**The plan file is your task list; where this prompt differs, the plan file wins.**

## Gate check (verify before working; on any failure, stop and report)

- `master_plan.md` §4 tracker shows phase 1 **APPROVED** and phase 2 **PROMPT_READY**
  (projection round 0 ran 2026-08-12; its 16-row ledger is fully routed into the
  artifacts you will read — nothing is pending).
- No phase-2 implementer handoff exists (you are round 1).

## Read order (after doctrine)

1. `master_plan.md` — §5; **§6 entire, including the CLOSED CHECK-constraint table,
   the deliberate-absence list, and the three named FKs** (every name is fixed; a
   needed unlisted name routes back to the coordinator — never invent one); §9
   (P-B, P-G incl. named mutations for near-identical rows); **§10 including the
   disposable-database recipe** (which DB each criterion targets is pinned in the
   plan's criteria preamble).
2. `plans/phase_2_schema_models.md` — your task list and criteria, as amended
   2026-08-12 (per-table column shapes, the three-population enum-ownership table,
   the 12-row type CHECK table, C1(a)/(b), C5's migration-site proof, C6).
3. Intention §4 entire (incl. §4.5's round-7 term-table pin and §4.6 as amended
   round 6), §4A (A1–A8), §4.7A, §4.8, §6A.4, §7A intro; §2.5 conventions.
4. Re-emit the master plan §5 contract resolution before coding (your doctrine's
   obligation) — `03_models`, `30_migrations`, `21_naming_conventions`,
   `25_soft_delete`, `24_multi_tenancy`, `15_testing` are the load-bearing ones here.

Line numbers in the artifacts date to 2026-08-11/12 — verify by symbol name.

## Hard scope fences (violations are automatic review findings)

- **No writes to any existing table's model, and no data migration** — the §10.2
  legacy migration is phase 6; the three reused PG enum types belong to `tasks` and
  your migration neither creates nor drops them.
- No commands, queries, routers, serializers, or calculator — schema layer only.
- The configured development database is **never downgraded** (charter rule 7);
  destructive verification only on the §10-recipe disposable DB.
- Deliberate absences stay absent: no CHECK on `production_budget_minor` /
  `allowed_worker_minutes` (A8), no narrowing CHECK on `task_state_snapshot`, no
  upper-bound CHECK on `percent_value` (the `Numeric(6,3)` type is the bound).

## Non-optional constraints (from the routed projection ledger)

- The §6.2 CHECK list is **closed** — build exactly it; C1(a) asserts it by exact
  name (three names deliberately use the `pcbv`/`ice` prefix tokens because the
  full-table forms exceed PostgreSQL's identifier limit — do not "normalize" them).
- Column shape is **per-table** (plan task 2), never blanket: the membership table
  has interval columns only; `item_valuations` has no `updated_*`; the term-snapshot
  table follows the §4.5 round-7 pin (`workspace_id`, `percent_value`/
  `fixed_amount_minor`, `created_at` only).
- Enum ownership is enforced **in the migration only** (the model-layer
  `create_type=False` flag is inert on `sa.Enum`): hand-fix reused types to
  `postgresql.ENUM(..., create_type=False)` in `upgrade`; drop exactly the five new
  types in `downgrade`; hand-add the three named `use_alter` FKs (autogenerate
  omits them — precedent `243e62bcd858`).
- Exception classes per C3: CHECK violations are `IntegrityError`; the
  `percent_value = 1000` row is `DBAPIError`/DataError. Do not blur them.
- Named mutations you must run and revert, declaring results in your handoff:
  C5's M-a and M-b (enum ownership, both directions), and the C2 predicate-clause
  mutations on the three multi-clause indexes (INV-B1, INV-E1, INV-V1) at minimum.
- **Before your first change:** confirm the full-suite baseline against master plan
  §10's recorded 23-failure list (run from `backend/app/`, healthy containers; a
  run with connection noise is never evidence) and record the confirmation in the
  plan's Review log.

## Explicit delegation list (granted on purpose — from the projection)

1. **Flush vs commit in constraint tests:** flush-only on the rolled-back
   `db_session` is recommended (rule 11½ by construction). Do NOT copy
   `test_shopify_foundation_constraints.py` — it commits without teardown (a live
   rule-11½ violation).
2. **Reject-case isolation:** `begin_nested()` per case or parametrized
   one-case-per-test — your choice; if parametrized, name the constraint in the
   test id, not an example value (P-G(b)).
3. **Import placement in `models/__init__.py`** within the plan's Notes constraints
   (after tasks/items/working_sections/users/workspaces; trailing block
   recommended).
4. **`is_deleted` `index=True` or not** — uniform across the eight tables either way.
5. **Test file placement:** `tests/integration/models/item_economics/` matches the
   existing layout; factory design is yours (every factory needs a caller this
   phase — rule 4). Note C4's fixture needs the full FK graph (workspace, item,
   task, group, basis version, model version).

## Closing protocol (per your doctrine; summarized)

1. All criteria green (C1a/C1b, C2 incl. (b)-per-clause, C3 incl. the 12-row table,
   C4, C5a/C5b, C6); named mutations run, reverted, declared.
2. Manual round-trip on the disposable DB recorded in the Review log (rule-1
   exemption record); disposable DB dropped afterwards; configured DB verified at
   head.
3. Full suite green against the §10 baseline (the 23 known failures, no new ones).
4. Archgraph: `archgraph_status` + orient on `table-task-step`, `table-task-item`
   at start; at close record the phase delta in ONE batched
   `archgraph_apply_changes` — the nine new `table-*` nodes (+ obvious FK edges),
   evidence = the model files with accurate spans. Never adjudicate pending
   reviews. (Your delta lands as pending items; the phase reviewer verifies them
   and the coordinator confirms them after approval — standing owner authorization,
   master plan §8.)
5. Tracker row → `IMPLEMENTED` (append to the Note; never overwrite prior actors'
   stamps); Review log entry (baseline confirmation, round-trip record, judgment
   calls, mutation declarations).
6. Checkpoint commit under the standing authorization:
   `CHECKPOINT (not approved): item-cost phase 2 — <summary>`.
7. Deposit the handoff at
   `handoffs/implementer/2026-08-12_phase2_implement_r1_handoff.md` (frontmatter
   `plan`, `role`, `round`, `date`, `state`, `verdict`, `actor`): summary;
   `⚠ OWNER DECISIONS REQUIRED (n)` (one line if zero); what was implemented vs the
   plan with every judgment call named; test counts before/after; mutation-probe
   declaration (files + reversion); the archgraph delta you recorded (node ids);
   full write perimeter incl. the checkpoint hash. **Deposit the handoff before
   ending the session.**
