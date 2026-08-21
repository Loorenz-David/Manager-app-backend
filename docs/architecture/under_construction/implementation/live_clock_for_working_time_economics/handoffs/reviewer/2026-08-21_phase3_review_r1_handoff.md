---
plan: 3
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-21
actor: Opus 5 (review r1)
---

# Phase 3 review r1 handoff — D9, the frozen percent blocks

**Verdict: CHANGES_REQUESTED — 0 blocking, 2 should-fix, 6 notes.**

**The production code is correct and no production line needs to change.** N-4 is applied
at both feed sites with the right argument order, guarded correctly, and the response
shape is untouched. Both should-fix findings are in the *proof and the authorities*: one
region of the frozen percent has no guard anywhere in the repository (measured ∅/∅ at
L4 under a new mutant shape), and intention §5.3A names the wrong C6 row as the guard for
the coupling OD-10 exists to prevent (measured — the row it names stays green under the
exact edit it is said to stop).

This is the third consecutive phase in this project whose every finding is in a plan, a
criterion or a document rather than in the code.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this round needs an owner answer — OD-10 already settles the semantics
both findings touch, and the archgraph backlog is tracked at `plans/plan_4.md` C6.

## Evidence identity

Reviewer tree: `184f48a`, `git status --porcelain` empty (asserted before and after every
probe). `git diff 5b8329b HEAD -- app/ docs/domains/` is **empty**, so the code and test
surface is byte-identical to the checkpoint; `184f48a` adds only pipeline documents. The
implementer's L4 cycle-close stamp (`26 failed / 2486 passed / 1 deselected`, baseline IDs
unchanged both directions) is therefore tree-valid for this session and is **cited, not
reproduced**, per the charter's test-evidence section. The review budget went to variation:
two mutant shapes no ledger has run.

## Findings

### S1 — should-fix. Intention §5.3A names the wrong C6 row as OD-10's guard. Measured.

`planning/intention.md` §5.3A states: *"A future edit that blanks the frozen percent
whenever `status == "infeasible"` reintroduces exactly the coupling D9 removes;
`plans/plan_3.md` C6 row (b) exists to redden on it."* **Row (b) does not redden on it.**

C6b's fixture sets the current evaluation's `allowed_worker_minutes = 0.00`, so its
payload's `status` is `infeasible`. An implementation that blanks the frozen percent
whenever `status == "infeasible"` therefore produces exactly the `null` C6b asserts, and
C6b passes. The row that bites is **C6a**, whose fixture is the one holding a positive
reconstructed allowance beside an `infeasible` current status.

Measured, this session:

| field | value |
|---|---|
| hypothesis | under a status-based blanking implementation at both sites, does C6b redden? |
| scope | **L1** — a named-row bite question, not an absence claim |
| mutant | `if _enum_value(status) == "infeasible": frozen_percent_consumed = None`, inserted after the reconstruction at **both** sites (`division_serializers.py:serialize_task_production_time`, `serializers.py:serialize_task_budget_status`) |
| command | `PYTHONPATH=. python3 -m pytest -q --tb=line -o log_cli=false tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py -p no:randomly` |
| tree | `184f48a` + declared probe diff; clean before and after |
| result | **1 failed / 24 passed** |
| ID delta | `+test_c6a_frozen_percent_survives_infeasible_current_evaluation` only. **`test_c6b…` stayed green.** No removals. |

The implementer's own ledger already contains the disproof — its two status-blanking rows
report `+test_c6a…` and nothing else — but it was read in the direction "did C6a bite?"
and never in the direction "did C6b?". The same inversion is carried in `plans/plan_3.md`
§5 C6 (*"row (b) is what stops a future 'just null it whenever status is infeasible' edit
from passing"*) and in `master_plan.md` §3's PROMPT_READY row.

**Authority violated:** `planning/intention.md` §5.3A (semantic authority); echoed in
`plans/plan_3.md` §5 C6 and `master_plan.md` §3.

**Correction:** swap the attribution in all three places — **row (a)** reddens on the
status-blanking edit; **row (b)** reddens on a positive-fallback denominator. Optionally
strengthen C6b by giving its *current* evaluation a positive allowance (status `ok`) while
keeping the frozen figures summing to `≤ 0`, so its `null` can only come from the frozen
basis. As written, C6b's fixture satisfies **two independent sufficient causes** for
`null` — the charter rule-2 companion condition, and the same shape as the plan-3
round-2 B1 the charter cites.

Not a code defect and not the implementer's: they built what the plan specified.

### S2 — should-fix. The frozen percent's over-budget region has no guard anywhere in the repository. Measured ∅/∅ at L4.

Every fixture in the phase that pins a **numeric** frozen percent sits at or below 100 %:
C1/C2/C4b/C4c at exactly `100.00`, C3 at `80.00`, C6a at `15.00`; both goldens at
`15.00`; `test_c17` at `20.00`. C6b is the phase's only negative-variance row, and its
variance is chosen so the reconstructed allowance lands on exactly `0.00` and the answer
is `null`. **The phase therefore never evaluates the reconstruction where
`variance_worker_minutes < 0` and the reconstructed allowance is still positive** — a
finished job that overran its budget, which is OD-10's own first table row (`"150.00"`
beside a negative `remaining_worker_minutes`) and the most consequential number the frozen
block serves.

Probe — a mutant shape in no ledger: clamp the frozen percent at 100, the plausible
"a percentage cannot exceed 100" edit.

| field | value |
|---|---|
| hypothesis | **absence claim** — does *any* test in the repository redden when the frozen percent is clamped at `100.00`? |
| scope | **L4**, charter trigger (d): an absence claim is repository-wide by construction |
| mutant | `if frozen_percent_consumed is not None and frozen_percent_consumed > Decimal("100.00"): frozen_percent_consumed = Decimal("100.00")`, inserted after the reconstruction at **both** sites |
| command | `PYTHONPATH=. python3 -m pytest -q --tb=no -o log_cli=false -m 'not e2e'` |
| tree | `184f48a` + declared probe diff; clean before and after |
| result | **26 failed / 2486 passed / 1 deselected / 2 warnings** — identical to the cycle-close stamp |
| ID delta | `comm`-diffed against `master_plan.md` §6's enumerated 26: **∅ added, ∅ removed** |
| focused cross-check | phase file + goldens + the two enumerated files + `test_production_time_query.py`: **100 passed** under the mutant |

**Corollary for `plans/plan_3.md` §5B — the degeneracy is one worse than recorded.** §5B
records that `_make_live_fixture`'s `variance = 0.00` makes the reconstructed and current
denominators coincide. It also puts the frozen percent at exactly `100.00`, the boundary
of this entire mutant family — so four of the phase's seven rows are pinned at the one
value a clamp cannot move. §5A's rule (*compute the verdict under both bases before
choosing the fixture*) was applied to the numerator and not to the output's range.

**Authority:** `planning/intention.md` §10.4 (OD-10's premise table, row 1) and §5.3A;
`master_plan.md` §5 ("every term of a defining equation gets a criterion that varies it
away from its identity element" — extended here to the output's regions).

**Correction:** one row, cheapest home beside C6b in `test_phase2_live_surfaces.py`:
stored `actual_worker_minutes = 15.00` / `variance_worker_minutes = −5.00` →
reconstructed allowance `10.00` → frozen `"150.00"`, with the current evaluation left at
a positive allowance so `status` stays `ok`. **Named mutation:** the clamp above ⇒
contract `"150.00"`, mutant `"100.00"`, red. Assert on both faces, as C6a does.

### N1 — note. C3 shows the live percent landing, not moving.

`test_c3_recommit_changes_live_denominator_not_frozen_percent` asserts
`after["budget"]["percent_consumed"] == "80.00"` but never `before["budget"]`, which is
`"120.00"` (live `24.00` against the pre-recommit allowance `20.00`). In the *after* state
the live and frozen percents coincide at `80.00`. The row's discrimination rests entirely
on `before["final"] == "80.00"`: under C1's mutation the two after-state assertions pass
and only the before one bites. That is sound, and `after["budget"]` does prove the
re-commit was observable (a mutant ignoring it yields `120.00`). Adding
`assert before["budget"]["percent_consumed"] == "120.00"` makes the movement explicit and
survives a later fixture change. Confirms probe P2 with no load-bearing dependency on the
coincidence.

### N2 — note. Two criteria in one test function: sufficient, with one residue.

C4b's assertions live inside `test_c1_ep_final_freezes_while_budget_percent_ticks`
(declared; permitted by P3-D2). Both criteria carry independent exact literals and each
named mutation trips a *different* assertion, so attribution is derivable by construction:
C1's mutant fails at assertion 1 (`final` `120.00 ≠ 100.00`), C4b's at assertion 3
(`budget` `100.00 ≠ 120.00`). **Residue:** assertions run in sequence, so under C1's
mutation the test short-circuits and C4b's assertions never execute — that run carries no
information about C4b. C4b's own mutation supplies it, so the pair is jointly sufficient.
Verdict on probe P1: **acceptable evidence, C4b need not become its own row.** Lesson
only — when one test function carries two criteria, the ledger row records which
*assertion* each mutation trips, not just the test ID.

### N3 — note. T13's E-B clause is proven narrower than stated.

`planning/intention.md` §9A T13 asks that the E-B worker face's **`result` block** be
byte-identical to the pre-open payload. C1 delivers exactly that for E-P
(`open_now["final"] == pre_open["final"]`); C2 and C4c pin only the `percent_consumed`
key on the E-B side. Residual risk for *this* phase is nil — the block's other keys read
straight off the frozen ORM row and only the percent argument moved — but a future change
to the E-B result block has no byte-identity guard. Phase 2's
`test_c4_frozen_open_record_payloads_are_byte_identical` does not close this: it is a
two-serves-on-one-frozen-clock determinism row, not a pre-open-vs-open comparison.

### N4 — note. `test_c17`'s misleading name is recorded where its readers will not look.

Recording rather than retargeting was one of the two options `plans/plan_3.md` §6
permitted, so this is not a conformance failure, and the record is durable (`plans/` does
not archive). But the false claim lives in
`tests/integration/services/queries/item_economics/test_production_time_query.py` and the
correction lives in a pipeline document a reader of that file has no reason to open — the
"a delegation grant names its post-closeout medium" rule (master §5) applied to a claim
rather than a delegation. A one-line comment above `test_c17` costs nothing and puts the
correction where the claim is read. Probe P6 assessed: the judgment is defensible, the
medium is not.

### N5 — note. Site comments name the other site in prose rather than `path:symbol`.

*"The budget-status serializer names this feed site"* / *"The production-time serializer
names this feed site"*. `plans/plan_3.md` §4 task 2 asked only that the comment name the
other site, so this is compliant. Recorded because master §5 binds citations to
`path:symbol` so a cross-reference resolves from a clean checkout, and
`serialize_item_cost_result_worker` is a second serializer a reader could land on.

### N6 — note. The frozen computation runs on the manager face and is discarded.

`serialize_task_budget_status` computes `frozen_percent_consumed` before branching;
`_serialize_result(include_monetary=True)` ignores the argument entirely. Harmless — both
stored columns are `Numeric(12, 2) NOT NULL` — and keeping one computation in one place is
the right trade. Recorded because it is *why* `test_phase8_serializers.py`'s manager-side
fixture was forced open, and because it makes `calculator.py:_require_rate` reachable from
a path that consumes nothing.

## Verified correct — settled ground for any re-review

- **N-4 applied correctly at both sites.** Argument order checked against
  `calculator.py:calculate_percent_consumed(allowed_worker_minutes, actual_worker_minutes)`:
  both call sites pass the reconstructed sum first. No quantize or clamp added; the only
  rounding locus on the path remains the calculator's own `0.01 / ROUND_HALF_EVEN`.
- **The `result is not None` guard is complete.**
  `get_task_budget_status.py:_empty_status` sets `result=None`, so every
  non-`ok`/`infeasible` path — including all ten
  `test_c7_readiness_producer_drives_each_status_exactly` parametrizations — never reaches
  the computation, and E-P's `idle_no_result` golden serves `"final": null`.
- **HC-4 holds.** No key added or removed at either site; both key-set parametrizations in
  `test_item_economics_handoff_accuracy.py` are unchanged.
- **C4a is structural, not behavioural.** `_serialize_result`'s `include_monetary=True`
  branch has no `percent_consumed` key at source, and the recursive walk is non-vacuous
  (nine keys yielded).
- **P7 — absence claim over the repository, L4 by construction.** Search terms recorded
  per master §5: `percent_consumed`, `percentConsumed`, `percent-consumed`, via
  `grep -rn --include="*.py"` over `app/beyo_manager/` (23 hits across 5 files). **Exactly
  two production sites produce a frozen percent and both are changed.** The price-scenario
  endpoint consumes `get_task_budget_status` but `serialize_task_price_scenario` emits no
  `percent_consumed`; `serialize_item_lifetime_economics` passes through
  `episodes`/`totals` and emits none; `serialize_item_cost_result_worker` is the third
  `_serialize_result` producer, has no production caller, and its `percent_consumed` is
  `None` by parameter default — plan §1's exclusion confirmed independently.
- **P5 — doc class sweep over `docs/`, excluding the pipeline folder.** The two prose
  statements of the old undifferentiated rule were `docs/domains/item_economics/states.md`
  ("Numerics rule") and `docs/domains/item_economics/README.md` ("The concrete rule"); both
  are corrected, and **both new statements are true**: `calculate_percent_consumed` returns
  `None` iff `allowed ≤ 0`, and `_build_evaluated_status` sets `INFEASIBLE` iff
  `allowed ≤ 0`, so "the live `percent_consumed` is `null` for `infeasible`" holds exactly,
  and the frozen clause matches §5.3A. The remaining occurrences are JSON examples sitting
  at the no-drift point and **still numerically true after D9** — `api.md:539/571/577`
  (`120.00 / 40.00 → 160.00 → 75.00`) and
  `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md:96/166`
  (`160.00 / 35.00 → 195.00 → 82.05`) — so neither needs correcting, which is worth
  recording because both look like the old rule at a glance. The one false statement left
  in the tree is `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md:513`, already
  tracked as `plans/plan_4.md` C8 and correctly out of scope here.
- **The corrected `_serialize_production_time_final` docstring is true** — the block it
  serializes carries the frozen percentage and no monetary key.
- **P4 — the degenerate fixture.** C1, C2, C4b and C4c each retain a sufficient
  discriminator at `variance = 0.00` (frozen `100.00` against live `120.00 → 170.00`), and
  no row silently depends on the degeneracy for its *stated* hypothesis. The one thing §5B
  did not record about that fixture is S2's corollary above.
- **Perimeter.** Ten declared items = ten files in `5b8329b`; goldens and
  `test_live_clock_goldens.py` untouched, which is what makes C5's green-golden claim mean
  anything.

## Mutation-probe declaration

Two probes, both applied to production files and both reverted.

| probe | files touched | reverted | verification |
|---|---|---|---|
| clamp-at-100 (S2) | `app/beyo_manager/domain/item_economics/division_serializers.py`, `app/beyo_manager/domain/item_economics/serializers.py` | yes, `git checkout --` | SHA-256 diffed against the pre-probe capture: **byte-identical** |
| status-blanking (S1) | the same two files | yes, `git checkout --` | SHA-256 diffed against the same pre-probe capture: **byte-identical** |

Pre-probe digests (both restored to these exactly):

```
d9160f92fad81991729d67e1714b9492f4215a75bbffb7f9684b69384ef48979  division_serializers.py
65558c5179bc8596bf10c27b16215baabc9875cfadc66459e550fcab52b0ee46  serializers.py
```

`git status --porcelain` is empty at `184f48a` after both reverts. **No file outside these
two was written by any probe**, and this handoff plus one tracker row plus one Review-log
entry are this session's entire write perimeter.

**Database/state side effects:** none beyond ordinary suite execution — no manual writes,
no fixture left committed, no schema or migration touched. Two L4 runs and two L1 runs
were executed; per master §6 the suite's residue rows are never evidence of a change.
**Tool-recorded state:** no architecture-graph call of any kind was made this session — no
orientation, no write. The graph remains at the inherited 9 pending / 2 stale.

## Lessons for the plans

1. **A ledger answers the question it was asked, and reviewers must ask the complement.**
   The status-blanking rows were recorded as "did C6a redden?" and answered yes. Nobody
   asked "did C6b?", and the answer was sitting in the same row's ID delta — a single ID
   where the plan's prose implied two. **When a plan divides labour between two rows, the
   ledger row for a mutation states which of the pair did *not* bite, not only which did.**
2. **"Neither row can be satisfied by the other's fixture" is not the same claim as
   "each row kills its own mutant".** `plans/plan_3.md` §5 C6 asserts the first (true) and
   uses it to justify the second (false as attributed). Two rows can be mutually
   unsatisfiable and still both be blind to the same edit.
3. **A criterion must vary the *output's* regions, not only the input terms.** §5A's rule
   pushes fixtures off identity elements of the arithmetic. S2 is the same class one level
   out: every input term was varied, but the reconstruction's output never left the
   `≤ 100` region, so a whole family of plausible edits is invisible. **For a derived
   quantity with named regions in its own authority (OD-10's table names three), the
   criteria enumerate the regions.** Eleventh instance of the row-that-cannot-fail class
   on this project, and a fifth distinct shape: degenerate fixture *value*, degenerate
   *controlling term*, degenerate *procedure*, *absent-but-recorded-as-shipped*, and now
   **degenerate output range**.
4. **A "retarget or record" option set should name the medium for the record.**
   `plans/plan_3.md` §6 offered recording in the Review log; master §5 already requires a
   record to name a medium that survives where its claim is read. The two rules did not
   meet, and the correction landed in a document the misleading test's readers never open.
5. **When a plan permits two criteria in one test function, it should also require the
   ledger to attribute by assertion.** Sequential asserts short-circuit; the second
   criterion's evidence comes only from its own mutation, and the ledger should say so.

## Carry-forward dispositions

Not applicable — the verdict is CHANGES_REQUESTED, so nothing carries past this round
unresolved. For the fix cycle's scope:

| id | severity | destination | scope |
|---|---|---|---|
| S1 | should-fix | coordinator (documents only) | `intention.md` §5.3A, `plans/plan_3.md` §5 C6, `master_plan.md` §3 — swap the attribution; optionally re-specify C6b's current allowance as positive |
| S2 | should-fix | fix cycle (test-only) | one row in `test_phase2_live_surfaces.py`; `plans/plan_3.md` §5 gains it as **C6c**, §5B gains the range corollary |
| N1 | note | fix cycle (test-only, same file) | one added assertion in `test_c3…` |
| N4 | note | fix cycle or `plans/plan_4.md` | one comment above `test_c17` |
| N2, N3, N5, N6 | note | coordinator | lessons and record only; no code or test change required |

**No production line is in scope for the fix cycle.** If any file under
`app/beyo_manager/` changes, that is an automatic finding at re-review.
