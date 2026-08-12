---
plan: phase 3 (canonical calculator)
role: reviewer
session_doctrine: plan-projection (charter: reviewer role tables, round 0)
round: 0
date: 2026-08-12
state: COMPLETE
verdict: AMENDMENTS_REQUIRED
actor: Claude (plan-projection agent)
---

# Projection handoff — phase 3, round 0

## Opening (owner-readable)

Phase 3 builds the single module that owns every money calculation in this domain. I
did the builder's first hours on paper, and the design underneath is sound — the
formulas, the rounding decisions and the snapshot rules all hold up. What does not yet
hold up is the plan's list of *proofs*: four of the required tests cannot be written as
described. Two are simply impossible — one asks for a rounding example that arithmetic
says cannot exist, and one asks a test to detect something that quietly does nothing.
Two more are contradictory or point at a stale reference, so two builders would write
different numbers of tests. I also found one genuine factual error in the governing
contract (a stated tolerance of "one öre" that is really up to eight at realistic
rates), and one leftover from the previous phase that will trip this one on its first
fixture.

Nothing here needs you personally — every item is a wording or test-table fix the
coordinator can route. The gate holds until those are routed; then the builder's
prompt can be written.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Every finding below routes to the coordinator as a plan amendment, an upstream
correction, or a recorded delegation — no product semantic is in question.

## Gate check

| Check | Result |
|---|---|
| `master_plan.md` §4: phase 2 **APPROVED**, phase 3 `NOT_STARTED` with ⚑ | ✅ `master_plan.md:86-87` |
| `plans/phase_3_canonical_calculator.md` exists, Review log empty | ✅ `:130-133` (header + "(append-only)", no entries) |
| No phase-3 implementer handoff (round 0) | ✅ `handoffs/` held only `mechanism_inventory/` and `planner/`; `handoffs/reviewer/` did not exist |
| Branch | ✅ `fix/idempotent-completion-analytics` |
| Archgraph orientation (read-only) | ✅ `archgraph_status` = 125 nodes / 161 edges, revision `10d94f14…`, **0 pending** — matches `master_plan.md:74-76`; `domain-work-analytics` found, origin `human_confirmed`, reviewState `reviewed`. No delta. |

## Decision ledger

Severity: **B** = blocking (a criterion no implementer can satisfy or decide from the
artifacts); **S** = should-fix; **D** = free choice → explicit delegation.

| # | Decision point | Classification | Routing |
|---|---|---|---|
| B1 | C2 requires a HALF_EVEN tie row at Q4; no such input exists | plan gap | amend C2 (replace with a residue row + quantize-site mutation) |
| B2 | C7's "any dereference raises" is false — unset FKs read as `None` | plan gap | amend C7 (pin a tripwire or static-source form) |
| B3 | C1 needs an error identity for term-shape rejection; §6.4 has none | plan gap (registry) | amend `master_plan.md` §6.4 |
| B4 | C1's row count self-contradicts and cites phase 2 C3 as "five" (it is 12) | plan gap | amend C1 (carry the 12-row table) |
| S1 | C2's row count self-contradicts (5+5 vs 4 tie rows); Q1/Q4 exactness content unpinned | plan gap | amend C2 into a 5×2 table |
| S2 | C2's named mutation site ambiguous (shared helper vs five call sites) | plan gap | amend C2 → five named per-site mutations |
| S3 | §6A.1's guard table is not total; C6 covers 2 of 6 input classes | plan gap | amend C6 into a per-cell table |
| S4 | C6's `Decimal(str(v))` row has no home — no request layer ships in phase 3 | plan gap | amend C6 (register a helper in §6.5, or move the row to phase 4) |
| S5 | Tasks 2 and 6 have no criterion; §6A.2's "never relies on" the global context is false as specified | plan gap + intention wording | add criterion C9; route the §6A.2 sentence upstream |
| S6 | §6A.8's "up to one minor unit" variance bound is factually wrong (up to 8 observed) | **intention gap** | upstream correction to §6A.8 |
| S7 | Eleven phase-2 `Numeric` columns annotated `Mapped[float]`, contradicting §6A.1 | out-of-perimeter code defect | coordinator: phase-2 follow-up or phase-9 batch; phase 3 plan states §6A.1 governs |
| S8 | Duplicate `item_purchase_cost` snapshot terms unguarded anywhere (inventory row 11, S1) | plan gap | amend C1 (add the row) or record the non-guard decision |
| S9 | Task 5's currency helper: returns a failure vs raises — undetermined | plan gap | amend task 5 + C8 |
| D1 | Public function names for the calculator's API | free choice | delegate + require report-back into §6.5 |
| D2 | Test file location | free choice | delegate (`tests/unit/domain/item_economics/`) |
| D3 | Guard placement: one shared function vs per-function checks | free choice | delegate (pin C6's singular reading) |
| D4 | `rederive`'s skip-marker representation | free choice | delegate, must be a named module constant |
| D5 | Whether `rederive` re-derives term `amount_minor` or sums the stored values | free choice | delegate with recommendation (re-derive) |

---

## Blocking findings

### B1 — C2's Q4 tie row is unsatisfiable; Q4's rounding mode has no arbiter, ever

C2 requires, per quantization site, a tie fixture "whose unquantized value ends in
exactly `.5` at the target scale with an even floor … A HALF_UP implementation must
turn each red." At **Q4** (`Decimal(actual_worker_seconds) / Decimal(60)`, 2 dp,
`intention.md:663`) no such input exists.

*Proof.* `actual_worker_seconds` is `int` (§6A.1, and `task_steps.total_working_seconds`
is `Integer NOT NULL`). A 2-dp HALF_EVEN/HALF_UP divergence requires
`frac(s/60 × 100) = 1/2`. But `Fraction(k, 60) × 100 = 5k/3`, whose denominator is 1 or
3 — never 2. Verified two ways: the residue set over all `k ∈ [0,60)` yields
denominators `{1, 3}`, and an exhaustive sweep of `s ∈ [0, 100000)` found **zero**
inputs where the two rounding modes differ.

Consequence: the row cannot be written, and the criterion's named mutation can never
bite at Q4. Every second value lands either exactly on 2 dp (multiples of 3 → `.05`
steps) or on a repeating third (`0.0166…`, `0.0333…`), which both modes round
identically.

*Proposed amendment.* C2 states the impossibility with its proof, so no later reviewer
files it as missing coverage, and replaces Q4's tie row with:
- an exactness row on a repeating residue — `sec=100 → 1.67`, `sec=20 → 0.33`
  (verified);
- named mutation: **delete the `.quantize(Decimal("0.01"), …)` at the Q4 call site in
  `calculator.py`** → the row reddens (raw `1.666…667` ≠ `1.67`). This is the only
  defect Q4 can actually be guarded against.

*Verified constructible, for contrast* (so the amendment does not over-correct — every
other site keeps its tie row):

| Site | Tie fixture | Raw | HALF_EVEN | HALF_UP |
|---|---|---|---|---|
| Q1 | `price=4900`, `percent_value=0.500` | `24.500` | `24` | `25` |
| Q2 | `fixed=24000003`, `hours=1000.00`, `util=100.00` | `400.00005` | `400.0000` | `400.0001` |
| Q3 | `budget=1`, `rate=0.0128` | `78.125` | `78.12` | `78.13` |
| Q4 | — | **impossible** | — | — |
| Q5 | `sec=60`, `rate_snapshot=24.5000` | `24.5000` | `24` | `25` |

All four have an even floor as C2 requires, and all inputs satisfy the phase-2 CHECKs
(`util ≤ 100.00`, `fixed_monthly_cost_minor > 0`, `Numeric` scales). Q2's is the one an
implementer will not find by trial — the search is a Diophantine one (the denominator
`hours × util × 3/5` must be a multiple of 20000), so the plan should seed it.

**Trap worth naming in the same amendment:** the obvious small-rate Q2 tie (`0.00005`)
quantizes to `0.0000` and therefore raises `ITEM_COST_RATE_UNDERFLOW` (§6A.6, plan task
4) instead of returning a value. The tie row must sit at a non-zero rate.

### B2 — C7's "never dereferences an FK" has no live arbiter

C7: "rederive must not touch FK fields (fixture leaves them `None` — any dereference
raises)." Verified in-process against the shipped phase-2 models:

```
construct unsaved OK
  client_id (unflushed) = None
  FK cost_model_version_id = None <- read did NOT raise
  FK production_cost_group_id = None
  FK production_cost_basis_version_id = None
  relationship attrs on ItemCostEvaluation: []
```

Two facts kill the criterion. `nullable=False` is a DDL-level constraint, so an unset
column attribute simply reads `None` — no exception. And `ItemCostEvaluation` declares
**no `relationship()` at all** (verified: `__mapper__.relationships` is empty), so
there is no lazy load to trip either. A `rederive` that reads all three FKs passes this
row unchanged.

Good news for the rest of C7: unsaved `ItemCostEvaluation` + `ItemCostEvaluationTerm`
instances **are** constructible without FK values, so charter rule 3 is satisfiable as
the plan intends.

*Proposed amendment.* Pin one decidable form:
- **(a) recommended** — a tripwire: `mock.patch.object(ItemCostEvaluation, "<col>",
  property(_raise))` over the three FK columns **and** the two episode snapshots
  (`task_type_snapshot`, `return_source_snapshot` — §6A.11 excludes them too), with the
  named mutation "make `rederive` read `evaluation.production_cost_basis_version_id`"
  reddening the row;
- (b) fallback — the P-J static proxy on `inspect.getsource(rederive)`, with its own
  named mutation.

(a) is the stronger arbiter and is what §6A.11's theorem actually claims.

### B3 — C1 requires an error identity that does not exist in the registry

C1: "each per-type NULL-column violation → rejected by the calculator's re-validation".
§6A.4 (`intention.md:682-684`) mandates the second rejection ("a row written by a future
path cannot silently produce a wrong `amount_minor`"), but **`master_plan.md` §6.4's
identity list contains no identity for an invalid term shape** — I checked every group
(selection, inputs, rate, chain races, version admission, guarded deletes, valuation,
group membership, API bridge, migration). §6 is explicit that "a session needing an
unlisted name routes it back to the coordinator rather than inventing one", so the
implementer is blocked by construction.

*Proposed amendment (master plan §6.4, Inputs group):* register
**`ITEM_COST_TERM_SHAPE_INVALID`** — raised as `ValidationError`, message naming the
`calculation_type` and the offending column. Verified implementable: `ValidationError`
takes a single `message` (`errors/validation.py:4-8`) with no `code` field, so §6.4's
leading-token carrier works unchanged.

### B4 — C1's row count self-contradicts, and its cross-reference is stale

C1 says "one row per invalid combination, mirroring phase 2 C3's five". Two defects:

- **The count is wrong.** The total space is 3 types × `percent_value` {NULL, ¬NULL} ×
  `fixed_amount_minor` {NULL, ¬NULL} = 12 cells, 3 valid → **9 invalid combinations**,
  not five.
- **The citation is stale.** Phase 2's C3 term table is a **12-row** table
  (`plans/phase_2_schema_models.md:151-165`, 9 reject / 3 accept), introduced by the
  phase-2 projection's D9 on 2026-08-12 — one day *after* this plan was written
  (`plans/phase_3_canonical_calculator.md:6`, dated 2026-08-11). The master plan's own
  tracker calls it "C3 12-row table" (`:86`).

An implementer following "five" writes five rows and silently drops four — precisely
the sampling charter rule 2 exists to prevent.

*Proposed amendment.* C1 carries the same 12-row table as phase 2 C3, each row with its
one exact outcome: the 3 accept rows assert the exact `amount_minor`, the 9 reject rows
assert `ITEM_COST_TERM_SHAPE_INVALID` (B3).

---

## Should-fix findings

### S1 — C2's row count self-contradicts; two exactness rows have no pinned content

The lead-in reads "per site one exactness row and one tie row" (5 + 5 = 10 rows). The
tie bullet then reads "At least one such row per integer-target site (Q1, Q5), one at
4 dp (Q2), one at 2 dp (Q3, Q4)" — **four** tie rows for five sites, with Q3 and Q4
sharing one. Under the bullet's reading one of Q3/Q4 has no arbiter at all (charter
rule 2). Separately, exactness content is pinned only for Q2, Q3 and Q5; Q1's and Q4's
exactness rows have no stated fixture or expected value.

*Proposed amendment.* Replace C2's prose with a 5 × 2 table (site × {exactness, tie}),
each cell carrying its fixture and one exact expected value, Q4's tie cell marked "not
constructible — see B1". The verified fixtures in B1's table can seed the tie column;
the Q3-persisted and Q5-drift rows below can seed two of the exactness cells.

### S2 — C2's named mutation site is ambiguous (charter rule 11, P-G(a)'s lesson)

C2 names one mutation: "a HALF_UP implementation must turn each red (that is the row's
named mutation, applied at the quantize call in `calculator.py`)". If the implementer
writes a shared `_quantize(value, scale)` helper — the natural design — then a single
definition-site mutation reddens every tie row simultaneously, and **no individual site
is independently arbitrated**. A per-site defect (Q1 accidentally HALF_UP while the
others are correct) survives. That is inventory row 4, ranked S1.

This is the same defect class the charter records from plan 3 round 1: "'delete the
guard' is ambiguous between deleting the function and deleting its call, and the
function-side mutation can bite while the call-site one sails through".

*Proposed amendment.* Five separately named mutations, one per Q-site **call site**,
each naming the site and exactly which row it must redden.

### S3 — §6A.1's boundary table is not total; C6 covers two of six input classes

C6 tests `float`-for-money, `float`-for-rate, `None`-for-required, and the
`Decimal(str(v))` parse (S4). §6A.1's table has six input classes, and the following
cells have no decidable outcome in any artifact:

| Cell | Status |
|---|---|
| `Decimal` arriving where money (`int`) is specified | undetermined |
| `int` arriving where a rate/percent (`Decimal`) is specified | undetermined |
| `str` arriving at the module | undetermined — §6A.1's `str` row describes the **pre-module** request layer, not the module boundary |
| `bool` for money | undetermined **and dangerous**: `isinstance(True, int)` is `True`, so a naive `isinstance(x, int)` guard admits `True` as 1 minor unit |
| enum **value** string instead of a member | §6A.1 says `TypeError`; **no criterion exists** |
| `None` for an input with no named identity — `monthly_paid_hours`, `planning_utilization_percent`, `fixed_monthly_cost_minor`, `actual_worker_seconds`, the rate | undetermined: §6A.1's last row promises "the named `ValidationError` of §6A/§7A", but §6.4 names identities only for expected price and purchase cost |

*Proposed amendment.* C6 becomes a table over (input class × arriving type) with one
exact outcome per cell. Recommended rule, which needs no new identities beyond B3's:
`TypeError` for every type violation, `bool` explicitly included; `None` on a
**user-supplied** input → its named identity
(`ITEM_COST_EXPECTED_PRICE_REQUIRED` / `ITEM_COST_PURCHASE_COST_REQUIRED`); `None` on a
**system-supplied** input (snapshots, rate, seconds) → `TypeError`, since it is a
programmer error that must never reach a user as a validation message.

### S4 — C6's `Decimal(str(v))` row has no home in phase 3

C6 requires "`Decimal(str(v))` request-layer parsing proven on a value with more
decimals than target scale". But §6A.1 places that parse **before** the module
("JSON-borne numerics (request layer, before the module)"), phase 3 ships no request
schema, service or router (plan Goal: "NOT in this phase: any I/O, service, command, or
persistence"), and `master_plan.md` §6.5's inventory of `calculator.py` lists no parse
helper. There is nothing to test.

*Proposed amendment.* Either register the helper in §6.5 as calculator-owned (e.g.
`parse_request_decimal`) and keep the row, or strike it from C6 and move it to phase 4,
the first phase that ships a request schema. Recommend the second — it keeps phase 3
free of I/O-shaped surface.

### S5 — Tasks 2 and 6 have no criterion, and §6A.2's context claim is false as specified

Task 2 (decimal discipline: "global context never touched") and task 6
(`CALCULATION_VERSION` with §6A.10's bump contract as its docstring) carry no
acceptance criterion — charter rule 1. Task 6 is partly reachable through C7's
skip-marker row; task 2 is not covered at all.

More substantively, §6A.2 states the module "never mutates the global decimal context
and **never relies on it**". Verified — the first half is achievable, the second is not,
for any implementation that does not open a `localcontext()`:

```
default prec = 28   default rounding = ROUND_HALF_EVEN
baseline          Q5(100s, 400.0000) = 667   Q3(100000, 3.0000) = 33333.33
ambient=CEILING   Q5 = 667   Q3 = 33333.33   <- explicit rounding= protects
ambient prec=6    Q3 -> decimal.InvalidOperation  <- explicit rounding= does NOT protect
```

An ambient **rounding** change is neutralized by §6A.2's explicit `rounding=` argument,
exactly as intended. An ambient **precision** change is not: both `Decimal.__truediv__`
and `.quantize()` read `getcontext().prec`, and a lowered precision turns Q3 into a
hard `InvalidOperation`. The failure is loud rather than silent (S3, not S1), but the
contract as written is unmet.

*Proposed amendment.* Add **C9 — ambient-context hostility**: under
`getcontext().rounding = ROUND_CEILING` and a lowered `getcontext().prec`, every Q1–Q5
output is byte-identical to the baseline row. Two named mutations: "drop the explicit
`rounding=` at the Q1 call site" reddens the rounding half; "remove the
`localcontext()` wrapper" reddens the precision half. Plus a one-line criterion that
`CALCULATION_VERSION == 1` and its docstring names the bump/never-bump lists.
Route to the coordinator whether §6A.2's "never relies on it" is (i) tightened into a
`localcontext()` requirement — recommended, C9 then proves it — or (ii) weakened
upstream to rounding-mode independence only.

### S6 — §6A.8's "up to one minor unit" variance bound is factually wrong (intention gap)

§6A.8 (`intention.md:738-742`) pins: "`variance_cost_minor` may differ from
`variance_worker_minutes × rate` by up to one minor unit. Pinned as correct, so no
future reviewer 'reconciles' them." The independence claim is right; the **bound** is
not. The discrepancy scales as ≈ `0.01 × rate + 0.5`, because both `allowed` (Q3, 2 dp)
and `actual_worker_minutes` (Q4, 2 dp) carry rounding error that the multiplication
amplifies:

| rate | max observed &#124;var_cost − var_min × rate&#124; |
|---|---|
| `1.0000` | 0.5 |
| `10.0000` | 0.5 |
| `400.0000` | **3** |
| `1000.0000` | **8** |

At the plan's own worked rate of `400.0000` the real bound is three minor units. Anyone
writing an assertion from the current sentence gets a test that flakes on real data.

*Routing:* upstream to §6A.8 (home-artifact rule) — replace the fixed "one minor unit"
with the derived bound. The formulas themselves are unaffected; nothing in phase 3's
arithmetic changes.

*Good news for C5:* the criterion's row **is** constructible. Verified triple, worth
seeding into the plan so the implementer does not have to search:
`budget = 100000`, `rate = 100.5000`, `sec = 12181` → `allowed = 995.02`,
`actual = 203.02`, `consumed = 20403`, `var_min = 792.00`, `var_cost = 79597`,
`var_min × rate = 79596.000000` — difference exactly 1. My first search missed it
because I sampled rates below 6.0; at those rates a difference of 1 is arithmetically
impossible, which is itself the evidence for the bound correction above.

### S7 — Eleven phase-2 `Numeric` columns are annotated `Mapped[float]` (out of perimeter)

Every `Numeric` column shipped by phase 2 is annotated `float`:

- `production_cost_basis_version.py:24,25,26`
- `item_cost_evaluation.py:33,34,36,38`
- `item_cost_evaluation_term.py:22`, `cost_model_term.py:22`
- `item_cost_result.py:23,25`

This contradicts §6A.1, which specifies rates and percentages cross the calculator's
boundary as `decimal.Decimal` — "what SQLAlchemy `Numeric` returns under asyncpg" — and
contradicts the repo's own precedent, `user_work_profile.py:33`, which annotates
`Numeric(12,4)` as `Mapped[Decimal | None]`. Runtime behavior is correct (asyncpg
returns `Decimal`); only the annotations lie.

It matters to **this** phase specifically: the phase-3 implementer builds C7's fixtures
from exactly these classes, and the calculator's float guard is specified to raise
`TypeError` on precisely the type the annotations promise. An implementer trusting the
annotations writes `monthly_paid_hours_snapshot=320.0` and gets a `TypeError` from the
module they just wrote. No phase-2 review round caught this (checked r1–r3 and the
carry-forward table: not present).

*Routing:* outside phase 3's declared perimeter (`calculator.py` + its tests), so the
coordinator decides — a phase-2 follow-up or the phase-9 drift batch. Phase 3's plan
should carry a one-line note that **§6A.1 governs the boundary types, not the ORM
annotations**, and that C7 fixtures assign `Decimal` explicitly (unsaved instances get
no DB round-trip, so nothing coerces them).

### S8 — Duplicate `item_purchase_cost` snapshot terms are unguarded anywhere

Inventory row 11 ("Duplicate `item_purchase_cost` terms", **S1**) sits inside phase 3's
⚑ range (rows 1–14). A5's partial unique protects `cost_model_terms` — the *live*
terms. The snapshot table `item_cost_evaluation_terms` carries **no constraint at all**
(verified: no `__table_args__` in `item_cost_evaluation_term.py`), and §6A.5's budget is
a plain sum over the snapshot rows. Two purchase-cost snapshot rows subtract the
purchase cost twice, silently — the exact failure A5 exists to prevent, one table over.

This is the same "written by a future path" argument that motivates C1's re-validation,
so the plan already accepts the principle; it just stops at NULL combinations.

*Proposed amendment.* C1 gains a row: two `item_purchase_cost` terms in one snapshot set
→ `ITEM_COST_TERM_SHAPE_INVALID` (B3). If the coordinator prefers not to guard it, the
non-guard should be recorded in the plan's Notes so a later reviewer does not file it.

### S9 — Task 5's currency helper: return-a-failure vs raise is undetermined

Task 5: "Currency three-way equality helper … pure — takes the three currency members,
**returns** ok or the `ITEM_COST_CURRENCY_MISMATCH` failure naming both sides and which
pair failed." C8 says "three mismatch rows … each naming its failing pair; equal row
passes", and §6.4 defines an identity as the leading token of an exception `message`.
Return-a-value and raise-an-exception need different assertions, and the plan supports
both readings.

*Proposed amendment.* Pin it — recommend **raise `ValidationError`**, consistent with
every other identity in §6.4 and with the calculator's other error paths.

---

## Delegations (free choices, granted explicitly)

| # | Choice | Delegated resolution |
|---|---|---|
| D1 | Public function names for Q1–Q5, budget, allowance, consumption, currency helper | Implementer's choice per `21_naming_conventions`. **§6's registry lists none of them** and forbids inventing unlisted names, so this must be granted on purpose. Requirement: the handoff reports the resulting public API so the coordinator folds it into §6.5 — phases 4, 5, 7 and 8 all call these functions and cite none by name today (only `rederive`, `phase_7:85`). |
| D2 | Test file location | `tests/unit/domain/item_economics/`, mirroring the existing `tests/unit/domain/<domain>/` layout (verified: `items/`, `analytics/`, `execution/`, …). The plan says only "unit tests for it". |
| D3 | Guard placement — one shared entry guard vs per-function checks | C6's mutation says "the float guard at its **definition site**" (singular) → one shared guard. Delegated with that reading pinned; note it interacts with S2 (the quantize mutations must stay per-site regardless). |
| D4 | `rederive`'s skip-marker on a `calculation_version` mismatch | Implementer's choice of representation, but it must be a **named module-level constant** (not a bare `None` returned from two different paths), because C7 asserts one exact outcome for the `calculation_version = 2` row. |
| D5 | Whether `rederive` re-derives each term's `amount_minor` or sums the stored values | Recommend **re-derive and compare**. §6A.11's theorem explicitly claims every term's `amount_minor` is reproducible, but the plan's signature returns only `(rate, budget, allowed)`; if `rederive` merely sums stored `amount_minor`, HC-7 never proves the term half of its own theorem. |

---

## Citation and decidability verification

Every path and citation in the plan, checked against the tree:

| Claim | Result |
|---|---|
| `domain/item_economics/calculator.py` marked new | ✅ absent; package holds only `__init__.py` + `enums.py` |
| Imports `domain/item_economics/enums.py` (phase-2 dependency) | ✅ present, 3 enum classes |
| §6A.11's closed set vs shipped columns | ✅ **all 13 fields present and correctly named** — evaluation: `expected_sale_price_minor`, `purchase_cost_minor`, `currency`, `fixed_monthly_cost_minor_snapshot`, `monthly_paid_hours_snapshot`, `planning_utilization_percent_snapshot`, `cost_per_worker_minute_minor_snapshot`, `calculation_version` (`item_cost_evaluation.py:27-39`); terms: `name`, `calculation_type`, `percent_value`, `fixed_amount_minor`, `amount_minor` (`item_cost_evaluation_term.py:18-25`). A2's `_minor_snapshot` rename and A3's `percent_value`/`fixed_amount_minor` (never `value`) both landed. |
| Error identities the plan cites exist in §6.4 | ✅ `ITEM_COST_PURCHASE_COST_REQUIRED`, `ITEM_COST_RATE_UNDERFLOW`, `ITEM_COST_CURRENCY_MISMATCH`, `ITEM_COST_EXPECTED_PRICE_REQUIRED`. Raise pattern implementable: `ValidationError(message)` only, no `code` (`errors/validation.py:4-8`) — §6.4's leading-token carrier holds. The one missing identity is B3's. |
| `validate_<concern>` pattern (task 1) | ✅ real repo idiom — `domain/users/validators.py:6`, `domain/pause_reasons/validators.py:1`, and 12 more |
| §6A.2: repo's only *explicit* quantize rounds HALF_UP | ✅ `services/commands/upholstery/requests/__init__.py:17` — sole hit for `ROUND_HALF` in the tree |
| §6A.2: `_cost_minor` at `process_step_transition.py:161-234` | ⚠️ **N2** — no function of that name exists; the value is the local `cost_minor` at `:231-233` inside `_recompute_step_time_totals` (starts `:161`). The substance is verified true: `.to_integral_value()` is called **with no argument**, inheriting the ambient context. The plan's Note ("`_cost_minor` is NOT a precedent") stands. |
| C2: "§6.3's worked shape — `fixed=57_600_00, hours=320.00, util=75.00`" | ⚠️ **N1** — **no such worked example exists in the intention.** §6.3 (`:561-573`) carries only the formula; grepping `57_600` / `400.0000` / `320.00` across `intention.md` returns zero hits. The arithmetic is correct (5 760 000 / 14 400 = 400.0000, verified), so keep the fixture and drop or fix the attribution. |
| C2 Q3-persisted-rate row constructible | ✅ but needs a large fixture: `rate_raw = 400.00005`, `rate_persisted = 400.0000`, `budget = 40 000 000` → persisted `100000.00` vs raw `99999.99`. At `budget = 4 000 000` the two agree, so the row silently degenerates — the plan should seed the value. `Numeric(12,2)` holds `100000.00` ✅ |
| C2 Q5-drift row constructible | ✅ easily: `sec=20, rate=400.0000` → pricing Q4's `0.33` gives 132, Q5 gives 133 (drift 1); `sec=100` → 668 vs 667 |
| C4 underflow pair constructible | ✅ on one basis shape (`hours=1000.00, util=100.00`): `fixed=2` → `0.0000` (underflow), `fixed=6` → `0.0001` (accepted). Both satisfy A1's `> 0` CHECK |
| C3 rows (empty set, multi-term, negative, shuffled) | ✅ decidable as written |
| C5 `percent_consumed` totality | ✅ decidable; note `allowed > 0 ∧ actual = 0` correctly yields `0.00`, which does not conflict with the "never 0" rule (that rule governs the `allowed ≤ 0` branch) |
| C7 unsaved ORM instances constructible | ✅ verified in-process (see B2); `client_id` default fires at flush, so unsaved rows carry `None` |
| Phase 3 iterates `EconomicsStatusEnum`? | ✅ **no** — nothing in the plan's tasks or criteria touches it. The declaration-order hazard is real (`enums.py:15-26` lists §11A.4's group-2 order with `INFEASIBLE`/`OK` last, while §11A.4 evaluates the committed branch first) but lands in phase 4's `configuration.py`, already flagged at `plans/phase_2_schema_models.md:476` |
| §6.5 domain files not built here (`configuration.py`, `serializers.py`) | ✅ correctly out of scope — `configuration.py` is claimed by phase 4 (`:34-35`), `serializers.py` by phases 5 and 8 |
| Inventory rows 1–14 coverage | rows 1, 3–10, 13, 14 covered by C1–C8; row 2 (gross base) covered implicitly by C1's percentage row but carries **no named mutation**; row 11 → **S8**; row 12 (term mutability) is a command concern, correctly absent |
| C8's "naming its failing pair" | ⚠️ **N3** — no message format is pinned anywhere; §6.4 pins only the leading token, so any assertion past the token is undecidable. Suggest: assert the token plus the presence of both currency values |
| P-K / P-M shared-fixture obligations | ⚠️ **N4** — inherited via the criteria preamble, but no C-row states *which field of the shared fixture it varies* (P-M's L3 companion). Worth restating in the implementer prompt: most C-rows will hang off one basis/evaluation factory |

## Explicit delegation list

Granted on purpose, in writing: **D1** (public function names, with report-back),
**D2** (test location), **D3** (shared guard), **D4** (skip-marker representation),
**D5** (term re-derivation strategy). Everything else in this plan is either determined
by the artifacts or is a ledger row above. No other freedom is granted — in particular,
the implementer does **not** choose error identities (B3), tie fixtures (B1/S1),
mutation sites (S2), or guard-cell outcomes (S3).

## Write perimeter

**This handoff only** —
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase3_projection_r0_handoff.md`
(new; created `handoffs/reviewer/`).

- **Code, plans, intention, master plan: zero writes.** No implementation, no
  amendments applied in place.
- **Archgraph: zero delta** — read-only orientation (`archgraph_status`,
  `archgraph_search_nodes`) only; revision `10d94f14…` unchanged, 0 pending.
- **Outside the repo:** three throwaway arithmetic probes in the session scratchpad
  (`probe.py`, `probe2.py`, `probe3.py`) — evidence for B1, S5 and S6, not deliverables.
- **Not mine:** `git status` shows one other untracked file,
  `handoffs/maintenance/2026-08-12_migration-shim-followup_r1_handoff.md`, deposited by
  the parallel maintenance session. Declared here so the perimeter check does not
  attribute it to this session.

## Verdict

**AMENDMENTS_REQUIRED** — 4 blocking, 9 should-fix, 5 delegations. The blocking four
(B1 impossible Q4 tie, B2 unarbitrated FK claim, B3 missing error identity, B4
contradictory row count) each stop an implementer mid-criterion with no artifact to
resolve them. The implementer prompt compiles once the ledger is routed; B3 and S6 are
the two rows that change artifacts other than the phase plan (`master_plan.md` §6.4 and
`intention.md` §6A.8 respectively), and S7 needs a routing decision that is not phase
3's to make.

*Non-authoritative note:* no skeleton is attached. The fixtures quoted above are
evidence that criteria are (or are not) constructible — they are not a design for the
module, and the implementer owes them nothing beyond the values the amended plan
chooses to seed.
