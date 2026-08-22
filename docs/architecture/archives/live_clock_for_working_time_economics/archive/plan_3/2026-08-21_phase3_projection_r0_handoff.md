---
plan: 3
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-21
actor: Opus 5 (projection r0)
---

# Projection handoff — plan 3 (round 0), `live_clock_for_working_time_economics`

Tree identity for every measurement below: **`6508ce1`**, `git status --porcelain` empty
before and after this session (asserted twice — §7).

---

## 1. Opening (for the owner)

The formula this phase is built on is sound. I re-derived it by hand and by running it,
and there is no case — not an over-budget task, not a zero budget, not a negative one —
where the frozen percentage comes out different from the number the task was actually
measured against. The plan can be built.

Three things need fixing before someone starts building. The plan says the change touches
two files and nothing else; I applied the change in a sandbox and **four existing tests
elsewhere in the codebase went red**, so the list of files is wrong and needs widening on
purpose rather than by surprise. Several of the plan's checks name "the site" where a
deliberate sabotage must be applied, but the plan creates *two* such sites, so a builder
could sabotage one, watch a test fail, and ship the other one unproven.

And one thing needs you personally. Our own written documentation promises that when a
task's budget is zero or negative, the percentage shown is blank. After this change the
*frozen historical* percentage will sometimes show a real number on exactly those tasks.
That is defensible — it is the honest record of what the task was measured against — but
it contradicts a promise we published, and nothing in the test suite would notice. Card
below.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — May a finished job show a percentage on a task whose budget has since gone to zero?

> **ANSWERED 2026-08-21 — the owner ratified the recommendation. See §9.**

**Question.** When a task's current budget is zero or negative, should the *frozen*
historical percentage still show its own number, or go blank like the live one?

**Story.** A chair was priced at 4 000 kr, worked for 15 minutes of a 100-minute budget,
and the finished-job block froze at 15 %. Weeks later you re-price the chair down to
where production leaves no budget at all. The screen now says the task is *infeasible* —
no budget — while the finished-job block beside it still reads 15 %, which is exactly
what that job actually consumed at the time. Our published documentation says the
percentage is blank whenever a task is infeasible, so the two disagree.

**Branches.**
- *Keep its own number (15 %)* — the historical block stays an honest record; the
  published "blank when infeasible" line becomes wrong and must be corrected.
- *Blank it whenever the task is currently infeasible* — matches the published line;
  a settled historical block starts changing because of a decision made afterwards,
  which is the thing we are removing this month.

**Recommendation.** Keep its own number, and correct the two documentation lines — a
frozen block that reacts to a later re-pricing is the defect this whole phase exists to
delete.

**On silence.** The gate holds; no criterion is written for this boundary and the phase
does not start.

**Trace.** intention §5.3 / §4.1A B / §10.3 D9; `docs/domains/item_economics/states.md`
"Numerics rule"; `docs/domains/item_economics/README.md` "The concrete rule";
plan 3 §5 (no row at this boundary); findings F-4, F-11.

---

## 2. Decision ledger

| # | Decision point | Classification | Proposed routing |
|---|---|---|---|
| L1 | §3 says `serialize_task_production_time` **computes** the frozen percent; §6 says the E-P internal dict **gains an internal key** for it. The second is only true under §3's *alternative* (service-layer) shape. The implementer cannot tell whether to add a row key. | plan gap | Amend §6 to state the key is added **only** under the service-layer shape; under the default shape no row key exists. See F-1. |
| L2 | "Files expected to change … Nothing else." Measured: the default shape reddens **4 tests in 2 files** outside that set. | plan gap | Amend §3 to name both files, each with its mode of contact, per master §5's "an amendment that widens a perimeter is itself an enumeration". See F-2. |
| L3 | C3 and C5 name "the reconstruction site" in the singular; §3's default creates **two**. | plan gap | Amend C3/C5 to name both sites and require a per-site observation. Measured deltas supplied in F-3. |
| L4 | `calculate_percent_consumed` returns `None` when the reconstructed allowance ≤ 0. No §5 row sits at that boundary. | intention gap → owner | Card 1. On answer, add criterion C6 at the boundary; correct the two domain docs in the same phase or record the correction as a phase-4 obligation. See F-4, F-11. |
| L5 | C4b keeps D6 alive at the **E-P budget block** only. Nothing guards that E-B's *top-level* `percent_consumed` still ticks while `result.percent_consumed` freezes. | plan gap | Add **C4c**, the E-B analogue of C4b, its own fixture and its own mutation. Measured: the gap is real — F-5. |
| L6 | §5A names `variance_worker_minutes = 0` as the fixture that cannot fail, but §5 prescribes no numbers. The one reusable phase-2 fixture sits exactly on that degeneracy. | plan gap | Amend §5 to carry the computed both-sides numbers per row, the way plan 2 §5 C6 rows 2–3 do ("Measured: `stp_b` → `stp_a`"). Numbers supplied in F-6. |
| L7 | C5 asserts an existing golden stays green — a claim about a test file this phase does not own, with no enumerated bite set. | plan gap | Amend C5 with the measured expected bite set and its evidence scope (L4 — coupling discovery). See F-7 and §4. |
| L8 | `test_production_time_query.py:test_c17_frozen_final_uses_live_percent_without_money` stays **green** after D9, by fixture coincidence, while its name asserts D9's negation. | plan gap | Amend §6 with a note and a Review-log obligation: either retarget the row or record the coincidence explicitly. See F-8. |
| L9 | `division_serializers.py:_serialize_production_time_final`'s docstring says "with the **live** percentage". §4 task 2 mandates new comments but not the correction of this false one. | plan gap | Add to §4 task 2: correct the docstring in the same edit (master §5 — a comment asserting a property is a claim). See F-9. |
| L10 | `serializers.py:serialize_item_cost_result_worker` is a **third** `_serialize_result` call site emitting `percent_consumed`, with no production caller. Silent about it, the class-sweep rule pulls it in. | plan gap | Amend §1's "NOT in this phase" to name it out of scope, with the measured reason. See F-10. |
| L11 | The computation must be guarded on `result is not None`; ten parametrized rows and the `idle_no_result` golden pass `result=None`. | plan gap | One clause in §4 task 2. See F-12. |
| L12 | Which of §3's two shapes to build. | free choice | **Proposed explicit delegation D10:** the implementer picks, and the handoff declares the file set. Consequences measured in F-13 — under service routing the new `TaskBudgetStatus` field **must carry a default** or a third file breaks, and §3's "reciprocal comments naming each other" is not implementable and becomes "each site names the single computation home". |
| L13 | New test file vs extending `test_phase2_live_surfaces.py`. | free choice | **Proposed explicit delegation D11:** implementer's call; the handoff names the file. |
| L14 | The exact fixture literals per row. | free choice | **Proposed explicit delegation D12:** implementer's call **within** the constraints of F-6, recorded **as a comment beside each fixture** (master §5 — a delegation grant names its post-closeout medium). |

---

## 3. Deep passes — what the artifacts actually determine

### 3.1 N-4's identity: derived, then measured. **It holds, with one behavioural boundary.**

`calculator.py:calculate_variance_worker_minutes` delegates to
`:calculate_remaining_worker_minutes`, which is `allowed − actual` under `prec = 50` with
**no quantize and no clamp**. The sole writer of the row is
`process_item_cost_result.py:handle_process_item_cost_result`, which stores
`actual_worker_minutes = calculate_actual_worker_minutes(actual_seconds)` (2 dp) and
`variance_worker_minutes = calculate_variance_worker_minutes(evaluation.allowed_worker_minutes, actual_minutes)`.
Both columns are `Numeric(12, 2)`, both `nullable=False`
(`item_cost_result.py:ItemCostResult`). `migrations/versions/90cdd23a828e_item_economics_schema.py`
creates the table and **back-fills nothing** — there is no second provenance for a row.

Measured at `6508ce1` over the boundaries the prompt named:

| allowed | actual | variance | `actual + variance` | identity | old percent | N-4 percent |
|---|---|---|---|---|---|---|
| 100.00 | 15.00 | 85.00 | 100.00 | ✓ | 15.00 | 15.00 |
| 100.00 | 150.00 (over budget) | −50.00 | 100.00 | ✓ | 150.00 | 150.00 |
| 0.00 (zero allowance) | 15.00 | −15.00 | 0.00 | ✓ | None | None |
| −5.00 (negative) | 15.00 | −20.00 | −5.00 | ✓ | None | None |
| 100.00 | 0.00 (zero actual) | 100.00 | 100.00 | ✓ | 0.00 | 0.00 |
| 0.01 | 0.00 | 0.01 | 0.01 | ✓ | 0.00 | 0.00 |

**The identity has no failing input.** Negative variance does not break it; clamping does
not exist; `None` fields cannot occur on a persisted row. The one boundary is behavioural,
not arithmetic: `calculate_percent_consumed` returns `None` when its denominator is ≤ 0,
so the reconstruction is `None` exactly when the **frozen** allowance was ≤ 0 — which is
independent of the payload's current `status`. That is F-4 and Card 1.

**Plan §4 task 1's obligation is discharged in principle** but the plan must say what the
task-1 verification is *for*: it is not "does the identity hold" (it does, unconditionally)
but "where is its output undefined" — and that is the row §5 lacks.

### 3.2 Quantization and rounding loci. **Plan §6's assertion holds — no new locus.**

The reconstruction adds two `Numeric(12,2)` Decimals under `prec = 50`: exact, ≤ 2 dp,
no rounding. The only quantize on the path is the one already inside
`calculate_percent_consumed` (`0.01`, `ROUND_HALF_EVEN`), unchanged. `_decimal(…)` is
`str(Decimal)` over an always-2-dp value, so serialization is exponent-stable. I looked
for values where the two routes disagree in the last place: **none exist**, because both
routes are the *same function* applied to a denominator that is exactly equal
(§3.1's table, column "identity"). §6's STOP-and-report clause is therefore expected never
to fire; it costs nothing and should stay.

### 3.3 The frozen/live split — which keys freeze, which tick

Established from the artifacts and the tree alone, with the branch each surface reaches:

| payload | key | after D9 | producer / branch |
|---|---|---|---|
| E-P | `final.percent_consumed` | **frozen** | `division_serializers.py:_serialize_production_time_final`, via `:serialize_task_production_time` |
| E-P | `budget.percent_consumed` | ticks (D6) | same function, the `budget` dict literal |
| E-B worker | `result.percent_consumed` | **frozen** | `serializers.py:_serialize_result`, `include_monetary=False` branch |
| E-B worker | top-level `percent_consumed` | ticks (D6) | `serializers.py:serialize_task_budget_status`, `_decimal(status.percent_consumed)` |
| E-B manager | top-level `percent_consumed` | ticks (D6) | same expression, shared by both faces |
| E-B manager | `result.*` | no such key | `_serialize_result`, `include_monetary=True` branch ignores the parameter |

The split is implementable inside §3's file set without a key moving (HC-4 safe): both
frozen keys are fed by an argument, and both live keys are separate expressions in the
same function. **But the two live keys are guarded asymmetrically** — C4b guards the E-P
one, nothing guards the E-B one. That is L5 / F-5.

### 3.4 The two feed sites and the one-copy rule

Both §3 shapes are implementable; the plan does **not** determine the choice, and the
consequences differ in ways the plan does not state (F-13). The reciprocal-comment
obligation as written is implementable in the **default** shape only: under service
routing there is one copy, so "comments naming each other" has no referent and must
become "each serializer site names the single computation home". Answering the prompt's
question directly: **the plan delegates the choice, and the obligation is not implementable
in one of the two shapes as worded.**

---

## 4. Evidence scope per criterion (charter "Test-evidence scope and reuse")

| Criterion | Hypothesis | Scope | Why |
|---|---|---|---|
| C1 | "this named row reddens under this named mutation at the E-P call site" | **L1** | phase test file; single named test |
| C2 | same, E-B call site | **L1** | " |
| C3 | same, reconstruction site(s) | **L1** per site, **two** observations | two sites exist under the default shape (F-3) |
| C4a | key absent from one payload under a key walk | **L1** | it is a payload-shape assertion, *not* a repository-wide absence claim — the walk is over one served dict |
| C4b / C4c | two values in one payload differ | **L1** | " |
| **C5** | **"an existing golden this phase does not own stays green, and reddens under the named mutation"** | **L4** | **coupling discovery** — charter L4 trigger (d). The claim is about the bite set outside the phase file, and a bite set can only be bounded by the full suite. My L2 measurement below is a **floor, not a ceiling**. |
| cycle close | clean stamp | **L4** | one per implement/fix cycle, unchanged |

**C5 measured now, at L2** (both item-economics trees, `6508ce1`, clean; 295 tests):

| run | command scope | result | ID delta |
|---|---|---|---|
| contract (change applied, no mutant) | `tests/integration/services/queries/item_economics/ tests/integration/services/commands/item_economics/` | **295 passed** | ∅ / ∅ |
| C5 mutant at **both** sites | same | 2 failed / 293 passed | `+test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`, `+test_production_time_query.py::test_c17_frozen_final_uses_live_percent_without_money` |
| C5 mutant at **E-P only** | same | 2 failed / 293 passed | same two |
| C5 mutant at **E-B only** | same | 1 failed / 294 passed | goldens **only** |

Every criterion can be turned into a complete evidence record **except C5 as written**,
because "the golden stays green" has no both-directions ID delta until the expected bite
set is enumerated. It now is; the amendment should carry it.

---

## 5. Findings

Ordered by consequence. Citations are `path:symbol` per master §5.

### F-1 (blocking) — §3 and §6 describe two different designs
`plans/plan_3.md` §3 makes `division_serializers.py:serialize_task_production_time`
compute the frozen percent; §6 says "the E-P internal dict gains an internal key for the
frozen percent". Under §3's default no such key exists — the serializer already receives
`row["result"]` (`get_task_production_time.py:get_task_production_time` puts
`"result": status.result` in the dict, verified at source). §6 is a correct description of
§3's *alternative*. As written, the implementer's first hour ends in a coin flip.
**Routing:** amend §6. → ledger L1.

### F-2 (blocking, measured) — the declared file set is incomplete
Plan §3 closes with "Nothing else." I applied §3's **default** shape in a sandbox
(repo untouched — §7) and ran the affected suites:

```
4 failed, 171 passed
FAILED tests/unit/services/queries/item_economics/test_phase8_serializers.py::test_budget_status_worker_surface_excludes_money
FAILED tests/unit/docs/test_item_economics_handoff_accuracy.py::test_the_documented_budget_status_keys_are_the_shipped_keys[budget-status-manager-shape]
FAILED tests/unit/docs/test_item_economics_handoff_accuracy.py::test_the_documented_budget_status_keys_are_the_shipped_keys[budget-status-worker-shape]
FAILED tests/unit/docs/test_item_economics_handoff_accuracy.py::test_the_worker_budget_status_carries_no_monetary_key
```

Cause: both suites hand-build the `result` object with **string** minute fields
(`test_phase8_serializers.py:_result` → `actual_worker_minutes="2.00"`,
`variance_worker_minutes="-1.00"`; `test_item_economics_handoff_accuracy.py:_status` →
`"120.00"` / `"40.00"`). `"120.00" + "40.00"` **silently concatenates** to `'120.0040.00'`
and the failure surfaces one frame later as
`TypeError: allowed_worker_minutes must be a Decimal` at
`calculator.py:_guard_type` — a wrong-frame failure of exactly the shape phase 1's
B1-r4 was about.

Note the history: plan 2 §5 C7 explicitly ruled `test_phase8_serializers.py`
**outside** the phase perimeter, on the grounds that it "builds its status objects by
hand". Phase 3 forces the file open. The widening must be deliberate and enumerated
per master §5 ("an amendment that widens a perimeter is itself an enumeration"), with
each file's mode of contact recorded.
**Routing:** amend §3's file set. → ledger L2.

### F-3 (blocking, measured) — C3's and C5's mutation sites are under-determined
Charter rule 11: a named mutation names **where** it is applied. C3 says "the
reconstruction site, whichever file §3 settles on"; C5 says "the same reconstruction site
as C3". §3's default settles on **two** files. Measured (§4's table): mutating E-P alone
and mutating both sites produce the **identical** two-ID delta; mutating E-B alone
produces one ID. So "the golden reddened" is satisfied by mutating either site, and the
un-mutated site ships unproven — the definition-vs-call-site defect phase 1 recorded
(five named mutations never run, B1/B2 the same defect twice).

A second consequence: `test_live_clock_goldens.py:test_prechange_payloads_match_byte_golden_files`
is **one test function looping over all three goldens** (verified at source) and asserts
in sequence, so it short-circuits on the first mismatch — the ID delta alone cannot
attribute a site. The amendment must require **one observation per site**.
**Routing:** amend C3 and C5. → ledger L3.

### F-4 (blocking, upstream) — no criterion at the identity's only boundary
Derived and measured (§3.1): the reconstruction is `None` exactly when
`result.actual_worker_minutes + result.variance_worker_minutes ≤ 0`, and that condition is
**independent of the payload's `status`**. `get_task_budget_status.py:_build_evaluated_status`
sets `status = INFEASIBLE if allowed <= 0` from the **current** evaluation, so a task can
serve `status: "infeasible"` beside a frozen block carrying a real percentage — reachable
by exactly C3's own scenario (re-commit with a lower allowance, here to ≤ 0; a
`production_budget_minor` of 0 yields `allowed = 0.00` through
`calculator.py:calculate_allowed_worker_minutes`). §5 has no row at either side of this
boundary. See also F-11 — this contradicts published documentation, which is why it is
Card 1 rather than a plain amendment.
**Routing:** owner Card 1, then a new criterion. → ledger L4.

### F-5 (blocking, measured) — the E-B live percent is unguarded
C4b keeps D6 alive at the E-P budget block. The E-B **top-level** `percent_consumed`
(`serializers.py:serialize_task_budget_status`, `_decimal(status.percent_consumed)`) has
no equivalent row. I checked whether an existing test covers it: the only candidate is
`test_phase2_live_surfaces.py:test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`,
which asserts `worker_payload[field] == manager_payload[field]` for `percent_consumed`.
Both faces read the **same expression**, so an implementer who froze that expression
freezes both faces equally and the equality still holds — the row cannot see it. And in
the goldens the frozen and live percents coincide at `"15.00"`, so the goldens cannot see
it either. This is the "two surfaces, two rows — sweep the class" lesson (intention
§4.1A B, phase 2's own C12 finding) applied to the *live* half of the split.
**Routing:** add C4c. → ledger L5.

### F-6 (blocking, measured) — the fixture §5A warns about is the fixture that exists
`test_phase2_live_surfaces.py:_make_live_fixture` — the natural reuse target, and the only
fixture in the tree that pairs an `ItemCostResult` with an open working record — carries
`variance_worker_minutes=Decimal("0.00")`, `actual_worker_minutes=Decimal("20.00")`, and
sets `evaluation.allowed_worker_minutes = Decimal("20.00")`. That is §5A's named
degeneracy, present in the code, one import away.

Computed both sides on it (live worked = 2040 s, measured by plan 2's own assertion
`production["budget"]["actual_worker_seconds"] == 2040`; pre-open = 1440 s):

| quantity | value |
|---|---|
| frozen percent (N-4) | 20.00 / (20.00 + 0.00) → **100.00** |
| live percent, pre-open | (1440/60 = 24.00) / 20.00 → **120.00** |
| live percent, open | (2040/60 = 34.00) / 20.00 → **170.00** |

So on this fixture **C1, C2 and C4b bite** (numerators differ) but **C3's and C5's
denominator mutations are inert** — reconstructed allowance 20.00 equals the evaluation's
20.00. The plan warns about the class and prescribes no numbers; master §5's F-C1 rule
("when a contract's reason is 'form A and form B differ', the fixture must be placed where
they differ — compute that before choosing it") requires the plan to carry them, as
plan 2 §5 C6 rows 2–3 do.

For C3 specifically, the plan's "move `allowed_worker_minutes` by enough to change the
quantized percent" is decidable and should be spelled: with frozen `actual = A` and
reconstructed allowance `L`, the contract percent is `round(A/L × 100, 2)` and the mutant
is `round(A/L' × 100, 2)` for the re-committed `L'`; the two differ once
`|A/L − A/L'| × 100 ≥ 0.005`. On the fixture above (`A = L = 20.00`, contract `100.00`),
`L' = 25.00` gives `80.00`.
**Routing:** amend §5 with per-row numbers. → ledger L6.

### F-7 (should-fix, measured) — C5's bite set, supplied
C5's contract side is **confirmed non-vacuous**: the goldens do reach the changed path.
`golden_production_time.json:frozen_no_drift.final` carries `actual 15.00 / variance 85.00
/ percent 15.00`, and `golden_budget_status.json:frozen_no_drift.worker.result` the same,
so the reconstruction returns `15.00` on both and the goldens stay green (measured: 295
passed). Under C5's named mutation both go red (§4's table). The plan's "if the golden
proves not to reach this path, that is a finding" resolves **negative** — no finding — but
the amendment should record the expected bite set (two IDs, not one) so the second red is
not reported as an anomaly, and should state C5's scope as L4.
**Routing:** amend C5. → ledger L7.

### F-8 (should-fix, measured) — an existing test whose name asserts D9's negation survives it
`test_production_time_query.py:test_c17_frozen_final_uses_live_percent_without_money`
asserts `body["final"]["percent_consumed"] == body["budget"]["percent_consumed"]` — the
exact wiring D9 removes. Measured: it stays **green** after the change, because its
fixture sits at the no-drift point (frozen `20.00 / 80.00` → allowance `100.00` → `20.00 %`;
live `1200 s = 20.00 min` against `_seed`'s `allowed_worker_minutes = Decimal("100.00")`
→ `20.00 %`). It is a row that cannot fail with a name that claims otherwise, and it is
now *pre-existing* rather than introduced — but leaving it silent is the prose-claim rot
re-review r5's S1 was about.
**Routing:** §6 note plus a Review-log obligation — retarget or record. → ledger L8.

### F-9 (should-fix) — a comment that becomes a false claim
`division_serializers.py:_serialize_production_time_final` docstring: *"Serialize the
frozen result with the **live** percentage and no money."* After D9 that is false. Master
§5: a comment asserting a property is a claim and inherits the mutation rule. §4 task 2
mandates two *new* comments and is silent about this one.
**Routing:** one clause in §4 task 2. → ledger L9.

### F-10 (note, measured) — the third `_serialize_result` call site
`serializers.py:serialize_item_cost_result_worker` also produces the worker `result` block
with a `percent_consumed` key, always `None` (the parameter defaults). Measured: it has
**no production caller** — `grep -rn` across `app/beyo_manager` finds only
`serializers.py` itself; the sole caller anywhere is
`test_phase8_serializers.py:test_worker_result_serializer_has_no_monetary_fields`.
(`get_item_lifetime_economics.py` uses the *manager* `serialize_item_cost_result`, whose
branch ignores the parameter.) Left unnamed, "sweep the class, not the instance" argues
for changing it; the measured reason not to is that nothing serves it. Say so.
**Routing:** name it in §1's "NOT in this phase". → ledger L10.

### F-11 (note, upstream) — the documented numerics rule
`docs/domains/item_economics/states.md` ("Numerics rule") and
`docs/domains/item_economics/README.md` ("The concrete rule") both state
"`percent_consumed` is `null` for `infeasible`". Today both copies of the key satisfy it
because the frozen copy echoes the live one. After D9 the frozen copy answers to its own
allowance (F-4). **Nothing reddens:**
`test_phase8_status_results.py:test_c7_committed_evaluation_branch_drives_evaluated_status`
asserts `status.percent_consumed is None` on the status object only, and
`test_item_economics_handoff_accuracy.py` compares **key sets**, not this rule — verified
by reading both. A silent doc/code divergence in a rule-6 mechanism.
**Routing:** Card 1's answer; then either a same-phase doc correction or a phase-4
closeout obligation. → ledger L4.

### F-12 (note) — the guard the plan does not state
The computation must sit **inside** the `result is not None` branch at both sites.
`test_phase8_serializers.py:test_c7_readiness_producer_drives_each_status_exactly` drives
ten parametrized rows with `result=None`, and E-P's `idle_no_result` golden serves
`"final": null`. An unguarded computation raises `AttributeError` on all eleven. Cheap to
state, expensive to discover.
**Routing:** one clause in §4 task 2. → ledger L11.

### F-13 (note, measured) — what the delegated shape choice actually costs
Under the **service-layer** shape, `TaskBudgetStatus`
(`get_task_budget_status.py:TaskBudgetStatus`) gains a field. Two constructions in
`tests/unit/routers/api_v1/test_item_economics_router.py` (both inside
`fake_run_service`, `result=None`) pass the full field list by keyword; a field **without
a default** breaks that file too. Measured: under the *default* shape that file is
untouched (171 passed, no router failures). `_empty_status` would also need the field.
Both shapes are viable; the delegation should carry this cost so the choice is informed.
**Routing:** delegation D10. → ledger L12.

---

## 6. Reality checks that passed (recorded so they are not re-derived)

- Every path in §3 exists; `division_serializers.py`, `serializers.py`,
  `item_cost_result.py` and `calculator.py` all carry the symbols §2 names, with the
  wiring §2 claims.
- **Re-commit immunity is structurally real.** `commit_item_cost_evaluation.py` dispatches
  workspace events and **never touches `item_cost_results`** (verified at source); the only
  writer is `process_item_cost_result.py:handle_process_item_cost_result`, enqueued from
  task-state transitions (`_task_state_transitions.py`, `resolve_task.py`, `fail_task.py`,
  `cancel_task.py`, `process_step_transition.py`), upserting on
  `uq_item_cost_results_task_id`. C3's fixture is constructible: supersede + insert a new
  evaluation and the result row is untouched.
- **Precision on D9's wording.** Plan §1 and intention §5.3 say the frozen percent "moves
  on **no** event after the freeze". Strictly, the *result row itself* is re-upserted on
  every admitted task-state transition, so the frozen percent moves exactly when
  `final.actual_worker_minutes` and `final.variance_worker_minutes` move — which is D9's
  real content ("freeze **whole**"). Not a defect; noted because a criterion written to
  the absolute wording is unconstructible.
- The goldens reach the changed path on **both** surfaces (F-7).
- Master §6's baseline, flaky-test facts and `TZ` fact were read. **No `TZ` variation is
  required by this phase** — nothing on the changed path reads a clock or a naive
  datetime; the only time value in the frozen block is `result.computed_at`, already
  tz-aware and untouched.
- Architecture graph: oriented only (`archgraph_status`, two searches). Nothing in the
  graph asserts the percent wiring —
  `projection-item-economics-task-production-time` says "a flat time-only final snapshot"
  with no percent claim, so phase 4's delta is unaffected by this phase's choice.
  **Environment drift, for the coordinator, not for me:** master §6 records the graph as
  "0 pending, 0 stale"; `archgraph_status` at `6508ce1` reports **9 pending, 2 stale**,
  0 diagnostics. The projection prompt says three items pend. I promoted, rejected and
  edited nothing.

---

## 7. Write perimeter (declared in full)

**Documents written — one:**
- `handoffs/reviewer/2026-08-21_phase3_projection_r0_handoff.md` (this file).

**Documents edited — one, my own tracker row only:**
- `master_plan.md` §3 — one appended row for phase 3, actor `Opus 5 (projection r0)`.
  I did not relabel, supersede or edit any other row; the standing
  `PROMPT_READY` row is the coordinator's to supersede at the fold.

**Not touched:** `plans/plan_3.md` (including its Review log — the coordinator's, per the
prompt), any other plan, `planning/intention.md`, `planning/owner_decisions.md`, any file
under `app/`, `docs/domains/`, `docs/handoff/`, or the goldens.

**Code changed: none.** `git status --porcelain` at
`6508ce1` was **empty before this session's first command and empty after its last** —
asserted twice, output recorded in-session.

**Tool-recorded state: none.** Two read-only archgraph calls (`archgraph_status`,
`archgraph_search_nodes` ×2). No `apply_changes`, no review decision, no anchor repair.

**Sandbox artefacts, outside the repository**, in this session's scratchpad
(`…/scratchpad/`), never on `PYTHONPATH` for any run but my own probes, and discarded:
`conftest_probe.py` (§3's default shape applied by monkeypatch at import),
`conftest_mut_c5.py`, `conftest_sitemut.py` (C5's mutant, whole and per-site). Every
measurement in this handoff was produced by loading one of those as a pytest plugin
against an **unmodified** working tree — this is the mechanism by which a projection
session measures without editing code.

**Skeleton:** derived on paper and **discarded**. No sketch is attached; nothing here is
guidance to the implementer beyond the findings and their routings.

---

## 8. Verdict and exit

**AMENDMENTS_REQUIRED** — 14 ledger rows: **10** plan gaps (L1–L3, L5–L11), **1** routed
upstream to the owner (L4, Card 1), **3** free choices proposed as explicit delegations
D10–D12 (L12–L14). 10 + 1 + 3 = 14. Thirteen findings, F-1…F-13, every one cited by a
ledger row. One row (L4) cannot be routed by the coordinator alone.

The gate holds until every row is routed. The implementer prompt for phase 3 compiles
after that, not before.

---

## 9. Addendum — Card 1 answered (2026-08-21, owner, same session)

Appended, not merged: §2's ledger row L4 and the card in §1's decision section are left
exactly as they were relayed, so the record keeps what was **asked** separate from what
was **answered**. A pointer line was added under the card heading and nothing else in
this document was edited.

### 9.1 The answer

**Owner, 2026-08-21:** *"yes, the recommendation is the correct answer."*

Ratified: **the frozen `final.percent_consumed` (E-P) and `result.percent_consumed`
(E-B worker face) keep their own reconstructed number even when the payload's current
`status` is `infeasible`.** The frozen block reports what that job was actually measured
against; it does not go blank because of a re-pricing that happened afterwards. The
documents promising otherwise are corrected, not the code.

**0 owner cards now open.** The gate no longer waits on the owner; it waits on the
coordinator routing the remaining 13 ledger rows.

### 9.2 A premise correction that came out of the exchange — record it, it will recur

The owner's first reading of `infeasible` was "worked time has grown past the budget".
That is **not** what the enum means, and the distinction decides which case the card is
about. Both arise from the same act — shrinking the budget by re-pricing the item — but
they are different states:

| re-pricing outcome | allowance | `status` | `percent_consumed` (live) | affected by D9? |
|---|---|---|---|---|
| budget shrinks, stays positive; worked time exceeds it | e.g. `10.00` | `ok` | `"150.00"`, with `remaining_worker_minutes: "-5.00"` | no — already ships, unchanged |
| budget shrinks to nothing (cost terms ≥ price) | `≤ 0` | `infeasible` | `null` — no denominator exists | **yes — this is the card** |

Grounded at source this session: `calculator.py:calculate_production_budget` returns
`min(price − Σ term_amounts, cap_minor)` with **no floor at zero**, so a residual at or
below zero yields a zero-or-negative budget, and
`:calculate_allowed_worker_minutes` carries no guard against it —
`get_task_budget_status.py:_build_evaluated_status` then reads
`INFEASIBLE if allowed <= 0`. `commit_item_cost_evaluation.py` has no commit-side
rejection of a non-positive budget (grepped). The state is first-class and documented,
not a corner the code stumbles into.

Worth stating plainly because it is the reason the owner's instinct was right for a
reason different from the one they gave: at a zero allowance the manager does **not** go
blind. `actual_worker_minutes`, `variance_worker_minutes` and `remaining_worker_minutes`
are subtractions and keep serving real numbers
(`_build_evaluated_status` computes all three unconditionally). Only the *percentage*
is null, because a percentage of zero is undefined — arithmetic, not policy, and
untouched by this phase.

### 9.3 New finding, raised by the answer

**F-14 (should-fix) — the promise is in a shipped frontend contract, not only in
internal docs.** F-11 named
`docs/domains/item_economics/states.md` and `docs/domains/item_economics/README.md`.
Checking the commit path for §9.2 surfaced a third carrier, and it is the one that
matters most:
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
states, in its status table, *"`infeasible` | the allowance is zero or negative | the
budget does not buy any work; `percent_consumed` is `null`"* — a published promise to
the frontend, in a document
`tests/unit/docs/test_item_economics_handoff_accuracy.py` already treats as a contract
(by key set, not by this rule, so nothing reddens).

Consequence: the correction cannot be a quiet internal doc edit. Master plan §7 closeout
obligation 2 is explicit — **new dated handoff, never an edit** — so the frontend-facing
half of this correction belongs in phase 4's closeout handoff, beside the existing
decrease-semantics disclosure (obligation 5). The internal `docs/domains/` half can land
in phase 3 or 4 at the coordinator's discretion.
**Routing:** new ledger row **L15**, below.

### 9.4 Ledger delta

| # | Decision point | Classification | Routing (updated) |
|---|---|---|---|
| L4 | The `allowed ≤ 0` boundary | intention gap → **ANSWERED 2026-08-21** | Card 1 ratified as recommended. Now a plan amendment: plan 3 §5 gains a boundary criterion with **two rows** — (a) frozen allowance > 0 while current `status == "infeasible"` ⇒ the frozen key carries its exact reconstructed literal, and (b) frozen allowance ≤ 0 ⇒ the frozen key is `null` — each with its own fixture and its own named mutation at each of §3's reconstruction sites (F-3's per-site rule applies). Row (a) is the one the owner decided; row (b) is what stops a future "just null it whenever status is infeasible" edit from passing. |
| L15 | The `infeasible ⇒ percent null` promise also sits in a **published frontend handoff** | plan gap (phase 4) | Fold into phase 4's closeout handoff as a named correction; new dated document, never an edit (master §7 obligation 2). Internal `docs/domains/` correction at the coordinator's discretion in phase 3 or 4. See F-14. |

**Revised totals: 15 ledger rows — 11 plan gaps (L1–L3, L5–L11, L15), 1 owner decision
now ANSWERED (L4), 3 proposed delegations (L12–L14). 11 + 1 + 3 = 15.** Fourteen
findings, F-1…F-14.

### 9.5 What the coordinator's fold owes on this row

1. The owner decision recorded in its **home artifact** — `planning/owner_decisions.md`
   and intention §10 — not only here, and not only in a handoff, which archives
   (master §5: *"record the decision" names its post-closeout medium*). Mine is a
   reviewer handoff; folding upstream is not my write perimeter.
2. **A naming-registry collision to settle before minting the number.** Two `D`
   namespaces already run side by side: the intention's **owner decisions D1–D9**
   (§10.3) and plan 2 §6's **written delegations D4–D9**. `D8` and `D9` therefore
   already denote different things in different files. This answer would naturally
   become owner decision **D10**, and §2 of this handoff proposes plan-3 delegations
   **D10–D12** — a third collision on the same token. Master plan §4 exists to prevent
   exactly this; the fold should disambiguate (e.g. `OD-10` vs `P3-D1…D3`) rather than
   mint `D10` twice. Flagged, not chosen — the registry is the coordinator's.
3. The two internal doc lines (F-11) and the frontend handoff correction (F-14, L15).
4. The boundary criterion in plan 3 §5 per L4's updated routing.

### 9.6 Write perimeter, updated

Unchanged in kind. This addendum and a single `**ANSWERED — see §9**` pointer line under
Card 1's heading were appended to **this file**; my tracker row in `master_plan.md` §3
gained one clause recording the ratification. Still no plan, no intention, no
`owner_decisions.md`, no code, no graph write. `git status --porcelain` remains exactly
two entries: this handoff (new) and `master_plan.md` (my row only).
