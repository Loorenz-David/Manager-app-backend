---
plan: phase 3
role: fix
round: 2
state: IMPLEMENTED
date: 2026-08-12
actor: Codex
verdict: CHECKPOINT (not approved)
---

# Phase 3 fix-cycle handoff — canonical calculator (r2)

Implemented the routed phase-3 review fixes and deposited this handoff after the
required checkpoint commit. The checkpoint is
`8378a1b672831e56c89bffe6843d1e815fd9383e` with subject
`CHECKPOINT (not approved): item-cost phase 3 fix r2 — close review findings`.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. The three review-r1 cards were already answered and folded upstream; the
pending `domain-item-economics` graph node remains held per card 3.

## Summary

- B1: wrapped remaining and variance worker-minute arithmetic in precision-50
  `localcontext()` blocks and extended C9's hostile-context proof to every public
  function performing Decimal arithmetic.
- B2: added the system-supplied money-`None` C6 row; `_require_money` cannot
  silently infer zero.
- S1: every currency mismatch row asserts both currency values and its exact
  failing-pair label.
- S2: replaced all unregistered `ITEM_COST_SNAPSHOT_MISMATCH` exceptions with
  the `REDERIVE_MISMATCH` marker and structured mismatch payload; `rederive`
  never raises for snapshot disagreement.
- S3: the version test now checks a bump token and a never-bump token against the
  module docstring.
- Absorbed guards: added exact rows for negative percentage, negative fixed
  amount, and zero rate reaching allowance.
- N2: added the exact registered `__all__` surface, including both snapshot
  Protocols and both re-derivation markers.

## Finding-by-finding resolution

### B1 — Decimal arithmetic outside `localcontext()`

Both public minute-variance paths now execute with precision 50. The C9 baseline
and hostile tuples include `calculate_remaining_worker_minutes`,
`calculate_variance_worker_minutes`, and `calculate_percent_consumed`; the
existing Q1–Q5 coverage remains intact.

### B2 — system-supplied money × `None`

Added `calculate_variance_cost_minor(None, 100)` as a system-supplied money
boundary row and asserted its exact `TypeError` identity. The named mutation that
changes `_require_money`'s system-supplied `None` branch to `return 0` reddened
that row and was reverted.

### S1 — currency message disjunction

Replaced the `or` assertion with separate assertions for `basis.value` and
`model.value`, while retaining the exact failing-pair assertion. Deleting the
right-hand currency from the production message reddened the incomplete rows.

### S2 — re-derivation mismatch carrier

Added module marker `REDERIVE_MISMATCH = "rederive_mismatch"`. `rederive` gathers
all disagreements into `{"marker": REDERIVE_MISMATCH, "mismatches": [...]}`;
each entry carries `field`, `rederived_value`, and `stored_value`. The C7 ORM
fixture asserts the marker and exact term payload. No `ValidationError` or
`ITEM_COST_SNAPSHOT_MISMATCH` remains on the production mismatch paths.

### S3 — calculation-version contract

The test now checks the module docstring for the bump-side `term formula` token
and the never-bump-side `renames` token, in addition to `CALCULATION_VERSION == 1`
and the §6A.10 marker.

### Absorbed guards

Added exact `ITEM_COST_TERM_SHAPE_INVALID` rows for negative `percent_value` and
negative `fixed_amount_minor`, plus an exact `ITEM_COST_RATE_UNDERFLOW` row for
zero rate at `calculate_allowed_worker_minutes`.

### N2 — public surface

`calculator.__all__` is asserted equal to the exact set of the registered 16 API
names, `EvaluationSnapshot`, `TermSnapshot`, `REDERIVE_SKIPPED`, and
`REDERIVE_MISMATCH`. Stray imported names are excluded from the public surface.

## Verification

- Focused calculator suite: **59 passed**.
- Ruff on both changed Python files: **All checks passed**.
- Full suite from `app/`, `PYTHONPATH=. pytest -m 'not e2e'`:
  **1743 passed / 23 failed / 1 deselected**. The 23 failures are the routed,
  pre-existing baseline set; the five-test increase over r1 is exactly the five
  new fix-cycle assertions.
- Architecture Graph: status was initialized/valid, 126 nodes, 161 edges, zero
  diagnostics, zero stale nodes, revision
  `671fd92a560fbaffda67e74f21eff8128c55cacfae807d98ab27fdf6e586319b`, one
  pending review item. **Delta: zero.** No pending node was promoted, rejected,
  edited, deprecated, or removed.

## Mutation declarations

Every probe was applied at the named site, observed red, reverted, and the final
working-state hashes were verified before the checkpoint.

| Mutation | Site | Result |
|---|---|---|
| B1 context removal | Remove `calculate_remaining_worker_minutes`'s `localcontext()` wrapper | C9 hostile-context row red; reverted |
| B2 inferred zero | Make `_require_money`'s system-supplied `None` branch return `0` | New system-`None` row red; reverted |
| C8 message weakening | Remove the right-hand currency value from the mismatch message | 2 of 3 currency rows red; reverted |
| M-Q1 | Q1 call site changed to HALF_UP | Q1 tie row red; reverted |
| M-Q2 | Q2 call site changed to HALF_UP | Q2 tie row red; reverted |
| M-Q3 | Q3 call site changed to HALF_UP | Q3 tie row red; reverted |
| M-Q4 | Q4 call-site quantize removed | Both Q4 exactness rows and variance fixture red; reverted |
| M-Q5 | Q5 call site changed to HALF_UP | Q5 tie row red; reverted |
| C6 | Shared `_guard_type` body removed | 14 guard rows red; reverted |
| C7 | `rederive` reads `production_cost_basis_version_id` | Closed-set rederive rows red, including FK tripwire; reverted |
| C9(a) | Q1 explicit `rounding=` removed | Hostile-context row red; reverted |
| C9(b) | Q3 `localcontext()` wrapper removed | Hostile-context row red with `InvalidOperation`; reverted |

## Hashes at checkpoint

The following hashes are the final committed file hashes. The handoff itself was
deposited after the checkpoint so its contents can cite the immutable checkpoint
hash without amending the checkpoint.

| File | SHA-256 |
|---|---|
| `app/beyo_manager/domain/item_economics/calculator.py` | `1c9a75fa24b0c60da2c6c449b931cac3bafdf8f3a91c288d6cd2e42fffeb5d20` |
| `app/tests/unit/domain/item_economics/test_calculator.py` | `971232312acce140aaba6f554ac8c855b16aaf01cabb6f702844f3fe7acc885b` |
| `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` | `a11ca7f13c44d30a7e1363bee1f54bbe74adccd624899e278122fb26a86844f3` |
| `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md` | `05b16fecd05e875723e441edb6eb428c680bf456bdd323f43fe96bf64b58f0e2` |

## Full write perimeter

### Fix changes

- `app/beyo_manager/domain/item_economics/calculator.py`
- `app/tests/unit/domain/item_economics/test_calculator.py`
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md`
- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/implementer/2026-08-12_phase3_fix_r2_handoff.md`

### Mutation-probe perimeter (applied and reverted; separate from fix changes)

- `app/beyo_manager/domain/item_economics/calculator.py`
- `app/tests/unit/domain/item_economics/test_calculator.py`

### Tool-recorded state

- Architecture Graph: zero changes.
- Git checkpoint: `8378a1b672831e56c89bffe6843d1e815fd9383e`.
