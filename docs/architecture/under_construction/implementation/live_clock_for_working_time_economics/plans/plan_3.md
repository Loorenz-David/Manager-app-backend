# Plan 3 — D9: the frozen blocks freeze whole

```
state: NOT_STARTED
phase: 3
date: 2026-08-20
depends_on: plan 2 APPROVED 2026-08-21 (`efd6b99`) — holds. The live basis exists, so
            T13's mutation can discriminate.
```

## 1. Goal

Implement D9: `final.percent_consumed` (E-P) and the worker face's
`result.percent_consumed` (E-B) stop tracking the request-level percent and derive
from the frozen result record's own stored figures (decision N-4) — a frozen block
never carries a ticking field, and moves on **no** event after the freeze.

**NOT in this phase:** no key added or removed anywhere (HC-4); the **live**
`percent_consumed` on the budget block / status payload is untouched (it ticks, D6);
no change to `ItemCostResult`, the analytics worker, or anything persisted (HC-1).
No handoff (phase 4).

**Also NOT in this phase, named so the class-sweep rule does not pull it in (L10/F-10):**
`serializers.py:serialize_item_cost_result_worker` is a **third** producer of a worker
`result` block carrying `percent_consumed`, and "sweep the class, not the instance"
would argue for changing it too. The measured reason not to: it has **no production
caller** — the only caller anywhere in the repository is
`test_phase8_serializers.py:test_worker_result_serializer_has_no_monetary_fields`, and
its `percent_consumed` is always `None` because the parameter defaults (verified by the
projection and reproduced by the coordinator: one definition, one test caller, zero
production callers). Nothing serves it, so D9 has nothing to say about it. Leave it
untouched and do not report it as an omission.

**The frontend-facing documentation correction is phase 4's, not this phase's** (L15 /
F-14) — see §4 task 4 for the internal half that *is* this phase's.

## 2. Read first

1. `master_plan.md` §4 (N-4 — the reconstruction formula and its verification
   obligation), §5.
2. Intention §5.3 (the D9 contract), §4.1A B (the two keys, the two sites, the
   manager-face absence), §4.2, §9A T13, §10.3 D9.
3. Source: `division_serializers.py:_serialize_production_time_final` and
   `:serialize_task_production_time` (the E-P feed);
   `serializers.py:_serialize_result` and `:serialize_task_budget_status` (the E-B
   feed); `item_cost_result.py:ItemCostResult` (the stored figures);
   `calculator.py:calculate_percent_consumed` and `:calculate_variance_worker_minutes`
   (the formula and the identity N-4 rests on).

## 3. Files expected to change

- `app/beyo_manager/domain/item_economics/division_serializers.py` — E-P feed:
  `serialize_task_production_time` computes the frozen percent per N-4 and passes it
  to `_serialize_production_time_final` instead of the request-level percent (the
  budget block's `percent_consumed` keeps the request-level value).
- `app/beyo_manager/domain/item_economics/serializers.py` — E-B feed:
  `serialize_task_budget_status` passes the N-4 frozen percent into
  `_serialize_result` instead of `status.percent_consumed`.
- One test file (new or the phase-2 family) for C1–C6 — **P3-D2** (§6A).
- **Two existing test files are forced open by the default shape — enumerated, not
  discovered (L2/F-2).** Both hand-build their status/result objects with **string**
  minute fields, and `"120.00" + "40.00"` silently concatenates to `'120.0040.00'`,
  surfacing one frame later as `TypeError: allowed_worker_minutes must be a Decimal` at
  `calculator.py:_guard_type` — a wrong-frame failure of the shape phase 1's B1-r4 was
  about. Each file with its mode of contact:
  - `tests/unit/services/queries/item_economics/test_phase8_serializers.py` — its
    `_result()` builder passes `actual_worker_minutes="2.00"` /
    `variance_worker_minutes="-1.00"` (two builders, lines ~20 and ~55). Contact:
    **fixture types**, one row red (`test_budget_status_worker_surface_excludes_money`).
    Note the history — plan 2 §5 C7 explicitly ruled this file *outside* the phase
    perimeter on the grounds that it builds its objects by hand; **phase 3 forces it
    open, and that widening is deliberate.**
  - `tests/unit/docs/test_item_economics_handoff_accuracy.py` — its `_status()` builder
    passes `"120.00"` / `"40.00"`. Contact: **fixture types**, three rows red
    (both `test_the_documented_budget_status_keys_are_the_shipped_keys` parametrizations
    plus `test_the_worker_budget_status_carries_no_monetary_key`).
  Fix them by giving the builders `Decimal` values — **not** by loosening `_guard_type`
  and **not** by making the production code tolerate strings. If a third file appears,
  that is a STOP-and-report: the enumeration above is the perimeter, and an amendment
  that widens a perimeter is itself an enumeration (master §5).
- Nothing else under `app/`. If the implementer routes the computation through the
  service layer instead of the serializers (**P3-D1**, §6A), the file set is declared in
  the handoff and the reciprocal-comment obligation takes its one-copy form — see §6A,
  which also carries the measured cost of that shape.

## 4. Ordered tasks

1. **N-4's identity is already verified — what task 1 owes is its *boundary*.** The
   projection derived and measured it, and the coordinator re-derived it independently
   at nine quantization-stressing values (sub-cent actuals, three-decimal inputs,
   half-even boundaries): `calculate_variance_worker_minutes` is `allowed − actual`
   with **no quantize and no clamp**, both columns are `Numeric(12, 2) NOT NULL` with a
   single writer, so `actual + variance` reconstructs `allowed` exactly and **no failing
   input exists** — over-budget, zero actual, zero allowance and negative allowance all
   hold. Do not re-litigate this; cite it. What you must handle is the one place the
   *output* is undefined: `calculate_percent_consumed` returns `None` when its
   denominator is ≤ 0, so the frozen percent is `null` **iff the frozen allowance was
   ≤ 0** — independent of the payload's current `status` (intention §5.3A, OD-10).
   C2 still carries a by-hand worked example; C6 carries the boundary.
2. The two feed-site changes, each with a comment naming the other site and D9's
   one-line reason (resolvable from a clean checkout — no criterion IDs, no round
   numbers). Under the one-copy shape (P3-D1) the comments take the form "each site
   names the single computation home" instead — reciprocal naming has no referent when
   there is one copy.
   Two clauses that are cheap to state and expensive to discover:
   - **Guard on `result is not None` at both sites (L11/F-12).** The computation must
     sit *inside* the existing `result is not None` branch.
     `test_phase8_serializers.py:test_c7_readiness_producer_drives_each_status_exactly`
     drives **ten** parametrized cases through one `result=None` construction (verified
     at source: ten rows, lines ~81–90), and E-P's `idle_no_result` golden serves
     `"final": null`. An unguarded computation raises `AttributeError` on all eleven.
   - **Correct the docstring you are about to falsify (L9/F-9).**
     `division_serializers.py:_serialize_production_time_final` reads *"Serialize the
     frozen result with the **live** percentage and no money."* After D9 that is false.
     A comment asserting a property is a claim (master §5) — correct it in the same
     edit, do not leave it for review.
3. **The internal documentation correction OD-10 created (L4/F-11).** Two lines promise
   `percent_consumed` is `null` for `infeasible`, which after D9 is no longer true of
   the *frozen* copy: `docs/domains/item_economics/states.md` ("Numerics rule") and
   `docs/domains/item_economics/README.md` ("The concrete rule"). Correct both to
   distinguish the live copy (still `null` — no denominator exists) from the frozen copy
   (its own reconstructed number, `null` only if the *frozen* allowance was ≤ 0). The
   **published frontend handoff** carries the same promise and is **not** yours to edit —
   phase 4 issues a new dated handoff (master §7 obligation 2).
4. Tests C1, C2, C3, C4a, C4b, C4c, C5, C6 — each with its own fixture and its own named
   mutation; evidence records per master plan §5 (hypothesis, scope, command, tree
   identity, result, ID delta) at the scope each hypothesis requires (§5B).

## 5. Acceptance criteria

- **C1 — T13, E-P row.** Fixture: task with a persisted result whose step is re-opened
  into `working` with an open record (live request percent ≠ frozen percent by
  construction). One payload: live fields tick; the whole `final` block —
  `percent_consumed` included — byte-identical to the same task's pre-open payload.
  **Named mutation (call site: `division_serializers.py:serialize_task_production_time`,
  the argument feeding `_serialize_production_time_final`):** feed the request-level
  percent back ⇒ contract = frozen value, mutation = live value, red.
- **C2 — T13, E-B worker-face row, its own fixture and its own mutation** (site:
  `serializers.py:serialize_task_budget_status`, the `percent_consumed=` argument) —
  two sites, two rows, sweep the class. The row's fixture also carries the C2 worked
  example: frozen percent computed by hand from the result's stored
  `actual_worker_minutes` and `variance_worker_minutes`, asserted as an exact literal
  (never an equality between two calls — master plan §5).
- **C3 — re-commit immunity** (N-4's reason): supersede the evaluation and commit a
  new one with a **different** `allowed_worker_minutes`; the frozen percent is
  byte-identical before and after (it derives from the result row alone). This row is
  why N-4 reconstructs the denominator instead of reading the current evaluation.
  **Named mutation — applied at EACH reconstruction site separately, one observation
  per site (L3/F-3):** read the *current* evaluation's `allowed_worker_minutes` instead
  of reconstructing `actual + variance` from the result row ⇒ contract = the two
  percents equal and asserted as one exact literal, mutation = they differ, red.
  Under the default (two-site) shape that is **two** observations, E-P and E-B, each
  recorded separately. A single "the row went red" is not acceptable evidence here:
  measured at the projection, mutating E-P alone and mutating *both* sites produce the
  **identical** ID delta, so one observation cannot tell them apart and the un-mutated
  site would ship unproven — phase 1's definition-vs-call-site defect exactly.
  **The fixture must move `allowed_worker_minutes` by enough to change the quantized
  percent.** With frozen `actual = A` and reconstructed allowance `L`, the contract
  percent is `round(A/L × 100, 2)` and the mutant is `round(A/L' × 100, 2)` for the
  re-committed `L'`; they differ once `|A/L − A/L'| × 100 ≥ 0.005`. **Worked, on the
  reusable fixture (`A = L = 20.00`, contract `100.00`): `L' = 25.00` gives `80.00`.**
  A re-commit that lands on the same rounded value is a row that cannot fail.
- **C4a — the manager face still has no `percent_consumed` key in its result block**
  (§4.1A B key-walk row), asserted by a recursive key walk, not a `.get()`.
  **Named mutation (site: `serializers.py:_serialize_result`, the manager branch):**
  emit `percent_consumed` in that block ⇒ contract = key absent, mutation = key
  present, red.
- **C4b — the live percent still ticks on the same payload as C1.** One row asserting
  the budget-block `percent_consumed` **moved** between the pre-open and open serves
  while `final`'s did not — both values exact literals, both taken from the C1
  payloads. **Named mutation (site: the budget-block `percent_consumed` argument at
  the E-P feed):** feed the frozen value there too ⇒ contract = the two values differ,
  mutation = they are equal, red. This row is what keeps D9 from freezing the
  surfaces D6 says must tick.
- **C4c — the E-B live percent still ticks too** (L5/F-5). C4b guards E-P's budget block;
  the **top-level** `percent_consumed` on E-B (`serializers.py:serialize_task_budget_status`,
  the `_decimal(status.percent_consumed)` expression, shared by both faces) has no
  equivalent row, and **no existing test can see it**: the only candidate,
  `test_phase2_live_surfaces.py:test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`,
  asserts `worker_payload[field] == manager_payload[field]` over a field list that
  includes `percent_consumed` — both faces read the *same expression*, so freezing it
  freezes both equally and the equality still holds (verified at source, line ~468–477).
  The goldens cannot see it either: there the frozen and live percents coincide at
  `"15.00"`. **Named mutation (site: that `_decimal(status.percent_consumed)`
  expression):** feed the frozen reconstruction there ⇒ contract = pre-open and open
  serves differ, mutation = equal, red. Two surfaces, two rows — sweep the class.
- **C5 — the no-drift identity.** In the T5 golden state (zero post-freeze drift, same
  evaluation) the new source produces the **same value** as the old wiring — proven by
  the plan-1 golden test staying green with its files untouched (read-only in this
  phase's diff, as in plan 2 C1). This is the criterion that makes D9 invisible to
  every frozen task that has not been reopened. **Named mutation, applied at EACH
  reconstruction site separately (L3/F-3), same rule as C3:** replace the reconstructed
  denominator with `result.actual_worker_minutes` alone ⇒ the golden must **redden**.
  Contract = golden green, mutation = golden red.

  **The vacuity question is already answered — negative, and measured (L7/F-7):** the
  goldens *do* reach the changed path. `golden_production_time.json:frozen_no_drift.final`
  and `golden_budget_status.json:frozen_no_drift.worker.result` both carry
  `actual 15.00 / variance 85.00 / percent 15.00`, so the reconstruction yields
  `15.00 / (15.00 + 85.00) → 15.00 %` and the goldens stay green (coordinator-verified
  from the golden files at `6508ce1`). So this row is non-vacuous by construction, and
  the amendment records the **expected bite set** so the second red is not reported as
  an anomaly:

  | mutation applied at | expected added IDs |
  |---|---|
  | both sites | `test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files` **and** `test_production_time_query.py::test_c17_frozen_final_uses_live_percent_without_money` |
  | E-P only | the same two |
  | E-B only | the goldens test **only** |

  **Scope: L4 (full suite)** — this is a coupling-discovery hypothesis about a bite set
  outside this phase's own test file, and a bite set can only be *bounded* by the full
  suite (charter L4 trigger (d)). The projection's L2 measurement above is a **floor,
  not a ceiling**.

  **CORRECTED 2026-08-21 (coordinator, mid-round — this clause was wrong as written).**
  It previously read "treat any additional ID as a finding, not noise." That instruction
  mislabels the expected case, because **the bite set above was measured on a tree where
  this phase's own rows did not yet exist.** C5's mutation and **C6b's named mutation are
  literally the same edit** — both replace the reconstructed denominator with
  `result.actual_worker_minutes` alone (compare this row with C6b) — so C6b *must* redden
  under it, and C3 and C6a assert exact reconstructed literals, so they redden too unless
  their literal happens to be `100.00`. That overlap is a property of the criteria as
  written, derivable from this plan without running anything. The expected bite set is
  therefore **two classes**:
  1. the two legacy IDs in the table above (the goldens test and `test_c17`), and
  2. this phase's own rows that assert the reconstruction — C3, C6a, C6b.

  **A finding is an ID outside both classes.** An ID from class 2 is the criteria working.
  Record the union as measured; do not remove a correct row to make a bite set match a
  stale expectation.
  **One more trap in the instrument:** `test_prechange_payloads_match_byte_golden_files`
  is a **single** test function looping over all three goldens and asserting in sequence
  (verified at source — one test function in the file), so it short-circuits on the first
  mismatch. The ID delta therefore cannot attribute *which* golden or which site moved —
  which is precisely why the per-site observations above are mandatory rather than
  cosmetic.
- **C6 — the boundary OD-10 settled** (L4/F-4, intention §5.3A). Two rows, each with its
  own fixture and its own named mutation at **each** reconstruction site:
  - **C6a — frozen allowance > 0 while the current `status` is `infeasible`.** Fixture:
    a persisted result whose stored figures reconstruct a positive allowance, then
    re-commit an evaluation whose `allowed_worker_minutes ≤ 0` (a
    `production_budget_minor` of 0 yields `allowed = 0.00`; `_build_evaluated_status`
    reads `INFEASIBLE if allowed <= 0`). Assert the payload serves
    `status: "infeasible"` **and** the frozen key carries its exact reconstructed
    literal — not `null`. **Named mutation:** blank the frozen percent whenever
    `status == "infeasible"` ⇒ contract = the literal, mutation = `null`, red.
  - **C6b — frozen allowance ≤ 0.** Fixture: stored figures whose sum is ≤ 0 (e.g.
    `actual 15.00 / variance −15.00`). Assert the frozen key is `null` — because
    `calculate_percent_consumed` has no denominator, not because of `status`.
    **The current evaluation must carry a POSITIVE allowance** (so the payload's `status`
    is `ok`) — see the correction below; a fixture whose current allowance is also ≤ 0
    gives the `null` two independent sufficient causes and proves neither.
    **Named mutation:** substitute any positive fallback denominator (e.g. `actual`
    alone, which is > 0 here) ⇒ contract = `null`, mutation = a number, red.
  Row (a) is the one the owner decided; **row (a) is also what stops a future "just null
  it whenever status is infeasible" edit from passing**; row (b) stops a positive-fallback
  denominator.

  > **CORRECTED 2026-08-21 (review r1, S1 — measured).** This paragraph originally read
  > *"row (b) is what stops a future 'just null it whenever status is infeasible' edit
  > from passing"*. False, and measured false: C6b as built sets the current evaluation's
  > `allowed_worker_minutes = 0.00`, so its own payload is `infeasible` and a
  > status-blanking implementation returns exactly the `null` it asserts — **C6b passes
  > under the edit it was said to stop.** The status-blanking mutant at both sites reddens
  > **C6a only**. Two consequences: the attribution is swapped above (and in intention
  > §5.3A and the master plan tracker), and **C6b's fixture must be re-specified with a
  > positive current allowance**, so its `null` has exactly one sufficient cause — charter
  > rule 2's companion condition, the same shape the charter cites from plan 3 round 2 B1.
  > Note the fixture's own comment claims the percentage is "undefined independently of
  > the current status" — a prose claim its fixture cannot demonstrate, because that
  > fixture holds the status at `infeasible`.
  - **C6c — the over-budget region** (review r1, S2 — added 2026-08-21). A finished job
    that overran its budget is OD-10's own first premise row and the most consequential
    number the frozen block serves, and **no test in the repository constrains it**:
    every fixture pinning a numeric frozen percent sits at or below `100.00`
    (C1/C2/C4b/C4c at `100.00`, C3 at `80.00`, C6a at `15.00`, both goldens at `15.00`,
    `test_c17` at `20.00`), and C6b's negative variance is chosen to land the
    reconstruction on exactly `0.00`. Measured: clamping the frozen percent at `100.00`
    at both sites leaves the **whole suite green — ∅ added, ∅ removed**.
    Fixture: stored `actual_worker_minutes = 15.00` / `variance_worker_minutes = −5.00`
    → reconstructed allowance `10.00` → frozen **`"150.00"`**, with the current evaluation
    left at a positive allowance so `status` stays `ok`. Assert on **both** faces, as C6a
    does. **Named mutation, applied at each reconstruction site:** clamp the frozen
    percent at `100.00` ⇒ contract `"150.00"`, mutation `"100.00"`, red.
    **Scope: L1** — this is a named-row bite question once the row exists; the ∅ that
    justified adding it was the L4 absence claim, already measured and recorded here.
    *Coordinator note, sharper than the finding:* the region is not merely untested, it is
    **already computed on every suite run and observed by nothing** —
    `test_phase8_serializers.py:_result()` carries `actual 2.00 / variance −1.00`, so the
    worker payload built in `test_budget_status_worker_surface_excludes_money` currently
    serves `result.percent_consumed == "200.00"` while that test asserts only
    `allowed_worker_minutes` and four key absences. A clamp changes `200.00` to `100.00`
    there and nothing notices.

## 5A. Carried from phase 2 — read before writing a single criterion

Phase 2 ran six rounds and **every blocking finding was in a plan, a ledger or a
criterion — never in the code.** Four things it earned bind this plan directly:

- **Write criteria as lettered rows, one named mutation each — not as a headline
  sentence with subordinate clauses.** Phase 2's C2, C4, C6 row 1 and C7 were each written
  as a headline plus clauses, and in all four **the headline shipped and the clauses did
  not**. C6's rows 2–4, written as separate lettered rows with their own mutations, shipped
  complete on the first attempt. This plan's §5 is to be lettered throughout.
- **This phase's determinism guard is C1/C2's pre-open comparison — NOT phase 2's
  two-serve byte-identity rows.** Re-review r5 closed that search structurally: two serves
  on one session with a frozen `ctx.now` can differ through exactly two channels, and
  rounding collapses the interesting one (this is T1, which the gate already retired once).
  Those rows guard the two-serve loader count and whole-second determinism, nothing more.
  A comparison between genuinely different states — pre-open vs open — is what discriminates
  here.
- **T13's rows name the branch each surface actually reaches, not the surface.** Phase 2's
  C12 claimed four surfaces and could only prove two: E-A no longer imports `today_utc`, and
  E-P's fixture reaches `_build_evaluated_status` and never touches the preview path. A
  criterion that lists surfaces over-claims; one that names branches is checkable.
- **Before choosing a fixture, compute the *verdict* under both bases, not just the
  values** (master §5, the degenerate-controlling-term rule). Percent is a ratio and a
  ratio has its own degeneracies: a denominator that makes both bases agree, an allowance of
  zero, a frozen block whose stored figures happen to equal the live ones. **`allowed ≡
  actual + variance` (N-4) means a fixture with `variance_worker_minutes = 0` makes the
  frozen and live denominators identical** — that fixture cannot fail, and it is the most
  natural one to reach for.

## 5B. The fixture numbers, and the evidence scope per row

**The degenerate fixture §5A warns about is the one already in the tree, one import
away** (L6/F-6). `test_phase2_live_surfaces.py:_make_live_fixture` — the natural reuse
target, and the only fixture pairing an `ItemCostResult` with an open working record —
carries `actual_worker_minutes = 20.00`, **`variance_worker_minutes = 0.00`**, and sets
`evaluation.allowed_worker_minutes = 20.00` (verified at source). Computed both sides on
it (live worked 2040 s open / 1440 s pre-open, from plan 2's own asserted figures):

| quantity | value |
|---|---|
| frozen percent (N-4): `20.00 / (20.00 + 0.00)` | **100.00** |
| live percent, pre-open: `24.00 / 20.00` | **120.00** |
| live percent, open: `34.00 / 20.00` | **170.00** |

So on this fixture **C1, C2 and C4b bite** (the numerators differ) but **C3's and C5's
denominator mutations are inert** — the reconstructed allowance `20.00` equals the
evaluation's `20.00`, which is exactly the degeneracy. Reuse it for the first group;
C3, C5 and C6 need their own figures.

**The degeneracy is one worse than this section originally recorded** (review r1, S2).
That fixture also puts the frozen percent at exactly **`100.00`** — the boundary of a
whole family of plausible edits ("a percentage cannot exceed 100"). Four of the phase's
rows are pinned at the one value a clamp cannot move, and until C6c was added, **no
fixture anywhere in the repository constrained the frozen percent above 100**. The rule
generalizes and is now a standing one: §5A says compute the verdict under both bases
before choosing a fixture — that was applied to the **numerator** and not to the
**output's range**. For a derived quantity whose own authority names regions (OD-10's
premise table names three: over-budget-but-positive, non-positive, and ordinary), **the
criteria enumerate the regions**, not merely vary the input terms. Every row states both sides as literals before
it is written (master §5's F-C1 rule: place the fixture where the two forms differ, and
compute that *before* choosing it).

**Evidence scope per criterion** (charter "Test-evidence scope and reuse"):

| criterion | hypothesis | scope |
|---|---|---|
| C1, C2 | "this named row reddens under this named mutation at this call site" | **L1** |
| C3 | same, **once per reconstruction site** | **L1 ×2** |
| C4a | a key is absent from one served payload under a recursive key walk | **L1** (a payload-shape assertion, *not* a repository-wide absence claim) |
| C4b, C4c | two values in one payload differ | **L1** |
| C6a, C6b | the frozen key's value at the boundary | **L1** |
| **C5** | an existing golden **this phase does not own** stays green and reddens under the named mutation — a bite set outside the phase file | **L4** (coupling discovery, charter trigger (d)) |
| cycle close | the clean stamp | **L4**, one per implement/fix cycle |

## 6. Notes

- `_decimal(…)` serialization of the percent must round-trip identically for the
  reconstructed value — if `calculate_percent_consumed` quantizes, the frozen input is
  Decimal-exact (both stored fields are `Numeric(12, 2)`), so no new rounding locus
  appears. **Confirmed by the projection and not expected to fire:** the reconstruction
  adds two `Numeric(12,2)` Decimals under `prec = 50` — exact, ≤ 2 dp, no rounding — and
  the only quantize on the path is the one already inside `calculate_percent_consumed`
  (`0.01`, `ROUND_HALF_EVEN`), unchanged. The STOP-and-report clause stays anyway: it
  costs nothing and a new rounding locus would be a rule-6 mechanism outside the
  contract.
- **CORRECTED 2026-08-21 (L1/F-1) — this note previously described the *other* shape.**
  It read: "The E-P internal dict gains an internal key for the frozen percent." That is
  true **only** under the service-layer shape (P3-D1). Under the default two-site shape
  **no new key exists**: `get_task_production_time.py:get_task_production_time` already
  puts `"result": status.result` into the row dict (verified at source, line 117), so
  `serialize_task_production_time` computes the frozen percent from what it already
  receives. Either way HC-4 is untouched — nothing new reaches a payload. As written the
  contradiction between §3 and §6 ended the implementer's first hour in a coin flip.
- **An existing test asserts D9's negation and survives it (L8/F-8).**
  `test_production_time_query.py:test_c17_frozen_final_uses_live_percent_without_money`
  asserts `body["final"]["percent_consumed"] == body["budget"]["percent_consumed"]` —
  the exact wiring D9 removes — and stays **green** after the change because its fixture
  sits at the no-drift point (frozen `20.00 / 80.00` → allowance `100.00` → `20.00 %`;
  live `1200 s = 20.00 min` against `_seed`'s `allowed_worker_minutes = 100.00` →
  `20.00 %`). Coordinator-verified at source. It is a row that cannot fail wearing a name
  that claims the opposite of what ships — pre-existing, not introduced here.
  **Obligation:** either retarget it (move its fixture off the no-drift point so the name
  becomes true, or rename it to what it actually tests) **or** record the coincidence
  explicitly in the Review log with the numbers above. Silence is not an option — that is
  the prose-claim rot re-review r5's S1 was about. Note it also appears in C5's expected
  bite set, which is a second reason not to leave it unexplained.

## 6A. Written delegations (granted on purpose, not taken silently)

Per the naming registry (master §4), phase delegations are `P3-D<n>`.

- **P3-D1 — the shape: two serializer sites, or one service-layer computation.** The
  implementer picks; the handoff declares the resulting file set. **Measured cost of the
  service route (F-13), so the choice is informed:** `TaskBudgetStatus`
  (`get_task_budget_status.py`) gains a field, and two constructions in
  `tests/unit/routers/api_v1/test_item_economics_router.py` (both inside
  `fake_run_service`, `result=None`) pass the full field list by keyword — **a field
  without a default breaks that file too**, and `_empty_status` would also need it.
  Under the default shape that file is untouched. Both shapes are viable; the one-copy
  shape also changes the comment obligation (§4 task 2).
- **P3-D2 — new test file or extend `test_phase2_live_surfaces.py`.** Implementer's call;
  the handoff names the file.
- **P3-D3 — the exact fixture literals per row**, within §5B's constraints. Implementer's
  call, **recorded as a comment beside each fixture** (master §5: a delegation grant names
  its post-closeout medium — a handoff archives, a comment does not).

## 7. Review log

**2026-08-21 — coordinator, pre-projection amendment (no session spent).** §5 carried
named mutations on C1 and C2 only, while §5A's own first bullet requires one per
lettered row (charter rule 11). Added: C3's current-evaluation denominator mutation
with the quantization warning; C4 split into **C4a** (manager-face key emission) and
**C4b** (the budget-block percent frozen too), each with its own site and mutation;
C5's `actual`-alone denominator mutation, which is what makes "the golden stayed
green" mean anything — an unreached golden is green under every mutation of the code
it does not reach. §4 task 3 re-lettered to match. No criterion was weakened and none
was added; every change makes an existing row falsifiable.

**2026-08-21 — projection r0 consumed and routed (coordinator).** Verdict
`AMENDMENTS_REQUIRED`, **15 ledger rows / 14 findings**, all routed; the handoff is
`handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md`. Perimeter verified
against the tree: exactly the declared two items (its own handoff + one appended tracker
row, `1 insertion`), no code, no plan, no intention write. **The coordinator reproduced
every load-bearing claim independently rather than reading the ledger** — F-1 (`"result":
status.result` at source), F-2 (the string minute fields in both builders and the
`_guard_type` Decimal guard they trip), F-3 (one test function looping over three
goldens), F-4 (`percent_consumed` → `None` at allowed ≤ 0, a number at `0.01`), F-5 (the
shared-expression equality that cannot see a frozen E-B percent), F-6 (`_make_live_fixture`
at `variance = 0.00`), F-7 (the goldens' `15.00 / 85.00`), F-8 (test_c17's assertion and
its no-drift fixture), F-9 (the docstring), F-10 (one definition, one test caller, zero
production callers), F-12 (ten parametrize cases through one `result=None`), F-14 (the
promise at line 513 of the published frontend handoff). **Every one reproduced.** The
count that looked wrong resolved in the projection's favour: one `result=None`
construction driving exactly ten parametrized rows.

Routed here: **L1** → §6 note corrected in place (it described the *other* shape);
**L2** → §3 file set widened by enumeration, with each file's mode of contact and the
note that plan 2 §5 C7 had deliberately excluded one of them; **L3** → C3 and C5 now
require one observation **per reconstruction site**; **L5** → **C4c** added; **L6** →
§5B carries the measured both-sides numbers; **L7** → C5 carries its expected bite set
and an L4 scope; **L8** → §6 note plus a retarget-or-record obligation; **L9**, **L11**
→ §4 task 2 clauses; **L10** → §1 "NOT in this phase"; **L4** → **C6a/C6b** after the
owner ratified OD-10; **L12–L14** → §6A as written delegations **P3-D1…P3-D3**.
Routed elsewhere: **L4's** decision to `planning/owner_decisions.md` + intention §10.4
and the new §5.3A (round 4h); **L15** to `plans/plan_4.md`; the `D`-namespace collision
to master §4; the archgraph drift to master §6.

**Independent additions, not in the ledger.** (1) The identity was re-derived at nine
quantization-stressing values the projection never tried — sub-cent actuals,
three-decimal inputs, and half-even boundaries such as `actual = 99.995` against
`allowed = 100.00` — and holds at every one, so §4 task 1 could be downgraded from
"verify it" to "cite it, and handle the boundary instead". (2) The `D`-namespace
collision was one fold from shipping a third meaning of `D10`.

**2026-08-21 — coordinator correction, mid-round (implement r1 in flight).** C5's scope
clause instructed "treat any additional ID as a finding, not noise." Wrong as written,
and wrong in a way this project has now seen eight times: **the expected bite set was
measured by the projection on a tree where this phase's own rows did not exist.** C5's
named mutation and **C6b's named mutation are the same edit** — both substitute
`result.actual_worker_minutes` as the denominator — so C6b must redden under C5's probe,
and C3/C6a assert exact reconstructed literals so they redden too. The overlap is
derivable from this plan's own text without running anything, and **the coordinator
wrote both rows in the same fold**. The implementer measured exactly this (two legacy IDs
plus C3, C6a, C6b) and classified it correctly as necessary rather than anomalous, which
is the right call; the criterion is now corrected to say so, in two classes, with the
finding condition narrowed to an ID outside both. Eighth instance of the
class-inside-its-own-correction shape and the coordinator's fourth.

**Not a licence to relax the row:** C5 stays at L4 and stays per-site. Its two site
observations are what bound the set; the correction only fixes what counts as a surprise.

**2026-08-21 — implementer r1 (Codex).** Implemented D9 using the default two-site
shape (P3-D1): E-P and E-B compute the frozen percentage from the stored result figures
inside their existing `result is not None` branches, and each site comment names the
other feed site. P3-D2 was resolved by extending `test_phase2_live_surfaces.py`; P3-D3
was resolved with comments beside each fixture's hand-computed literals. The two
enumerated hand-built fixture files were widened only to use `Decimal` minute values,
and the two internal numerics documents now distinguish live infeasible nulls from
frozen-result nulls. The false live-percentage docstring was corrected; the unused
worker serializer and published frontend handoff remain out of scope.

The pre-existing `test_c17_frozen_final_uses_live_percent_without_money` remains green
by coincidence (20.00 / 100.00 on both live and frozen bases); this is recorded rather
than retargeted. Named mutations reddened at every required site and were reverted.
C5's L4 per-site unions were the 26-ID baseline plus the golden and `test_c17` legacy
IDs, plus this phase's C3/C6a/C6b rows; no IDs outside the two plan classes appeared.
No Architecture Graph delta was warranted: the change rewires existing serializer
feed sites and adds no new architectural boundary.

**2026-08-21 — implement r1 consumed (coordinator).** Verified rather than read, and
**this is the first consumption in the pipeline that cited a stamp instead of re-running
it.** Tree identity checked cryptographically: the handoff declares the L4 stamp at
`HEAD 88c8f5f` with dirty-diff digest `d2ca0320…`; the checkpoint `5b8329b` (parent
`88c8f5f`) reproduces that digest **exactly** over `app/` + `docs/domains/`, which proves
the shipped content is byte-identical to what was measured and that only coordination
documents were added afterwards — precisely what the handoff claimed. Under the retired
policy this would have cost a 2m47 re-run to learn less.

**Perimeter: exact.** Ten declared items, ten files in `5b8329b`, no others. Tool-recorded
state independently confirmed: `archgraph_status` returns revision `120c4c38…`,
**byte-identical to the coordinator's own measurement taken before this session**, with
9 pending / 2 stale unchanged — so the "no graph writes" claim is proven, not accepted.
Lint claims verified by a different question than the one asked: ruff is clean on the five
changed files **and** the repo-wide 136 errors are unchanged from the parent commit, so
"introduces none" holds.

**Arithmetic reconciles across every row.** 2479 + 7 new tests = 2486 passed. Every L4
row totals 2512 collected (26+2486, 31+2481, 30+2482). The C5 site asymmetry is
internally consistent and could not have been guessed: E-P reddens `test_c17` and E-B does
not, because `test_c17` is a production-time test — and **neither reddens C1 or C2**,
which is exactly right, since those sit on the `variance = 0.00` fixture where
`actual` and `actual + variance` coincide and C5's mutation is inert by construction.
A fabricated ledger does not have that property.

**Criteria checked at assertion level, not by ID.** C4b lives inside `test_c1` (declared),
but the two criteria have **independent assertions with exact literals** — final
`100.00` / block byte-identity for C1, budget `120.00 → 170.00` for C4b — so each
mutation trips its own. C6a and C6b are jointly complete: C6a (status `infeasible`
asserted on **both** surfaces, frozen `15.00`) kills a status-based blanking
implementation, C6b (frozen `15.00 + (−15.00) = 0.00` → `null`) kills a positive-fallback
one, and neither fixture satisfies the other's predicate. C3 escapes §5B's degeneracy by
setting `variance = 5.00` (allowance `25.00`, frozen `80.00`, re-commit `30.00`), and its
`before` assertion is what discriminates frozen from live — worth noting because in its
**after** state live and frozen coincide at `80.00`; nothing load-bearing rests on that
coincidence today, and `after["budget"] == "80.00"` doubles as proof the re-commit was
observable at all. The shipped doc corrections were read as claims: both now state the
live/frozen split and the "null only when the reconstructed allowance is non-positive"
rule, which matches intention §5.3A exactly.

**Coordinator class sweep, not in the handoff:** `test_c17` is the **only** test in the
repository asserting `final.percent == budget.percent` (grep over `tests/`), so the
recorded-not-retargeted disposition covers the entire class rather than one instance.

Review r1 prompt at `prompts/reviewer/2026-08-21_phase3_review_r1.md`; seven probes, with
the settled ground above marked do-not-re-spend.

**2026-08-21 — review r1 (Opus 5). `CHANGES_REQUESTED` — 0 blocking, 2 should-fix, 6
notes. No production line is in scope for the fix cycle.** Handoff at
`handoffs/reviewer/2026-08-21_phase3_review_r1_handoff.md`. Tree `184f48a`, clean;
`git diff 5b8329b HEAD -- app/ docs/domains/` is empty, so the implementer's L4 stamp was
**cited, not reproduced**, and the round's budget went to two mutant shapes no ledger has
run.

**S1 — intention §5.3A names the wrong C6 row, measured.** §5.3A says row (b) reddens on a
"blank whenever `status == infeasible`" edit. It does not: C6b's fixture sets the current
allowance to `0.00`, so its payload's status *is* `infeasible` and a status-blanking
implementation produces exactly the `null` C6b asserts. **C6a** is the guard. Probe (L1,
status-blanking mutant applied at **both** sites, phase file): **1 failed / 24 passed**,
the single red `+test_c6a_frozen_percent_survives_infeasible_current_evaluation`, C6b
green, no removals. The implementer's ledger already carried the disproof — its
status-blanking rows report one ID where the prose implies two — but was read only in the
"did C6a bite?" direction. Same inversion in this §5 C6 and in `master_plan.md` §3.
**Correction:** swap the attribution in all three; row (a) kills status-blanking, row (b)
kills a positive-fallback denominator. Optionally give C6b's *current* evaluation a
positive allowance so its `null` has one sufficient cause instead of two (charter rule-2
companion).

**S2 — the frozen percent's over-budget region is unguarded repository-wide; ∅/∅ at L4.**
Every row pinning a numeric frozen percent sits at or below 100 % — C1/C2/C4b/C4c at
exactly `100.00`, C3 `80.00`, C6a `15.00`, both goldens `15.00`, `test_c17` `20.00` — and
C6b, the only negative-variance row, is placed where the reconstructed allowance is exactly
`0.00` and the answer is `null`. So `variance < 0` **with a positive allowance** — OD-10's
own first table row, a finished job that overran — is never evaluated. Probe: clamp the
frozen percent at `100.00` at both sites (absence claim ⇒ **L4**, charter trigger (d));
`26 failed / 2486 passed / 1 deselected`, failing-ID set `comm`-diffed against §6's
enumerated 26 → **∅ added, ∅ removed**; focused surface 100 passed. **§5B's degeneracy is
one worse than recorded:** `variance = 0.00` also puts the frozen percent at exactly
`100.00`, the boundary of this whole mutant family, so four of seven rows sit on the one
value a clamp cannot move. **Correction — new row C6c**, beside C6b: stored `actual 15.00 /
variance −5.00` ⇒ allowance `10.00` ⇒ frozen `"150.00"`, current evaluation left positive
so `status` stays `ok`, asserted on both faces; named mutation = the clamp.

**Notes.** N1 — C3 never asserts `before["budget"]` (`"120.00"`), so the live percent is
shown landing, not moving; its discrimination rests wholly on `before["final"]`, which is
sound. N2 — C4b inside `test_c1` is **sufficient**: each mutation trips a different
assertion with its own literal; the residue is that C1's mutant short-circuits before
C4b's asserts, so only C4b's own mutation evidences it. N3 — T13 asks for E-B `result`
block byte-identity; C2/C4c pin only the percent key (E-P gets the full block via C1).
N4 — `test_c17`'s record is durable but lives where its readers will not look; one comment
above the test closes it. N5 — the site comments name the other site in prose, not
`path:symbol`. N6 — the frozen value is computed on the manager face and discarded
(harmless; it is why the manager-side fixture was forced open).

**Verified correct:** N-4's argument order against the calculator signature; the
`result is not None` guard complete via `_empty_status`; HC-4; C4a structural and
non-vacuous; **P7 absence claim at L4** — terms `percent_consumed` / `percentConsumed` /
`percent-consumed` over `app/beyo_manager/`, exactly two production producers, both
changed (price-scenario, item-lifetime and the third `_serialize_result` producer emit
none); **P5 doc sweep** — both corrected statements are true, and `api.md` and the
2026-08-18 handoff sit at the no-drift point so their examples remain valid after D9;
the corrected docstring; the perimeter, goldens untouched. Both probes reverted,
SHA-256 byte-identical, tree clean; no archgraph call made.
