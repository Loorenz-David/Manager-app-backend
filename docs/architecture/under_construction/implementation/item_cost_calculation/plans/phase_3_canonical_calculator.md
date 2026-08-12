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

### Implementer r1 — 2026-08-12 — Codex

Built the pure canonical calculator in `app/beyo_manager/domain/item_economics/calculator.py` and its 54-test unit proof in `app/tests/unit/domain/item_economics/test_calculator.py`. The implementation owns the boundary guards, the five visible quantization sites, total term-shape validation (including duplicate purchase-cost snapshots), budget, rate/underflow, allowance, consumption, remaining/variance, currency equality, calculation version, and HC-7 re-derivation. It performs no I/O, request parsing, service orchestration, persistence, or FK dereferencing.

Judgment calls: D1 public API names are the exported `calculate_percentage_term_amount`, `calculate_term_amount`, `calculate_term_amounts`, `calculate_production_budget`, `calculate_cost_per_worker_minute`, `calculate_allowed_worker_minutes`, `calculate_actual_worker_minutes`, `calculate_consumed_cost_minor`, `calculate_remaining_worker_minutes`, `calculate_percent_consumed`, `calculate_variance_worker_minutes`, `calculate_variance_cost_minor`, `validate_currency_equality`, and `rederive`; D3 is implemented as one `_guard_type` definition used by all boundary wrappers; D4 uses the module constant `REDERIVE_SKIPPED = "rederive_skipped_calculation_version"`; D5 re-derives every term amount and compares it before returning the rate/budget/allowance tuple. C9's precision-hostile ambient row uses Q3 `(40_000_000, 400.0000)` so removal of `localcontext()` raises `InvalidOperation` at the intended site.

Baseline from the correct app-topology invocation (`backend/app`, `PYTHONPATH=. pytest -m 'not e2e'`) was 1684 passed / 23 failed / 1 deselected. After implementation the full suite was 1738 passed / 23 failed / 1 deselected; the failure IDs are set-identical to baseline. Focused calculator suite: 54 passed.

Named mutations were applied at and reverted from their required sites: M-Q1, M-Q2, M-Q3, M-Q4 quantize deletion, M-Q5; C6 shared `_guard_type` definition deletion; C7 FK read of `production_cost_basis_version_id`; C9 removal of Q1 explicit rounding; C9 removal of the Q3 `localcontext()` wrapper. Each mutation reddened its named assertion set. Calculator SHA-256 after every probe and at close: `088e6514ee3552f433b5aa28f082932ff98273e6507a2bfd82bff67ee1845e90`.

Architecture Graph delta: one inferred `domain` node, `domain-item-economics` (`Item Economics`), recorded in one batch with calculator evidence at lines 1–26, 137–212, and 371–425. No pending review item was adjudicated. No owner decision is required.

### Reviewer r1 — 2026-08-12 — Claude (plan-reviewer) — CHANGES_REQUESTED

Verified correct and independently re-derived: perimeter exact (4 files at `2a860b2`, working tree
clean, declared sha256s match byte-for-byte); scope fence clean (no service/command/router/schema/
persistence, no phase-2 model edits, no `EconomicsStatusEnum`, no request-layer parse); purity holds
structurally — `calculator.py` imports only `decimal`, `typing`, two domain enum modules and
`ValidationError`, zero matches for sqlalchemy/session/httpx/os/await (P-F, `08_domain`); ruff clean.
All ten Q-site values re-computed by hand and confirmed (C2's 5×2 table incl. the Diophantine Q2 tie
`400.00005 → 400.0000`, and C5's seeded triple `995.02 / 203.02 / 20403 / 792.00 / 79597` with
`792.00 × 100.5000 = 79596.000000`, difference exactly 1). C1 = 12 rows and `_term_shape` is total over
type × presence. Suite re-run by the reviewer: **1738 passed / 23 failed / 1 deselected**, +54 exactly,
zero connectivity noise, failure set **byte-identical** to the phase-1 routed 23-item list (diff empty;
N14's Shopify flake did not fire — no re-run needed). All **nine** declared mutations re-run
independently in a disposable worktree and each reddens exactly its named assertion set (M-Q1/Q3/Q5 per
site; M-Q2 the tie row; M-Q4 the two exactness rows + the variance triple; C6 the 14 guard rows; C7 the
FK tripwire; C9(a)/(b)). P3-6 verified positively: swapping C9's Q3 row for the plan's *other* seeded Q3
fixture makes the C9(b) mutation **pass** — the declared test change genuinely strengthened the
criterion. P3-8: all 16 §6.5 names present, none missing.

**B1 (blocking) — `calculate_remaining_worker_minutes` (`calculator.py:312`) and
`calculate_variance_worker_minutes` (`:335`, delegates) run Decimal arithmetic OUTSIDE
`localcontext()`.** Authority: intention §6A.2 as amended round 8 (R8-2) — the module "runs its
arithmetic inside a `decimal.localcontext()`", realized "by construction, not by hope"; §6A.8 ("exact
2 dp subtraction"). Verified: under `getcontext().prec = 6`,
`calculate_remaining_worker_minutes(Decimal("100000.00"), Decimal("0.33"))` returns `99999.7`, not
`99999.67`; `calculate_variance_worker_minutes` returns the same wrong value; every other public
function is unaffected. C9 cannot see it because the criterion enumerates only Q1–Q5 — the exact hole
P3-4 named. Correction: wrap both in `with localcontext() as context: context.prec = 50` as at the five
Q sites, and extend C9's baseline/hostile tuples to **every** public function performing Decimal
arithmetic (`calculate_remaining_worker_minutes`, `calculate_variance_worker_minutes`,
`calculate_percent_consumed`), with the named mutation "remove the `localcontext()` wrapper from
`calculate_remaining_worker_minutes`" reddening the new row.

**B2 (blocking) — C6's `money × None (system-supplied)` cell has no asserting row, and the R-9
inferred-zero defect survives the entire suite.** C6 is declared TOTAL; 24 of 25 cells have a row. Every
money guard row (`test_calculator.py:240-246`) drives `expected_sale_price_minor` — a *user-supplied*
field carrying `required_identity` — so its `None` row asserts `ITEM_COST_EXPECTED_PRICE_REQUIRED` and
the system-supplied branch of `_require_money` (`calculator.py:72-75`) is never exercised. Authority:
plan C6, master plan §9 **P-B** (R-9: absent input ⇒ named error or null, **never 0**), charter rule 2.
Verified by mutation: replacing `raise _type_error(...)` at `calculator.py:75` with `return 0` — exactly
the inferred zero P-B forbids — leaves **54/54 green**. C6's declared shared-`_guard_type` mutation does
not reach it either: it reddens 14 rows, and both the money and rate `None` paths return before
`_guard_type`. Correction: add the cell on a system-supplied money parameter (e.g.
`calculate_variance_cost_minor(None, 100)`), with the named mutation "`_require_money`'s system-supplied
`None` branch returns 0" (charter rule 11).

**S1 (should-fix) — C8's message assertion is a disjunction; 2 of 3 rows never check the second
currency.** `test_calculator.py:303`: `assert basis.value in message or model.value in message`. C8
requires "the presence of **both** currency values" per row. Verified: dropping the right-hand value
from the message (`f"{left_name}={left.value} differs from {right_name}"`) reddens only **1 of 3** rows —
rows 2 and 3 survive because `basis.value` is `swedish_krona`, still present in the left-hand text.
`assert pair in message` (`:301`) is likewise trivially true — every mismatch message enumerates a pair
beginning with `valuation`. Authority: plan C8; charter rule 2 (no disjunctive assertions). Correction:
per row, assert both distinct currency values by name and the exact failing-pair label.

**S2 (should-fix) — `ITEM_COST_SNAPSHOT_MISMATCH` (`calculator.py:397, 413, 418, 425`) is not in the
§6.4 registry**, which is marked FINAL and registry-authored. §6A.11 specifies `rederive` only as
returning `(rate, budget, allowed)`; C7/D5 mandate the comparison without pinning a mismatch outcome, so
the implementer had to author one. Raising is a defensible reading, but the identity is unregistered and
a snapshot-integrity failure will travel the §10 `run_service` boundary as a user-facing
`ValidationError`. → owner card 1. Correction: register in §6.4 or change the carrier.

**S3 (should-fix) — C9's version-constant row under-asserts.** `test_calculator.py:388-391` asserts
`CALCULATION_VERSION == 1`, `"§6A.10" in calculator.__doc__`, `"rounding" in ...lower()`. C9 requires the
docstring to name §6A.10's **bump/never-bump lists**; no never-bump token (`renames`, `widening`,
`API shape`, `documentation`) is asserted, and the assertion reads the *module* docstring while the
constant carries its own (`calculator.py:21-23`). Correction: assert a distinctive token from each list
against the intended docstring.

**Notes.** N1 `test_purchase_term_missing_purchase_cost_...` (`:148-156`) and
`test_purchase_cost_none_is_a_named_user_input_error` (`:261-269`) have byte-identical bodies — one of
the 54 is dead weight → next touch. N2 public surface exceeds §6.5's 16: `EvaluationSnapshot`,
`TermSnapshot` and re-exported `ROUND_HALF_EVEN` are public and there is no `__all__` → coordinator:
fold the two Protocols into §6.5 or add `__all__`. N3 `_term_shape` (`:131-134`) rejects negative
`percent_value`/`fixed_amount_minor` — consistent with §6A.4's `≥ 0` but beyond the plan's
"presence/type, not range" note, and **both branches are untested** → owner card 2. N4
`calculate_allowed_worker_minutes` (`:269-272`) raises `ITEM_COST_RATE_UNDERFLOW` on a zero rate; §6A.6
sites that identity at Q2/basis-version creation — reasonable, unregistered at this site, untested →
owner card 2. N5 `_require_rate`'s `required=False` (`:86-90`) has no caller and its `-> Decimal`
annotation is false on that path (charter rule 4) → next touch. N6 C2's fixtures are evaluated at
collection time inside the `parametrize` lists (`:171-176, 186-189`); mutations still bite, but a raising
mutation becomes a whole-module collection error and the parametrize ids shift with the computed value
(`[Q1-24-24]` → `[Q1-25-24]`), which makes per-row mutation declarations hard to read across rounds →
next touch. N7 (plan-level, passing glance) C2's Q3 exactness cell claims it "asserts Q3 consumes the
persisted rate", but in phase 3 the rate is a parameter, so nothing distinguishes a caller passing the
persisted value from one passing the raw — the arbiter belongs where the call is wired → phase 4/5.

**Lessons for the plans.** L1: C9 scoped a module-wide construction rule (§6A.2) to "every Q1–Q5
output"; such a criterion enumerates over the module's public surface, not over the mechanism list that
motivated it (earned: B1). L2: C6's cells name an input *class* and arriving *type* but not **which
parameter** the row drives — every money row was satisfied by a user-supplied parameter while the cell
looked covered; extends P-M's companion to parameters, not only fields (earned: B2). L3: charter rule
2's no-disjunction clause needs restating for criteria asserting message *content*, not only expected
outcomes — "presence of both values" was satisfiable by an `or` (earned: S1). L4: a criterion mandating
a comparison names the outcome **and** its error identity, or the implementer authors one that lands
unregistered (earned: S2).

**P3-7 (graph, no adjudication).** One pending item, `node:domain-item-economics`; graph revision
`671fd92a…` matches the handoff. Claims 1–3 all ACCURATE against the code (read before the stored
claim). Anchors imprecise: evidence 2 (`137–212`, symbol `calculate_term_amount`) starts at
`calculate_percentage_term_amount` (`:137`) and ends mid-body of `calculate_term_amounts`, excluding the
duplicate-purchase guard (`:215-218`) that S8 made load-bearing; evidence 3 is stored as **`365–425`**,
not the handoff's declared `371–425` — it starts inside `validate_currency_equality`'s list
comprehension (`:365`) and stops one line before `rederive`'s `return` (`:426`). Recommendation: hold,
do not promote as-is — the B1/B2 fix cycle will shift these line numbers anyway; re-anchor
(`1–26`, `137–219`, `371–426`) after the fix and adjudicate once.

### Implementer fix r2 — 2026-08-12 — Codex

Resolved the review-r1 findings within the declared fix-cycle perimeter. B1 now
runs `calculate_remaining_worker_minutes` and `calculate_variance_worker_minutes`
inside `localcontext()` with precision 50, and C9's hostile-context tuple covers
those functions plus `calculate_percent_consumed`. B2 adds the system-supplied
money `None` row and its zero-return mutation probe. S1 asserts both currency
values and the exact failing pair in every C8 row. S2 replaces every unregistered
`ITEM_COST_SNAPSHOT_MISMATCH` exception with the module marker
`REDERIVE_MISMATCH` and a structured list of field, rederived value, and stored
value; re-derivation never raises for a snapshot mismatch. S3 asserts one bump
token and one never-bump token against the module docstring. The absorbed guards
now have exact rows for negative percentage, negative fixed amount, and zero rate
at allowance. N2 adds the exact registered `__all__` surface: the 16 calculator
API names, both snapshot Protocols, and both re-derivation markers.

Judgment calls: the structured mismatch carrier is a dictionary with
`marker` and `mismatches` keys so callers can log every disagreement in one
result; a mismatch entry uses `field`, `rederived_value`, and `stored_value`.
The public surface follows master-plan §6.5's set, with duplicate mention of
`REDERIVE_SKIPPED` in the prompt naturally deduplicated by set semantics. Optional
N1, N5, and N6 were not taken because they are outside the routed findings and
would add unrelated surface changes to this fix cycle.

Verification: focused calculator suite **59 passed**; Ruff clean; full suite
**1743 passed / 23 failed / 1 deselected**, with the 23-failure set unchanged
from the routed baseline. Every inherited Q-site, shared-guard, closed-set FK,
and hostile-context mutation was applied at its named site, reddened its expected
assertions, reverted, and hash-checked. The new B1 context-removal mutation
reddened the hostile-context row; the B2 `_require_money` zero-return mutation
reddened the system-`None` row; and the C8 right-value deletion reddened the
incomplete message assertions. The absorbed guard rows and public-surface row
are green. No architecture-graph change was made; the pending
`domain-item-economics` node remains held per owner card 3.
