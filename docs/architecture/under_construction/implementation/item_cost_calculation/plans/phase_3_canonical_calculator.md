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

### Reviewer r2 (re-review, delta-scoped) — 2026-08-12 — Claude (plan-reviewer) — CHANGES_REQUESTED

Perimeter **exact**: `git show 8378a1b` = the four allowed files only; declared hashes match
byte-for-byte (calculator `1c9a75fa…eb5d20`, tests `971232312a…cc885b`); tree clean at start and end.
Suite re-run: **1743 passed / 23 failed / 1 deselected**, +5 exactly, zero connectivity noise, failure
set byte-identical to the phase-1 routed list (`diff` empty; N14 did not fire). Ruff clean. Graph
read-only and unchanged — revision `671fd92a…`, 126 nodes / 161 edges, 1 pending item, zero
diagnostics/stale: **zero delta**, as declared.

**r1 findings verified closed.** **B1 CLOSED — structurally, not just by its test:** I swept *every*
public callable under `prec=6, ROUND_CEILING` and all twelve are byte-identical to baseline, including
the two that diverged in r1 (`calculate_remaining_worker_minutes` and `calculate_variance_worker_minutes`
now both return `99999.67`, the exact r1 reproduction). Removing the wrapper reddens the C9 row.
**B2 CLOSED:** the new row drives `calculate_variance_cost_minor(None, 100)` — a genuinely
system-supplied parameter (no `required_identity`) — and the inferred-zero mutation that left 54/54
green in r1 now reddens it. **S1 CLOSED:** the `or` is gone; the message-weakening mutation reddens
**2 of 3** rows (the P-O bar; row 2 is structurally immune because both its surviving left-hand values
are `swedish_krona`). **S2 CLOSED:** zero `ITEM_COST_SNAPSHOT_MISMATCH` anywhere in `app/`; `rederive`
returns `{"marker": REDERIVE_MISMATCH, "mismatches": [...]}`; the C7 fixture asserts marker **and**
exact payload, and its two-term fixture correctly reports only the disagreeing term (budget still
reconciles because it is re-derived from the *re-derived* amounts). **S3 CLOSED as routed:** both the
bump token (`term formula`) and the never-bump token (`renames`) bite when stripped from the module
docstring. **Absorbed guards (R9-2) CLOSED:** all three rows exist and each reddens when its own guard
branch is deleted. **N2 CLOSED:** `__all__` is exact and every name in it resolves.

**B3 (blocking) — `rederive` still raises user-facing `ValidationError`s on corrupt snapshots,
contravening R9-1.** Authority: intention §6A.11 as amended round 9 — a re-derivation disagreement
"**never raises a `ValidationError`** and no user-facing error identity exists for it … the read still
renders". Verified live on unsaved ORM instances, three classes:
(a) stored `cost_per_worker_minute_minor_snapshot = 0` → **`ITEM_COST_RATE_UNDERFLOW`**. This is
squarely a stored-value-disagrees case (stored `0` vs re-derived `400.0000`) and it is *this fix's*
seam: the S2 refactor replaced the early raise at the rate-mismatch site with an appended entry, so
execution now continues into `calculate_allowed_worker_minutes(budget, stored_rate)`
(`calculator.py:465`) and dies there instead of returning the marker. The column is
`Numeric(12,4) NOT NULL` with **no CHECK > 0** (`90cdd23a828e:204`), so the row is representable —
and a zeroed snapshot is exactly the integrity event `rederive` exists to detect.
(b) a corrupt snapshot term shape → `ITEM_COST_TERM_SHAPE_INVALID`; (c) a purchase term with NULL
`purchase_cost_minor` → `ITEM_COST_PURCHASE_COST_REQUIRED`. (b) and (c) are pre-existing, in scope only
because R9-1 is new. Correction: no path out of `rederive` may be a `ValidationError` — fold these into
the `REDERIVE_MISMATCH` payload (or a sibling integrity marker), with one criterion row per class and a
named mutation each. **Scope boundary is an owner call — see card 1.**

**S4 (should-fix) — the `calculate_percent_consumed` row added to C9 is decoration.** Proven by
mutation: removing `calculate_percent_consumed`'s `localcontext()` wrapper leaves **59/59 green**, so
the row does not hold the wrapper it was added to guard (charter rule 11 / P-N). Its fixture
`(995.02, 203.02)` is too small for `prec=6` to change the 2-dp result. The sibling rows are fine —
removing `calculate_remaining_worker_minutes`'s wrapper *does* redden. Correction: swap the fixture in
both C9 tuples to `calculate_percent_consumed(Decimal("0.01"), Decimal("100000.00"))` — verified
end-to-end: with the wrapper intact 59 pass; with the wrapper removed the row reddens (`InvalidOperation`
at `prec=6`, the same mechanism as C9(b)'s Q3 row).

**S5 (should-fix) — three of the four `REDERIVE_MISMATCH` field branches have no test.** Only
`term[<name>].amount_minor` is asserted. I exercised all four: `production_budget_minor`,
`allowed_worker_minutes` and `cost_per_worker_minute_minor_snapshot` each produce well-formed entries,
so the code is right — the contract has no arbiter. Also unpinned: a rate mismatch *cascades* into a
second `allowed_worker_minutes` entry (verified fields
`['cost_per_worker_minute_minor_snapshot', 'allowed_worker_minutes']`), because the allowance is
re-derived from the stored rate. Reasonable, but nobody decided it. Authority: charter rule 2
(enumerate, never sample); §6A.11 R9-1 ("naming the disagreeing fields"). Correction: one row per
field branch with its exact payload, and a row pinning the cascade.

**Notes.** N8 `__all__` holds **19** names, not the "20" asserted in the fix handoff, the tracker note
and probe R2-P5 — §6.5's enumerated surface is 16 + `EvaluationSnapshot` + `TermSnapshot` +
`REDERIVE_MISMATCH` (`REDERIVE_SKIPPED` is already among the 16). **The code is right and knowingly so**
(the implementer's own log records the dedup); only the prose count is wrong — a direct repeat of P-L.
N9 the `CALCULATION_VERSION` constant's own docstring — which plan task 6 names as the contract carrier
— has no arbiter: gutting it to `"""Version constant."""` leaves 59/59 green, because the test reads
the *module* docstring (as R2-P5 directed). Two docstrings now carry the same two lists and can drift
apart → next touch. N10 `calculate_variance_worker_minutes` wraps a `localcontext()` around a call that
already wraps one (`calculator.py:357-359`); removing the outer wrapper changes nothing (59/59) —
harmless redundancy → next touch. N11 cosmetic indentation artifact at `calculator.py:390` (the f-string
in `validate_currency_equality`'s comprehension gained four spaces); ruff-clean, zero behavioural effect
→ next touch. r1's optional N1/N5/N6 correctly not taken.

### Implementer fix r3 — 2026-08-12 — Codex

Resolved B3, S4, and S5 within the declared fix-cycle perimeter. `rederive` now converts
calculation-path `AttributeError`, `TypeError`, `ValidationError`, and arithmetic guard failures
into the `REDERIVE_MISMATCH` integrity marker, covering malformed evaluation snapshots, malformed
term snapshots (including invalid shapes and NULL purchase cost), and the zero-rate allowance path.
The rate-zero path preserves the rate mismatch and emits the pinned `allowed_worker_minutes`
cascade entry. Added exact payload rows for `term[...].amount_minor`, `production_budget_minor`,
`allowed_worker_minutes`, and `cost_per_worker_minute_minor_snapshot`, plus the rate cascade.
Replaced both C9 `calculate_percent_consumed` fixtures with `(Decimal("0.01"), Decimal("100000.00"))`.

Judgment calls: malformed-input entries use `field` values `evaluation_snapshot` or `term_snapshot`,
null derived/stored values where no calculation completed, and the original guard identity in an
`error` field; ordinary value disagreements retain the existing three-field payload. A rate mismatch
forces the allowance entry to remain present, as required by R10-1, even when quantization would
otherwise make the allowance value equal. Optional N9–N11 were not taken because the prompt routes
them to a later touch.

Verification: focused calculator suite **65 passed**; full `PYTHONPATH=. pytest -m 'not e2e'`
**1749 passed / 23 failed / 1 deselected**, with the 23-failure set matching the established baseline;
Ruff and `git diff --check` are clean. Named mutations were applied and reverted individually:
B3 class (a) re-raise at the allowance seam → `test_rederive_malformed_evaluation_rate_returns_integrity_marker_and_cascade` red;
B3 class (b) re-raise at the term-shape conversion branch →
`test_rederive_malformed_term_shape_returns_integrity_marker` red;
B3 class (c) re-raise at the NULL-purchase conversion branch →
`test_rederive_malformed_purchase_snapshot_returns_integrity_marker` red;
S4 remove the `calculate_percent_consumed` `localcontext()` wrapper →
`test_all_quantization_sites_ignore_ambient_rounding_and_precision` red;
S5 corrupt the term, budget, allowance, and rate field labels → each corresponding exact-payload
row red; S5 invert the rate-cascade condition →
`test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` red. Final SHA-256:
calculator `e5f42531d59c66a06e384f772f41c0971d63fa5990189f39276ff6d1d9611a49`;
tests `d7251cdeed549a1ac663253f969a994e8cce1a428815afbeeddab0690497ba30`.
Architecture Graph: zero delta; revision remains `671fd92a…`, 126 nodes / 161 edges, one pending
`domain-item-economics` node held per owner card 3.

**Lessons.** L5: R9-1 specified the *happy* mismatch path but not what `rederive` does when the snapshot
is malformed rather than merely disagreeing — a "never raises" contract must enumerate the input classes
it covers, or the implementer closes only the class the finding named (earned: B3). L6: when a fix
extends a hostile-context criterion to new functions, each added row needs its own fixture chosen to
*bite*, and the fix's mutation declaration must name the row it reddens per function — one blanket
"hostile-context row red" hid an inert row among two live ones (earned: S4; extends P-I).

### Reviewer r3 (re-review, delta-scoped: B3/S4/S5) — 2026-08-12 — Claude (plan-reviewer) — CHANGES_REQUESTED

Perimeter **exact**: `git show 8908619` = the five expected files; declared hashes match byte-for-byte
(calculator `e5f42531…611a49`, tests `d7251cde…97ba30`); tree clean at start and end. Suite **1749
passed / 23 failed / 1 deselected**, focused **65**, zero connectivity noise, failure set byte-identical
to the phase-1 routed list (`diff` empty; N14 did not fire). Ruff clean. Graph read-only and unchanged —
`671fd92a…`, 126 nodes / 161 edges, 1 pending item, zero diagnostics/stale: **zero delta**, as declared.
The handoff-inside-the-checkpoint process slip was pre-recorded by the coordinator and is not re-filed.

**B3 CLOSED — and verified TOTAL, not just on the three named classes.** All three R10-1 input classes
return the `REDERIVE_MISMATCH` payload on unsaved ORM instances: (ii) NULL typed term value and
duplicate `item_purchase_cost` rows → `term_snapshot`; (iii) zeroed stored rate → rate entry + cascaded
`allowed_worker_minutes` entry carrying the converted `ITEM_COST_RATE_UNDERFLOW`; (iii) NULL purchase
cost → `term_snapshot`. I then hunted a fourth escape across **17 further hostile inputs** — negative
stored rate, `Decimal("NaN")` in the rate and in the allowance, zero `monthly_paid_hours`, zero
utilization, Q2 underflow, a `float` rate, `None`/`str` expected price, `None` budget, `None` allowance,
`None` term amount, a `str` `calculation_type`, a `float` `percent_value`, a negative percent term,
empty `term_rows`, `None` calculation version, and version 2. **Every one returned the marker (or
`REDERIVE_SKIPPED`); no `ValidationError` escaped on any path.** Both conversion-seam re-raise mutations
bite: the allowance seam reddens the zeroed-rate row; the term-amounts seam reddens both malformed-term
rows. **Regression check that mattered most:** the except tuple is
`(AttributeError, TypeError, ValidationError, ArithmeticError)` and deliberately excludes
`AssertionError`, so the C7 closed-set tripwire still bites through the new catch-all — re-running the
FK-read mutation reddens `test_rederive_uses_unsaved_orm_instances_and_only_the_closed_snapshot_fields`
(a broader `except Exception` would have silently swallowed the phase's closed-set guarantee).

**S4 CLOSED.** r2's verified counterfactual is now the shipped fixture in **both** C9 tuples
(`calculate_percent_consumed(Decimal("0.01"), Decimal("100000.00"))`); removing
`calculate_percent_consumed`'s `localcontext()` wrapper reddens the row (1 failed / 64 passed) where in
r2 it left 59/59 green.

**S5 — four of five parts closed.** The four field-branch rows each assert their exact payload and each
is live: corrupting the `production_budget_minor` label reddens exactly its row, corrupting the
`term[...]` label reddens exactly its row.

**S6 (should-fix) — the pinned rate→allowance cascade has no live arbiter.** R10-1 pins it: "a mismatched
stored rate **also** yields a derived `allowed_worker_minutes` entry … both entries are reported, by
design", implemented as the `or rate != stored_rate` clause at `calculator.py:533`. **Deleting that
clause leaves 65/65 green.** The cascade row's fixture (`cost_per_worker_minute_minor_snapshot =
399.0000`) carries a *second sufficient cause*: at that rate the allowance re-derives to `5.43` against a
stored `5.42`, so the entry appears for the ordinary disagreement reason and the pinned clause is never
exercised — charter rule 2's sole-predicate companion, the same shape as phase-2 B5. The clause also
*looks* redundant, so a future "cleanup" would delete it and silently drop the owner's pinned behaviour.
**Verified correction:** set the fixture's stored rate to `Decimal("399.5000")` and its expected
allowance entry to `rederived_value = stored_value = Decimal("5.42")` — at that rate the allowance
agrees, so the entry can only come from the cascade clause. End-to-end: fixture swapped + clause intact →
65 pass; fixture swapped + clause deleted → **1 failed, exactly
`test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload`**.
**Related declaration defect:** the fix-r3 handoff and the Review-log entry above both state "invert the
rate-cascade condition → `test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload` red".
Re-run independently, the `and` inversion reddens
`test_rederive_reports_allowed_worker_minutes_mismatch_payload` — the plain allowance row — **not** the
cascade row. The mis-attributed declaration is exactly how the unguarded clause reached re-review.

**Notes.** N12 `term_row.name` (`calculator.py:487`) is the one attribute read left outside a `try`; a
term object lacking the attribute raises `AttributeError` out of `rederive`. **Not an R10-1 violation**
(that contract names `ValidationError`) and **unreachable for real rows** — `name` is NOT NULL and an ORM
instance always carries the attribute — but it is the single asymmetry in an otherwise total defensive
perimeter → next touch. N13 dead branching at `calculator.py:472-477`: two
`if str(error).startswith(...)` tests guard three **identical** `return marker(mismatches,
"term_snapshot", error)` statements — it reads as if it discriminates and does not → next touch.
N14 the payload shape is heterogeneous: converted-exception entries carry an extra `"error"` key that
value-disagreement entries lack, so a caller doing `entry["error"]` raises `KeyError` on half the
entries; R10-1 pins no shape → pin it, or phases 7/8 must key defensively. N15 the broad
`except (AttributeError, TypeError, …)` also converts **programmer** errors into data-integrity markers —
a future caller passing a wrong-typed object is told "the data is corrupt" rather than getting the
`TypeError` §6A.1 deliberately reserves for that. R10-1 asked for totality including "missing snapshot
field", so this is the chosen trade-off, but phases 7/8 must not read the marker as proof of corruption
→ phase 7/8. N16 (test fidelity) `test_rederive_malformed_purchase_snapshot_returns_integrity_marker`
(`:509`) passes a `SimpleNamespace` from `_term()` into `rederive`, while the other five new rederive
rows use `ItemCostEvaluationTerm`; C7 pins ORM instances and charter rule 3 requires the production
object type — one-line fix, bundle with S6.

**Lessons.** L7: a criterion pinning an **implication** ("X also implies Y") needs a fixture in which Y
would NOT otherwise fire; otherwise the row passes for the ordinary reason and the pin has no arbiter.
Extends rule 2's sole-predicate companion from equality rows to cascade/implication pins (earned: S6).
L8: extending L6 — a mutation declaration must be checked **against the run that produced it**; naming a
plausible-but-wrong row ("the cascade row reddened") is worse than naming none, because it converts an
unguarded clause into an apparently-verified one (earned: S6's declaration defect).

### Implementer fix r4 — 2026-08-12 — Codex

Resolved S6, N14, and N16 within the fix-cycle perimeter. S6's cascade fixture now stores the rate as
`Decimal("399.5000")` and expects the cascade allowance entry to carry
`rederived_value = stored_value = Decimal("5.42")`, making the `or rate != stored_rate` clause the sole
reason that entry exists. N16 now passes an unsaved `ItemCostEvaluationTerm` to the malformed-purchase
re-derivation row. N14 pins a homogeneous four-key mismatch shape (`field`, `rederived_value`,
`stored_value`, `error`), using `error: None` for plain disagreements and retaining the existing error
text for converted failures. Optional N12/N13 were not taken; they are outside the routed corrections.

Verification: focused calculator suite **65 passed**; Ruff and `git diff --check` are clean. The full
non-E2E suite is **1749 passed / 23 known failures / 1 deselected**, with the 23-failure set matching the
established baseline; the failures are unrelated pre-existing failures. The S6 mutation (delete
`or rate != stored_rate` at the production call site) failed exactly
`test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload`. N14 error-key mutations were
run and reverted at each plain-entry call site: the rate entry failed
`test_rederive_malformed_evaluation_rate_returns_integrity_marker_and_cascade` and
`test_rederive_rate_mismatch_reports_rate_and_allowed_cascade_payload`; the term entry failed
`test_rederive_detects_a_changed_term_amount_on_the_same_orm_shape`; the budget entry failed
`test_rederive_reports_production_budget_mismatch_payload`; and the allowance entry failed
`test_rederive_reports_allowed_worker_minutes_mismatch_payload` plus the cascade row. All mutation edits
were reverted before the final suite and hash capture. Final SHA-256: calculator
`03389d0a2743ae7968a0e5aecc88cc5b2675bea6762c2b9bbec2d87662af8eb0`; tests
`6733181ed998b101ac2bcb0d95f4f5bfc3729f4d1a6ca8e40b619b8b705daa86`.

Architecture Graph: zero delta; the graph remains read-only for this fix, at revision
`671fd92a…`, 126 nodes / 161 edges, one pending `domain-item-economics` node, zero diagnostics and
zero stale nodes. No owner decision is required.
