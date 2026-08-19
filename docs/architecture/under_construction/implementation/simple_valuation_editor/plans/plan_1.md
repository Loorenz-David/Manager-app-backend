# Plan 1 — the pure price mechanisms

```
plan: 1
state: PROMPT_READY
date: 2026-08-19
gate: projection r0 COMPLETE — AMENDMENTS_REQUIRED, all 17 ledger rows routed
```

## 1. Goal

Ship the arithmetic, alone, with no I/O and no route. Every number this feature publishes
is produced here: the rounding primitive, the collapsed affine form, the break-even search,
the infeasibility boundary, the step helpers and the slider band.

**Why this is its own phase.** The whole feature is rule-6 surface, and all of it is
provable without a database. Splitting the arithmetic out means phase 1 is verified by fast
unit tests against real ORM instances, and phase 2's review never has to re-derive a number
— it only has to prove the wiring. It also makes the perimeter check meaningful: a phase
boundary that runs between two modules is checkable by `git diff`, one that runs between
two functions in one file is not.

## 2. Files

**New, and the only files this phase may create or change:**

| Path | Contents |
|---|---|
| `app/beyo_manager/domain/item_economics/price_scenario.py` | every mechanism below; pure, no session, no I/O, no ORM query |
| `app/tests/unit/domain/item_economics/test_price_scenario.py` | the criteria below |

Nothing else. Not `budget_division.py`, not `calculator.py`, not any router, not any
service. **If a criterion appears to require a change outside these two files, that is a
STOP and a report, not a judgement call.**

### HC-2 amendment (coordinator, 2026-08-19) — read this before starting

Intention HC-2 enumerates "one new query service, one new serializer, one new route". It
does not name a pure domain module, because the intention was written before the work was
decomposed. **A fourth artifact is authorized: one new pure module under
`domain/item_economics/`.**

Rationale, so this is a recorded extension and not drift: HC-2's binding clause is *"no
change to any existing endpoint's payload … deleting this feature must leave zero
residue"*, and a new pure module satisfies both — it is deleted by deleting the file. The
alternative, putting the arithmetic inside the query service, would put pure functions in
an I/O module against the pattern `budget_division.py` and `calculator.py` already
establish, and would make this phase boundary unverifiable. Same precedent and same
rationale as `simple_production_budget_division`'s HC-1a (3 → 4 artifacts under the
existing authorization, no new owner card, because the extension is entailed by the
decision rather than being a separate one).

**No migration, no schema change, no `CALCULATION_VERSION` bump** (HC-1, HC-3).

## 3. Tasks

Each cites the contract that governs it. **Where this plan and the intention differ, the
intention wins** — these are pointers, not restatements.

1. `round_half_even(a, b)` — the reference algorithm of §3.1A verbatim: floor semantics,
   then the tie test. `a` any sign, `b > 0`. Not `round()`, not `Decimal.quantize`.
2. `collapse_terms(terms, purchase_cost_minor)` → `(residual_percent_milli,
   constant_deduction_minor)` per §3.1 and §3.1B. Takes the real term objects.
   **Two outcomes are specified, and they are different kinds of thing** (projection L5/L6):
   - **A purchase term exists and `purchase_cost_minor` is `None` → return `None`.** This is
     a *data state*, not an error: phase 2 branches on it to produce status
     `item_missing_purchase_cost` and a `null` model block (§3.1B). Return type is
     therefore `tuple[int, int] | None`.
   - **A `percent_value` whose scale exceeds 3 → raise
     `ValidationError("ITEM_COST_TERM_SHAPE_INVALID: …")`.** This is a *shape* error and
     must be distinguishable from the case above, or phase 2 turns bad data into a 500
     instead of a status. **The identity token is reused, not minted** — it already exists
     at `calculator.py:127`, `:240` and `create_cost_model_version.py:29-34`, and minting a
     new one would require editing the registered-identity set in
     `tests/unit/docs/`, which is outside this phase's two-file perimeter.
3. `budget_minor(P)`, `allowed_centimin(P)`, `allowance_seconds(P)` — §3.1's three lines,
   in that order. The seconds conversion is the **two-step** form; the shortcut from budget
   to seconds is the defect criterion C8 exists to catch.
4. `break_even_price_minor(...)` — the lower-bound bisection of §4.2A on the non-decreasing
   predicate, with `P_hi` obtained by **doubling from 1**, capped at `2**40`. `P = 0`
   checked first. Never reads a band value: the dependency runs M2 → M5 and never back.

   **§4.1's two null conditions are checked *before* the search and belong to this
   function** (projection L12): `residual_percent_milli <= 0 → None`, and
   `typical_total_seconds == 0 → None`. §4.2A's contract block carries the doubling, the
   bisection and the cap but **not** these two, and the second one is not cosmetic — with
   `T = 0` the search returns **0**, because `P = 0` is checked first and
   `allowance_seconds(0) = 0 >= 0` holds. An implementer working from §4.2A alone ships a
   break-even of `0` for D7's no-evidence case. (The degenerate case needs no special-casing
   to be *correct* — the doubling reaches the cap and returns `None` either way — but the
   early return is cheaper and is what this task specifies.)
5. `infeasible_at_or_below_minor(...)` — §4.2A: the same search against a target of `1`
   second, minus one. **Never `None`.** When the search reaches the cap the published value
   is **exactly `2**40`** (projection L11), not `2**40 − 1`: there is no "least `P`" to
   subtract from, and `2**40` is the honest reading of "every price up to the cap is
   infeasible".
   **Note the corrected §4.2A**: there is **no shortcut for a purely proportional model**.
   The old "purely proportional ⇒ 0" claim was false — for the mockup's own configuration
   the value is **29**. Always run the search.
6. `floor_to_step` / `ceil_to_step` — §4.4A, over exact rationals where the input is one.
   Never pre-round to an integer and then step.
7. `two_significant_digits(a, b)` — §7A.1, integer-only, floored at 1.
8. `slider_domain(...)` — §7A.1: exact rationals throughout, the step derived **per piece**
   and multiplied back, `min_minor` floored above infeasibility and on-grid, `None` when
   `min_minor >= max_minor`.

   **`B` is `int | None`, and this function returns `None` for a `None` `B`** (projection
   L8). §7A.1 opens by typing `B` as an integer and §7.3 states the null-domain rule without
   assigning it to any function; left unresolved, §7.3's branch would fall to phase 2 and
   C13/C20 would be unsatisfiable inside this perimeter. Deciding it here makes the function
   total and gives phase 2 one call instead of a call plus a guard.

### Delegations — granted explicitly, not taken silently

Four decisions are the implementer's. They are recorded here so the freedom is granted on
purpose (projection L9, L10, L14, L16).

- **D-1 — signatures and the parameter carrier.** Task 3 writes `budget_minor(P)` with one
  argument, but the three M1 functions also need `residual_percent_milli`,
  `constant_deduction_minor` and `cost_per_worker_minute_ten_thousandths`. Parameter object,
  closure factory or explicit arguments is the implementer's call — **but this is phase 2's
  interface**, and master plan §4's registry does not cover this module. **Report the chosen
  module name, every public function name and the parameter carrier in the handoff**; the
  coordinator registers them at closeout and amends plan 2 to cite them.
- **D-2 — the `is_deleted` filter in `collapse_terms`.** `_load_preview_inputs` already
  filters (`_common.py:212`), so a second filter is redundant but harmless. Either is
  acceptable. **The trap is not**: an unflushed `CostModelTerm(...)` carries
  `is_deleted = None`, not `False` — SQLAlchemy applies column defaults at flush and this
  phase's tests have no session. Empirically confirmed at head `f1c0ebb`. So
  `if not term.is_deleted` works, `if term.is_deleted is not True` works, and
  **`if term.is_deleted is False` silently drops every term in every phase-1 test**. The
  failure is silent and lands on C4's and C7's own fixtures.
- **D-3 — term-shape validation beyond C5.** Whether `collapse_terms` also rejects a
  percentage term with a `None` `percent_value` is the implementer's call. Persisted rows
  cannot be in that state (`ck_cost_model_terms_value_by_type`, `cost_model_term.py:34`) but
  unpersisted fixtures bypass the CHECK.
- **D-4 — `digits` exposure.** C15 asserts `digits(0) = 1`, a helper that exists only inside
  §7A.1's pseudocode. Expose it and assert it directly, or assert the same behaviour through
  `two_significant_digits` — but **not the second one silently**:
  `two_significant_digits(0, b)` returns `1` via the `max(1, …)` floor, which is the right
  number for a different reason, so a row named after `digits` could pass while `digits`
  does not exist. Say in the handoff which you did.

## 4. Acceptance criteria

Charter rule 1: every criterion is met by an automated test. Rule 2: one row per case, and
**each row's fixture makes its own predicate the only reason its outcome holds**. Rule 3:
the term-consuming criteria hold real `CostModelTerm` ORM instances, never dicts. Rule 11:
each named mutation names its **site** — definition or call.

### `round_half_even` (§3.1A)

| C | Criterion |
|---|---|
| C1 | Positive operands, one row each: `(3,2)→2`, `(5,2)→2`, `(7,2)→4`, `(1,2)→0`. Both tie directions present, so a half-up implementation fails and a half-down one fails too. |
| C2 | **Negative operands**, one row each: `(−3,2)→−2`, `(−5,2)→−2`, `(−1,2)→0`, `(−7,2)→−4`. **Named mutation: replace `floor` with truncation in the helper's *definition* → C2 red, C1 green.** This is the split that matters: `a < 0` is reachable at every price below the constant deduction, i.e. the `infeasible` state the screen exists to show. |
| C3 | **Tie reachability, per operation** (§3.1A's table). One row reaching a tie in `round_half_even(P × residual, 100_000)` (`residual = 50_000`, odd `P`); one in the rate division (`rate_tt = 2_000_000` — a legal rate, 200.0000, inside `Numeric(12,4)` and `CHECK > 0` — with odd budget). **Third row restated** (projection L15/F15): "is tie-free" is a property, not a value, and no range was given. The observable form: **over `cm ∈ [0, 1000]`, `round_half_even(cm × 3, 5)` equals a half-**up** reference implementation on every value** — which makes "a later rounding-mode change to this operation is inert" a fact the test states rather than a comment in the margin. |

### The collapsed form and its inputs (§3.1, §3.1B)

| C | Criterion |
|---|---|
| C4 | `collapse_terms` over the seven model shapes of §12.1 — one percentage; two distinct; **two equal**; percentage + fixed; percentage + purchase; percentages summing to exactly 100; summing above 100 — each asserting its exact `(residual_percent_milli, constant_deduction_minor)` pair. **Real ORM instances** (rule 3). *Corrected*: the parenthetical claiming "the shape guard inside `calculate_term_amount` is part of what is proven" is true of **C7**, which runs the real persisted path — not of C4, which need never call the calculator. Rule 3 still binds: real `CostModelTerm` instances, because the ORM is what production hands this function. |
| C5 | A `percent_value` carrying scale > 3 raises **`ValidationError` whose message begins `ITEM_COST_TERM_SHAPE_INVALID:`** (task 2). Asserted as the exception class **and** the identity token, not a truthy check. A companion row proves no false positive: `Decimal("22.0")` is accepted, because `Decimal.__eq__` compares numeric value and not exponent. |
| C6 | Purchase-term handling, two rows, each violating only its own predicate: purchase term present + `purchase_cost_minor is None` → **returns `None`** (task 2 — the exact outcome, not "the no-model signal"); purchase cost present + **no** purchase term → the cost is **ignored** and the residual is unchanged (matching `calculate_term_amounts`). A third row separates the two failure kinds: a shape error **raises** where a missing purchase cost **returns `None`**, so phase 2 can tell a status from a 500. |
| C7 | **The `(n+1)/2` bound** (§3.2A) asserted in integers as `2*abs(delta) <= n + 1` against the real `calculate_term_amounts` / `calculate_production_budget` path, over all seven shapes of C4. `n` is the count of **non-deleted percentage terms**. **Two named mutations, replacing the inert one** (projection F1, §12A.3 corrected upstream): **(a) weaken `n+1` to `n` in the assertion helper's definition → the `percentage + fixed` row red at `P = 25`, where the bound is attained** (`round_he(0.78×25)=20`, `round_he(0.22×25)=6`, `Δ=1`, `2|Δ|=2=n+1`) — this is what proves the criterion is not vacuous and is the only thing pinning §3.2A's "attained" claim; **(b) in `collapse_terms`' definition, derive `residual_percent_milli` by float multiply (`int(float(percent_value) * 1000)`) instead of `int(value.scaleb(3))` → `Δ` leaves the bound.** The old mutation (`n → len(terms)`) is **forbidden**: it only enlarges the right-hand side of a `<=`, and on the shape it named the two counts are equal. |
| C8 | **The two-step seconds conversion.** A row where the shortcut (budget → seconds directly) and the contract (budget → 2dp minutes → seconds) disagree, asserting the contract's value — **`budget = 7` is such a row** (two-step 1 s, shortcut 0 s). **Named mutation: replace the two-step conversion with the shortcut at its definition site in `price_scenario.py` → this row red.** |

### The search (§4.2A)

| C | Criterion |
|---|---|
| C9 | **Break-even minimality, both halves**: `allowance_seconds(B) >= T` **and** `allowance_seconds(B − 1) < T`. Plus a row on the mockup's data asserting the exact literal **`1_211_335`** — a row that fails against §4.4's superseded `1_211_364`, and is the regression guard for the defect the inventory gate found. |
| C10 | **`P_hi` independence, restated as an exact literal** (projection F4). The old form asked for a mutation "seeding `P_hi` from `domain.max_minor`" — but §4.2's superseded wording is a *circular definition*, not a rival implementation, so there was no code to mutate and the row asserted only "the search returns something". New form: `residual_percent_milli = 1`, `rate_tt = 13_000_000`, `K = 0`, `typical_total_seconds = 12_300` → **`break_even_price_minor == 26_649_350_000`** (verified: allowance 12 300 s there, 12 299 s at `P−1`). That is ≈ 2³⁴·⁶, far above anything a band could seed. **Named mutation: cap `P_hi` at any constant below 2³⁴ in the search's definition → this row red** (it returns `None`). |
| C11 | A model whose search reaches the `2**40` cap returns **`break_even_price_minor(...) is None`** — asserted as absence, never as zero. *(Restated in this phase's vocabulary: `is_fundable` is an `anchors` payload key derived in phase 2, and no phase-1 task produces it — projection F7.)* |
| C12 | **`infeasible_at_or_below_minor`**: one row with `constant_deduction_minor > 0` asserting the exact boundary and that `min_minor` sits above it — **`K = 150_000` is such a fixture** (break-even 1 893 153, infeasibility floor 702 000, which beats the `raw_low` floor of 655 200); one degenerate model asserting the value is exactly **`2**40`** (task 5 — the exact integer, not "the cap"); and one purely-proportional row on the mockup's own configuration asserting **`29`**, which is the value the superseded §4.2A claimed was `0`. |
| C13 | **Degenerate model** (`residual_percent_milli <= 0`, §3.5): `break_even_price_minor(...) is None` **and** `slider_domain(...) is None` — both asserted as absence. *(Restated per F7/F8: the pure functions, not the payload keys; `slider_domain` accepts `B = None` per task 8, which is what makes the second half testable inside this perimeter at all.)* |
| C20 | `typical_total_seconds == 0` (D7's no-evidence case, §5.3) → `break_even_price_minor(...) is None` and `slider_domain(...) is None`. **This is the row that catches the §4.1/§4.2A gap** (task 4): a search that omits the `T == 0` early return returns **0**, not `None`, because `P = 0` is checked first and `allowance_seconds(0) >= 0` holds. |

### The band (§7A.1)

| C | Criterion |
|---|---|
| C14 | `floor_to_step` / `ceil_to_step` over an **exact rational** input, including a row where pre-rounding to an integer and then stepping differs from stepping the rational. **The fixture's required property is stated, because the natural candidates do not exhibit it** (projection F13): the mockup's own `raw_low = 423_967.25` at step `15_000` gives the same answer both ways, so a row built from it passes under the very implementation the criterion forbids. The difference appears only when the rational sits within `1/2` **below** a multiple of the step — e.g. `v = 29_999.6`, `s = 30_000`: stepping the rational floors to `0`, pre-rounding gives `30_000` and floors to `30_000`. |
| C15 | `two_significant_digits`, enumerated: 1, 2, 3 and 4 integer digits — `7 → 7`, `42 → 42`, `423 → 420`, `4237 → 4200`; a row where the raw value is below 1 (`a < b`), asserting the floor at 1; and the `digits(0)` row per delegation **D-4**, which says explicitly which form was used. |
| C16 | **The mockup's band, exactly**: `step_minor == 15_000`, `min_minor == 420_000`, `max_minor == 1_650_000` for `B = 1_211_335`, `Q = 6`. Note `max_minor` is `1_650_000` per D10 — a row asserting `1_635_000` is asserting the superseded value. |
| C17 | **The band at `Q = 7`, as exact literals**: `step_minor == 15_400`, `min_minor == 415_800`, `max_minor == 1_647_800`. **Named mutation: derive the whole-item step first and snap it up to a multiple of `Q` (the superseded §7.2 order) at the definition site → all three red** (the mutation gives `15_001 / 420_028 / 1_650_110`). **The old form was inert** (projection F2, §12A.9 corrected upstream): it asserted `step_minor % 7 == 0`, and snapping *up to a multiple of `Q`* makes that true by construction — `15_001 = 7 × 2_143` passes. Keep `step_minor % Q == 0` and the multiple-of-step assertions as by-construction invariants, but they are **not** the mutation's target. At `Q = 6` the two orders are identical, which is why the criterion needs a second quantity at all. |
| C18 | `min_minor` is both **above** `infeasible_at_or_below_minor` and **on-grid** (a multiple of `step_minor`) — one fixture where the two constraints disagree and the contract's `max(...)` of the two ceiled values is what resolves it. |
| C19 | `min_minor >= max_minor` → `domain is None`, asserted as absence. |

### Purity

| C | Criterion |
|---|---|
| C21 | **Purity, with the forbidden set fixed and the scope named** (projection F14). The assertion is **direct-import only** — the module's own `import` statements, not the transitive closure — and the forbidden prefixes are exactly **`sqlalchemy`, `beyo_manager.models`, `beyo_manager.services`**. Consequence, and the reason the scope had to be decided rather than left open: a transitive reading would fail on importing `CostModelTerm` for a type hint, since the models package pulls in SQLAlchemy. So **the module duck-types its term inputs against a `Protocol`**, the idiom `calculator.py:67-72` already uses for `TermSnapshot`, rather than typing against the ORM class. The *mechanism* (AST walk, source scan, or otherwise) is the implementer's choice — there is no precedent in `tests/unit/` to copy — but the set and the scope are not. |

## 5. Out of scope — this is phase 2

No query service, no serializer, no route, no route-mirror artifact, no role test, no
`config_fingerprint`, no `can_commit`, no typical statement, no byline, no status table.
**M3, M4, M6 and the twelve-row status table are phase 2 and touching them here is a scope
breach**, however small the edit looks.

## 6. Review log

**projection r0 — 2026-08-19, Opus 5 — `AMENDMENTS_REQUIRED`, 0 owner cards, 17 ledger rows,
all routed by the coordinator before the implement prompt compiled.**

Four rows went **upstream** to the intention (§12A.3's inert mutation, §12A.9's inert
mutation and false rationale, §4.2A's false "purely proportional ⇒ 0" plus §8/§8A.1,
§2A.1.3's line citation). Eleven became **plan amendments** — C3, C4, C5, C6, C7, C10, C11,
C12, C13, C14, C15, C17, C20, C21 and tasks 2, 4, 5, 8. Four became **written delegations**
(D-1 … D-4 in §3).

**The finding that mattered: three named mutations could not fail.** C7's, C17's and C10's
were each proved inert — C7's by a sweep of all seven model shapes over `P ∈ [0, 40 000)`,
C17's by computing both derivation orders at `Q = 6` and `Q = 7`, C10's by observing that
the thing it mutates is a circular definition and therefore not implementable. Charter rule
11: *a safety test that survives the defect it exists to prevent is decoration.*

**The design survived intact.** The M1 three-line form is exactly faithful to
`calculate_allowed_worker_minutes` + `_budget_seconds`; the break-even literal `1 211 335`
and the band literals `15 000 / 420 000 / 1 650 000` are exact; the `(n+1)/2` bound holds on
every enumerated shape. What failed was the evidence, not the mechanism — the same shape as
the mechanism-inventory gate one level up.

Coordinator verification before folding (nothing accepted on the handoff's word): the
`infeasible = 29` computation re-derived; the `P = 25` bound attainment recomputed by hand;
both band derivation orders recomputed at `Q = 7`; C10's `26 649 350 000` re-derived; the
`is_deleted = None` trap **confirmed empirically** on an unflushed `CostModelTerm` at head
`f1c0ebb`; the `:38` vs `:40` CHECK citation read at the line.
