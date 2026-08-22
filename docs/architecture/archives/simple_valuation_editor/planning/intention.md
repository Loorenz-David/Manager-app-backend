# Intention: Simple Valuation Editor (price-scenario read surface for the expected-sold-price screen)

```
status: RESOLVED and PLAN-READY (round 4, 2026-08-19). Mechanism-inventory gate
        **PASSED** — all eight mechanisms contract-grade, ledger empty
        (D1–D3 shaping, D4–D7 round 2, D8–D10 round 4; §13.1–§13.3).
        Next: implementation-planner.
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-19 (no raw_intention.md; the conversation
             followed three frontend mockups of the "Expected sold price" screen —
             two rich variants, then the simplified variant the team settled on)
date: 2026-08-19
round: 4
```

---

## 1. Objective & hard constraints

**One read-only endpoint** that hands the frontend the closed set of constants the
"Expected sold price" screen needs, so the screen can project the consequences of a
price live — at every frame of a slider drag — without a network round trip.

The screen answers one question: *"if I ask this much for the item, how much work time
does that buy, and is it enough?"* Everything on it is a deterministic function of one
variable, the expected sale price. The backend already owns that function as a **pure,
no-I/O domain** (`domain-item-economics` in the architecture graph;
`app/beyo_manager/domain/item_economics/calculator.py`). This pipeline exposes the
function's *inputs* as a payload instead of exposing one evaluated output at a time.

The simplified screen (owner + team, 2026-08-19) renders exactly seven things:

| element | source |
|---|---|
| `1 425 SEK` per piece | draft price ÷ `quantity`, frontend-side |
| `× 6 pieces · 8 550 SEK total` | `quantity`, draft price |
| `AT PRICE 2h 25m` | M1 — price → allowance seconds |
| `TYPICAL 3h 25m` | M3 — one constant |
| chip `Below typical work` | draft price vs M2 break-even |
| `suggested 2 025/piece` | M2 |
| slider ends `700` / `2 700` | M5 |
| `Marta Lind · saved version · 14 Aug, 10:24` | M4 |

**Hard constraints:**

- **HC-1 — Read-only, derive-on-read.** No new tables, no migration, no persisted
  derived value, no worker, no event. Consequence: `CALCULATION_VERSION`
  (`calculator.py:20`) is **not** bumped — its contract covers persisted formula
  outputs (§6A.10) and this feature persists nothing. Same reasoning as
  `simple_production_budget_division` HC-2.
- **HC-2 — Additive only.** One new query service, one new serializer, one new route.
  No change to any existing endpoint's payload, to `set_item_valuation`,
  `commit_item_cost_evaluation`, `get_task_budget_status`, `divide_production_budget`,
  or to any published contract in `Application_contracts`. Deleting this feature must
  leave zero residue.
  **HC-2a — enumerated exception.** Mounting a new item-economics route trips the v1
  route-mirror tripwires by design. Exactly **four** artifacts change, by addition
  only, each reverted by one edit:
  1. `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` —
     `_EXPECTED_ROUTES` (+1 row, `:33`) and both count assertions **25 → 26**
     (`:126`, `:127`);
  2. `app/beyo_manager/routers/README.md` — one Quick Index row (the block at
     `:58-82`) and one detail section;
  3. `app/tests/unit/routers/api_v1/test_item_economics_router.py` — `_ROUTES`
     (`:14`), and **not** `_ALL_ROLE_ROUTES` (`:48`), because this route is
     manager-gated (HC-3);
  4. the router module `app/beyo_manager/routers/api_v1/item_economics.py`.
  No other v1 artifact may change.
- **HC-3 — Money audience.** The payload is dense with monetary figures. ADMIN and
  MANAGER only, per the standing decision `decision-money-audience-admin-manager-only`
  (a withheld monetary key is ABSENT, never null). WORKER and SELLER are not routed
  here at all; there is no redacted variant of this endpoint in v1.
- **HC-4 — The wire unit is whole-item minor units.** `expected_sale_price_minor` is
  per item, never per piece; the backend never multiplies by `quantity` and never
  divides by it. `quantity` travels in the payload solely as the frontend's display
  divisor (owner-settled, D1). This preserves the rule stated in
  `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
  §8.4 — only that section's *display prohibition* is amended at closeout, not its
  contract.
- **HC-5 — This is a declared display model, not an authority.** The arithmetic this
  endpoint publishes is a bounded approximation of the persisted formula (M1), it is
  labelled as such in the payload, and it never feeds a persisted value.
  `commit_item_cost_evaluation` remains the sole producer of
  `production_budget_minor` / `allowed_worker_minutes`. A screen driven by this
  endpoint must therefore reconcile against the commit response before believing its
  own numbers (§9.3).
- **HC-6 — Swappability is contract-level.** The response names its derivation
  (`calculation_version`, `model` labels, `typical.method`, `domain.rule`) so a future
  refinement changes a labelled value, never the payload shape — same hook as
  `simple_production_budget_division` HC-5.

---

## 2. Grounding — what exists today (verified 2026-08-19, all paths read this session)

### 2.1 The price → budget formula

`app/beyo_manager/domain/item_economics/calculator.py` owns it, pure, no I/O:

- `calculate_term_amount` (`:169-207`) — one snapshot term amount. Three calculation
  types (`domain/item_economics/enums.py:4-7`): `percentage_of_expected_sale_price`,
  `fixed_amount`, `item_purchase_cost`.
- `calculate_percentage_term_amount` (`:154-166`) —
  `round_half_even(price_minor × percent / 100)` at `prec=50`, quantized to integer
  minor units. **Each percentage term is rounded individually, before summing.**
- `calculate_production_budget` (`:225-239`) — `price − Σ term_amounts`.
- `calculate_allowed_worker_minutes` (`:266-280`) — `budget / rate`, quantized to
  `0.01` HALF_EVEN, refusing a zero rate.
- `_budget_seconds` (`budget_division.py:62-64`) —
  `int((allowed_worker_minutes × 60).quantize(1, HALF_EVEN))`. **Two-step rounding:**
  minutes are quantized to 2dp first, *then* multiplied by 60.

Storage precisions that bound the arithmetic exactly:
`cost_model_terms.percent_value` is `Numeric(6,3)`
(`models/tables/item_economics/cost_model_term.py:23`);
`production_cost_basis_versions.cost_per_worker_minute_minor` is `Numeric(12,4)`
(`models/tables/item_economics/production_cost_basis_version.py:27`).

### 2.2 The rate has two derivation paths that agree today

`create_production_cost_basis_version` (`:27-31`) derives the persisted
`cost_per_worker_minute_minor` through `calculate_cost_per_worker_minute`.
`set_item_valuation._preview` (`:48`) divides by that **persisted column**, while
`commit_item_cost_evaluation` (`:260-264`) **recomputes** the rate from
`fixed_monthly_cost_minor / monthly_paid_hours / planning_utilization_percent`. Both
routes end in the same function with the same 4dp HALF_EVEN quantization, so they
agree by construction — but they are two code paths, and this endpoint must declare
which one it publishes (M1, R3).

### 2.3 Configuration selection and readiness

`resolve_economics_selection` (`domain/item_economics/configuration.py:80-126`) picks
the item's cost group by major category, then the applicable basis version and cost
model version by date. `resolve_item_economics_status` (`:129-169`) resolves the
twelve-value `EconomicsStatusEnum` (`enums.py:16-28`) by explicit precedence.
`_load_preview_inputs` (`services/commands/item_economics/_common.py:186-219`) is the
existing loader for the whole live configuration set — this endpoint reuses it rather
than issuing its own selects.

### 2.4 The typical time source

`typical_times_statement` (`services/queries/working_sections/get_working_section_typical_times.py:22-64`)
is the shared grouped-median statement: `(task, section)` group totals over
`completed`, non-deleted, not-marked-wrong steps; window 90 days on the group's latest
close; `NULL` below 5 qualifying groups; constants
`TYPICAL_WINDOW_DAYS / TYPICAL_MIN_SAMPLE_SIZE / TYPICAL_METHOD`
(`budget_division.py:14-17`). Its contract is `simple_production_budget_division` §3
(M1) and it is not re-derived here.

`divide_production_budget` (`budget_division.py:245-401`) substitutes the **median of
the usable typicals** for any section whose typical is `NULL`, falling back to weight
`1` when none are usable (`:355-370`). That substitution rule is what M3 must mirror.

### 2.5 The task and its live state

`get_task_budget_status` (`services/queries/item_economics/get_task_budget_status.py`)
resolves task → PRIMARY `TaskItem` → `Item` (`:53-76`), computes `item_binding`
(`bound` / `detached` / `mismatched`, `:110`), and raises `NotFound` for an unknown,
deleted or cross-workspace task. The same resolution is reused here.

`commit_item_cost_evaluation._load_task_and_primary` (`:117-141`) admits only tasks in
`_ADMITTED_STATES = {PENDING, ASSIGNED, WORKING, STALLED, READY}` (`:62-70`) and
requires an active PRIMARY item — so a screen offering a Save button needs to know the
task's admissibility before the user presses it.

### 2.6 The valuation row and its author

`item_valuations` (`models/tables/item_economics/item_valuation.py:18-29`):
`expected_sale_price_minor` and `purchase_cost_minor` both nullable, `currency`
required, `superseded_at` / `superseded_by_id` forming the chain, `created_at`,
`created_by_id`. `serialize_item_valuation`
(`domain/item_economics/serializers.py:93-106`) exposes `created_by_id` **and nothing
else** — no username, no picture. The screen's byline is therefore a genuine new
requirement, not a re-serialization (M4).

`serialize_user_light` (`domain/cases/serializers.py:102-108`) is the existing
three-key light user shape (`client_id`, `username`, `profile_picture`).

### 2.7 Quantity

`items.quantity` is `Integer, nullable=False, default=1`
(`models/tables/items/item.py:33`) with **no CHECK constraint**. `quantity >= 1` is
enforced by field validators on all three write paths —
`services/commands/items/requests/__init__.py:232-236` (create), `:279-283` (update),
`:507-511` (find-or-create). It is therefore an **application** invariant, not a
storage one: a row written before those validators existed could in principle hold
`0`, which is a division by zero at the frontend boundary (M-note in §9.4).

### 2.8 The route surface today

25 item-economics routes, mirrored in four places (HC-2a). The only read-only
task-scoped manager-gated precedent is
`GET /tasks/{task_client_id}/budget-status` — which is in fact all-role with a
separate worker service; there is no existing manager-only task-scoped GET on this
router, so this route establishes that shape.

### 2.9 What does not exist

**There is no read-only price preview.** `PUT /items/{id}/valuation` writes a chain row
before previewing; `POST /tasks/{id}/projections` persists an `ItemCostEvaluation`.
Every existing way to ask "what would this price give me" mutates. That absence is the
reason this pipeline exists.

---

## 2A. Citation corrections (mechanism-inventory, round 3, 2026-08-19)

Every code citation in §2 was re-read at head `f1c0ebb`. The **semantics** of §2 survived
the sweep — the corrections below are line drift, with two exceptions marked ⚠ where the
cited range points at a *different mechanism* than the sentence claims, which is how an
implementer reads the wrong rule and reproduces it faithfully.

| §2 says | Actual | |
|---|---|---|
| `calculate_percentage_term_amount` `:154-166` | `:160-175` | |
| `calculate_term_amount` `:169-207` | `:178-210` | |
| `calculate_production_budget` `:225-239` | `:245-258` | |
| `calculate_allowed_worker_minutes` `:266-280` | `:285-299` | |
| `_budget_seconds` `budget_division.py:62-64` | `:64-66` | |
| typical constants `budget_division.py:14-17` | `:15-18` | |
| `EXCLUDED_STEP_STATES` `:18-24` | `:19-25` | |
| `divide_production_budget` `:245-401` | `:273-399` | |
| participating set `:322-327` (§5.1) | **`:309-313`** | ⚠ `:322-327` is the *per-section typical resolution*, not the participating-set filter |
| median fallback `:355-370` (§5.2) | **`:317-335`** | ⚠ `:355-370` is the excluded-section row builder; the median lives at `:332` |
| `charged_seconds` `:329-331` | `:314-315` | |
| `typical_times_statement` `:22-64` | `:21-63` | |
| `_load_preview_inputs` `_common.py:186-219` | `:172-216` | |
| `get_task_budget_status` resolution `:53-76` | `:51-78` | |
| `item_binding` `:110` | `:111` | |
| `_load_task_and_primary` `:117-141` | `:106-137` | |
| `_ADMITTED_STATES` `:62-70` | `:60-68` | |
| commit rate recompute `:260-264` | `:263-267` | |
| `set_item_valuation._preview` `:48` | `:50` | |
| `serialize_item_valuation` `:93-106` | `:96-108` | |

**Verified correct, no change:** `CALCULATION_VERSION` `calculator.py:20`;
`resolve_economics_selection` `:80-126`; `resolve_item_economics_status` `:129-169`;
`cost_model_term.py:23`; `production_cost_basis_version.py:27`; `item_valuation.py:18-29`;
`item.py:33`; `serialize_user_light` `:102-108`;
`create_production_cost_basis_version.py:27-31`.

### 2A.1 Three grounding facts §2 does not state, each load-bearing

1. **`TaskStep` has no `typical_worker_seconds` column.** `divide_production_budget`
   `:322-326` falls back to a step-level typical, but that attribute exists only on the
   `DivisionStep` test dataclass (`budget_division.py:38`) — a search of
   `beyo_manager/models/` from the repository root returns no such column on any table.
   In production the allocator's *only* typical source is the `typicals_by_section`
   mapping its caller builds from `typical_times_statement`
   (`get_task_production_time.py:52-71`). **Consequence for M3: §5.2's description of the
   allocator is accurate for production, and the step-level fallback must NOT be copied.**
   Reimplementing it would make this screen consult a source the other screen cannot.
2. **Cost model terms are immutable for the life of their version.** `CostModelTerm` rows
   are constructed at exactly two sites — `create_cost_model_version.py:57` and the
   bootstrap seeder — and there is no term update or delete route
   (`routers/api_v1/item_economics.py` exposes only POST/GET/DELETE on
   `/cost-model-versions`). **Consequence for M6: `cost_model_version_id` is a sufficient
   proxy for the entire term set**, which is what makes a two-id fingerprint honest
   rather than optimistic (§9A.3).
3. **`cost_per_worker_minute_minor` carries `CHECK > 0`**
   (`production_cost_basis_version.py:38` — corrected from `:40` at the projection r0 fold;
   `:40` is `planning_utilization_percent > 0`. The claim was true, the address was not)
   and is written only by
   `calculate_cost_per_worker_minute` at version creation; basis versions have no update
   route. **Consequence for M1: the published rate can never be zero or negative**, so the
   division in `allowed_centimin` needs no zero-guard, and §2.2's "two derivation paths"
   agree because the recompute reads the same row that produced the column.

---

## 3. Mechanism contract M1 — the price → allowance display model

For a candidate whole-item price `P` (integer minor units, `P >= 0`).

### 3.1 The collapsed affine form (what the endpoint publishes)

Let, over the selected cost model version's non-deleted terms:

```
residual_percent_milli   = 100000 − Σ round(percent_value_i × 1000)   [integer, may be ≤ 0]
constant_deduction_minor = Σ fixed_amount_minor_i
                         + (purchase_cost_minor if a purchase term exists else 0)
```

`percent_value` is `Numeric(6,3)`, so `× 1000` is exact — never a float multiply.
A `NULL` `purchase_cost_minor` combined with a present purchase term is **not** a
zero: it is status `item_missing_purchase_cost` and the whole model block is `null`
(§9.1).

The published function is:

```
budget_minor(P)  = round_half_even(P × residual_percent_milli, 100_000)
                   − constant_deduction_minor
allowed_centimin(P) = round_half_even(budget_minor(P) × 1_000_000,
                                      cost_per_worker_minute_ten_thousandths)
allowance_seconds(P) = round_half_even(allowed_centimin(P) × 3, 5)
```

All three are exact integer operations. `round_half_even(a, b)` is
banker's-rounded integer division of `a` by `b`; it must be implemented as integer
arithmetic on both sides (BigInt in the client), never floating point, and never via
a language `round()` that is half-away-from-zero.

The `× 1_000_000` in the second line is `10^4` (undoing the rate's `Numeric(12,4)`
scale) × `10^2` (expressing the result in centi-minutes). The third line is the
two-step `minutes → seconds` conversion of §2.1, **not** a shortcut from budget to
seconds; taking the shortcut disagrees with `_budget_seconds` by up to a second and
would make this screen and the production-time screen name different numbers for the
same task.

### 3.1A `round_half_even(a, b)` — the two-language integer contract

§3.1 says "banker's-rounded integer division … integer arithmetic on both sides (BigInt in
the client)". That is a requirement, not a contract: it does not say what happens when `a`
is negative, and every language disagrees there. `a` **is** negative on this screen —
`budget_minor(P) < 0` for any price below the constant deduction, which is exactly the
`infeasible` state §9.1 says the screen exists to show.

**Signature.** `a: integer, any sign`. `b: integer, strictly positive`. Returns the integer
nearest `a/b`, ties to even. `b <= 0` is a programming error, not a runtime state: the two
call sites use `100_000` and `cost_per_worker_minute_ten_thousandths` (≥ 1 by §2A.1.3) and
the literal `5`.

**Reference algorithm — floor semantics, then the tie test.** Both languages implement
*this*, not their own rounding primitive:

```
q  = floor(a / b)          # floor, NOT truncation
r  = a - q*b               # therefore 0 <= r < b, whatever the sign of a
if 2*r > b            -> q + 1
if 2*r == b and q odd -> q + 1     # tie: step to the even neighbour
otherwise             -> q
```

**Python.** `divmod(a, b)` is already floor semantics for positive `b`, so the reference
algorithm transcribes directly. `round()` must not be used: it is half-even but returns a
float for `int/int`. `Decimal(a).quantize(…, ROUND_HALF_EVEN)` is permitted **only** with
an exact `Decimal(a)/Decimal(b)` under sufficient `prec`; the integer form is preferred
because it cannot silently lose precision.

**JavaScript/BigInt.** `/` truncates toward zero and `%` takes the sign of the dividend, so
a direct transcription is wrong for negative `a`. The correction is mandatory:

```js
function roundHalfEven(a, b) {            // BigInt, b > 0n
  let q = a / b, r = a % b;               // truncating
  if (r < 0n) { q -= 1n; r += b; }        // -> floor semantics
  const twice = 2n * r;
  const qIsOdd = ((q % 2n) + 2n) % 2n === 1n;   // q may be negative
  if (twice > b || (twice === b && qIsOdd)) q += 1n;
  return q;
}
```

`Number` is forbidden throughout: `855_000 × 22_000 = 1.881e10` already exceeds what a
float can carry losslessly once multiplied by `1_000_000` in the second line.

**Which operations can actually tie** — enumerated, because a tie rule nobody can reach is
untestable and a tie rule nobody noticed is a defect:

| Operation | Tie reachable? | Why |
|---|---|---|
| `round_half_even(P × residual_percent_milli, 100_000)` | **yes** | `residual = 50_000`, `P` odd → remainder exactly `50_000` |
| `round_half_even(budget × 1_000_000, rate_ten_thousandths)` | **yes** | `rate_tt = 2_000_000`, `budget` odd → exactly `.5` |
| `round_half_even(allowed_centimin × 3, 5)` | **no** | `3·cm mod 5 ∈ {0,1,2,3,4}`; a tie needs remainder `2.5`, unreachable over integers |

The third row is a fact worth keeping: the seconds conversion is tie-free, so the whole
half-even question is confined to the two operations the client also runs.

### 3.1B M1 inputs — every type they arrive as, and canonicalisation

| Input | Arrives as | Canonicalisation |
|---|---|---|
| `percent_value` | `Decimal`, scale 3 (`Numeric(6,3)`, `cost_model_term.py:23`), `CHECK >= 0` | `int(value.scaleb(3))`; **raise** if `value != value.quantize(Decimal("0.001"))` rather than rounding. `×1000` is exact, never a float multiply. |
| `fixed_amount_minor` | `int | None`, `CHECK >= 0` | summed as-is |
| `purchase_cost_minor` | `int | None` on the **valuation**, `CHECK >= 0` | added to `constant_deduction_minor` **iff** a non-deleted `item_purchase_cost` term exists; `None` + such a term ⇒ status `item_missing_purchase_cost`, model block `null` (§3.1). A purchase cost present with no purchase term is **ignored**, matching `calculate_term_amounts`. |
| `cost_per_worker_minute_minor` | `Decimal`, scale 4 (`Numeric(12,4)`), `CHECK > 0` | `cost_per_worker_minute_ten_thousandths = int(value.scaleb(4))` |
| `P` (candidate price) | `int` minor units, `CHECK >= 0` on the column | `P >= 0`; the client never sends a price to this endpoint — `P` is the client's own slider value |

**Short-circuit and validation exhaustiveness (added at the review r1 fold, 2026-08-19 —
N1).** The missing-purchase-cost outcome **short-circuits the collapse**: terms after the
purchase term are not shape-validated. The consequence is order-dependence — for the same
two-term set, `[purchase, malformed]` returns the no-model `None` while
`[malformed, purchase]` raises. Demonstrated on real ORM instances by review r1.

**This is sound, and the reason is structural, not incidental.**
`ck_cost_model_terms_value_by_type` (`cost_model_term.py:38`) enumerates exactly the three
term shapes the collapse accepts, so no *persisted* row can be malformed; `percent_value` is
`Numeric(6,3)`, so no persisted row can exceed scale 3; and
`uix_cost_model_terms_purchase_cost` bounds purchase terms at one per version. The order
this section fixes (`created_at, client_id`) is therefore immaterial to every published
value. Recorded because charter rule 5 says ordering semantics are **contracted, not
inherited** — an implementer who later relaxes a CHECK, or feeds this function unpersisted
rows from a new caller, needs to find this sentence rather than rediscover the behaviour.

**The term set is `_load_preview_inputs`'s, not a new query.** Non-deleted terms of the
selected cost model version, ordered `created_at, client_id` (`_common.py:207-215`). The
partial unique index `uix_cost_model_terms_purchase_cost` guarantees **at most one**
non-deleted purchase term per version, so `calculate_term_amounts`' duplicate-purchase
rejection is unreachable for live rows and the collapsed form cannot disagree with the
persisted one over duplicates.

**Which rate is published — the §2.2 obligation, discharged.** §2.2 says "this endpoint
must declare which one it publishes (M1, R3)"; no section ever did, and there is no §R3 in
this document. **Decision: the endpoint publishes the persisted column**
`ProductionCostBasisVersion.cost_per_worker_minute_minor × 10^4`. Reason: it is a direct
integer read, it carries `CHECK > 0`, and §2A.1.3 establishes it cannot drift from the
commit path's recompute because there is no update route for a basis version and both
values come from the same row through the same function.

### 3.2 The declared error bound

The persisted path (`calculate_term_amounts`) rounds **each** percentage term
individually; the published form rounds **once**. Per-term error is at most `0.5`
minor units; over `n` percentage terms the persisted path's total error is at most
`n/2`, and the published form's at most `0.5`. Hence:

```
| budget_published(P) − budget_persisted(P) |  ≤  (n + 1) / 2   minor units
```

For a two-term model that is ≤ 1 minor unit (1 öre), i.e. ≤ `1/rate` minutes — at the
rate measured in the mockups (1300 minor/minute) about **0.07 seconds**. The screen
displays whole minutes. The approximation is therefore invisible in every rendered
figure, and it buys two things worth more than the last öre: a payload of three
integers instead of an unbounded term array, and a **strictly monotone** budget
function (§4.2).

**This bound is a contract, not a hope.** It is asserted by test against the real
`calculate_term_amounts` path across the model shapes of §12.

### 3.2A The bound's contract — `n`, the proof, and a corrected illustration

**The bound is sound.** Re-derived independently at this gate:

- `percent_value` has scale 3, so `Σ round(percent_value_i × 1000) / 100_000` equals
  `Σ percent_value_i / 100` **exactly** — the collapsed residual introduces *no* error of
  its own before the single rounding. This is the step the bound depends on and §3.1
  already states its reason.
- `budget_published(P) = round_he(P·(1−Σpct)) − K`, one rounding, error ≤ `1/2`.
- `budget_persisted(P) = P·(1−Σpct) − K − Σeᵢ` with `|eᵢ| ≤ 1/2` over `n` terms, error ≤ `n/2`.
- Triangle inequality ⇒ `≤ (n+1)/2`. **Attained**, not merely bounded, so the criterion
  asserting it must use `≤` and not `<`.

**`n` is the number of non-deleted `percentage_of_expected_sale_price` terms in the
selected version** — not the term count. §3.2's phrase "a two-term model" means one
percentage term plus one non-percentage term (`n = 1`, bound `1`). A model with two
percentage terms is `n = 2`, bound `1.5`, and that is the shape §12.1 enumerates as the
§4.2 dip. Because the bound is a half-integer for even `n`, the assertion is written
`2·|Δ| ≤ n+1` in integers rather than comparing against a float.

**Corrected illustration.** §3.2 computes "≤ 1 minor unit … about 0.07 seconds". The two
halves use different `n`: `1` minor unit at rate `1300` minor/minute is
`60/1300 = 0.046 s`; the quoted `0.07 s` is `1.5` minor units (`n = 2`). Both are correct
for their own `n` and neither changes the conclusion — the largest error either way is
under a tenth of a second against a display quantised to whole minutes.

**How the display quantises** (undefined in §3.2, and the invisibility argument depends on
it): the screen renders `allowance_seconds` **rounded to the nearest minute**, ties away
from zero, e.g. `8681 s → 145 min → "2h 25m"`. Truncation would render `"2h 24m"` for the
same second count and would make the §1 mockup row wrong (§8A.2, row `AT PRICE`).

### 3.3 Why not ship the term array

The screen no longer itemises deductions — the "22% of 12 300 SEK" card and the
cost-of-work card were both cut in the simplified design. Shipping `terms[]` would be
shipping display data nothing displays, and it would push the per-term rounding rule
(and its non-monotonicity, §4.2) into the client. When the breakdown returns, `terms[]`
returns with it and `residual_percent_milli` becomes a redundant convenience — a
purely additive change.

### 3.4 The non-proportional case

`budget(P) = P·(1 − Σpct) − K` is **affine, not proportional**, whenever
`constant_deduction_minor > 0`. The effective share of the price left for restoration
then drifts as the handle moves, and any fixed-percentage headline is wrong at both
ends of the slider. The simplified screen shows no percentage headline, so v1 is
unaffected — but the payload carries `is_purely_proportional`
(`constant_deduction_minor == 0`) so the first component that wants to print a "%"
knows whether it may.

### 3.5 Degenerate models

`residual_percent_milli <= 0` means the term set consumes the whole price: `budget` is
non-increasing in `P` and no price ever funds any work. This is a **configuration**
fault, not a pricing one. The endpoint returns `status: "ok"` with the model block
populated, `anchors.break_even_price_minor: null`, `anchors.is_fundable: false`, and
the domain suppressed (§7.3); the screen shows the slider disabled with a
configuration message rather than an empty band.

---

## 4. Mechanism contract M2 — break-even and suggested price

### 4.1 Definition

```
break_even_price_minor =
    the smallest integer P ≥ 0 such that allowance_seconds(P) ≥ typical_total_seconds
```

where `allowance_seconds` is M1's published function (§3.1) and
`typical_total_seconds` is M3. It is the price at which the work this item typically
needs is exactly funded — the boundary the screen's chip flips on, and the anchor the
`suggested` marker sits at.

`null` when `residual_percent_milli <= 0` (§3.5) or when M3 yields
`typical_total_seconds == 0` (a task whose sections have no typicals at all and no
usable median — §5.3); in both cases `is_fundable: false` and the chip is not
rendered.

### 4.2 Why the search is safe on the published form and not on the persisted one

`budget_published(P)` is **strictly monotone non-decreasing** in `P` when
`residual_percent_milli > 0`: it is a single rounded multiplication by a positive
constant, minus a constant. Bisection over `[0, P_hi]` is therefore correct and
terminates in `⌈log2(P_hi)⌉` evaluations.

`budget_persisted(P)` is **not** monotone. Two percentage terms with equal
`percent_value` cross their rounding boundary on the same unit step, so
`Σ term_amounts` can rise by 2 while `P` rises by 1, and the budget **dips by one
minor unit**. A bisection on the persisted form can therefore straddle a dip and
return a price one unit off the true boundary. Running the search on the published
form removes the trap entirely, and §3.2 bounds the resulting difference from the
persisted boundary at ≤ `(n+1)/2` minor units — far below any price step a human
drags in.

This is the load-bearing reason HC-5 declares the endpoint a display model. Recorded
here so the question is not reopened by a later "let's make the anchor exact" change,
which would reintroduce a non-monotone search.

`P_hi` for the search is `domain.max_minor` (§7) raised by one doubling if
`allowance_seconds(P_hi) < typical_total_seconds`, capped at `2^40` minor units; a
search that reaches the cap returns `null` and `is_fundable: false`.

### 4.2A The search, contract-grade — monotonicity, the bound, and the circularity

**The monotonicity claim needs two repairs.**

1. §4.2 says `budget_published(P)` is "**strictly** monotone non-decreasing". Those are
   different properties and only the weaker one is true: `round_he(P·r, 100_000)` is flat
   across consecutive `P` whenever `r < 100_000`, which is every real model. **The contract
   is: non-decreasing, not strictly increasing.** An implementer who believes the strict
   claim may search for a unique crossing point; there isn't one, there is a plateau, and
   the definition in §4.1 ("the smallest `P` such that …") is what disambiguates it.
2. §4.2 argues monotonicity of the **budget**, but §4.1 searches on **`allowance_seconds`**.
   The missing step: `allowance_seconds` is a composition of `budget` with two further
   `round_half_even` divisions by positive constants, and `round_half_even(·, b)` is
   non-decreasing for `b > 0`. Composition of non-decreasing maps is non-decreasing, so
   `allowance_seconds` is non-decreasing in `P` when `residual_percent_milli > 0`. **That**
   is the property the bisection rests on.

**The search.** Bisection for the least `P` in `[0, P_hi]` with
`allowance_seconds(P) >= typical_total_seconds`, on the non-decreasing predicate
`allowance_seconds(P) >= T` (false-then-true). Standard lower-bound form: invariant
`lo` false-or-0, `hi` true; terminate at `lo + 1 == hi`, answer `hi`. `P = 0` is checked
first and returned when it already satisfies the predicate.

**`P_hi` is not `domain.max_minor` — that is circular.** §4.2 sets `P_hi` from
`domain.max_minor`, but §7.2 derives `max_minor` from `break_even_price_minor`, which is
what the search is computing. The dependency runs M2 → M5, never back. **The contract:**

```
P_hi = 1
while allowance_seconds(P_hi) < typical_total_seconds and P_hi <= 2**40:
    P_hi *= 2
if P_hi > 2**40:  ->  break_even_price_minor = null, is_fundable = false
```

Doubling from `1` (not "one doubling" of a band end) is what makes the upper bound
independent of M5 and total over every model shape. The `2**40` cap and its `null` are
§4.2's, unchanged.

**`anchors.infeasible_at_or_below_minor` — defined here for the first time.** §7.2 uses it
to floor the band and §8 ships it, but no section derives it. It is the same search with a
different target:

```
infeasible_at_or_below_minor = (least P >= 0 with allowance_seconds(P) >= 1) − 1
```

i.e. the highest whole-item price that buys no work at all.

> **CORRECTED at the projection r0 fold (2026-08-19).** This paragraph read: *"For a purely
> proportional model it is `0` (at `P = 0` the allowance is `0`, and `P = 1` already buys
> ≥ 1 second unless the rate exceeds the residual value of one öre), which is the value §8's
> example carries."* **That is false, and false for the mockup's own configuration.** The
> parenthetical names the correct escape hatch and then draws the opposite conclusion: at
> `rate_tt = 13_000_000` (1 300 minor/minute) one öre of budget buys `0.046 s`, so the rate
> exceeds the residual value of one öre by a factor of about 22. Computed from this
> section's own definition with `residual_percent_milli = 22_000`, `K = 0`:
> `P = 1` → budget `0` → `0 s`; the least `P` with `allowance_seconds >= 1` is **30**
> (budget 7 → 1 centiminute → 1 s), so **`infeasible_at_or_below_minor = 29`**.
> Independently re-derived by the coordinator at the fold.
>
> The `0` claim holds only for models with residual ≥ 50 % **and** a rate ≤ 200
> minor/minute; the mockup meets neither. **There is no general shortcut — the value is
> always the search's result**, and an implementer who encodes "purely proportional ⇒ 0"
> ships a band floored one step too low on most real configurations.
>
> **Blast radius, enumerated.** §8's example payload is corrected (§8A.1, now four values).
> §7A.2's worked-check row is **unaffected**: `ceil_to_step(29 + 1, 15 000) = 15 000`, which
> still loses to the `raw_low` floor of `420 000`, so C16's three literals and D10 stand —
> verified, not assumed.

It is **never `null`**, including when `break_even_price_minor` is `null`: a
degenerate model (§3.5) makes every price infeasible, and the value is then the `2**40`
cap. The same doubling bound and cap apply.

### 4.3 The chip and the marker are anchor-driven, never curve-driven

The screen decides `Below typical work` / `Just covers typical work` by comparing the
**draft price** to `break_even_price_minor`, and positions the `suggested` marker at
`suggested_price_minor` — never by comparing its own computed
`allowance_seconds(P)` to `typical_total_seconds`.

Rationale: comparing computed values puts the chip's flip at the mercy of the last
minor unit of rounding, exactly at the boundary, which is the single most visible
place on the screen to be off by one step. Comparing against a server-computed
integer makes the flip exact regardless of any arithmetic drift, and makes the chip
and the marker agree by construction. This is the same "compute the threshold once in
the backend so two clients cannot disagree" rule as
`simple_production_budget_division` HC-4 / D7, applied within one screen.

### 4.4 Suggested price

```
suggested_price_minor = ceil_to_step(break_even_price_minor, domain.step_minor)
```

`null` whenever `break_even_price_minor` is `null`. Rounding **up**, never to nearest:
the suggestion is "the cheapest price that funds the typical job", and rounding it
down would suggest a price that does not.

Worked check against the mockup: typical `12 300s` = 205 min, rate `1300` minor/min →
`205 × 1300 = 266 500` minor needed; `residual 22%` → `P = 266 500 / 0.22 = 1 211 364`
minor = `2 018.94`/piece over 6 pieces; ceiled to the `15 000` minor step (§7.2) →
`1 215 000` minor = **`2 025`/piece**, the mockup's figure.

---

### 4.4A The step helpers, and the worked check redone

**`ceil_to_step` / `floor_to_step`** (used by §4.4 and §7.2, defined nowhere):

```
floor_to_step(v, s) = (v // s) * s          # floor division, s > 0
ceil_to_step (v, s) = -((-v) // s) * s
```

Both take an integer `v >= 0` and integer `s >= 1` and return a multiple of `s`. Where the
input is an exact rational (§7A), the rational is floored/ceiled directly — never
pre-rounded to an integer and then stepped, which double-rounds.

**§4.4's worked check does not follow §4.1's rule.** Redone by hand at this gate, with
`typical_total_seconds = 12_300`, `residual_percent_milli = 22_000`,
`cost_per_worker_minute_ten_thousandths = 13_000_000`, `K = 0`:

| Step | §4.4 does | §4.1 requires | |
|---|---|---|---|
| needed budget | `205 min × 1300 = 266_500` | least `B` with `allowance_seconds >= 12_300` → **`266_494`** | `266_494/13 = 20_499.54 → 20_500` centimin → `12_300 s` |
| price | `266_500 / 0.22 = 1_211_364` | least `P` with `round_he(0.22P) >= 266_494` → **`1_211_335`** | `0.22 × 1_211_335 = 266_493.7 → 266_494` |

§4.4 solves the **real-arithmetic** equation; §4.1 defines the **least integer price whose
rounded allowance reaches the typical**. They differ by **29 minor units**, and §4.4's
answer is not minimal: at `P = 1_211_363` the allowance is still exactly `12_300 s`, so a
correct implementation of §4.1 can never return `1_211_364`. **§4.1's definition governs;
`break_even_price_minor = 1_211_335` for the mockup's data**, and §8's example value is
corrected accordingly (§8A.1).

### 4.4B `suggested_price_minor` when there is no band (projection r0, L6)

§4.4 gives `suggested_price_minor = null` only when `break_even_price_minor` is `null`. But
§7A.1 makes `domain` `null` whenever `min_minor >= max_minor`, which is **reachable with a
non-`null` `B`** — so `ceil_to_step(break_even, domain.step_minor)` has no step to read.

Measured against the shipped module: `PriceModel(residual=100_000, K=0, rate_tt=10_000)` —
a rate of `1.0000` minor/minute, legal under `Numeric(12,4)` and `CHECK > 0` — with
`typical_total_seconds = 60` gives `break_even_price_minor = 1`,
`infeasible_at_or_below_minor = 0`, and `slider_domain(1, 6, 0) is None`. A bounded sweep
found thirty-four such `(rate, residual, T, Q)` combinations.

**Contract: `suggested_price_minor` is `null` whenever `domain` is `null`, as well as
whenever `break_even_price_minor` is `null`.** It is a multiple of the step, so it cannot
exist without one.

The corner is degenerate — it needs `B < 80·Q`, a break-even under about five kronor — and
it is unguarded: an implementer following §4.4 literally writes
`ceil_to_step(B, domain.step_minor)` and gets an `AttributeError` on a `null` `domain`,
which is a 500 where the contract wants a `null`.

**`suggested_price_minor` had no acceptance criterion in either phase** — it is a published
key and one of the mockup's seven rendered elements, and nothing pinned the composition
`ceil_to_step(break_even, step_minor)`. Plan 2 now carries one.

**The suggested price is unaffected**, which is why this survived round 2 unnoticed:
`ceil_to_step(1_211_335, 15_000) = 81 × 15_000 = 1_215_000` = `2 025`/piece over 6 —
still the mockup's figure. §4.4's *conclusion* holds; its *derivation* does not, and the
derivation is what an implementer would have copied.

---

## 5. Mechanism contract M3 — typical total for this task

### 5.1 The section set

The sections that participate are the task's **allocated section set**, defined
exactly as `divide_production_budget` defines it (`budget_division.py:322-327`):
sections holding at least one non-deleted step whose state is not in
`EXCLUDED_STEP_STATES = {SKIPPED, CANCELLED, FAILED}` (`:18-24`).

A section whose every step was skipped or cancelled contributes nothing: that work is
not going to happen, and charging the price for it would make every such item look
underpriced.

### 5.2 The per-section value and the fallback

Per participating section, the typical is `typical_times_statement`'s
`typical_worker_seconds` (§2.4) — `NULL` below 5 qualifying groups. For a `NULL`, the
value substituted is **the median of the participating sections' non-null, positive
typicals**; if none of them is usable, the substitute is `0` (see §5.3).

This mirrors `divide_production_budget`'s `_median` fallback (`:355-370`) so this
screen's "typical" and the production-time screen's section rows are computed from the
same numbers. Duplicating the rule rather than sharing it would guarantee they drift;
the pure helper is imported, not reimplemented (HC-2 is about not *changing*
`budget_division.py`, not about not calling it).

```
typical_total_seconds   = Σ resolved value over participating sections
is_estimated            = any participating section had a NULL typical
sections_without_sample = count of those sections
sections_total          = count of participating sections
```

### 5.3 The no-evidence case

When **no** participating section has a usable typical, `typical_total_seconds` is
`0`, `is_estimated` is `true`, and `sections_without_sample == sections_total`. The
allocator's `Fraction(1,1)` weight fallback is deliberately **not** copied here: a
weight of 1 is meaningful as a *proportion* between sections and meaningless as a
*duration*, and rendering "typically 4 seconds" would be worse than rendering nothing.
The screen shows the typical column empty with a reason, and M2 returns `null`
(§4.1) — there is no evidence to break even against.

**Owner-ratified (D7, 2026-08-19).** Showing the partial sum was the rejected branch: a
typical built on two completed jobs can be wrong by a factor, and a manager who trusts
it prices the next fifty items on it. Absence with a reason is the contract.

### 5.3A M3 contract — usability, quantisation, and what the counters count

§5.2 is accurate about the allocator (verified against `budget_division.py:309-335`, and
see §2A.1.1 on the step-level fallback that only exists in the test dataclass). Three
things it leaves an implementer to resolve silently:

**1. "Usable" is not "non-null".** The allocator substitutes the median whenever the
resolved weight is `<= 0` (`:333-335`), and a typical enters `usable` only if it is
`not None and > 0` (`:327`). A section with a genuine typical of `0` seconds — reachable:
five or more qualifying groups all with `total_working_seconds = 0` — is **not usable**.
§5.2 defines `is_estimated` as "any participating section had a NULL typical" and
`sections_without_sample` as "count of those sections", which under-counts by every
zero-typical section and makes this screen's counters disagree with the other screen's
substitution. **Contract:**

```
usable(t)               = t is not None and t > 0
is_estimated            = sections_total == 0 or any participating section is not usable
sections_without_sample = count of participating sections that are not usable
sections_total          = count of participating sections
```

> **The empty case, added at the projection r0 fold (2026-08-19, L12).** The `is_estimated`
> line originally read *"any participating section is not usable"*. With **no** participating
> sections — a task with no steps, or one whose every section's steps are all in
> `EXCLUDED_STEP_STATES`, both reachable — `any()` over the empty set is `False`, so the
> block published `total_seconds: 0, is_estimated: false, sections_without_sample: 0,
> sections_total: 0`: a screen rendering a **measured** typical of zero. §5.3's no-evidence
> contract says the opposite and never noticed it was describing a non-empty set.
>
> Downstream the damage is contained — `T = 0` makes `break_even_price_minor` return `None`
> and the slider is suppressed — so exactly one boolean says "measured" about nothing. That
> is the rule-6 profile precisely: the number looks plausible and is wrong.

**2. The median is a `Fraction`; the total is an integer.** `_median` (`:69-74`) returns
the mean of the two middle values for an even count, so the substitute is `x.5` whenever
the two middles differ by an odd number. In the allocator that stays exact because it is a
*weight* fed to largest-remainder; here it becomes a **duration** that must land in an
integer `typical.total_seconds`. **Contract: quantise once, per section, at substitution
time** — `round_half_even(numerator, denominator)` of the `Fraction` (§3.1A), then sum
integers. Quantising the sum instead would let two substituted sections cancel a half each
and produce a total no section's value supports; not quantising at all leaks a rational
into a field typed as an integer.

**3. The participating set is `budget_division.py:309-313`, not `:322-327`** (§2A). A
section participates iff it has at least one non-deleted step whose state is not in
`EXCLUDED_STEP_STATES`. §5.1's prose is right; only its citation pointed elsewhere.

**Order-insensitivity.** `typical_total_seconds` is a sum and `_median` sorts its input, so
M3 is independent of section and step ordering. Nothing else in M3 is order-sensitive, and
no ordering may be introduced: there is no tie-break to specify because there is no rank.

### 5.4 Gross, not net of progress

`typical_total_seconds` and `allowance_seconds(P)` are both **whole-item totals that
ignore work already done**. The allocator's `charged_seconds` deduction (excluded
steps' consumed seconds, `budget_division.py:329-331`) is **not** applied.

Rationale: the screen compares a plan to a plan — "does this price fund the job this
item needs?" Time already burned on a failed step is sunk; it changes what is *left*,
not whether the price covers the *job*. Mixing the two would make the answer to a
pricing question depend on how badly the job has gone so far.

**Known divergence, owner-ratified (D5, 2026-08-19).** On a task carrying excluded-step
time, this screen's `AT PRICE` is larger than the production-time screen's distributable
total by exactly `charged_seconds`. That is a real inconsistency between two screens and
it is accepted deliberately: a divergence that can be explained is better than a price
that moves with accidents. It is recorded here rather than hidden because a manager who
notices it and is not told why will conclude one of the two screens is broken —
**the closeout handoff must name it** (§10, `progress` remains out of v1).

---

## 6. Mechanism contract M4 — the saved-version byline

The screen's `Marta Lind · saved version · 14 Aug, 10:24` identifies **who set the
price that is currently saved**, which is the current (non-superseded, non-deleted)
`item_valuations` row for the task's PRIMARY item.

```
saved.created_at   = the current valuation row's created_at (ISO 8601, UTC)
saved.created_by   = { client_id, username, profile_picture }  or  null
```

Three cases the contract must name, because two of them are invisible until they
happen in production:

1. **A person set it** through `PUT /items/{id}/valuation` or through the commit
   path's price override — `created_by` is that user.
2. **Inline task creation set it** — `create_task` writes the first chain row through
   `write_item_valuation_chain_in_session` with `created_by_id = ctx.user_id`, so this
   is still a real person, but one who was creating a task and may not remember
   pricing anything. The byline is accurate; the screen's copy should not imply the
   person opened this screen.
3. **The user row is gone** — `created_by_id` is a non-null FK with
   `ondelete="RESTRICT"`, so the row cannot vanish under a live valuation; but a
   defensive `null` is still served rather than failing the whole payload, because a
   byline is not worth a 500.

The three-key shape is deliberately identical to `serialize_user_light`
(`domain/cases/serializers.py:102-108`). It is **re-declared** in the item-economics
serializer rather than imported: importing `domain/cases` into `domain/item_economics`
couples two unrelated domains for three keys, and HC-2's independence is worth more
than the duplication. The duplication is pointed at in a comment at both sites so a
later consolidation finds both.

---

## 6B. M4 contract — resolution, types and the absent cases

*(Lettered `6B`, not `6A`: `§6A` already names a section of the item-cost intention, cited
by HC-1 and by `calculator.py`'s module docstring. Reusing it here would collide across
documents.)*

**Resolution.** The current valuation is the one row for the task's PRIMARY item with
`superseded_at IS NULL AND is_deleted = false` — the same predicate as
`_load_current_valuation` (`commit_item_cost_evaluation.py:176-184`) and
`write_item_valuation_chain_in_session` (`_common.py:130-137`), enforced unique by
`uix_item_valuations_current`. This endpoint reads **without** `FOR UPDATE`.

**Types.** `created_at` is `DateTime(timezone=True)`, serialised ISO 8601 with an explicit
UTC offset (`.isoformat()`, matching `serialize_item_valuation`). `username` is
`String(128) NOT NULL`; `profile_picture` is `String(512) NULL` and travels as `null`, not
as an empty string. `client_id` is a prefixed ULID (`ival_…`, `usr_…`) — never truncated.

**The absent cases, which §6's three named cases do not cover.** §6 names three ways the
byline's *author* can be surprising; it does not say what `saved` is when there is no row
to build it from. Both are reachable and both are the pricing screen's normal first day:

| Case | `saved` |
|---|---|
| No valuation row at all (status `item_unvalued`) | `saved: null` — there is no created_at, no author, and no price |
| Row exists, `expected_sale_price_minor` is `NULL` (status `item_missing_expected_price`; legal because `ck_item_valuations_amount_present` only requires *one* of the two amounts) | `saved` present, `expected_sale_price_minor: null` |
| Row exists, user row unreachable | `saved` present, `created_by: null` (§6 case 3) |

This **overrides** §9.1's "`item`, `saved` and `typical` stay fully populated" for the
no-row case: a null `saved` is the absence of a fact, not a degraded rendering, and
asserting it as absence rather than as zeros is the no-weaker-assertions rule (master plan
§5). `currency` moves with it — it is read from the valuation row, so it is `null` exactly
when `saved` is `null` (§8A.1).

---

## 7. Mechanism contract M5 — the slider domain

### 7.1 Why the backend owns it

`700/piece` and `2 700/piece` are hardcoded in the mockup. Left in the client they are
magic numbers that stop being sensible the moment a workspace's cost model or rate
changes, and two clients will pick differently. Derived server-side from the anchors,
the band is always meaningful and always the same everywhere.

**Owner-ratified (D6, 2026-08-19).** Fixed ends were the rejected branch: a workspace
pricing cabinets at 9 000 a piece would find every item pinned to the right edge, and a
band typed in today stays centred on today's economics after the hourly cost changes.

### 7.2 The rule

```
span_low   = floor_to_step(0.35 × break_even_price_minor, step_minor)
span_high  = ceil_to_step (1.35 × break_even_price_minor, step_minor)
step_minor = a "nice" step near (span_high − span_low) / 80, snapped up to a
             multiple of `quantity` so the per-piece label is never fractional
domain.rule = "break_even_band_v1"   ← the HC-6 swappability label
```

`min_minor` is additionally floored at `max(0, infeasible_at_or_below_minor + 1)` so
the band never contains a price that funds nothing.

Worked check against the mockup: `break_even = 1 211 364` → `0.35× = 424 000`
(`706`/piece), `1.35× = 1 635 000` (`2 726`/piece); span `1 211 000`, `/80 = 15 142`
→ nice step `15 000` = `25`/piece × 6. Rendered: `700`/piece … `2 700`/piece with
`25`/piece steps — the mockup's band, reproduced from the data rather than typed in.

### 7.3 When there is no break-even

`break_even_price_minor == null` (§3.5, §5.3) ⇒ `domain: null`. The screen disables
the slider and says why. It does not invent a band around the saved price: a band with
no anchor invites a manager to drag it and trust the result.

### 7.4 The step is a display convenience, not an invariant

Because the wire unit is whole-item (HC-4), a price that is not a multiple of
`quantity` is perfectly legal and the backend enforces nothing. The step is a multiple
of `quantity` only so that the screen's own two labels agree: at
`P = 855 100` and `quantity = 6`, per-piece reads `1 425 SEK` and the total reads
`8 551 SEK`, and `1 425 × 6 = 8 550`. The total label is the authoritative one.

---

## 7A. M5 contract — the band, made decidable

§7.2 is the least-defined mechanism in this document and the one whose output the manager
drags with their thumb. Three defects, then the contract.

**Defect 1 — the rule is circular.** `span_low`/`span_high` are defined via
`floor_to_step`/`ceil_to_step`, which need `step_minor`; `step_minor` is defined as a value
near `(span_high − span_low) / 80`, which needs the spans. Nothing in §7.2 can be computed
in the order it is written.

**Defect 2 — "a *nice* step *near* X" is not a specification** (charter rule 5, master plan
§5). Two adjectives doing the whole of the specification's work. No stated ladder produces
`15 000` from `15 142`: a 1‑2‑5 ladder gives `20 000`, decade rounding gives `10 000`, and
"snapped up to a multiple of `quantity`" applied to `15 142` gives `15 144`.

**Defect 3 — `min_minor`'s floor has no defined interaction with the step.** §7.2 floors
`min_minor` at `infeasible_at_or_below_minor + 1`, which is not a multiple of `step_minor`;
applied literally it breaks §7.4's only reason for the step to exist.

### 7A.1 The contract

Let `B = break_even_price_minor` (integer ≥ 0, from §4.2A) and `Q = max(1, quantity)`
(§9.4). All intermediate values are **exact rationals**; only the four published integers
are rounded, once each.

```
raw_low   = 35 * B / 100                     # exact
raw_high  = 135 * B / 100                    # exact
raw_span  = raw_high - raw_low  =  B         # exactly B; 1.35 - 0.35 = 1

step_per_piece = two_significant_digits( B / (80 * Q) ),  floored at 1
step_minor     = Q * step_per_piece

max_minor = ceil_to_step (raw_high, step_minor)
min_minor = max( floor_to_step(raw_low, step_minor),
                 ceil_to_step(infeasible_at_or_below_minor + 1, step_minor) )

domain = null  if  min_minor >= max_minor
```

**`two_significant_digits(a/b)`** — total, integer-only, and the replacement for "nice":

```
i = a // b                                   # integer part
s = 10 ** max(0, digits(i) - 2)              # digits(0) = 1
return max(1, round_half_even(a, b * s) * s)
```

Why two significant digits and not a 1‑2‑5 ladder: it is the coarsest rule that reproduces
the mockup's own step, it is monotone in `B`, and it has no table to get wrong in a second
language.

**Why the step is derived per *piece* and multiplied back.** §7.4 wants the per-piece label
to be exact; deriving the whole-item step first and then snapping it to a multiple of `Q`
destroys the nice value (`15 142 → 15 144`). Deriving the per-piece step first makes
divisibility by `Q` true **by construction**, and it is the per-piece number the manager
actually reads. Every published band value is therefore a multiple of `step_minor`, hence
of `Q`, so `min_minor / Q`, `max_minor / Q` and `step_minor / Q` are exact integers.

**`domain.rule = "break_even_band_v1"`** is the HC-6 label and covers **all** of §7A.1 —
the multipliers, the `/80`, the two-significant-digit rule and the floor. Any change to any
of them is a new label, because the client cannot detect the difference in any other way.

### 7A.2 The worked check, redone — and where it fails

With the corrected `B = 1 211 335` (§4.4A) and `Q = 6`:

| Quantity | Exact | Published | Per piece |
|---|---|---|---|
| `step_per_piece` | `1 211 335 / 480 = 2 523.61…` → 2 s.f. → `2 500` | | `25.00 SEK` ✓ mockup |
| `step_minor` | `6 × 2 500` | `15 000` | |
| `raw_low` | `423 967.25` | `floor_to_step → 420 000` | **`700.00 SEK`** ✓ mockup |
| `raw_high` | `1 635 302.25` | `ceil_to_step → 1 650 000` | **`2 750.00 SEK`** ✗ mockup says `2 700` |
| `min_minor` floor | `ceil_to_step(0 + 1, 15 000) = 15 000`, loses to `420 000` | `420 000` | |

**Two of the mockup's three numbers are reproduced from the data; the top end is not.**
`2 700`/piece needs a whole-item `1 620 000`, i.e. a multiplier of `1.337`, and no rounding
direction of `1.35 × B` reaches it — `ceil` gives `2 750`, `floor` gives `2 725`. §7.2's
claim "Rendered: `700`/piece … `2 700`/piece — the mockup's band" is therefore **false at
the top end**, and §7.2's own intermediate figures (`424 000`, `1 635 000`) are neither the
exact values nor the stepped ones: they are the exact values rounded by hand, and the
per-piece figures beside them (`706`, `2 726`) are computed from the *unstepped* rationals.

This does not reopen D6 — derived-versus-fixed stays decided, and the band still
re-centres on the economics, which is the property the owner accepted. What it does is
falsify the *evidence* D6 was accepted on ("it reproduces your mockup today"), which is why
it is an owner card and not a silent correction (**owner card 3**).

> **RATIFIED — D10 (owner, 2026-08-19): accept `2 750`/piece at the top.** Owner, verbatim:
> *"about card 3: the recommendation is the right approach."* The multipliers stay
> `0.35` / `1.35`; `max_minor` for the mockup's data is `1 650 000`, one step wider than the
> drawing at the far right, on a handle that opens near the middle.
>
> **Recorded rejection:** re-picking the top multiplier to `1.337` so the band lands on
> `2 700`. It matches the drawing by fitting a constant to one item's numbers — which is
> the failure D6 rejected fixed ends to avoid, reintroduced one level down where it is
> harder to see.
>
> **One correction to owner card 3 as authored**, so the record does not preserve a false
> premise: its story stated *"No pair of multipliers gives both 700 and 2 700 from this
> item's data."* That is overstated — `(0.35, 1.337)` gives both, and the card's own second
> branch says as much. The decision is unaffected; the objection to `1.337` was never that
> it is unreachable, only that it is fitted.

---

## 8. API contract E1

```
GET /api/v1/item-economics/tasks/{task_client_id}/price-scenario
Auth: ADMIN, MANAGER   (HC-3)
```

Task-scoped, not item-scoped, for three reasons: the participating section set and the
typical only exist relative to a task's steps (M3); the write this screen pairs with
(`POST /tasks/{task_client_id}/evaluations/commit`) is task-scoped and resolves the
item through `_load_task_and_primary`; and routing read and write the same way means
both resolve the same item by the same rule instead of the frontend having to pick.

**Naming note:** `basis` is already taken in this domain by
`production_cost_basis_versions`. `price-scenario` is chosen to avoid a second meaning
for a word this domain already owns.

```jsonc
{
  "task_id": "tsk_…",
  "status": "ok",                       // EconomicsStatusEnum, 12 values
  "item_binding": "bound",              // bound | detached | mismatched
  "can_commit": true,                   // task state ∈ _ADMITTED_STATES and PRIMARY present
  "currency": "swedish_krona",
  "calculation_version": 1,
  "config_fingerprint": "cmv_7a1:pcbv_3f9:v1",

  "item": {
    "client_id": "itm_…",
    "article_number": "0000608",
    "label": "Dining chairs",           // item_category_snapshot
    "quantity": 6                       // display divisor only (HC-4)
  },

  "saved": {
    "valuation_id": "ivl_…",
    "expected_sale_price_minor": 855000,
    "purchase_cost_minor": null,
    "created_at": "2026-08-14T10:24:00Z",
    "created_by": {"client_id": "usr_…", "username": "Marta Lind",
                   "profile_picture": "https://…"}
  },

  "model": {                            // M1 — null unless status is ok/infeasible
    "cost_model_version_id": "cmv_…",
    "basis_version_id": "pcbv_…",
    "residual_percent_milli": 22000,
    "constant_deduction_minor": 0,
    "cost_per_worker_minute_ten_thousandths": 13000000,
    "is_purely_proportional": true
  },

  "typical": {                          // M3 — always present
    "total_seconds": 12300,
    "is_estimated": false,
    "sections_without_sample": 0,
    "sections_total": 4,
    "method": "median_completed_section_totals",
    "window_days": 90,
    "min_sample_size": 5
  },

  "anchors": {                          // M2
    "is_fundable": true,
    "break_even_price_minor": 1211364,
    "suggested_price_minor": 1215000,
    "infeasible_at_or_below_minor": 29    // §8A.1 — NOT 0; see §4.2A
  },

  "domain": {                           // M5 — null when not fundable
    "rule": "break_even_band_v1",
    "min_minor": 420000,
    "max_minor": 1635000,
    "step_minor": 15000
  }
}
```

Envelope, error shape and decimal-as-string conventions are the house ones
(`{"data": …, "ok": true, "warnings": []}`; errors carry no `code` field, the identity
is the leading token of `error` up to the first colon).

**Note the integer-scaled fields.** `residual_percent_milli` and
`cost_per_worker_minute_ten_thousandths` are integers, not the house
decimal-as-string, precisely *because* the client must do exact integer arithmetic
with them (M1). A decimal string here invites a `parseFloat` and reintroduces the
float exposure the whole contract exists to avoid. The unscaled decimal strings are
**not** also shipped — two representations of one number is how they drift.

---

## 8A. The payload, key by key — every key's deriving section

Walked at this gate. A key with no deriving section is a mechanism with no contract; four
were found and all four are now derived.

| Key | Derived by | |
|---|---|---|
| `task_id` | §2.5 resolution | |
| `status` | §9A.1 | ⚠ was: "EconomicsStatusEnum, 12 values" and nothing else |
| `item_binding` | §2.5 (`get_task_budget_status.py:111`) | |
| `can_commit` | §9A.2 | ⚠ was: §8's own inline gloss, which is incomplete |
| `currency` | §6B — the valuation's `currency`; `null` when `saved` is `null` | ⚠ undefined for an unvalued item |
| `calculation_version` | HC-1, `calculator.py:20` (constant `1`) | |
| `config_fingerprint` | §9A.3 | ⚠ was: named in §8/§9.3/§9.5, defined nowhere |
| `item.client_id / article_number / quantity` | `items` columns; `article_number` is `String(128) NULL` and travels as `null` | |
| `item.label` | `items.item_category_snapshot`, `String(255) NULL` | |
| `saved.*` | §6 + §6B | |
| `model.cost_model_version_id / basis_version_id` | §2.3 selection | |
| `model.residual_percent_milli` | §3.1, §3.1B | |
| `model.constant_deduction_minor` | §3.1, §3.1B | |
| `model.cost_per_worker_minute_ten_thousandths` | §3.1B (persisted column × 10⁴) | |
| `model.is_purely_proportional` | §3.4 (`constant_deduction_minor == 0`) | |
| `typical.total_seconds / is_estimated / sections_without_sample / sections_total` | §5.2, §5.3A | |
| `typical.method / window_days / min_sample_size` | §2.4 constants, `budget_division.py:15-18` | |
| `anchors.is_fundable` | §4.1 (`break_even_price_minor is not null`) | |
| `anchors.break_even_price_minor` | §4.1, §4.2A | |
| `anchors.suggested_price_minor` | §4.4, §4.4A | |
| `anchors.infeasible_at_or_below_minor` | §4.2A | ⚠ was: used by §7.2, derived nowhere |
| `domain.*` | §7, §7A | |

### 8A.1 Corrections to §8's example

The example is a contract by demonstration — a frontend will copy it. Three values in it
are wrong:

- `"valuation_id": "ivl_…"` → **`"ival_…"`**. `ItemValuation.CLIENT_ID_PREFIX` is `ival`
  (`item_valuation.py:15`); no model in this domain uses `ivl`.
- `"break_even_price_minor": 1211364` → **`1211335`** (§4.4A).
- `"max_minor": 1635000` → **`1650000`**, and `"min_minor": 420000` stays (§7A.2).
  `1 635 000` is neither `ceil_to_step` nor `floor_to_step` of `1.35 × B` under either
  value of `B`.
- **Added at the projection r0 fold:** `"infeasible_at_or_below_minor": 0` → **`29`**
  (§4.2A's correction banner). The `0` was copied from the false "purely proportional ⇒ 0"
  claim, not computed. This section said "three values"; it is **four**.

`"residual_percent_milli": 22000` is **correct and easily misread**: it is the residual —
the share of the price left after all percentage terms — so the example's model deducts
78% in percentage terms. It is not "a 22% cost".

### 8A.2 The §1 element table, checked against the contract

| Element | Mockup | From the rules | |
|---|---|---|---|
| `1 425 SEK`/piece | `1 425` | `855 000 / 6 = 142 500` minor = `1 425.00` | ✓ |
| `8 550 SEK total` | `8 550` | `855 000` minor | ✓ (§7.4's `855 100` example is a *different*, deliberately non-multiple price) |
| `AT PRICE 2h 25m` | `2h 25m` | `budget = 188 100`; `centimin = round_he(188 100/13) = 14 469`; `seconds = round_he(14 469×3, 5) = 8 681` = `144.68 min` | ✓ **only if** the display rounds to nearest minute (§3.2A); truncation renders `2h 24m` |
| `TYPICAL 3h 25m` | `3h 25m` | `12 300 s = 205 min` exactly | ✓ |
| `suggested 2 025`/piece | `2 025` | `ceil_to_step(1 211 335, 15 000)/6 = 202 500` minor | ✓ |
| slider `700` … `2 700` | `700` / `2 700` | `700` ✓ / **`2 750`** ✗ | see §7A.2, owner card 3 |

---

## 9. Degradation, consistency and reconciliation

### 9.1 Non-`ok` statuses

> **SUPERSEDED by §9A.1's twelve-row table (D8, owner, 2026-08-19).** The rule below is
> kept as the recorded rejected branch, because the failure it produces is the one this
> feature could most easily have shipped: a `200`, a well-formed envelope, a correct
> status — and no slider, for every item nobody has priced yet. Read §9A.1 for the
> governing rule. What survives from this section unchanged: the *shape* discipline
> (absent structure, never zeros), the frame-keeping treatment, and §9.2.

`status` is the twelve-value vocabulary. When it is anything other than `ok` or
`infeasible`, `model`, `anchors` and `domain` are **`null`** — absent structure, never
zeros — while `item`, `saved` and `typical` stay fully populated. The screen keeps its
frame, names the missing thing, and disables the slider. This follows the pattern set
in the production-time handoff ("never hide the component and never show zeros") and
its status→treatment table applies unchanged.

**Two corrections to the paragraph above, both binding.** `item`, `saved` and `typical`
do *not* all stay populated — `saved` and `currency` are `null` when no valuation row
exists (§6B). And the "status→treatment table applies unchanged" claim is what D8
overturned: it is the shipped frontend contract's table, and amending it is a closeout
obligation (master plan §8), not an inherited default.

`infeasible` (allowance ≤ 0 at the saved price) is **not** a degraded state here: it is
a legitimate and important thing for this very screen to show, since fixing it is
exactly what the user came to do.

### 9.2 Unknown task, detached item

`404` for an unknown, deleted or cross-workspace task, via the existing resolution
(§2.5). `item_binding` of `detached` or `mismatched` returns `200` with `saved`,
`model`, `anchors` and `domain` all `null` — the task lost or swapped its primary item
and a price screen for it is meaningless, but that is an empty state, not an error.

### 9.2A `item_binding` wins over the status table — always, not sometimes (projection r0, L2)

§9.2 and §9A.1's table **collide on every occurrence of a non-`bound` binding**, not in an
edge case. Read at `get_task_budget_status.py:111`:

- **`mismatched`** requires `evaluation is not None`, so the branch always continues into
  `_build_evaluated_status` and the status is always `ok` or `infeasible` — §9A.1 rows A1/A2,
  which say the blocks are **present**, while §9.2 says all `null`.
- **`detached`** means `item is None`. Either the status is `not_evaluated` (row B10,
  present) or `ok`/`infeasible` (A1/A2, present). §9.2 says `null` on both paths.

**§9.2 governs.** It is the only rule that can be honoured: with no `Item` there is no
category, so no selection, no quantity, no rate — nothing from which a model, an anchor set
or a band could be derived. The status table describes what is *derivable when the item is
bound*; binding is upstream of it.

**The rest of the payload on those two paths, defined here because the serializer needs it
on the first request:**

| Key | `detached` | `mismatched` |
|---|---|---|
| `item` | **`null`** — there is no `Item` row at all | populated from the PRIMARY item |
| `saved`, `model`, `anchors`, `domain` | `null` | `null` |
| `typical` | **populated** — it derives from steps alone and stays honest | populated |
| `status` | as resolved | as resolved |
| `can_commit` | **`false`** — condition 3 fails | as resolved |
| `config_fingerprint` | `null` — the model is | `null` |

`item: null` requires §8's `item` object to be nullable; it was typed as always present.

### 9.3 Reconciliation at save time

The client echoes `config_fingerprint` and asserts the commit response's
`production_budget_minor` / `allowed_worker_minutes` against what it displayed. A
mismatch means the configuration moved mid-drag (a new basis or model version was
published) or that the ≤ `(n+1)/2` minor-unit approximation crossed a display
boundary. Either way the correct behaviour is refetch-and-tell, never silent save.
This is HC-5 made operational.

### 9.4 The divisor

The frontend applies `max(1, quantity)` as its divisor. §2.7 establishes that
`quantity >= 1` is an application invariant with no storage constraint behind it, and
a legacy `0` would otherwise be a division by zero on the screen's headline number.

### 9.5 Staleness

The payload is constants; they stop being constant when someone publishes a new cost
model or basis version, edits the item's quantity or category, or changes the task's
step set. `config_fingerprint` covers the first; refetch on item and step-transition
events covers the rest. There is no push channel in v1 — the screen is short-lived and
modal.

---

## 9A. Status totality, `can_commit`, and M6 — the fingerprint

### 9A.1 The status vocabulary is a branch, and §9.1's rule blanks the screen

**Fact §2.3 gets wrong.** `resolve_item_economics_status` does **not** "resolve the
twelve-value `EconomicsStatusEnum`". It can return only **ten** of the twelve: the five
`CONFIGURATION_FAILURE_PRECEDENCE` values (`configuration.py:14-20`) plus **all five**
`ITEM_READINESS_PRECEDENCE` values (`:33-39`), every one of which is reachable
(`configuration.py:135-169`).

> **Corrected by the coordinator at the fold, 2026-08-19: this said "nine".** It is ten —
> `ITEM_READINESS_PRECEDENCE` has five members and no member of it is unreachable. The
> B1–B10 table immediately below already enumerated ten, and §12A independently states
> "eleven non-`ok` values", so only this sentence was wrong; the table and the test
> criterion built on it are correct and unchanged. Recorded rather than silently fixed
> because a miscount inside a *correction of a miscount* is the exact failure mode the
> charter names: enumeration is one of the two places these documents reliably break, and
> a wrong count reads as authoritative precisely when it appears beside a right one.
It can never return `ok` and never `infeasible` — those two are produced only by
`_build_evaluated_status` (`get_task_budget_status.py:150`), and **only when a committed
`ItemCostEvaluation` exists**. The published frontend contract already says this
(`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` §6: "Branch A — this task has
a committed evaluation … Branch B — no committed evaluation", ten values).

**The consequence §9.1 did not see.** §9.1 says the `model`, `anchors` and `domain` blocks
are `null` for every status other than `ok` and `infeasible`, and imports the operational
handoff's table "unchanged" — a table whose rule is "everywhere else … the numerics are
`null`". Composed with the fact above:

> A task with no committed evaluation has status `not_evaluated` or `item_unvalued`,
> therefore no `model`, no `anchors`, no `domain` — **no slider**. An item nobody has
> priced yet, and a task nobody has committed yet, are exactly the two states this screen
> exists to resolve (§1). As specified, the screen works only for tasks that have already
> been priced and committed.

Nothing here fails loudly: the endpoint returns `200` with a well-formed envelope and a
correct status, and the slider is simply never there.

**The corrected rule is derivable, and it is not "ok or infeasible".** The `model` block
needs exactly what M1 consumes: a selected basis version, a selected cost model version,
an agreeing currency, and a purchase cost if a purchase term exists. That predicate is
total over all twelve values:

| # | Status | Committed eval? | `model`/`anchors`/`domain` | Why |
|---|---|---|---|---|
| A1 | `ok` | yes | **present** | everything resolves |
| A2 | `infeasible` | yes | **present** | §9.1: the state the screen exists to fix |
| B1 | `item_missing_major_category` | no | `null` | no group ⇒ no basis, no model |
| B2 | `not_configured_no_cost_group` | no | `null` | idem |
| B3 | `not_configured_ambiguous_cost_group` | no | `null` | idem |
| B4 | `not_configured_no_basis_version` | no | `null` | no rate |
| B5 | `not_configured_no_cost_model_version` | no | `null` | no terms |
| B6 | `item_unvalued` | no | **present iff collapsible** † | configuration fully resolved; only the price is missing, and the price is the slider's variable |
| B7 | `item_missing_expected_price` | no | **present iff collapsible** † | idem |
| B8 | `item_missing_purchase_cost` | no | `null` | `constant_deduction_minor` is undefined (§3.1) |
| B9 | `currency_mismatch` | no | `null` | the three-way equality of `validate_currency_equality` is broken |
| B10 | `not_evaluated` | no | **present** | configuration and price both resolved |

Twelve rows, twelve values, each decidable from the selection alone.

> **† Qualification added at the projection r0 fold (2026-08-19, L3).** B6 and B7 are
> **not** unconditionally present. `ITEM_READINESS_PRECEDENCE` places `ITEM_UNVALUED` and
> `ITEM_MISSING_EXPECTED_PRICE` **above** `ITEM_MISSING_PURCHASE_COST`
> (`configuration.py:33-39`), so a higher-precedence check fires first and the vocabulary
> cannot report that the purchase cost is *also* missing. When the cost model carries a
> non-deleted `item_purchase_cost` term and no purchase cost is available,
> `collapse_terms` returns `None` (§3.1B) and there is no model to publish.
>
> **Contract:** on B6 and B7 the three blocks are present **iff the model collapses** — i.e.
> the model has no purchase term, or a purchase cost exists. Otherwise all three are `null`,
> exactly as B8.
>
> Without this qualification a criterion asserting "present" on B6/B7 would hold only for a
> cost model without a purchase term, making the expected outcome a property of the fixture
> rather than of the status — which is what charter rule 2's companion forbids.
>
> **This does not reopen D8 or D9.** Under D9's flow the purchase price is set first, which
> creates the valuation row and makes the model collapsible; the case bites only where D9's
> precondition does not hold — the precondition master plan §8 obligation 6 exists to write
> down. A contract-text correction, not a lived failure.

> **RATIFIED — D8 (owner, 2026-08-19). This table governs; §9.1 is superseded.** Owner,
> verbatim: *"the frontend will allow to display the handle to set a expected sold price
> ( as the recommendation says, that is the whole point of that page, wheter there is or
> no expected sold price )."*
>
> The table publishes monetary figures under `item_unvalued` and
> `item_missing_expected_price`, for which the shipped frontend contract
> (`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` §6) says numerics are
> `null`. That is a contract change with a live consumer, which is why it needed an owner
> and not an implementer: amending §6's table is a **closeout obligation** (master plan
> §8, obligation 5), enumerated, and not a licence to revise that document generally.
> HC-3 is untouched — this endpoint is ADMIN/MANAGER only, so no monetary key reaches a
> worker or seller surface.

**Which configuration M1 publishes** — undefined until now, and it matters for A1/A2: the
`model` block is always built from the **live** selection (`_load_preview_inputs`), never
from the committed evaluation's snapshot. The screen is projecting a *new* price, so live
is right; and the possibility that live and the committed snapshot disagree is precisely
what §9.3's reconciliation exists to catch.

**One inaccuracy in §9.1's gloss.** "`infeasible` (allowance ≤ 0 at the saved price)" — the
code tests the **committed** evaluation's `allowed_worker_minutes`
(`get_task_budget_status.py:150`), which is the allowance at the *committed* price. When a
valuation has moved since the last commit, the two differ.

### 9A.2 `can_commit` — the real admission predicate

§8's gloss ("task state ∈ `_ADMITTED_STATES` and PRIMARY present") is missing three of the
five conditions the commit path actually enforces, and D4 made this field load-bearing:
a `true` that is wrong means the screen offers a button whose press is a guaranteed error,
which §11 names as the thing to avoid.

`POST /tasks/{task_client_id}/evaluations/commit` succeeds only when **all** of:

1. the task exists and is not deleted — else `404` (`:113-114`);
2. `task.state ∈ _ADMITTED_STATES` — else `ITEM_COST_TASK_TERMINAL` (`:115-116`);
3. an active PRIMARY `TaskItem` exists — else `ITEM_COST_NO_PRIMARY_ITEM` (`:126-127`);
4. its `Item` row is not deleted — else `404` (`:135-136`);
5. `resolve_item_economics_status(effective, selection, live_terms)` is **`not_evaluated`**
   — else the status is translated into a refusal by `_status_error` (`:228-230`).

Condition 5 is the one §8 misses entirely, and it has an asymmetry worth stating because
it is invisible from the outside: `effective` is `None` whenever **no current valuation row
exists**, *regardless of the price in the request body* (`:212-213`). So:

- valuation row exists, `expected_sale_price_minor` is `NULL` (status
  `item_missing_expected_price`) → **commit with a price succeeds**;
- **no valuation row at all** (status `item_unvalued`) → **commit always fails**, price in
  the body or not.

**Contract for the published field** — price-independent, because a GET cannot know which
price the user will choose:

```
can_commit = conditions 1–4
             AND a current valuation row exists
             AND the configuration selection resolved (not B1–B5)
             AND currency agrees (not B9)
             AND (no purchase term OR purchase_cost_minor is present)   (not B8)
```

~~Equivalently: `can_commit` is true exactly for statuses A1, A2, B7 and B10~~ — everything
except the expected price itself, which Save supplies.

> **RETRACTED at the projection r0 fold (2026-08-19, L14). The two forms are not
> equivalent, and the status form is unsafe.** A1/A2 are produced by
> `_build_evaluated_status` (`get_task_budget_status.py:150`) from the **committed**
> evaluation, which never consults `resolve_item_economics_status`. So a task committed while
> the configuration was healthy keeps status `ok` after the cost model version is deleted or
> its `effective_to` passes (`configuration.py:52-61` compares against `today_utc()`). The
> **live** selection is then B5, `commit_item_cost_evaluation` refuses at `:229-230`, and the
> status form publishes `can_commit: true` for a button whose press is a guaranteed error —
> precisely the failure §11 names and the reason D4 made this field load-bearing.
>
> **The block form above governs, and it is computed from the live selection.** The status
> shorthand is retained struck through rather than deleted, because it reads as a
> simplification anyone would reach for again. **`item_unvalued` (B6) yields
`can_commit: false`**, which would leave the screen with a slider and no way to save
through D4's endpoint.

> **RESOLVED — D9 (owner, 2026-08-19): Save stays commit-only; the B6 state does not
> arise.** Owner, verbatim: *"the frontend will build a default behaviour of telling the
> user to first place the purchase price of an item if missing, if that is set then the
> page for changing the expected sold price behaves normally, allowing the user to set the
> price and see the impact."*
>
> The card asked whether Save must set the price before committing. It does not, because
> the owner's flow removes B6 before the screen is reachable. Verified by the coordinator,
> 2026-08-19:
>
> 1. `purchase_cost_minor` lives **on the valuation row**, so "the purchase price is set"
>    and "a valuation row exists" are the same fact.
> 2. `PUT /items/{id}/valuation` accepts a purchase cost **alone** — the validator requires
>    only one of the two amounts
>    (`services/commands/item_economics/requests/__init__.py:177-179`) and the table's
>    `ck_item_valuations_amount_present` CHECK agrees (`item_valuation.py:34`).
> 3. That row yields **B7**, which is commit-admissible: `effective` is built from the row
>    with the request's price substituted, resolves to `not_evaluated`, and commits.
>
> **D4's one-call promise therefore holds unchanged**, and set-then-commit is not built.
>
> **The precondition the backend cannot enforce — recorded because it is the entire basis
> of this resolution.** If a later frontend change skips the purchase-price prompt (for
> instance as an optimisation when the cost model carries no purchase term), the item
> returns to B6 and Save fails on every press, saving nothing. `can_commit: false` is
> exactly the signal that guards it, which is why this predicate is load-bearing rather
> than informational. **Closeout obligation** (master plan §8, obligation 6): the frontend
> handoff states that no valuation row means Save cannot commit and the purchase price
> must be set first — Save will not create one.

### 9A.3 M6 — `config_fingerprint`

A fingerprint is a rule-6 mechanism by name; this one was named in §8, §9.3 and §9.5 and
defined in none of them. Contract:

```
config_fingerprint = "{cost_model_version_id}:{basis_version_id}:v{CALCULATION_VERSION}"
```

- **Full `client_id`s, never truncated.** §8's `"cmv_7a1:pcbv_3f9:v1"` is illustrative
  shorthand; client_ids are prefixed ULIDs (`identity.py:9-11`) and truncation would let
  two versions of one workspace share a fingerprint.
- **Fixed order**, cost model then basis then version. It is a concatenation, not a hash:
  there is nothing to compress, and an opaque digest would cost the client the ability to
  say *which* half moved.
- **`null` exactly when the `model` block is `null`** — there is no selection to fingerprint.
- **Identity.** The `v{CALCULATION_VERSION}` component is the formula's identity, so a
  future bump invalidates every held fingerprint. The label `break_even_band_v1` (§7A.1)
  is deliberately **not** in it: the band is a display derivation, and a client holding a
  stale band is not holding a stale budget.

**What it covers, and what it provably covers.** The pair of ids covers the rate and the
**entire term set** — not by assumption but because cost model terms are immutable for the
life of their version (§2A.1.2), so no term can change under a fixed
`cost_model_version_id`. It does **not** cover `quantity`, `item_category_snapshot`, the
task's step set, or the typical (which moves whenever any task in the workspace completes a
step); §9.5 already assigns those to refetch-on-event, and that division is now explicit
rather than implied.

**Selection can change with no row written.** `is_applicable` compares against
`today_utc()` (`configuration.py:52-61`), so a version with a future `effective_from`
takes over at 00:00 UTC. The fingerprint does change then — different ids — so this is
detected, but only by a client that re-reads it.

**§9.3's "the client echoes `config_fingerprint`" is not implementable and must not be
attempted.** `POST /tasks/{task_client_id}/evaluations/commit` accepts
`task_client_id`, `expected_sale_price_minor`, `purchase_cost_minor` and `label`
(`commit_item_cost_evaluation.py:396-412`) and has no fingerprint field; adding one is a
change to an existing endpoint's payload, which HC-2 forbids and HC-2a's enumerated
four-artifact exception does not cover. **The reconciliation is entirely client-side**, and
that is all §9.3's second sentence ever needed:

1. the client holds the `config_fingerprint` it rendered with;
2. on commit, it compares the response's `production_budget_minor` /
   `allowed_worker_minutes` against what it displayed;
3. on mismatch it refetches the price-scenario and compares fingerprints — **equal**
   ⇒ the `(n+1)/2` approximation crossed a display boundary (§3.2); **different**
   ⇒ the configuration moved mid-drag. Refetch-and-tell either way, never silent save.

---

## 10. Non-goals (v1)

Each of these was on an earlier mockup and was cut by the team on 2026-08-19 with
"later we will expand it based on usage". Recorded so the cut is a decision with a
date, not an omission:

- **Per-section breakdown** (`WORK ON THIS ITEM` table with per-section typical and
  at-price columns). Consequence: `divide_production_budget` is **not called** by this
  feature at all — no largest-remainder allocation, no per-step split, no share states.
- **The already-logged card** (worked seconds, consumed cost, percent of allowance).
  Consequence: `progress` is absent from the payload; see §5.4 and owner card 2 for
  what that costs.
- **The cost-of-work card** (typical work cost, budget, gap in money).
- **The allowance-vs-typical headroom bar.**
- **The "leaves 22% of the store price" percentage headline** — see §3.4 for what must
  be true before it can be printed.
- **`terms[]`** (§3.3).
- **A worker/seller variant** of this endpoint (HC-3).
- **Any write.** This pipeline ships one GET. The Save button uses existing endpoints
  (owner card 1 decides which).
- **Multi-task items.** The screen is entered from a task. An item-scoped variant for
  items with several episodes is deferred.

---

## 11. Relation to existing domains and to the write path

This feature reads across three existing boundaries and changes none of them:

- **Item economics** (`domain-item-economics`) — owns the price→budget formula (§2.1),
  the configuration selection (§2.3) and the status vocabulary. This endpoint is a new
  read model *inside* that boundary; the architecture-graph delta records it as a
  `projection` contained by `domain-item-economics`, alongside
  `projection-item-economics-task-budget-allocations` and
  `…-task-production-time`.
- **Working sections** — owns the typical (§2.4). Consumed through the shared
  statement, not re-derived.
- **Tasks** — owns the task, its PRIMARY item and its steps (§2.5).

**The write path is unchanged and remains the only authority.** Two existing endpoints
can save a price: `PUT /items/{id}/valuation` writes the chain, previews, and leaves the
task's committed budget stale; `POST /tasks/{id}/evaluations/commit` with
`expected_sale_price_minor` mirrors the price into the chain *and* supersedes the
committed evaluation, so the budget actually moves.

**Save commits (D4, owner-ratified 2026-08-19).** The screen's Save button is
`POST /tasks/{task_client_id}/evaluations/commit` carrying
`expected_sale_price_minor` — one call that both prices the item and moves the task's
working budget. The rejected branch, price-now/commit-later, fails **silently**: the
floor keeps working to an allowance the price no longer funds and nothing surfaces the
gap until the job overruns.

Two consequences this pipeline owns even though it ships no write:

1. **`can_commit` is load-bearing, not informational.** Commit is admitted only for
   tasks in `_ADMITTED_STATES` with an active PRIMARY item (§2.5). When `can_commit` is
   `false` the Save button must be disabled with the reason, because pressing it is a
   guaranteed error — the screen would otherwise offer an action it knows will fail.
2. **Reconciliation is mandatory, not advisory** (§9.3): the commit response is where
   the published display model meets the persisted authority (HC-5), so the client
   asserts the returned `production_budget_minor` / `allowed_worker_minutes` against
   what it displayed and refetches on mismatch.

Both belong in the closeout handoff's flow narrative.

---

## 12. Testing expectations

Charter standing rules apply in full. Named specifically, because these are where this
feature can fail silently:

1. **M1 fidelity is a test, not a claim.** A property test asserts
   `| budget_published(P) − budget_persisted(P) | ≤ (n+1)/2` against the real
   `calculate_term_amounts` / `calculate_production_budget` path, over an enumerated
   set of model shapes: one percentage term; two distinct percentages; **two equal
   percentages** (the §4.2 dip); percentage + fixed; percentage + purchase;
   percentage summing to exactly 100; percentage summing above 100. Rule 2 —
   enumerate, never sample: one row per shape, each asserting its one exact outcome.
2. **The two-step seconds conversion.** A row where the shortcut
   (`budget → seconds` directly) and the contract (`budget → 2dp minutes → seconds`)
   disagree, asserting the contract's value. Named mutation (rule 11): replacing the
   two-step conversion with the shortcut in the query service must turn this test red.
3. **Break-even is exact at its own boundary.** For a fixture model,
   `allowance_seconds(break_even) >= typical_total` and
   `allowance_seconds(break_even − 1) < typical_total`. Both halves, or the test
   passes for a break-even that is merely large enough.
4. **M3 fallback rows, enumerated:** all sections sampled; one section null (median
   substituted); every section null (`total_seconds == 0`, `is_estimated`, M2 `null`);
   a section whose only steps are `SKIPPED`/`CANCELLED`/`FAILED` (excluded from the
   participating set — one row per excluded state, not one row for "an excluded
   state"). Rule 2's companion applies: each fixture makes its own predicate the only
   reason its outcome holds.
5. **Degenerate model** (`residual_percent_milli <= 0`): `is_fundable: false`,
   `break_even: null`, `domain: null` — asserted as absence, not as zero.
6. **Status matrix.** One row per non-`ok` `EconomicsStatusEnum` value, each asserting
   that `model`/`anchors`/`domain` are absent and `typical`/`item`/`saved` are
   populated. Twelve values, twelve rows.
7. **Invariants on the production object type** (rule 3): the M1 fidelity test holds
   real `CostModelTerm` ORM instances, never hand-built dicts, because the shape guard
   in `calculate_term_amount` is part of what is being proven.
8. **No monetary leak** (HC-3): a route-level test that WORKER and SELLER receive
   `403`, in the same style as the existing role tests in
   `test_item_economics_router.py`.
9. **Route mirror**: the four HC-2a artifacts move together; the count assertions go
   25 → 26.

---

## 12A. Test obligations created by the round-3 contracts

§12 stands; these are additions, plus one correction to it.

**Correction to §12.6.** "One row per non-`ok` `EconomicsStatusEnum` value … Twelve values,
twelve rows" cannot all be true: there are eleven non-`ok` values, and §9.1 exempts
`infeasible` as well, leaving ten. The criterion is now **twelve rows over all twelve
values**, each asserting its own row of §9A.1's table — the seven `null` rows *and* the
five present rows, because "the block is present here" is exactly the half that fails
silently if the predicate is written as `status is OK`.

1. **`round_half_even` on negative operands** (§3.1A). Enumerated rows around a tie in both
   directions: `(−3,2) → −2`, `(−5,2) → −2`, `(3,2) → 2`, `(5,2) → 2`, `(−1,2) → 0`.
   A `divmod`-free implementation that truncates passes the positive rows and fails these;
   that is the point. Named mutation (rule 11): replacing `floor` with truncation in the
   helper's **definition** must turn this test red.
2. **Tie reachability, per operation** (§3.1A's table). One row proving a tie is reached in
   `round_half_even(P × residual, 100_000)` and one in the rate division; and one row
   asserting the seconds conversion is tie-free over an enumerated `cm` range, so a future
   change to that operation's rounding mode is provably inert.
3. **`n` in the bound** (§3.2A). The assertion is `2*abs(delta) <= n + 1` in integers, with
   `n` the count of non-deleted percentage terms — not `len(terms)`.

   > **CORRECTED at the projection r0 fold (2026-08-19).** This row read: *"Named mutation:
   > defining `n` as the term count must turn the two-equal-percentages row red."* **That
   > mutation cannot turn any row red, for two independent reasons.** (a) *Wrong direction*:
   > `len(terms) >= n` always, so the mutation only enlarges the right-hand side of a `<=`
   > bound, and a weakened bound never fails a case that already passed. (b) *Wrong row*: on
   > the named shape — two equal percentage terms — every term **is** a percentage term, so
   > `len(terms) == n == 2` and the mutation is the identity. Swept over all seven §12.1
   > shapes against the real `calculate_term_amounts` path for `P ∈ [0, 40 000)`: inert on
   > every one. This is charter rule 11 exactly — *a safety test that survives the defect it
   > exists to prevent is decoration*. As written the row proved the bound holds and nothing
   > about `n`.
   >
   > **Replaced by two mutations, because they bite on different things:**
   >
   > - **Tightness.** The bound is attained for odd `n` (for even `n`, `2|Δ|` is even so
   >   `2|Δ| <= n+1` collapses to `<= n`). On `percentage + fixed` (`n = 1`) it is attained
   >   at `P = 25`: `round_he(0.78 × 25) = 20`, `round_he(0.22 × 25) = 6`, so `Δ = 1` and
   >   `2|Δ| = 2 = n+1`. **Named mutation: weaken `n+1` to `n` in the assertion helper's
   >   definition → that row red.** This is what proves the criterion is not vacuous, and it
   >   is also the only thing that pins §3.2A's "attained, not merely bounded" claim.
   > - **The mechanism under test.** **Named mutation in `collapse_terms`' definition:
   >   derive `residual_percent_milli` with a float multiply
   >   (`int(float(percent_value) * 1000)`) instead of `int(value.scaleb(3))` → `Δ` leaves
   >   the bound.** This is the defect the bound exists to detect and it was unnamed.
   >
   > Both re-derived independently by the coordinator at the fold; the `P = 25` attainment
   > was recomputed by hand.
4. **Break-even minimality** (§4.2A). §12.3's two halves, plus a row on the mockup's own
   data asserting the exact literal **`1_211_335`** — a row that fails against §4.4's
   `1_211_364` and is the regression guard for the defect this gate found.
5. **`P_hi` independence** (§4.2A). A model whose break-even exceeds `1.35 ×` any plausible
   band still resolves; a test constructed so that a `P_hi` seeded from `domain.max_minor`
   cannot terminate.
6. **`infeasible_at_or_below_minor`** (§4.2A). One row with `constant_deduction_minor > 0`
   asserting the exact boundary and that `min_minor` is floored above it; one degenerate
   model asserting it is the cap and not `null`.
7. **M3 usability** (§5.3A). A section whose typical is exactly `0` with five qualifying
   groups: `sections_without_sample` counts it and the median is substituted for it. Under
   §5.2's "NULL" wording this row is red.
8. **Median quantisation** (§5.3A). An even number of usable typicals differing by an odd
   number, so the median is `x.5`, with two sections substituted — asserting per-section
   quantisation, which differs from sum-quantisation by exactly one second on this fixture.
9. **The band** (§7A). The mockup's data asserting `step_minor == 15_000`,
   `min_minor == 420_000`, `max_minor == 1_650_000`; and `quantity = 7` asserting the exact
   literals **`step_minor == 15_400`, `min_minor == 415_800`, `max_minor == 1_647_800`**.

   > **CORRECTED at the projection r0 fold (2026-08-19).** This row ended: *"and
   > `quantity = 7` asserting `step_minor % 7 == 0` — the divisibility that the
   > derive-per-piece order guarantees by construction and the derive-then-snap order
   > breaks."* **The derive-then-snap order does not break divisibility** — "snap **up to a
   > multiple of `Q`**" makes divisibility by `Q` true by construction, which is what the
   > phrase means. Computed for `B = 1 211 335`, `Q = 7`: the contract order gives
   > `15 400 / 415 800 / 1 647 800`; the mutated order gives `15 001 / 420 028 / 1 650 110`
   > — and `15 001 = 7 × 2 143`, so `step_minor % 7 == 0` **passes under the mutation**. At
   > `Q = 6` the two orders are identical outright. Every assertion the row named survived
   > the mutation it named.
   >
   > The drift was from §7A.1 itself, which states the real failure correctly — the wrong
   > order *"destroys the nice value (`15 142 → 15 144`)"* — and never claimed it breaks
   > divisibility. The criterion asserted the property that survives and omitted the one
   > that breaks. **The exact literals above go red under the mutation** (15 001 ≠ 15 400,
   > 420 028 ≠ 415 800, 1 650 110 ≠ 1 647 800). `step_minor % Q == 0` and the
   > multiple-of-step assertions are kept as by-construction invariants, but they are no
   > longer described as the mutation's target. All six values recomputed by the coordinator
   > at the fold.
10. **`can_commit`** (§9A.2). One row per condition, each fixture violating **only** its own
    condition (rule 2's companion), plus the two asymmetry rows: valuation-with-null-price
    ⇒ `true`, no-valuation-row ⇒ `false`. A test that only exercises task state passes
    against §8's incomplete gloss.
11. **`config_fingerprint`** (§9A.3). Full ids, fixed order, `null` with a `null` model; and
    a row proving a *new cost model version* changes it while *the same version re-read*
    does not.

---

## 13. Owner decisions

### 13.1 Settled during shaping (owner conversation, 2026-08-19 — recorded in `owner_decisions.md`)

**D1 — per-piece is a frontend display transform.** The wire carries whole-item minor
units; `quantity` travels only as the divisor. Owner: *"about the price per quantity i
agree with you and that will be a frontend boundery where it gets the quantity and
uses that as denominator for dividing the expected sold price."* Consequence: §8.4 of
the operational handoff keeps its contract and loses only its display prohibition, at
closeout.

**D2 — a dedicated constants endpoint, not a per-frame preview.** Owner: *"I like the
idea of creating an endpoint specialized in bringing this already configured values so
the frontend only needs to use them as constants to modify the ui."* Rejected
alternative: a debounced server round trip per drag, which cannot hold 60fps and makes
the screen unusable offline-ish on a warehouse tablet.

**D3 — the simplified screen is v1; expansion follows usage.** Owner: *"after some
talk with the team we have simplify the visual aspect of the page for changing the
price, this will make what the backend sends more light, later we will expand it base
on usage."* The cut list is §10, dated, so each item returns as an additive change.

### 13.2 Ratified round 2 (owner, 2026-08-19)

All four round-1 cards answered, every recommendation accepted. Owner, verbatim:
*"about the 4 owner cards all recommendations you have placed are correct."*

| D | decision | folded into |
|---|---|---|
| D4 | Save commits — one call that prices **and** moves the budget | §11 (with `can_commit` and reconciliation consequences) |
| D5 | `AT PRICE` is **gross** — sunk time is not deducted | §5.4 (divergence accepted, must be named in the handoff) |
| D6 | Slider band is **derived** (`break_even_band_v1`) | §7.1, §7.2 |
| D7 | No typical evidence ⇒ **show nothing**, with a reason | §5.3, §4.1 |

**Ledger empty as of round 2.** No decision in this intention is a guess; each rejected
branch is recorded with the failure it would have produced, in `owner_decisions.md`.

### 13.3 Ratified round 4 — the mechanism-inventory cards (owner, 2026-08-19)

| D | decision | folded into |
|---|---|---|
| D8 | The screen works for an item nobody has priced — §9A.1's twelve-row table governs, `model`/`anchors`/`domain` present for B6, B7, B10 | §9A.1 (ratification banner), §9.1 (superseded, kept as the rejected branch) |
| D9 | Save stays **commit-only**; the never-priced state does not arise, because the frontend sets the purchase price first — which *is* the valuation row | §9A.2 (with the precondition the backend cannot enforce) |
| D10 | Accept `2 750`/piece at the band's top; multipliers stay `0.35`/`1.35` | §7A.2 |

Two of the three were product calls the code genuinely could not settle. **D9 was not** —
it was answered by a fact about the frontend's flow that no artifact in this repository
carried, and the answer is only sound while that flow holds. That is why it is recorded
with its precondition and a closeout obligation rather than as a decision that disappears
once made: an assumption about another codebase, written down, is a contract; unwritten,
it is a defect waiting for the optimisation that removes it.

**Ledger empty.** Gate **PASSED**.

---

## 14. Changelog

**Round 1 — 2026-08-19, shaped from the owner conversation of the same day.**

Shaped from three mockups in sequence: two rich variants of the "Expected sold price"
screen, then the simplified variant the team settled on. The rich variants were mapped
against the shipped backend during the conversation and the mapping is preserved here
where it constrains v1 (§3.4 the percentage headline, §5.4 the gross/net divergence,
§10 the cut list) — the analysis is not discarded merely because the pixels were.

Resolutions made during shaping rather than deferred:

- **Term array vs collapsed residual** — resolved to the collapsed form (§3.1) with a
  proven error bound (§3.2) and a stated return path (§3.3). The draft wavered; the
  deciding argument was §4.2, that the persisted per-term form is non-monotone and
  cannot be safely bisected.
- **Chip driven by curve vs by anchor** — resolved to anchor (§4.3). The curve-driven
  reading was the obvious implementation and is wrong at exactly the pixel the user
  is looking at.
- **`typical` fallback: copy the allocator's `Fraction(1,1)` or not** — resolved to
  *not* (§5.3). A proportional fallback is meaningless as a duration.
- **Where the byline's user shape comes from** — resolved to re-declaration over a
  cross-domain import (§6), consistent with HC-2 independence.
- **Route naming** — `price-scenario`, because `basis` already means
  `production_cost_basis_version` in this domain (§8).
- **Item-scoped vs task-scoped route** — resolved to task-scoped (§8), because the
  participating section set does not exist without a task and the paired write is
  task-scoped.

Four questions were **not** resolvable from the conversation or the code and are owner
cards (§13.2). Each is genuinely a product call: what Save means, whether a pricing
question should see sunk time, where a slider's edges come from, and what to show a
manager pricing an item nobody has evidence for.

**Round 2 — 2026-08-19, owner ratification.** All four cards answered in one pass, every
recommendation accepted (D4–D7, §13.2). Folded into §11 (Save commits), §5.4 (gross),
§7.1 (derived band) and §5.3 (show nothing); each rejected branch kept beside its
decision so the reasoning survives the answer. Status draft → **resolved**; the
decisions ledger is empty.

Two obligations were *created* by the answers rather than merely recorded by them, and
both are new to round 2:

- **D4 makes `can_commit` load-bearing.** In round 1 it was a convenience field. Now
  that Save is the commit call, a `false` value means the button must be disabled: the
  screen would otherwise offer an action it already knows the admission rules will
  reject. Downstream criteria must cover the disabled path, not just the payload key.
- **D5 obliges the closeout handoff to name its own divergence.** An accepted
  inconsistency that is not written down is indistinguishable from an undetected one;
  the frontend has to be told why two screens disagree before a manager asks.

Next: **mechanism-inventory**. The claims most worth attacking there are M1's
`(n+1)/2` error bound and M2's monotonicity argument — the two places where this
intention trades exactness for safety and would fail silently if the trade is wrong.

**Round 3 — 2026-08-19, mechanism-inventory gate.** All eight mechanisms swept at equal
depth against source re-read at head `f1c0ebb`. Verdict `OWNER_DECISIONS_PENDING`: three
cards open, so the gate holds and the implementation-planner does not start.

*Round 2's closing nomination was wrong about where the weakness was, which is why the
prompt forbade using it as a scope.* Both nominated claims **survived**: the `(n+1)/2`
bound is sound and attained (§3.2A), and the monotonicity argument is sound once stated
about the right function (§4.2A). The defects were in the mechanisms nobody flagged — M5's
band, which was circular and specified by two adjectives, and §9.1's status rule, which
blanks the screen for the two states the screen exists to resolve.

Added, all as lettered sections so no existing citation moved: §2A (citation corrections
and three unstated grounding facts), §3.1A (the two-language `round_half_even` contract
with per-operation tie reachability), §3.1B (input types, canonicalisation, and the rate
§2.2 asked to be named), §3.2A (`n`, and the bound's integer assertion form), §4.2A (the
search, the monotonicity repair, `P_hi` decoupled from §7, and
`infeasible_at_or_below_minor` defined), §4.4A (the step helpers and the corrected
break-even), §5.3A (usability, median quantisation, counter semantics), §6B (M4's absent
cases), §7A (M5 made decidable), §8A (the key walk and corrected example values), §9A
(status totality, `can_commit`, and M6), §12A (the test obligations these create).

Changed, with reasons, each carrying shipped-behaviour consequence:

- **`break_even_price_minor` for the mockup's data: `1 211 364` → `1 211 335`** (§4.4A).
  §4.4 solved a real-arithmetic equation; §4.1 defines a least-integer search. The
  definition governs. `suggested_price_minor` is unchanged, which is how this survived
  round 2.
- **M5's step rule replaced outright** (§7A.1). "A nice step near span/80, snapped up to a
  multiple of `quantity`" was circular *and* adjectival *and* reproduced none of its own
  worked figures. Replaced by a per-piece two-significant-digit rule that reproduces
  `15 000` / `25`-per-piece from the data and makes divisibility by `quantity` hold by
  construction.
- **`max_minor` for the mockup's data: `1 635 000` → `1 650 000`**, and the mockup's
  `2 700`/piece top end is **not reproducible** under D6's ratified multipliers (§7A.2).
  D6 stands; the evidence it was accepted on does not. Owner card 3.
- **§9.1's degradation rule replaced by §9A.1's twelve-row table** — pending owner card 1,
  which is why §9.1 still stands as written for now.
- **`can_commit` gains three conditions** (§9A.2); `item_unvalued` yields `false`, which
  D4's Save flow has no path around. Owner card 2.
- **§2.3's "resolves the twelve-value enum" corrected to ~~nine~~ ten** (§9A.1) — `ok` and
  `infeasible` require a committed evaluation and come from a different function. *The
  round-3 correction itself said "nine" and was corrected to ten at the round-4 fold; see
  the note in §9A.1.*
- **`saved` and `currency` may be `null`** (§6B), overriding §9.1's "fully populated".
- **§9.3's "the client echoes `config_fingerprint`" retired** (§9A.3): the commit endpoint
  has no such field and HC-2 forbids adding one. The reconciliation is client-side, which
  is all the mechanism ever required.

**Round 4 — 2026-08-19, owner ratification and the coordinator's fold. Gate PASSED.**

All three round-3 cards closed: D8 (the screen works for an unpriced item), D9 (Save stays
commit-only), D10 (accept `2 750` at the band's top). Folded into §9A.1, §9A.2 and §7A.2,
each with its rejected branch kept beside it. §9.1 is marked **superseded** rather than
deleted — the rule it states is the single most shippable failure this feature had, and a
rejected branch removed from the record is a branch that gets re-proposed.

Corrected at the fold, by the coordinator:

- **§9A.1's "can return only nine of the twelve" → ten.** `ITEM_READINESS_PRECEDENCE` has
  five members, all reachable. The B1–B10 table beside it already enumerated ten and §12A
  already said "eleven non-`ok` values", so the sentence disagreed with two correct
  neighbours. Left visible in §9A.1 with its reason: a miscount inside a correction of a
  miscount is the charter's named failure mode, and it reads as authoritative precisely
  because it sits beside a right count.
- **Owner card 3's story overstated its premise** ("no pair of multipliers gives both 700
  and 2 700"); `(0.35, 1.337)` gives both, as the card's own second branch concedes. Noted
  at §7A.2 so D10 is not recorded as resting on a false claim. The decision is unaffected.

**What round 4 did not change.** No mechanism was reopened; no contract from round 3 was
weakened. D9 is the only decision whose soundness depends on something outside this
repository — a frontend flow that guarantees a valuation row exists before the screen is
reachable — and it is recorded at §9A.2 with that precondition explicit and a closeout
obligation attached, because an assumption about another codebase is a contract when it is
written down and a latent defect when it is not.

Next: **implementation-planner**. The mechanisms are contracted, the ledger is empty, and
§12A already enumerates the test obligations the round-3 contracts created — those are the
planner's raw material for the phase criteria, not a second design pass.

**Round 5 — 2026-08-19, projection r0 fold (phase 1). Four upstream corrections.**

The projection returned `AMENDMENTS_REQUIRED` with **zero owner cards**; the other thirteen
ledger rows are plan-local or delegations and live in `plans/plan_1.md`. The four that
belong here, all verified independently by the coordinator before folding:

- **§12A.3's named mutation was inert** — `n → len(terms)` can only weaken a `<=` bound, and
  on the very shape it named the two counts are equal. Replaced by two mutations that bite
  on different things (tightness, and the float-multiply defect the bound exists to detect).
- **§12A.9's named mutation was inert**, and its rationale was false: snapping *up to a
  multiple of `Q`* cannot break divisibility by `Q`. Replaced by exact literals for `Q = 7`.
- **§4.2A's "purely proportional ⇒ `0`" is false**, and false for this document's own
  worked configuration: the value is **29**. §8's example and §8A.1's correction list follow.
- **§2A.1.3's `production_cost_basis_version.py:40`** is `:38`; `:40` is a different CHECK.

**The pattern is now three for three, at three different levels.** Round 3 found the
intention's nominated weak points were sound and the unflagged ones were broken. Round 5
found the same thing one level down: the *mechanisms* survived the projection intact — the
M1 form is faithful to the shipped calculator, the break-even literal and all three band
literals are exact, the bound holds on every enumerated shape — and what failed was the
**evidence**: three of the criteria's named mutations could not fail. Charter rule 11 is the
rule this keeps re-earning: *a safety test that survives the defect it exists to prevent is
decoration*. Standing consequence for this project, recorded in the master plan: **a named
mutation is not accepted until someone has computed both sides of it.**
