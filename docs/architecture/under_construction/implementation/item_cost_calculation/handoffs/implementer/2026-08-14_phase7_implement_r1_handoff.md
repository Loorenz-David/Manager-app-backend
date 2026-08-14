---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: implementer
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
checkpoint: a7f421f5e32af9539f64ca904324c5f096c996ab
---

# Phase 7 implementer r1 handoff

Phase 7 is implemented and checkpointed at
`a7f421f5e32af9539f64ca904324c5f096c996ab` with the required subject:
`CHECKPOINT (not approved): item-cost phase 7 implement r1 — evaluations and projections`.

## Delivered

- One shared transactional commit procedure covers explicit commit, projection
  creation, and promotion. It locks task admission and valuation, resolves live
  configuration with `FOR SHARE`, calculates before writes, advances the
  evaluation S1/S2/S3 chain, snapshots calculator outputs, mirrors changed
  valuation figures, writes a TASK-linked history record/audit row, and builds
  the after-transaction `item_economics:evaluation-committed` event.
- Projection source modes are `committed`, `projection`, and `scratch`; labels
  and optional price/purchase overrides are preserved; projections are
  soft-deletable and promotion leaves the source row unchanged.
- The auto path is in `create_task.py`: precheck, `async with
  ctx.session.begin_nested()`, best-effort warning handling, and conditional
  append to the parent `pending_events` list only after normal savepoint exit.
  It never dispatches its own event.
- The evaluations read returns the exact separate `evaluations` and
  `projections` envelope, deterministic ordering, term drill-down, and a
  homogeneous `error` field. Re-derive failures log ERROR with “integrity check
  failed” wording.
- Five ADMIN/MANAGER routes, `_ROUTES` completeness coverage, router README
  entries, shared valuation-chain/config-loader extraction, evaluation request
  models, serializers, and the registered evaluation conflict identity are
  included.
- No migration was added. The configured development database is at
  `be9dfe42a035` (head).

## Exact write perimeter

Production:

- `app/beyo_manager/services/commands/item_economics/commit_item_cost_evaluation.py`
- `app/beyo_manager/services/commands/item_economics/create_item_cost_projection.py`
- `app/beyo_manager/services/commands/item_economics/delete_item_cost_projection.py`
- `app/beyo_manager/services/commands/item_economics/promote_item_cost_projection.py`
- `app/beyo_manager/services/commands/item_economics/requests/__init__.py`
- `app/beyo_manager/services/commands/item_economics/_common.py`
- `app/beyo_manager/services/commands/item_economics/set_item_valuation.py`
- `app/beyo_manager/services/commands/tasks/create_task.py`
- `app/beyo_manager/services/queries/item_economics/list_task_evaluations.py`
- `app/beyo_manager/domain/item_economics/serializers.py`
- `app/beyo_manager/routers/api_v1/item_economics.py`
- `app/beyo_manager/routers/README.md`

Tests and records:

- `app/tests/unit/routers/api_v1/test_item_economics_router.py`
- `app/tests/integration/services/commands/item_economics/test_phase7_evaluations.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_7_evaluations.md`
- `.archgraph/architecture.yml`

## Verification

- Focused final run: **97 passed** — phase-7 router/evaluation tests plus the
  established create-task SKU integration file.
- Full final non-E2E run: **2037 passed, 23 failed, 1 deselected**. The 23
  failures are the established phase-6 baseline set; no phase-7 failure was
  added. The four create-task integration files were also run after the final
  savepoint relocation: **29 passed**.
- Ruff, `git diff --check`, and Python compile checks passed.
- Architecture Graph status after the delta: valid, 166 nodes / 239 edges,
  zero stale nodes, 52 total pending reviews (the two pre-existing reviews
  were untouched; the additive delta contributes 50 pending inferred items);
  delta revision
  `0a71061554fa2123d7e2fba7ff853c328fb1405676194dd0d2cc7f067938266c`.

## Mutation probes (recorded separately)

1. C9 savepoint deletion at the governing definition site in
   `app/beyo_manager/services/commands/tasks/create_task.py`:
   final hash `f1daef7f3e40456eeefa3cd6d6a3518c4f1abffc0eb44710de8e2d1b4205e4c8`;
   mutant hash `51588d730467e2eb88bb6d052f5a4a3d914dbe961d6685c2e5462c674cf20589`;
   the overflow task test reddened with `PendingRollbackError`; restoration
   returned the test to green.
2. C13 route registration without an `_ROUTES` row in
   `app/beyo_manager/routers/api_v1/item_economics.py`:
   final hash `87fcb318050bb089e3e8a5f101e2c47a7def0f68ed85da17d016d4ae544840ae`;
   mutant hash `ce5d6486955dad28fb214dc7407a101e222e876d0e0c173510b7046956e81116`;
   `test_router_route_pairs_match_the_authoritative_route_table` reddened on
   the extra route; restoration returned it to green.

The remaining named two-session concurrency mutations (commit conflict,
valuation mirror race, task lock, and both FOR SHARE chain orderings) were not
run in this implementer session. They are explicitly left for the phase
reviewer’s bounded concurrency pass; no owner decision is required.

## Judgments and handoff notes

- The rate snapshot is recomputed from basis inputs through the canonical
  calculator, never copied from the persisted basis rate.
- The commit history row is `TASK`/`UPDATED` so the existing task-flow query
  sees it; no new history enum or migration was introduced.
- The resolver status-to-identity mapping is consumed as registered, including
  `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY`; ambiguous-group details use the
  already-loaded group rows.
- The phase-5 valuation focused suite was green before and after the extraction,
  and the phase-7 property row verifies set/supersede/delete chain invariants.
- No subagents or external delegations were used. No pending Architecture Graph
  review was adjudicated.
