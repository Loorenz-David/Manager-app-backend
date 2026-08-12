---
plan: phase 3
role: implementer
round: 1
date: 2026-08-12
state: IMPLEMENTED
verdict: CHECKPOINT (not approved)
actor: Codex
---

# Phase 3 implementer handoff — canonical calculator

Implemented the pure item-economics calculator and its C1–C9 unit proof. The
checkpoint commit is `2a860b271d3e4349894315c4d4243debaeb9a4cf`; this handoff is
deposited after that commit and must not amend it.

## ⚠ OWNER DECISIONS REQUIRED (0)

None.

## What was built

- `calculator.py` is the calculation monopoly: typed boundary guards, the full
  term-shape table and duplicate purchase-term guard, Q1–Q5, budget, rate and
  underflow, allowance, consumption, remaining/variance, currency equality,
  `CALCULATION_VERSION`, and HC-7 `rederive`.
- All arithmetic runs inside `decimal.localcontext()`; every quantize call has
  an explicit `ROUND_HALF_EVEN`. Q3 consumes the persisted Q2 rate and Q5 uses
  seconds directly rather than Q4's rounded display value.
- Re-derivation reads only the closed snapshot set, compares every term amount
  and derived value, and returns the named `REDERIVE_SKIPPED` marker on a future
  calculation version.
- No services, requests, routers, persistence, migrations, model annotations,
  FK reads, or `EconomicsStatusEnum` logic were added.

## Implementation versus plan

All C1–C9 criteria were implemented. The only judgment call within the written
delegations was the public API naming (D1), reported below. D3 uses one shared
`_guard_type` definition; D4 uses the named module constant
`REDERIVE_SKIPPED = "rederive_skipped_calculation_version"`; D5 re-derives and
compares each term amount. The C9 precision-hostile row uses Q3
`(40_000_000, Decimal("400.0000"))`, which makes removal of its local context
raise `InvalidOperation` under precision 6 as required by the mutation.

## Public API report (D1)

The exported phase-3 API is:

`CALCULATION_VERSION`, `REDERIVE_SKIPPED`,
`calculate_percentage_term_amount`, `calculate_term_amount`,
`calculate_term_amounts`, `calculate_production_budget`,
`calculate_cost_per_worker_minute`, `calculate_allowed_worker_minutes`,
`calculate_actual_worker_minutes`, `calculate_consumed_cost_minor`,
`calculate_remaining_worker_minutes`, `calculate_percent_consumed`,
`calculate_variance_worker_minutes`, `calculate_variance_cost_minor`,
`validate_currency_equality`, and `rederive`.

## Verification

- Correct baseline command from `backend/app`: `PYTHONPATH=. pytest -m 'not
  e2e'` → **1684 passed / 23 failed / 1 deselected**. The 23 failures matched
  the routed pre-existing set.
- Focused calculator suite: **54 passed**.
- Full post-change suite: **1738 passed / 23 failed / 1 deselected**. The 23
  failure IDs are set-identical to baseline; the added 54 tests are the only
  test-count increase.
- `ruff check` on both changed Python files: **All checks passed**.

## Named mutation declarations

Every named mutation was applied at its specified site, observed red, reverted,
and re-run/hash-checked:

| Mutation | Site and assertion that reddened | Result |
|---|---|---|
| M-Q1 | Q1 call-site rounding changed to HALF_UP; Q1 tie row | red, reverted |
| M-Q2 | Q2 call-site rounding changed to HALF_UP; Q2 tie row | red, reverted |
| M-Q3 | Q3 call-site rounding changed to HALF_UP; Q3 tie row | red, reverted |
| M-Q4 | Q4 call-site quantize deleted; Q4 exactness rows | red, reverted |
| M-Q5 | Q5 call-site rounding changed to HALF_UP; Q5 tie row | red, reverted |
| C6 | shared `_guard_type` definition body removed; 14 guard rows | red, reverted |
| C7 | `rederive` reads `production_cost_basis_version_id`; FK tripwire | red, reverted |
| C9(a) | Q1 explicit `rounding=` removed; ambient-context row | red, reverted |
| C9(b) | Q3 `localcontext()` wrapper removed; precision-half row | red, reverted |

Final calculator SHA-256 after all probes and at checkpoint:
`088e6514ee3552f433b5aa28f082932ff98273e6507a2bfd82bff67ee1845e90`.
Final test SHA-256:
`9096962c31e932fdda11491204c501ecf3b6edadcaae3128f97f098203733fd1`.

## Architecture Graph

Oriented on the existing human-confirmed `domain-work-analytics` node, inspected
its depth-1 neighborhood and depth-2 impact (no additional impact entries),
then recorded one additive inferred domain node in one batch:

- `domain-item-economics` — `Item Economics`, with calculator evidence at
  `calculator.py` lines 1–26, 137–212, and 371–425.
- Graph write revision after the batch:
  `671fd92a560fbaffda67e74f21eff8128c55cacfae807d98ab27fdf6e586319b`.
- No pending review item was promoted, rejected, edited, deprecated, or removed.

## Full write perimeter

### Intended implementation and pipeline artifacts

- `app/beyo_manager/domain/item_economics/calculator.py` — new calculator.
- `app/tests/unit/domain/item_economics/test_calculator.py` — new pure unit
  proof.
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  — phase-3 tracker row moved to `IMPLEMENTED`.
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_3_canonical_calculator.md`
  — append-only implementer Review log entry.
- This handoff file — deposited after the checkpoint commit.

### Mutation-probe perimeter (applied and reverted)

- `app/beyo_manager/domain/item_economics/calculator.py` — all nine production
  mutation probes listed above.
- `app/tests/unit/domain/item_economics/test_calculator.py` — C9 precision
  fixture was strengthened as an intended test change; all temporary mutation
  edits were reverted.

### Tool-recorded state and unrelated work

- `.archgraph/architecture.yml` — modified by the one batched Architecture
  Graph additive write; this is tool-recorded state, not part of the source
  checkpoint commit.
- An existing modification to
  `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/maintenance/2026-08-12_migration-shim-followup_r2_handoff.md`
  was present before this session and was not touched or staged.

Checkpoint:

`CHECKPOINT (not approved): item-cost phase 3 — canonical calculator and pure C1–C9 proof`

