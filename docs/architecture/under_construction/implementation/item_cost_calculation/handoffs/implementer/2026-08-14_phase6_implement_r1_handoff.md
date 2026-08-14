---
plan: phase 6
role: implement
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
---

# Phase 6 implementer handoff — legacy money migration and API bridge

## Opening summary

Phase 6 is implemented and checkpointed at `b940309`:
`CHECKPOINT (not approved): item-cost phase 6 implement r1 — legacy migration
and API bridge`. The three legacy `items` money columns are migrated into the
valuation surface through a reversible journaled migration, then dropped by a
separate migration. The four legacy request carriers remain visible at the
router boundary and reject only present/non-null values with the exact D1
validation error. The production write paths and nine serializer surfaces no
longer expose the legacy fields.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. No owner decision is requested by this implementation session.

## Coordinator-facing implementation record

- Data migration `5420acc6a7b3` performs P1 amount-without-currency, P2
  negative-amount, and P3 amount-without-creator refusal checks before any
  write; journals every legacy-bearing item; copies only eligible rows; uses
  Python-side `generate_id("ival")`; preserves the exact legacy-to-valuation
  mapping; and restores/deletes only journal-owned state on downgrade.
- Drop migration `be9dfe42a035` removes exactly the three `items` columns and
  re-adds the enum column with `create_type=False` on downgrade. The journal is
  retained through the drop revision and is removed on data-migration
  downgrade.
- The bridge helper is shared by the three item request schemas and the task
  nested-item schema. Absent and explicit-null values pass; present/non-null
  values raise `ValidationError` with
  `ITEM_MONEY_MOVED: item money fields moved to the item-valuation endpoint`.
- Four router bodies intentionally retain the three fields so requests cannot
  silently lose input before the bridge executes. No frontend files changed.
- One additive Architecture Graph node was recorded:
  `table-item-valuation-migration-journal`, with evidence from both migration
  directions. No pending graph review item was promoted, edited, rejected, or
  adjudicated. The existing `node:table-item` wording remains for the
  coordinator's authorized maintenance pass.

## Verification

- Focused phase-6 API, serializer, and disposable migration tests: **29
  passed**.
- Phase-5 synthetic equal-`created_at` history tie-breaker test: **1 passed**
  against the configured development profile.
- Full non-e2e suite: **1997 passed / 23 established failures / 1 deselected**;
  the established failure set remained unchanged.
- Ruff and `git diff --check`: passed.
- Configured development database: Alembic `be9dfe42a035 (head)`; `items=480`,
  migration journal `=0`, legacy `items` columns `=0`, and no remaining
  `beyo_manager_phase6_*` disposable databases. The rollback journal's enum
  snapshot column remains by design at head; the only non-journal enum user is
  `item_upholstery_requirements.currency`.
- Migration lifecycle tests created three refusal databases plus one seeded
  round-trip database and dropped each in `finally`; the final PostgreSQL
  catalog query found zero matching databases.

## Mutation ledger

Five named probes were applied, observed, and reverted. The task-validator
deletion reddened the nested-task non-null bridge node; deleting all item
validators reddened exactly six API nodes; restoring item serializer keys
reddened exactly three item rows; restoring task serializer keys reddened all
six task/upholstery rows; and removing `item_cost_minor` from the task router
body reddened the router-retention assertion. Full baseline/mutant hashes and
pytest red sets are recorded in the phase plan's append-only review log.

## Handoff instructions

Coordinator should consume checkpoint `b940309`, then route this phase through
the planned reviewer prompt. The phase plan and master tracker are already
updated to `IMPLEMENTED`; this handoff is intentionally created after the
checkpoint so its cited hash is immutable.
