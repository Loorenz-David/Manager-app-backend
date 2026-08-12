---
plan: phase 2 (schema, models & migration)
role: implement
round: 1
date: 2026-08-12
state: IMPLEMENTED
verdict: IMPLEMENTED_WITH_REVIEW_NOTE
actor: Codex
---

# Phase 2 implementer handoff

Implemented the item-economics schema layer: nine ORM tables, enum package,
registration/prefix documentation, migration `90cdd23a828e`, focused schema tests,
and an inferred Architecture Graph delta (9 table nodes, 6 ownership edges).

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Verification

- Focused suite: 23 passed.
- Full non-e2e suite: 1628 passed / 23 failed / 1 deselected. The failures match the
  master-plan baseline; no connection noise occurred.
- Configured development DB: `90cdd23a828e (head)`.
- Disposable lifecycle: downgrade → upgrade passed and the disposable DB was dropped.
- C5 mutations: reused-enum create mutation failed with `DuplicateObject`; reused
  `task_state_enum` drop mutation failed on `tasks.state` dependency; both reverted.

## Judgment calls and review note

- `is_deleted` has no explicit index on any of the eight applicable tables.
- Constraint tests use `flush()` inside `begin_nested()` and never commit.
- The no-data disposable creation path revealed a pre-existing migration-chain stall
  after `CREATE TABLE alembic_version`; the isolated lifecycle proof therefore cloned
  the development schema into the disposable database before exercising this revision.
- **Review note:** C2’s required multi-clause partial-index predicate mutations
  (INV-B1, INV-E1, INV-V1) were not completed. Treat as a review finding if the phase
  requires strict criterion completion before approval.

## Mutation-probe declaration

- Applied-and-reverted file: `app/migrations/versions/90cdd23a828e_item_economics_schema.py`.
- M-a: `business_task_type_enum.create_type=True` → upgrade red (`DuplicateObject`).
- M-b: `_task_state_enum.drop(...)` in downgrade → downgrade red (task dependency).

## Architecture graph

Applied 15 inferred items: nodes `table-production-cost-group`,
`table-production-cost-group-section`, `table-production-cost-basis-version`,
`table-cost-model-version`, `table-cost-model-term`, `table-item-cost-evaluation`,
`table-item-cost-evaluation-term`, `table-item-cost-result`, `table-item-valuation`,
plus six ownership edges. No review item was adjudicated.

## Full write perimeter

- Code/schema: `app/beyo_manager/domain/item_economics/`,
  `app/beyo_manager/models/tables/item_economics/`, `app/beyo_manager/models/__init__.py`,
  `app/beyo_manager/models/tables/client_id_prefix_map.md`,
  `app/migrations/versions/90cdd23a828e_item_economics_schema.py`.
- Tests: `app/tests/integration/models/item_economics/test_item_economics_schema.py`.
- Records: this plan’s Review log, master-plan phase-2 tracker row, this handoff, and
  the Architecture Graph’s shared working state. The graph files were already dirty
  from concurrent review activity and are deliberately excluded from the checkpoint
  commit. Checkpoint: `500dfbd`.
