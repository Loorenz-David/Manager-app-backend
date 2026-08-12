---
plan: phase 3 (canonical calculator)
role: fix
state: IMPLEMENTED
date: 2026-08-12
actor: Codex
---

# Phase 3 fix r3 handoff

Implemented B3, S4, and S5 from reviewer r2 under owner decision R10-1.

⚠ OWNER DECISIONS REQUIRED (0)

None. The pending Architecture Graph node remains held under the existing owner card 3.

## Built

- `rederive` now returns `REDERIVE_MISMATCH` for malformed evaluation and term snapshots
  instead of allowing calculation-path `ValidationError`, `TypeError`, `AttributeError`,
  or arithmetic guard failures to escape.
- The zero-rate evaluation path preserves the rate mismatch and reports the pinned
  `allowed_worker_minutes` cascade entry.
- Added exact payload assertions for the term amount, production budget, allowance, and
  stored-rate mismatch branches, plus the rate cascade.
- Replaced both C9 `calculate_percent_consumed` fixtures with the verified hostile-context
  fixture `Decimal("0.01"), Decimal("100000.00")`.

## Verification

- Focused: `PYTHONPATH=. pytest -q tests/unit/domain/item_economics/test_calculator.py` — **65 passed**.
- Full: `PYTHONPATH=. pytest -m 'not e2e'` — **1749 passed / 23 failed / 1 deselected**.
  The 23 failures match the established baseline; no new failure was introduced.
- Ruff and `git diff --check`: clean.
- Final SHA-256:
  - `app/beyo_manager/domain/item_economics/calculator.py` — `e5f42531d59c66a06e384f772f41c0971d63fa5990189f39276ff6d1d9611a49`
  - `app/tests/unit/domain/item_economics/test_calculator.py` — `d7251cdeed549a1ac663253f969a994e8cce1a428815afbeeddab0690497ba30`

## Mutation probes

Every r3 row mutation was applied at the named seam, run, and reverted immediately:

- B3 class (a): re-raise at the allowance conversion seam; the rate-zero marker/cascade
  row reddened.
- B3 class (b): re-raise at the term-shape conversion branch; the malformed-term row reddened.
- B3 class (c): re-raise at the NULL-purchase conversion branch; the malformed-purchase row reddened.
- S4: remove `calculate_percent_consumed`'s `localcontext()` wrapper; the hostile-context
  row reddened.
- S5: corrupt each exact term, budget, allowance, and rate field label; its corresponding
  exact-payload row reddened.
- S5 cascade: invert the rate-cascade condition; the cascade row reddened.

## Full write perimeter

Intended and retained changes:

- `app/beyo_manager/domain/item_economics/calculator.py`
- `app/tests/unit/domain/item_economics/test_calculator.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md` (Review log append only)
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` (phase 3 tracker row only)
- this handoff

Mutation-probe files touched and reverted, listed separately from the retained fix:

- `app/beyo_manager/domain/item_economics/calculator.py`
- `app/tests/unit/domain/item_economics/test_calculator.py` (read-only assertion target; no probe change retained)

Architecture Graph tool-recorded state: **zero delta**. Status remains revision
`671fd92a…`, 126 nodes / 161 edges, one pending `domain-item-economics` node, zero
diagnostics and zero stale nodes.

Coordinator action: update the phase 3 tracker state to `IMPLEMENTED`, consume this
handoff, and run the r3 re-review against the cycle-scoped perimeter.
