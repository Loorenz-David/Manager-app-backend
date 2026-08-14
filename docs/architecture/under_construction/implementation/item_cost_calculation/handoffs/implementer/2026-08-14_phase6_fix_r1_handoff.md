---
plan: phase 6
role: fix
state: IMPLEMENTED
date: 2026-08-14
actor: Codex
---

# Phase 6 fix r1 handoff

## Summary

Resolved B1/B2 and S1–S4 from review r1. The migration now blocks valuation
creation when any valuation row already exists, including soft-deleted and
superseded rows, and its in-migration guard aborts on an eligible-but-unmigrated
legacy item. The migration/drop cleanup notes were corrected. The test evidence
is authority-parametrized, endpoint-specific, ORM-backed, and TestClient-backed
as required by the fix prompt.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Verification

- Focused phase-6 plus phase-5 synthetic tie set: **58 passed**.
- Full non-e2e suite: **2012 passed / 23 established baseline failures / 1 deselected**.
  The 23 failures are the established baseline set; no phase-6 failure is in it.
- Ruff on the fix perimeter: passed.
- `git diff --check`: passed.
- Configured DB: `be9dfe42a035 (head)`; `item_valuation_migration_journal` has 0
  rows; legacy item columns have 0 remaining columns; disposable phase-6 and
  reviewer databases: 0.
- Migration lifecycle was rerun on disposable databases for refusal rows,
  all-null/currency-only/valid/soft-deleted/collision rows, all four valuation
  states, run-twice idempotency, both downgrades, and the full round-trip. All
  generated databases were dropped by the test cleanup.

## Mutation ledger

Each probe was applied at the named site, run, observed, and reverted. Final
production baseline hashes:

1. B1/R10 — `migrations/versions/5420acc6a7b3_migrate_item_money_to_valuations.py`:
   baseline `a3228a851997a90c6fdc7239da42370864b8149c5e27fbf79988ef93e7562160`;
   `[1:]` at `_copy_eligible_valuations` produced mutant
   `0190fb19d5fd3b9c57adaf1b9c53a8d2bb5889c8cc7f68dd7021ac37246c3365`.
   The valid non-deleted authority row failed with
   `item money migration left 1 eligible item(s) unmigrated`; the disposable
   migration rolled back.
2. R2 — the same migration baseline; replacing the three refusal ID lists with
   empty lists produced mutant
   `e55201f36717ec948e6e261db30af75d3bdceaff5b32c7ae1779db2715d181f6`.
   All three refusal rows failed because their seeded IDs disappeared from the
   report.
3. R3 — `beyo_manager/services/queries/upholstery/upholstery_orders_query.py`:
   baseline `b34e8e0ef0446f62c84781621f66cecabea6ccc0eb73e5dbe5f3ef3e81d5f746`;
   inline key re-exposure produced mutant
   `296b29395c5382a6580b569f256eff30ab03546b2953ae21060f0a9646dce7ca`.
   Exactly the `upholstery-orders` census row failed; the other eight passed.

## Full write perimeter

### Intended fix changes

- `app/migrations/versions/5420acc6a7b3_migrate_item_money_to_valuations.py`
- `app/migrations/versions/be9dfe42a035_drop_legacy_item_money_columns.py`
- `app/tests/integration/migrations/test_phase6_legacy_migration.py`
- `app/tests/unit/test_phase6_api_bridge.py`
- `app/tests/unit/test_phase6_serializers.py`
- `app/tests/integration/services/commands/item_economics/test_valuation_surface.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_6_legacy_migration_api_bridge.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- This handoff file.

### Mutation-probe files, applied and reverted; no production changes remain

- `app/migrations/versions/5420acc6a7b3_migrate_item_money_to_valuations.py`
  (B1/R10 and R2 probes)
- `app/beyo_manager/services/queries/upholstery/upholstery_orders_query.py`
  (R3 probe)

### Architecture/tool-recorded state

Architecture Graph was read for status and phase context. No graph mutation was
made: the journal node remains pending, and the coordinator-owned D19
`node:table-item` description/summary maintenance edit was not enacted.

## Coordinator notes

The superseded-only valuation fixture is explicitly covered although the current
command chain cannot produce that state. The plan's D9 text now says there are
two enum users at head including the journal snapshot and one non-journal user;
the structural test asserts the head count of two.
