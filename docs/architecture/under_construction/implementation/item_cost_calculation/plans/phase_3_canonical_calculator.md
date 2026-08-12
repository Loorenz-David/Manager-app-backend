# Phase 3 — Canonical calculator

```
plan: phase 3
role: phase plan
date: 2026-08-11
state: NOT_STARTED
```

## Goal

Build the one pure module that owns every formula: boundary guards, the five
quantization sites, term amounts, budget, rate, allowance, consumption, variance,
`CALCULATION_VERSION`, and the HC-7 re-derivation. **NOT in this phase:** any I/O,
service, command, or persistence — callers arrive in phases 4–8. No service may ever
compute economics inline (master plan rule P-F); this module is that monopoly.

## Read first

1. `master_plan.md` §§5, 6.3–6.5 (enums, error carrier, file layout), 9 (P-B, P-F).
2. Intention **§6A entire** (governs §6.1–6.6 where they differ) + §6.2, §6.6 for
   intent; §4A (A1–A3, A8 — the column semantics the functions assume); R4-2 / §6A.4
   (gross base, planning-allocation semantics).
3. Contracts: `08_domain` (pure, no I/O), `15_testing`, `50_testing_strategy`,
   `21_naming_conventions` (+ core set).

## Dependencies

Phase 2 APPROVED (imports `domain/item_economics/enums.py`).

## Files expected to change

- `app/beyo_manager/domain/item_economics/calculator.py` (new; includes
  `CALCULATION_VERSION: int = 1` and `rederive()`)
- unit tests for it (no DB needed except the rederive-on-ORM-instances rows, which
  build unsaved ORM objects)

## Implementation tasks (ordered)

1. Boundary guards per §6A.1's table (types per input class; `float` guard on entry
   for money and rates; enum members compared as members; absent input → the named
   error, never 0). Errors carry identities per master plan §6.4 (leading token of
   `message`); domain raises `ValidationError` per the `validate_<concern>` pattern.
2. Decimal discipline (§6A.2): every quantization passes `rounding=ROUND_HALF_EVEN`
   explicitly; global context never touched.
3. Q1–Q5 exactly as §6A.3's table, as named functions; Q3 consumes the quantized
   persisted rate; Q5 derives from seconds and the snapshot rate.
4. Term amounts (§6A.4 total table), budget (§6A.5, exact int arithmetic, negative
   stored as-is), rate (§6A.6 — quantized result 0 raises
   `ITEM_COST_RATE_UNDERFLOW`), allowance (§6A.7), consumption/remaining/variance/
   percent-consumed (§6A.8 — `percent_consumed` is `None` iff `allowed ≤ 0`).
5. Currency three-way equality helper (§6A.9 step 3): pure — takes the three
   currency members, returns ok or the `ITEM_COST_CURRENCY_MISMATCH` failure naming
   both sides and which pair failed.
6. `CALCULATION_VERSION = 1` with §6A.10's bump/never-bump contract as its docstring.
7. `rederive(evaluation_row, term_rows) -> (rate, budget, allowed)` (§6A.11): reads
   ONLY the closed field set; asserts `calculation_version == CALCULATION_VERSION`
   before comparing (mismatch → skip marker, never a failure); never dereferences an
   FK.

## Acceptance criteria

All pure unit tests; fixtures per row make the row's predicate the only reason the
expectation holds (rule 2 companion). Expected values are exact — no ranges, no
disjunctions.

**C1 — term amounts (intention test 1, §6A.4):** one row per type with exact
`amount_minor` (percentage → Q1; fixed → copied, no arithmetic; purchase → copied);
`item_purchase_cost` with NULL purchase cost → `ITEM_COST_PURCHASE_COST_REQUIRED`;
each per-type NULL-column violation → rejected by the calculator's re-validation
(the "written by a future path" guard — one row per invalid combination, mirroring
phase 2 C3's five).

**C2 — quantization sites:** per site one exactness row and one tie row:
- Tie rows: fixtures whose unquantized value ends in exactly `.5` at the target
  scale **with an even floor** (e.g. `…24.5 → 24`), where HALF_EVEN and HALF_UP
  differ; assert the HALF_EVEN result. At least one such row per integer-target
  site (Q1, Q5), one at 4 dp (Q2), one at 2 dp (Q3, Q4). A HALF_UP implementation
  must turn each red (that is the row's named mutation, applied at the quantize
  call in `calculator.py`).
- Q2 exactness: §6.3's worked shape — e.g. `fixed=57_600_00, hours=320.00,
  util=75.00` → rate `= 57_600_00 / (320 × 0.75 × 60)` = `400.0000` minor/min;
  assert 4-dp Decimal equality.
- Q3 consumes the **persisted** quantized rate: construct inputs where
  Q3(budget, quantize(rate)) ≠ Q3(budget, raw_rate); assert the persisted-rate
  result.
- Q5 derives from seconds: construct a case where pricing Q4's rounded minutes
  differs by ≥1 minor unit from Q5; assert Q5's value (M-14's drift row).

**C3 — budget (§6A.5):** empty term set → budget = price; multi-term sum row;
negative budget row stored as-is (−value asserted exactly); shuffled-terms equality
row (order-insensitivity exercised, not just argued).

**C4 — rate underflow (§6A.6):** inputs whose quantized rate is 0.0000 →
`ITEM_COST_RATE_UNDERFLOW` (identity = leading message token); nearby inputs
yielding 0.0001 → accepted.

**C5 — allowance/consumption/variance (§6A.7–6A.8):** negative-budget → negative
allowance (exact); `percent_consumed`: rows for allowed > 0 (exact 2-dp), allowed = 0
→ `None`, allowed < 0 → `None` — never 0, never 100; `remaining` exact subtraction
row; variance independence row: fixture where `variance_cost_minor` differs by
exactly 1 minor unit from `variance_worker_minutes × rate` — both asserted exactly
(pinned correct; a future "reconciliation" turns it red).

**C6 — boundary guards (intention test 15):** `float` for money → `TypeError`;
`float` for a rate → `TypeError`; `None` for a required input → named error, never
0; `Decimal(str(v))` request-layer parsing proven on a value with more decimals than
target scale. Named mutation: deleting the float guard at its definition site in
`calculator.py` must turn the float rows red.

**C7 — rederive (§6A.11, HC-7):** built from **ORM instances** (rule 3 — unsaved
`ItemCostEvaluation` + `ItemCostEvaluationTerm` objects): reproduces rate, budget,
allowance bit-for-bit from the closed field set; a row with
`calculation_version = 2` → skip marker, not a failure; rederive must not touch FK
fields (fixture leaves them `None` — any dereference raises).

**C8 — currency helper (§6A.9):** three mismatch rows (valuation≠basis,
valuation≠model, basis≠model), each naming its failing pair; equal row passes.

## Notes

- ROUND_HALF_EVEN is this domain's own decision (M-13) — `_cost_minor` is NOT a
  precedent; the repo's only explicit quantize rounds HALF_UP. Do not "align" with
  either.
- The `≤ 999.999` percent bound is schema-side (phase 2); the calculator re-validates
  presence/type, not range.
- Archgraph: orient on `domain-work-analytics` (sibling domain boundary); delta =
  the new `domain` node for item economics (calculator as evidence).

## Review log

(append-only)
