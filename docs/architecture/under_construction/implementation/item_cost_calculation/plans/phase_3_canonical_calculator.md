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
   currency members and **raises `ValidationError`
   (`ITEM_COST_CURRENCY_MISMATCH`, naming both sides and which pair failed)** on
   mismatch, returns None on success (S9 pinned: raise, not return-a-failure).
6. `CALCULATION_VERSION = 1` with §6A.10's bump/never-bump contract as its docstring.
7. `rederive(evaluation_row, term_rows) -> (rate, budget, allowed)` (§6A.11): reads
   ONLY the closed field set; asserts `calculation_version == CALCULATION_VERSION`
   before comparing (mismatch → skip marker, never a failure); never dereferences an
   FK.

## Acceptance criteria

All pure unit tests; fixtures per row make the row's predicate the only reason the
expectation holds (rule 2 companion). Expected values are exact — no ranges, no
disjunctions.

**C1 — term amounts (intention test 1, §6A.4; amended per projection B3/B4/S8):**
the full **12-row table** (same enumeration as phase 2 C3's type×presence matrix —
its "five" citation was stale): the 3 valid combinations each assert the exact
`amount_minor` (percentage → Q1; fixed → copied, no arithmetic; purchase → copied);
the **9 invalid combinations** each assert `ITEM_COST_TERM_SHAPE_INVALID`
(registry §6.4, registered 2026-08-12) — the calculator's re-validation, the
"written by a future path" guard. Plus: `item_purchase_cost` with NULL purchase
cost → `ITEM_COST_PURCHASE_COST_REQUIRED`; and (S8) **two `item_purchase_cost`
terms in one snapshot set → `ITEM_COST_TERM_SHAPE_INVALID`** — A5 guards the live
table only; the snapshot table has no constraint, and a duplicate would silently
subtract the purchase cost twice.

**C2 — quantization sites (amended per projection B1/S1/S2 — a 5×2 table, every
cell seeded with a VERIFIED fixture and one exact expected value):**

| Site | Exactness row (fixture → expected) | Tie row (HALF_EVEN vs HALF_UP; even floor) |
|---|---|---|
| Q1 | `price=4000, percent=15.000` → `600` | `price=4900, percent=0.500` → raw `24.500` → **24** (HALF_UP: 25) |
| Q2 | `fixed=57_600_00, hours=320.00, util=75.00` → `400.0000` (arithmetic verified; NOT an intention citation — the "§6.3 worked shape" attribution was false) | `fixed=24000003, hours=1000.00, util=100.00` → raw `400.00005` → **400.0000** (HALF_UP: 400.0001). Seeded deliberately — finding one is a Diophantine search. TRAP: a small-rate tie (raw `0.00005`) quantizes to `0.0000` and raises `ITEM_COST_RATE_UNDERFLOW` instead of returning; the tie row must sit at a non-zero rate. |
| Q3 | persisted-rate row: `rate_raw=400.00005 → persisted 400.0000`, `budget=40_000_000` → **100000.00** (raw rate would give 99999.99 — asserts Q3 consumes the persisted rate; smaller budgets degenerate) | `budget=1, rate=0.0128` → raw `78.125` → **78.12** (HALF_UP: 78.13) |
| Q4 | repeating-residue rows: `sec=100` → **1.67**; `sec=20` → **0.33** | **IMPOSSIBLE — proven, do not attempt and do not file as missing:** `frac(s/60×100) = 5s/3 mod 1` has denominator 1 or 3, never 2; exhaustive sweep over s∈[0,100000) found zero HALF_EVEN/HALF_UP divergences. Q4's only guardable defect is a deleted quantize — see the mutation column. |
| Q5 | drift row (M-14): `sec=20, rate_snapshot=400.0000` → **133** (pricing Q4's rounded 0.33 gives 132 — asserts Q5 derives from seconds) | `sec=60, rate_snapshot=24.5000` → raw `24.5000` → **24** (HALF_UP: 25) |

**Named mutations — five, one per Q-site CALL SITE (projection S2; a shared
`_quantize` helper's definition-site mutation reddening everything at once proves
nothing per-site):** M-Q1 "make the Q1 call site HALF_UP" → Q1 tie row red;
M-Q2 same at Q2 → Q2 tie row red; M-Q3 same at Q3 → Q3 tie row red;
M-Q4 **"delete the `.quantize(Decimal('0.01'), …)` at the Q4 call site"** → Q4
exactness rows red (raw `1.666…` ≠ `1.67`); M-Q5 same-as-Q1 at Q5 → Q5 tie row
red. Each run and reverted, declared per-site.

**C3 — budget (§6A.5):** empty term set → budget = price; multi-term sum row;
negative budget row stored as-is (−value asserted exactly); shuffled-terms equality
row (order-insensitivity exercised, not just argued).

**C4 — rate underflow (§6A.6):** inputs whose quantized rate is 0.0000 →
`ITEM_COST_RATE_UNDERFLOW` (identity = leading message token); nearby inputs
yielding 0.0001 → accepted.

**C5 — allowance/consumption/variance (§6A.7–6A.8 as amended round 8):**
negative-budget → negative allowance (exact); `percent_consumed`: rows for
allowed > 0 (exact 2-dp; note `allowed > 0 ∧ actual = 0` correctly yields `0.00` —
the "never 0" rule governs only the `allowed ≤ 0` branch), allowed = 0 → `None`,
allowed < 0 → `None`; `remaining` exact subtraction row; **variance independence
row (seeded — verified triple):** `budget=100000, rate=100.5000, sec=12181` →
`allowed=995.02, actual=203.02, consumed=20403, var_min=792.00, var_cost=79597`;
`var_min × rate = 79596.000000` — difference **exactly 1**, both quantities
asserted exactly (pinned deliberately unreconciled per §6A.8 round 8; a future
"reconciliation" turns it red). Do NOT assert the general bound — it scales with
the rate (R8-1).

**C6 — boundary guards (intention test 15; amended per projection S3/S4 — TOTAL
over input class × arriving type, one exact outcome per cell):**

| Arriving type | money (`int` spec) | rate/percent (`Decimal` spec) | seconds (`int` spec) | enum (member spec) |
|---|---|---|---|---|
| correct type | accepted | accepted | accepted | accepted |
| `float` | `TypeError` | `TypeError` | `TypeError` | — |
| `bool` | **`TypeError`** (bool is an int subclass — a naive `isinstance(x, int)` admits `True` as 1 minor unit; the guard excludes bool explicitly) | `TypeError` | `TypeError` | — |
| `Decimal` | `TypeError` | accepted | `TypeError` | — |
| `int` | accepted | `TypeError` | accepted | — |
| `str` | `TypeError` | `TypeError` | `TypeError` | `TypeError` (enum **value** string instead of a member) |
| `None`, user-supplied input | named identity: `ITEM_COST_EXPECTED_PRICE_REQUIRED` / `ITEM_COST_PURCHASE_COST_REQUIRED` | — | — | — |
| `None`, system-supplied input (snapshots, rate, seconds) | `TypeError` — a programmer error, never a user-facing validation message | `TypeError` | `TypeError` | `TypeError` |

The `Decimal(str(v))` request-layer parse row is **struck — moved to phase 4**
(projection S4: §6A.1 places that parse before the module; phase 3 ships no
request layer). Named mutation: deleting the shared guard at its definition site
in `calculator.py` must turn the type-violation rows red (D3 pins the shared-guard
reading; the quantize mutations of C2 stay per-site regardless).

**C7 — rederive (§6A.11, HC-7; amended per projection B2):** built from **ORM
instances** (rule 3 — unsaved `ItemCostEvaluation` + `ItemCostEvaluationTerm`
objects; constructible without FKs, verified; assign `Decimal` explicitly to the
Numeric-backed snapshot fields — the `Mapped[float]` annotations lie, §6A.1
governs): reproduces rate, budget, allowance bit-for-bit from the closed field
set; per D5's recommendation, also re-derives each term's `amount_minor` and
compares (the §6A.11 theorem claims term reproducibility — summing stored values
proves nothing); a row with `calculation_version = 2` → the named skip-marker
constant (D4), not a failure. **Closed-set enforcement — the tripwire form (an
unset FK reads `None`; it does NOT raise, so the old wording had no arbiter):**
`mock.patch.object` a raising property over the three FK columns
(`cost_model_version_id`, `production_cost_group_id`,
`production_cost_basis_version_id`) **and** the two episode snapshots
(`task_type_snapshot`, `return_source_snapshot`) — rederive completes untouched.
Named mutation: "make `rederive` read
`evaluation.production_cost_basis_version_id`" must turn the tripwire row red.

**C8 — currency helper (§6A.9; amended per projection S9/N3):** the helper
**raises `ValidationError`** (consistent with every §6.4 identity — the
return-a-failure reading is rejected); three mismatch rows (valuation≠basis,
valuation≠model, basis≠model), each asserting the `ITEM_COST_CURRENCY_MISMATCH`
leading token **plus the presence of both currency values** in the message (no
fuller format is pinned — do not assert one); equal row passes.

**C9 — ambient-context hostility + version constant (new, projection S5; proves
§6A.2 as amended round 8):** under `getcontext().rounding = ROUND_CEILING` **and**
a lowered `getcontext().prec` (e.g. 6), every Q1–Q5 output is byte-identical to
its baseline row. Named mutations: (a) "drop the explicit `rounding=` at the Q1
call site" reddens the rounding half; (b) "remove the `localcontext()` wrapper"
reddens the precision half (Q3 → `InvalidOperation`). Plus:
`CALCULATION_VERSION == 1` and its docstring names §6A.10's bump/never-bump lists
(string-presence assertion).

## Notes

- ROUND_HALF_EVEN is this domain's own decision (M-13) — the accidental precedent
  is the local `cost_minor` at `process_step_transition.py:231-233` (round-8
  citation fix), NOT a `_cost_minor` function; the repo's only explicit quantize
  rounds HALF_UP. Do not "align" with either.
- The `≤ 999.999` percent bound is schema-side (phase 2); the calculator re-validates
  presence/type, not range.
- **§6A.1 governs boundary types, not the ORM annotations** (projection S7):
  eleven phase-2 `Numeric` columns are annotated `Mapped[float]` — the annotations
  lie (runtime returns `Decimal`); fixtures assign `Decimal` explicitly. The
  annotation fix is phase 9's, not this phase's.
- **Delegations (projection D1–D5, granted in writing):** D1 public function names
  (per `21_naming_conventions`; the handoff MUST report the resulting public API so
  the coordinator folds it into master plan §6.5 — phases 4/5/7/8 call these
  functions); D2 test location (`tests/unit/domain/item_economics/`); D3 one shared
  entry guard (C6's singular mutation reading); D4 skip-marker = a named
  module-level constant; D5 rederive re-derives term amounts (recommended form,
  adopted in C7). Nothing else is delegated — identities, fixtures, mutation sites
  and guard-cell outcomes are all pinned above.
- P-K/P-M apply: most C-rows will hang off one shared factory — each row's test
  states which field it varies; audit the factory for pre-satisfied constraints.
- Archgraph: orient on `domain-work-analytics` (sibling domain boundary); delta =
  the new `domain` node for item economics (calculator as evidence).

## Review log

(append-only)
