# Projection r0 handoff — phase 1 (`simple_valuation_editor`)

```
plan: 1
role: reviewer (plan-projection)
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-19
actor: Opus 5 (projection r0)
```

## Opening — for the owner

The plan for the first block of work is sound in its design and wrong in a few of its
details, all of which are cheaper to fix now than after someone writes the code. The
important finding is that three of the plan's safety checks do not actually check
anything: they describe a specific way the code could go wrong and claim a test would
catch it, and I proved by arithmetic that the test would stay green in each case. I also
found one number in the specification that is simply wrong — a value the document says is
zero is actually twenty-nine for the very example the document uses — plus about a dozen
smaller places where the plan leaves the next decision to whoever implements it without
saying so. **Nothing here needs you personally**; these are all engineering corrections
and delegations for the coordinator. The plan should be amended and then the
implementation can start.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing in this projection needs the owner. Every finding is a plan amendment, an upstream
factual correction, or a delegation the coordinator can record — no product question was
reopened and no ratified decision (D1–D10) is affected.

## How the passes were spent

Ranked per prompt §4. Everything load-bearing was verified by executing the contract's own
arithmetic in a throwaway script (master plan §5, "a worked example is a test"), never by
reading agreement off the page.

| Pass | Depth | Result |
|---|---|---|
| 1 — `round_half_even` on negative operands (§3.1A) | deep; all 8 enumerated rows recomputed, plus the named mutation applied to both | contract sound; C1/C2 rows all correct; mutation confirmed to bite |
| 2 — the `(n+1)/2` bound vs the real persisted path (§3.2A, C7) | deep; all 7 shapes swept over P ∈ [0, 40 000) against real `calculate_term_amounts` | bound holds everywhere; **C7's named mutation proved inert on all 7 shapes** |
| 3 — the two searches (§4.2A) | deep; both searches implemented and run | break-even literal `1 211 335` **confirmed**; **`infeasible_at_or_below_minor` for the mockup is 29, not the 0 the intention states** |
| 4 — the band (§7A.1) | deep; band recomputed for Q = 6 and Q = 7, and the superseded order applied as a mutation | `15 000 / 420 000 / 1 650 000` **confirmed exactly**; **C17's named mutation proved inert** |
| 5 — everything else | criteria decidability sweep over all 21, plus path/citation reality checks | 11 further ledger rows |

Verified-good, stated so the coordinator does not re-spend the pass: the three-line M1 form
in §3.1 is *exactly* faithful to `calculate_allowed_worker_minutes` + `_budget_seconds`
(`budget/rate` quantised to 0.01 then ×60 ≡ `round_he(budget×10⁶, rate_tt)` then
`round_he(cm×3, 5)`); C8's disagreement row exists (budget = 7 → two-step 1 s, shortcut 0 s);
C9's minimality holds at `1 211 335` (allowance 12 300 s, and 12 299 s at `P−1`) and fails
against the superseded `1 211 364`, which is not minimal; C16's three literals are exact;
C18's fixture is constructible (`K = 150 000` → break-even 1 893 153, infeasibility floor
702 000 beats the `raw_low` floor 655 200); and rule 3 is achievable — an unpersisted
`CostModelTerm` feeds `calculate_term_amounts` correctly (probed).

## Decision ledger

Classification per the skill: **P** = plan gap (amendment), **I** = intention gap (routed
upstream, never patched downstream), **F** = free choice (delegation recorded in writing).

| # | Decision point | Class | Proposed routing |
|---|---|---|---|
| L1 | C7's named mutation (`n = len(terms)`) cannot turn any row red | **I + P** | correct §12A.3 upstream; replace C7's mutation with F1's two |
| L2 | C17's named mutation preserves every predicate C17 asserts | **I + P** | correct §12A.9 upstream; C17 asserts the exact `step_minor` literal |
| L3 | §4.2A's "`infeasible_at_or_below_minor` is 0 for a purely proportional model" is false for the mockup's own data (29) | **I** | correct §4.2A and §8's example payload; add to §8A.1's correction list |
| L4 | C10's named mutation is not implementable — the thing it mutates is circular | **P** | restate C10 as an exact-literal assertion on a large-break-even model |
| L5 | The "no model" signal's representation is undetermined (exception / sentinel / `None`) | **P** | plan task 2 names it; C6 then asserts one exact outcome |
| L6 | C5's exception type and error identity are undetermined | **P** | plan task 2 names the exception class and identity token |
| L7 | C11, C13 and C20 assert `is_fundable` and `domain` — payload fields no phase-1 task produces | **P** | restate as `break_even is None` / `slider_domain(...) is None`, or add the producing task |
| L8 | Whether `slider_domain` accepts `B = None`, i.e. whether phase 1 owns §7.3's null-domain branch | **P** | decides whether C13/C20's "domain null" is testable inside this perimeter at all |
| L9 | Signatures of `break_even_price_minor`, `infeasible_at_or_below_minor`, `slider_domain`, and the parameter carrier `budget_minor(P)` implies | **F + P** | delegate explicitly **and** register the names — this is phase 2's interface |
| L10 | Whether `collapse_terms` filters `is_deleted` and whether it validates term shape | **F** | delegate with the unflushed-ORM trap stated (see finding F10) |
| L11 | C12's degenerate value — "the cap" is `2**40` or `2**40 − 1`? | **P** | plan names the exact integer |
| L12 | Where the `typical_total_seconds == 0 ⇒ null` branch lives; task 4 cites §4.2A, which does not carry it | **P** | task 4 also cites §4.1's two null conditions |
| L13 | C14 names no fixture, and the natural candidates do not exhibit the double-rounding difference | **P** | criterion states the property the fixture must have |
| L14 | C21's assertion mechanism has no precedent; direct-vs-transitive imports and the forbidden set undetermined | **F + P** | delegate the mechanism; the plan fixes the forbidden set |
| L15 | C3's "tie-free across an enumerated `cm` range" has no exact expected outcome and no stated range | **P** | restate observably (see finding F15) |
| L16 | C15 asserts `digits(0) = 1`, a helper internal to §7A.1's pseudocode | **F** | delegate: expose `digits`, or assert through `two_significant_digits` |
| L17 | §2A.1.3 cites `production_cost_basis_version.py:40` for the rate's `CHECK > 0`; it is `:38` | **I** | one-line correction upstream |

**17 rows, none silent.** Exit gate: every row routed before the implementer prompt compiles.

---

## Findings

### F1 — C7's named mutation is inert. Two independent reasons. `plans/plan_1.md:104`

C7 reads: *"Named mutation: define `n` as `len(terms)` in the assertion helper's definition
→ the two-equal-percentages row red."* Upstream source: `planning/intention.md:1517-1519`
(§12A.3).

It cannot turn any row red.

1. **Wrong direction.** The assertion is `2*abs(delta) <= n + 1`. `len(terms) >= n` always,
   so the mutation can only *enlarge* the right-hand side, i.e. weaken a `<=` bound. A
   weakened bound never fails a case that passed.
2. **Wrong row.** On the specifically named shape — two equal percentage terms — every term
   *is* a percentage term, so `len(terms) == n == 2` and the mutation is not merely weak,
   it is the identity.

Swept over all seven §12.1 shapes against the real
`calculate_term_amounts` / `calculate_production_budget` path, P ∈ [0, 40 000):

| shape | n | len | max &#124;Δ&#124; | true bound | mutated bound | mutation |
|---|---|---|---|---|---|---|
| one percentage | 1 | 1 | 1 | pass | pass | inert |
| two distinct | 2 | 2 | 1 | pass | pass | inert |
| **two equal** | 2 | 2 | 1 | pass | pass | **inert** |
| percentage + fixed | 1 | 2 | 1 | pass | pass | inert |
| percentage + purchase | 1 | 2 | 1 | pass | pass | inert |
| sum exactly 100 | 2 | 2 | 0 | pass | pass | inert |
| sum above 100 | 2 | 2 | 1 | pass | pass | inert |

This is charter rule 11 exactly: *a safety test that survives the defect it exists to
prevent is decoration*. As written, C7 proves the bound holds; it proves nothing about `n`.

**Proposed amendment (two mutations, because they bite on different things):**

- **Tightness of the assertion.** The bound is attained for odd `n` (it is not for even `n`
  — `Δ` is an integer, so `2|Δ|` is even and `2|Δ| <= n+1` collapses to `2|Δ| <= n` when `n`
  is even). On the `percentage + fixed` shape (`n = 1`) the sweep attains `2|Δ| = 2 = n+1`
  at `P = 25`. Named mutation: **weaken `n+1` to `n` in the assertion helper's definition →
  that row red.** This is what proves the criterion is not vacuous, and it also pins
  §3.2A's "attained, not merely bounded" claim, which nothing currently tests.
- **The mechanism under test.** Named mutation in `collapse_terms`' **definition**: derive
  `residual_percent_milli` with a float multiply (`int(float(percent_value) * 1000)`)
  instead of `int(value.scaleb(3))` → `Δ` leaves the bound. This is the defect the bound
  exists to detect and is currently unnamed.

Route: §12A.3 upstream (it carries the same inert mutation), then C7.

### F2 — C17's named mutation is inert; its stated rationale is false. `plans/plan_1.md:125`

C17 reads: *"**Divisibility by `quantity`**, `Q = 7`: `step_minor % 7 == 0`, and
`min_minor`/`max_minor` are multiples of `step_minor`. **Named mutation: derive the
whole-item step first and snap it up to a multiple of `Q` (the superseded §7.2 order) at the
definition site → this row red.** `Q = 7` is chosen because 7 divides none of the round
numbers the wrong order lands on."* Upstream: `planning/intention.md:1535-1538` (§12A.9).

Snapping **up to a multiple of `Q`** makes divisibility by `Q` true by construction — that
is what "snap up to a multiple of Q" means. The mutation therefore cannot break the
predicate C17 asserts. Computed for `B = 1 211 335`:

| | contract order (per-piece first) | mutated order (whole-item, then snap up to ×Q) |
|---|---|---|
| Q = 6 | `step 15 000`, min 420 000, max 1 650 000 | `step 15 000`, min 420 000, max 1 650 000 — **identical** |
| Q = 7 | `step 15 400`, min 415 800, max 1 647 800 | `step 15 001`, min 420 028, max 1 650 110 |
| `step % 7` | 0 | **0** |
| `min % step`, `max % step` | 0, 0 | **0, 0** |

Every assertion C17 names stays green under the mutation at both quantities. The choice of
`Q = 7` does not help: the mutated step is 15 001, which *is* divisible by 7.

The plan's rationale has drifted from the intention's. §7A.1 (`intention.md:918-920`) states
the real failure correctly — the wrong order *"destroys the nice value (`15 142 → 15 144`)"*
— it never claimed the wrong order breaks divisibility. C17 asserts the property that
survives and omits the one that breaks.

**Proposed amendment.** C17 asserts the exact literals for `Q = 7`:
`step_minor == 15_400`, `min_minor == 415_800`, `max_minor == 1_647_800`. Under the named
mutation all three go red (15 001 / 420 028 / 1 650 110). Keep `step_minor % 7 == 0` and the
multiple-of-step assertions as the by-construction invariant, but stop calling them the
mutation's target. Route: §12A.9 upstream, then C17.

### F3 — `infeasible_at_or_below_minor` is 29 for the mockup's data, not 0. `planning/intention.md:566-570`, `:1037`

§4.2A states: *"For a purely proportional model it is `0` (at `P = 0` the allowance is `0`,
and `P = 1` already buys ≥ 1 second unless the rate exceeds the residual value of one öre),
which is the value §8's example carries."*

Computed from §4.2A's own definition on the mockup's own configuration
(`residual_percent_milli = 22 000`, `rate_tt = 13 000 000`, `K = 0`):

- `P = 1` → `budget = round_he(22 000, 100 000) = 0` → `centimin = 0` → `allowance = 0 s`.
- The least `P` with `allowance_seconds(P) >= 1` is **30** (`budget = 7`, `centimin = 1`,
  `seconds = 1`).
- Therefore `infeasible_at_or_below_minor = 29`.

The parenthetical names the correct escape hatch and then draws the opposite conclusion: at
1 300 minor/minute, one öre of budget buys 0.046 s, so the rate *does* exceed the residual
value of one öre — by a factor of about 22. The claim is true only for models with residual
≥ 50 % **and** a rate ≤ 200 minor/minute; the mockup meets neither.

Consequences, enumerated so the correction's blast radius is known:

- **§8's example payload** (`intention.md:1037`) carries `"infeasible_at_or_below_minor": 0`
  and is wrong. §8A.1 (`:1092-1102`) lists exactly three corrections to that example and
  does not list this one. §8 is "a contract by demonstration — a frontend will copy it"
  (§8A.1's own words), so this is a shipped-example defect, not a footnote.
- **§7A.2's worked-check row** (`:938`) reads `ceil_to_step(0 + 1, 15 000) = 15 000, loses
  to 420 000`. With the true value it is `ceil_to_step(30, 15 000) = 15 000` — same result,
  **so C16's three literals are unaffected** and D10 is untouched. Verified.
- **Phase 1 impact is confined to C12's fixture.** C12 requires
  `constant_deduction_minor > 0`, so it does not assert the purely-proportional value — but
  an implementer who reads §4.2A will believe "purely proportional ⇒ 0" and may encode it as
  a shortcut or a second fixture's expectation.

Route: upstream correction to §4.2A and §8, added to §8A.1's list. Not an owner matter — it
is arithmetic, and no ratified decision moves.

### F4 — C10's named mutation is not implementable. `plans/plan_1.md:112`

C10 asks for *"a model … constructed so that a `P_hi` seeded from `domain.max_minor` cannot
terminate. This is the circularity criterion: it fails against §4.2's original wording."*

§4.2's original wording is not a rival implementation that a test can be red against — it is
a circular definition (`max_minor` is derived from `break_even`, which is what the search is
computing, §7A's Defect 1). There is no code an implementer can write that "seeds `P_hi`
from `domain.max_minor`", so there is no mutation to apply and no outcome the row
distinguishes from C9's. As written it asserts "the search returns something", which every
correct implementation and most incorrect ones satisfy.

**Proposed amendment.** Make it an exact-literal assertion against a bound that only the
doubling can reach: `residual_percent_milli = 1`, `rate_tt = 13 000 000`, `K = 0`,
`typical_total_seconds = 12 300` → `break_even_price_minor == 26 649 350 000` (verified:
allowance 12 300 s there, 12 299 s at `P−1`). That break-even is ~2³⁴·⁶, far above any band
`1.35 × B` could seed from a plausible price, and any implementation with a fixed or
band-derived ceiling returns `null` instead — red. Name the mutation as *"cap `P_hi` at any
constant below 2³⁴ in the search's definition"*.

### F5 — the "no model" signal has no defined representation. `plans/plan_1.md:64-66`, `:103`

Task 2: *"Returns the 'no model' signal when a purchase term exists and the purchase cost is
`None`."* C6 asserts *"purchase term present + `purchase_cost_minor is None` → the no-model
signal"*.

§3.1B (`intention.md:375`) says only *"`None` + such a term ⇒ status
`item_missing_purchase_cost`, model block `null`"*. `status` and "the model block" are phase-2
concepts (plan 2 §3 task 5); this phase ships a pure function with no payload, so the
signal must cross the phase boundary as a Python value, and nothing says which:

- return `None` — then `collapse_terms` returns `tuple | None` and phase 2 branches on it;
- raise a domain exception — then phase 2 catches and maps to B8;
- return a sentinel or a two-field result object.

They are not interchangeable: phase 2 must distinguish *this* failure from a shape error
(C5's raise) to produce `item_missing_purchase_cost` rather than a 500. C6 currently asserts
"the no-model signal", which is not one exact expected outcome (charter rule 2). Route: plan
task 2 names it; C6 then names the exact assertion.

### F6 — C5's exception type is undetermined. `plans/plan_1.md:102`

C5: *"A `percent_value` carrying scale > 3 **raises**; it is not rounded. A row asserting the
exception, not a truthy check."* `pytest.raises(...)` needs a class. The house idiom in this
domain is `ValidationError` (`errors/validation.py`) with an identity token before the first
colon — e.g. `calculator.py:127` raises
`ITEM_COST_TERM_SHAPE_INVALID: …`, and intention §8 (`:1050-1051`) makes the leading token the
error's identity. Whether phase 1 reuses `ITEM_COST_TERM_SHAPE_INVALID` or mints a new token
is undetermined, and it is not a free choice — an identity token that reaches a route is a
contract. Route: plan task 2 names class and token.

Sanity check performed so the criterion is known to be satisfiable: `Decimal("22.0001")`
fails `value == value.quantize(Decimal("0.001"))` and raises; `Decimal("22.0")` passes,
because `Decimal.__eq__` compares numeric value and not exponent — so the guard has no false
positive on a legitimately-scaled value.

### F7 — three criteria assert payload fields this phase does not produce. `plans/plan_1.md:113`, `:115`, `:116`

- C11: *"returns `break_even = null` **and `is_fundable = false`**"*
- C13: *"`is_fundable false`, `break_even null`, `domain null`"*
- C20: *"`break_even null`, `domain null`"*

`is_fundable` is an `anchors` key (intention §8, `:1034`), derived per §8A as
`break_even_price_minor is not null`. `domain` is a payload block. Plan §5 (`:135-140`)
puts the serializer and the read model in phase 2, and §2 (`:25-34`) limits this phase to two
files with *"if a criterion appears to require a change outside these two files, that is a
STOP"*. None of the eight tasks in §3 produces either key.

The criteria are almost certainly meant as their pure equivalents
(`break_even_price_minor(...) is None`, `slider_domain(...) is None`) — but "almost
certainly" is the silent-improvisation this gate exists to remove, and an implementer taking
them literally hits §2's STOP on his first hour. Route: restate the three criteria in the
vocabulary of the functions §3 actually ships.

### F8 — `slider_domain`'s null-domain branch may not live in this phase at all. `plans/plan_1.md:80`, `intention.md:886`, `:851`

§7A.1 opens *"Let `B = break_even_price_minor` (integer ≥ 0, from §4.2A)"* — `B` is an
integer, not `int | None`. §7.3 states the rule *"`break_even_price_minor == null` ⇒
`domain: null`"* but assigns it to no function. Plan task 8 says `slider_domain(...)` returns
*"`None` when `min_minor >= max_minor`"* — the §7A.1 condition — and says nothing about a
null `B`.

So: if `slider_domain` takes `B: int`, §7.3's branch is the caller's, i.e. phase 2's, and
**C13 and C20's "domain null" cannot be asserted inside this phase's perimeter** — the two
criteria are unsatisfiable as scoped. If it takes `B: int | None` and returns `None` for
`None`, they are satisfiable and phase 2 inherits a total function. This is a real fork with
a phase-boundary consequence, not a style question. Route: plan task 8 decides; C13/C20
follow. (Related: L7/F7 — the same two criteria.)

### F9 — signatures are undetermined for half the module, and they are phase 2's interface. `plans/plan_1.md:61-80`

Task 3 writes the three M1 functions as `budget_minor(P)`, `allowed_centimin(P)`,
`allowance_seconds(P)` — one argument each. All three need `residual_percent_milli`,
`constant_deduction_minor` and `cost_per_worker_minute_ten_thousandths` as well. So the
notation implies either a parameter object, a closure factory, or four-argument functions,
and the plan does not say which. Tasks 4, 5 and 8 are written as `break_even_price_minor(...)`,
`infeasible_at_or_below_minor(...)`, `slider_domain(...)` — literal ellipses.

Two reasons this is more than housekeeping:

1. **The master plan's naming registry does not cover this phase.** §4 (`master_plan.md:60-66`)
   reserves five names — the query service, the route, the serializer, the band label and the
   typical-method label. Not the module, not one of the eight functions, not the parameter
   carrier. The registry's stated purpose is *"reserved before any code exists, so two
   sessions cannot pick two names for one thing"*, and phase 1 is the session that creates
   the things phase 2 consumes.
2. **Plan 2 never says it calls this module.** Plan 2 §3's eight tasks cover M3, M4, the
   status branch, `can_commit`, M6, the serializer and the route — none says "compute
   `model`/`anchors`/`domain` by calling `price_scenario.py`". Plan 2 §2 correctly forbids
   *changing* the module, which is not the same as specifying how it is consumed. Whatever
   phase 1 picks becomes the interface by default.

Route: this is a legitimate **free choice**, but it must be granted explicitly and then
written into the naming registry at phase 1's closeout, so plan 2's amendment has something
to cite. Recommended framing for the delegation: "the implementer chooses the parameter
carrier and the exact signatures; the coordinator registers them in master plan §4 at
closeout; plan 2 is amended to cite them."

### F10 — the deleted-term filter and the shape guard, with a concrete unflushed-ORM trap. `plans/plan_1.md:101`, `:104`

Two undetermined questions, one shared trap.

**Does `collapse_terms` filter `is_deleted`?** §3.1B (`intention.md:380-384`) says the term
set is `_load_preview_inputs`'s, and that loader already filters
(`_common.py:212`: `CostModelTerm.is_deleted.is_(False)`, ordered `created_at, client_id` at
`:213`). So the caller hands over non-deleted rows and a second filter is redundant — but C7
defines `n` as *"the count of **non-deleted** percentage terms"*, which reads as though the
function sees deleted ones. Either reading is defensible; only one gets written.

**The trap, whichever way it goes.** Probed at head `f1c0ebb`: an unflushed
`CostModelTerm(...)` carries `is_deleted = None`, not `False` — SQLAlchemy column defaults
apply at flush, and this phase's tests are unit tests with no session. So a filter written as
`if not term.is_deleted` works, `if term.is_deleted is False` silently drops every term in
every phase-1 test, and `if term.is_deleted is not True` works. The failure is silent and
lands on rule 3's own fixtures.

**Does `collapse_terms` validate term shape?** C4 claims *"the shape guard inside
`calculate_term_amount` is part of what is proven"*. That is true of **C7**, which runs the
real persisted path — it is not true of **C4**, which asserts `collapse_terms`' own output
pair and need never call the calculator. Whether `collapse_terms` rejects a percentage term
with a null `percent_value` (the `ck_cost_model_terms_value_by_type` CHECK guarantees this
for persisted rows, `cost_model_term.py:34`, but unpersisted fixtures bypass it) is
undetermined. Route: delegate both, with the `is_deleted = None` trap stated in the
implementer prompt; correct C4's parenthetical.

Verified while probing, so it is not re-spent: `calculate_term_amounts` reads only
`.calculation_type`, `.percent_value` and `.fixed_amount_minor` from a term. `CostModelTerm`
has no `amount_minor` attribute (that is `TermSnapshot`'s, used only by `rederive`), and an
unpersisted instance runs the real path correctly — **rule 3 is achievable in a unit test**.
Precedent for unpersisted ORM instances in a unit test exists at
`app/tests/unit/domain/item_economics/test_calculator.py:370` (`ItemCostEvaluationTerm`);
note that every `CostModelTerm(...)` construction in the repo today is under
`tests/integration/`, so this is the first unit-test use of that class.

### F11 — C12's degenerate value has no exact literal. `plans/plan_1.md:114`

C12: *"one degenerate model asserting the value is the **cap**, not `null`."* §4.2A defines
`infeasible_at_or_below_minor = (least P with allowance >= 1) − 1` and says that for a
degenerate model *"the value is then the `2**40` cap"* (`intention.md:568-570`). When the
search does not resolve there is no "least P" to subtract one from, so the published integer
is either `2**40` (= 1 099 511 627 776) or `2**40 − 1`, depending on whether the `− 1` of the
definition survives the cap branch. Charter rule 2 requires one exact expected outcome.
Confirmed reachable: with `residual_percent_milli = 0` the doubling exits past the cap.
Route: plan names the integer.

### F12 — task 4 does not carry §4.1's two null conditions. `plans/plan_1.md:69-71`, `:116`

Task 4 cites §4.2A only. §4.2A's contract block gives the doubling, the bisection and the
cap; it does **not** carry §4.1's rule that the break-even is `null` when
`residual_percent_milli <= 0` or when `typical_total_seconds == 0` (`intention.md:490-493`).

This is not cosmetic. With `T = 0` the §4.2A search returns **0**, not `null` — `P = 0` is
checked first and `allowance_seconds(0) = 0 >= 0` is true — so an implementer working from
task 4's citation alone ships a break-even of 0 for the no-evidence case. C20 catches it, but
only after the fact, and C20 is the criterion whose own vocabulary is in question (F7).
Route: task 4 cites §4.1's null conditions and states which function owns the branch.

(The degenerate case needs no special-casing to be correct — the doubling reaches the cap and
returns `null` either way, verified — so that half is a genuine free choice.)

### F13 — C14's double-rounding row has no fixture, and the natural ones do not bite. `plans/plan_1.md:122`

C14 wants *"a row where pre-rounding to an integer and then stepping gives a different answer
than stepping the rational"*. The obvious fixture — the mockup's own `raw_low = 423 967.25`
with `step = 15 000` — gives **the same answer both ways** (floor 420 000, ceil 435 000).
So does `14 999.5` at step 10 000. An implementer picking a natural value writes a row that
passes under the very implementation the criterion forbids: decoration with a correct name.

The difference only appears when the rational sits within `1/2` **below** a multiple of the
step, so that rounding to nearest crosses the step boundary — e.g. `v = 29 999.6`,
`s = 30 000`: stepping the rational floors to 0, pre-rounding gives 30 000 and floors to
30 000. Route: C14 states that property (or names the fixture) so the row is red against
double-rounding by construction.

### F14 — C21's purity assertion has no mechanism and an undetermined forbidden set. `plans/plan_1.md:133`

C21: *"`price_scenario.py` imports no session, no ORM query construct and no service module.
Asserted structurally (an import-set assertion in the test file), not by inspection — the
same discipline as the docs-accuracy guard."*

Two gaps.

- **No mechanism and no precedent.** The docs-accuracy guard does exist
  (`app/tests/unit/docs/test_item_economics_docs.py`) but it is a verbatim string-containment
  check on markdown; it supplies the *discipline* ("a rule nobody can run is a rule nobody
  keeps"), not a technique to copy. A search of `app/tests/unit/` finds no `ast.parse`, no
  `importlib` spec walk and no `sys.modules` assertion anywhere. The implementer must invent
  the mechanism, and the choices differ in what they can catch: an AST walk of the source
  sees only direct imports; a `sys.modules` probe sees transitive ones.
- **The forbidden set is undetermined, and the two readings disagree.** If the assertion is
  transitive, then importing `CostModelTerm` for a type hint fails it — `beyo_manager.models…`
  pulls in SQLAlchemy. If it is direct-only, the module may import the ORM class freely. That
  in turn decides whether the module is duck-typed against a `Protocol` (the idiom
  `calculator.py:67-72` already uses for `TermSnapshot`) or typed against the ORM class.

Route: plan fixes the forbidden set and states direct-vs-transitive; the mechanism itself is
a fair delegation once the set is fixed.

### F15 — C3's tie-free assertion has no exact expected outcome. `plans/plan_1.md:95`

C3's third row: *"one asserting the seconds conversion is **tie-free** across an enumerated
`cm` range, so a later change to that operation's rounding mode is provably inert."* No range
is given, and "is tie-free" is a property, not a value. Confirmed true and confirmed
observable: `round_half_even(cm×3, 5)` has remainder `3cm mod 5 ∈ {0,1,2,3,4}`, and a tie
needs `2r = 5`, unreachable over integers. The assertable form is that the operation returns
the same value under a half-up reference across the range — which makes "a later rounding-mode
change is inert" a fact the test states rather than a comment. Route: C3 names the range and
the observable form.

The other two rows of C3 are decidable and were verified: `residual = 50 000` with odd `P`
reaches a tie in the first operation; `rate_tt = 2 000 000` (a legal rate — 200.0000, well
inside `Numeric(12,4)` and `CHECK > 0`) with odd budget reaches one in the second.

### F16 — C15 asserts an internal helper. `plans/plan_1.md:123`

C15 requires a row for `digits(0) = 1`. `digits` appears only inside §7A.1's pseudocode
(`intention.md:909`); nothing says it is a function `price_scenario.py` exposes. Observably,
`two_significant_digits(0, b)` returns `1` via the `max(1, …)` floor, which is the same
number for a different reason — so a row named `digits(0) = 1` may pass while `digits` does
not exist. Route: delegate (expose `digits`, or restate the row against
`two_significant_digits`).

The rest of C15 is decidable and was verified: `two_significant_digits` over 1/2/3/4 integer
digits gives `7 → 7`, `42 → 42`, `423 → 420`, `4237 → 4200`; and the prompt's question about
`b > a` **is** determined — `two_significant_digits(3, 7)` = 1 by the floor, no gap there.

---

## Reality checks

| Check | Result |
|---|---|
| `app/beyo_manager/domain/item_economics/price_scenario.py` | does not exist; correctly marked **new** (plan §2) |
| `app/tests/unit/domain/item_economics/test_price_scenario.py` | does not exist; correctly marked **new**; parent directory exists |
| `domain/item_economics/` is the right home for a pure module | confirmed — `budget_division.py` and `calculator.py` are pure and sit there; HC-2 amendment's rationale (plan §2:36-51) holds |
| Every intention section plan 1 cites resolves and says what the plan claims | yes for §3.1, §3.1A, §3.1B, §3.2, §3.2A, §3.5, §4.1, §4.2, §4.2A, §4.4, §4.4A, §5.3, §7A.1, §7A.2, §12, §12A — with the two mutation defects above (F1, F2), which are faithful transcriptions of upstream errors, not plan drift |
| §9.1's superseded banner read | yes (`intention.md:1125-1130`); §9A.1's table governs; nothing in phase 1 depends on either |
| `calculate_term_amount` / `calculate_term_amounts` / `calculate_production_budget` / `calculate_allowed_worker_minutes` | read at `calculator.py:178-210`, `:213-242`, `:245-258`, `:285-299` — §2A's corrected ranges are accurate |
| `_budget_seconds`, `_median`, the constants | `budget_division.py:64-66`, `:69-74`, `:15-18` — §2A accurate |
| Storage precisions | `cost_model_term.py:23` `Numeric(6,3)` ✓; `production_cost_basis_version.py:27` `Numeric(12,4)` ✓ |
| §2A.1.3's citation for the rate's `CHECK > 0` | **wrong** — `production_cost_basis_version.py:40` is `planning_utilization_percent > 0`; the rate's check is `:38`. The claim itself is true. See L17 |
| House unit-test idiom | `test_calculator.py` — `SimpleNamespace` factory at `:39-51` for duck-typed terms, real unpersisted ORM instances at `:370`. Both idioms available; rule 3 forces the second for C4/C7 |
| The 21 criteria are all present | yes — C1–C21, though C20 is printed out of order inside the search block (`plan_1.md:116`). Cosmetic; noted so a later count is not alarmed |

## Write perimeter

Generated from `git status --porcelain --untracked-files=all`, run at the repository root
(`backend/`), 2026-08-19.

**This project folder is entirely untracked**, so `git diff` is empty by construction and
cannot serve as the perimeter — the enumeration below comes from the untracked listing,
cross-checked against mtimes.

Written by this session — **one file**:

```
docs/architecture/under_construction/implementation/simple_valuation_editor/
    handoffs/reviewer/2026-08-19_phase1_projection_r0_handoff.md
```

Not written by this session: the other **seventeen** untracked entries under the project
folder — `master_plan.md`, `planning/intention.md`, `planning/owner_decisions.md`,
`plans/plan_1.md`, `plans/plan_2.md`,
`prompts/reviewer/2026-08-19_phase1_projection_r0.md`, the three
`archive/gate_inventory/` documents, and eight `.gitkeep` files. Confirmed unchanged by
mtime: the newest of the seventeen is the projection prompt at **15:41:42**, and this
handoff is **16:02:54** — every other entry predates the session's first write.

Totals for the check: 18 untracked entries, of which 1 is this handoff; **0 tracked
modifications anywhere in the repository**.

- **No code file was created, edited or deleted.** `git status` reports no tracked
  modification anywhere in the repository.
- **No architecture-graph delta.** `.archgraph/` exists at the repository root; a projection
  writes no code, so there is nothing to record and no `archgraph_*` write was made.
- **No test was run and no database was touched** (permitted-not-required per prompt §6;
  nothing in this phase needs either).
- **Outside the repository**, discarded with the session: two throwaway verification scripts
  under the session scratchpad (`verify.py`, `verify2.py`). They reimplement the contract's
  arithmetic to check the plan's literals and mutations; they are evidence, not artifacts,
  and no part of them is offered to the implementer.

## Verdict

**AMENDMENTS_REQUIRED.** Seventeen ledger rows: three upstream corrections to the intention
(F1's §12A.3, F2's §12A.9, F3's §4.2A/§8, plus L17's line citation), eleven plan amendments,
and four delegations to record in writing. No owner decision. No ratified decision moves and
no mechanism is reopened.

The design survives the projection — the M1 three-line form is faithful to the shipped
calculator, the break-even literal and the band's three literals are exact, and the bound
holds on every enumerated shape. What did not survive is the *evidence* for three of the
criteria: C7's, C17's and C10's named mutations were each proved unable to fail, which is the
same failure mode the mechanism-inventory gate recorded one level up — the claims the
document nominated as strongest were fine, and the defects were in the checks nobody
suspected.
