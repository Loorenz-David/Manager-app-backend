---
plan: phase 3 (canonical calculator)
role: fix
round: 4
state: IMPLEMENTED
verdict: IMPLEMENTED
date: 2026-08-12
actor: Codex
---

# Phase 3 fix-r4 implementer handoff

Implemented S6, N14, and N16. Checkpoint commit: `71f137b`
(`CHECKPOINT (not approved): item-cost phase 3 fix r4 — close review findings`).

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## Summary

- S6 uses the verified sole-predicate cascade fixture: stored rate `Decimal("399.5000")` and cascade allowance `rederived_value = stored_value = Decimal("5.42")`.
- N14 gives every mismatch entry the four-key shape `field`, `rederived_value`, `stored_value`, `error`; plain disagreements use `error: None`.
- N16 uses an unsaved `ItemCostEvaluationTerm` for the malformed purchase-snapshot row.
- Optional N12/N13 were not taken.

## Verification

- Focused calculator suite: **65 passed**.
- Full non-E2E suite: **1749 passed / 23 failed / 1 deselected**; the 23 failures match the established pre-existing baseline.
- Ruff: clean.
- `git diff --check`: clean.
- Final SHA-256 after the checkpoint: calculator
  `03389d0a2743ae7968a0e5aecc88cc5b2675bea6762c2b9bbec2d87662af8eb0`; tests
  `6733181ed998b101ac2bcb0d95f4f5bfc3729f4d1a6ca8e40b619b8b705daa86`.

## Mutation probes — applied and reverted

All probes were run in the main worktree, then reverted before the final hashes:

| Mutation | Observed failing node id(s) |
|---|---|
| Delete `or rate != stored_rate` at the `rederive` allowance mismatch call site in `calculator.py` | `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` |
| Corrupt the plain rate mismatch `error` key in `calculator.py` | `test_rederive_malformed_evaluation_rate_returns_integrity_marker_and_cascade`; `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` |
| Corrupt the plain term mismatch `error` key in `calculator.py` | `test_rederive_detects_a_changed_term_amount_on_the_same_orm_shape` |
| Corrupt the plain budget mismatch `error` key in `calculator.py` | `test_rederive_reports_production_budget_mismatch_payload` |
| Corrupt the plain allowance mismatch `error` key in `calculator.py` | `test_rederive_reports_allowed_worker_minutes_mismatch_payload`; `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` |

Mutation-probe file touched and restored: `app/beyo_manager/domain/item_economics/calculator.py`.
No mutation probe changed production or test state at close.

## Full write perimeter

Checkpoint `71f137b` contains the fix's changes to:

- `app/beyo_manager/domain/item_economics/calculator.py`
- `app/tests/unit/domain/item_economics/test_calculator.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` (phase-3 tracker row only)
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md` (Review log append)

This handoff was deposited **after** that checkpoint as required. The Architecture Graph was read-only:
zero delta, revision `671fd92a…`, 126 nodes, 161 edges, one pending `domain-item-economics` node,
zero diagnostics, zero stale nodes. No database or external service state was changed.
