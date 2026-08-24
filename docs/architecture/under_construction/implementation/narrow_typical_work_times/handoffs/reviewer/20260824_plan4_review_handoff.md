---
plan: plan_4
role: reviewer
round: 1
date: 2026-08-24
actor: Opus 5
verdict: CHANGES_REQUESTED
---

# Plan 4 — review round 1 handoff

**Tree reviewed:** `748e709 docs(narrow-typicals): the review gate would have halted on my own miscount`,
`git status --porcelain -- app/` empty at entry and at exit.

## Opening, in plain words

The production engineering of phase 4 is sound and I could not break it. Both consumers derive a
spec, call the statement once, reconcile through `uniform_basis_v1`, and hand the *same*
`SelectedTypical`s to display and to weights. The refactor did not move a single number on either
golden — I verified that with an instrument nobody has used yet — and the mixed-batch production fix
that fix round 2 found is correct under all three attacks the prompt named. The 21-ID baseline is
stable in serial on a tree carrying three new integration files, which nobody had established.

The round is owed for **coverage**, and in the same place the phase has been owed twice before.
Two criteria (C1(c), C13(c)) never became committed tests at all, and C5 — the criterion that
carries §3B's layer-2 visibility contract — has rows whose stated shapes no fixture produces. I
measured C5's zero-disclosure row invisible at the criterion's own declared scope. Separately, the
mutation ledger is two rows short of the plan's actual mutation count; I ran both missing mutations
myself and both bite, so no further round is needed for *those two*, only for the record.

**⚠ OWNER DECISIONS REQUIRED (0)** — nothing needs you. One graph observation is routed as a note
for whenever you next open the graph; it is not a gate.

---

## Ledger

### BLOCKING

**B1 — blocking — C5's three rows are not implemented as specified, and row (b)'s reachable form is
invisible at C5's own declared scope.**

*Location:* `plans/plan_4.md` §6 C5 vs
`app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py:79-104`.

*What is wrong.* C5 specifies three rows over the division wire:

| row | specified | what exists |
|---|---|---|
| (a) | participating section, section-wide count **below floor** → `typical_worker_seconds: null`, `typical_basis: "insufficient_sample"`, `sample_count: <section_sample_count>` (§3B B3, i.e. **non-zero**), `allowance_seconds` present and non-null | no fixture. `test_c3_…:60-67` covers the **missing-key** shape (`divide_production_budget(…, {})`), whose `sample_count` is `0` — a different branch and the one value §3B B3 exists to pin |
| (b) | **T16b′** — `section_wide_uniform` task, participating section whose **section-wide median is `0` at count ≥ floor** → `typical_worker_seconds: 0`, `typical_basis: "section_wide"`, `sample_count: <n>`, allowance present | `:104` only: `serialize_budget_step({**row, "typical_worker_seconds": 0, "typical_basis": "section_wide"})["typical_worker_seconds"] == 0` — a pass-through on a hand-built dict that already carries the answer. The output `typical_basis` is not asserted, `sample_count` is not asserted, and no fixture produces a zero median at count ≥ floor |
| (c) | task level, **row (a)'s task** → `sections_by_basis.insufficient_sample >= 1` | absent. `:102` asserts `insufficient_sample: 1` inside a hand-built `TaskTypicalSelection`, not on row (a)'s task, which does not exist |

*Evidence gathered at source.* Mutation, `typical_filters.reconcile_task_typicals` (definition), the
participating non-narrowed branch — republish a zero section-wide median at count ≥ floor as
`insufficient_sample` / `None`:

```
- section_evidence.section_typical_worker_seconds,
- "section_wide" if section_evidence.has_section else "insufficient_sample",
+ section_evidence.section_typical_worker_seconds or None,
+ "section_wide" if section_evidence.has_section and section_evidence.section_typical_worker_seconds else "insufficient_sample",
```

L2 (C5's own declared scope: `tests/integration/services/queries/item_economics` +
`tests/unit/domain/item_economics`) → **346 passed**. The mutation is invisible. Corroborating sweep:
`grep -rn "SectionTypicalEvidence(" tests/` returns **no** construction with a zero section-wide
value at count ≥ floor, anywhere in `tests/`.

This is the exact hazard §4C was written to protect. §4C's own text: D25 made the narrowed-zero shape
unreachable on task surfaces, so *"the **reachable** zero form is `section_wide` + `0`, which is row
(b)"* — and that reachable form has no fixture. Charter rule 2's companion and master plan §9
(*"a criterion whose instrument cannot return the expected result"*, *"confirm the fixture contains a
row the mutation moves"*).

Note also that the plan's own projection fold closed C5(i) with an explicit instruction:
*"**Pin C5(a)'s fixture** — 'no participating section has a usable typical', which makes the flip
exactly `1` — **or** write the resolved fallback into the row. Either is acceptable; **leaving it
unstated is not.**"* Neither was done, because C5(a) has no fixture to pin.

*Correction.* Add to `test_narrowed_task_economics.py`, on a real session:
1. **row (a)** — a participating section with a section-wide count strictly between 1 and
   `TYPICAL_MIN_SAMPLE_SIZE`, asserting the wire triple with `sample_count` equal to that count as an
   **exact literal** (not `0`), plus `allowance_seconds is not None`;
2. **row (b)** — a section with ≥ `TYPICAL_MIN_SAMPLE_SIZE` completed section totals **all summing to
   0**, asserting `(0, "section_wide", <n>)` on the step row and the section row as exact literals,
   with the allowance present;
3. **row (c)** — on row (a)'s task, `sections_by_basis["insufficient_sample"] >= 1`.
   Then run C5's mutation (i) and (ii) against these rows and record which assert each bit, per rule 12.

---

**B2 — blocking — C1(c) and C13(c) never shipped as committed tests.**

*Location:* `plans/plan_4.md` §6 C1(c) and C13(c); nothing in `app/tests/`.

*What is wrong.* Both criteria state their form explicitly:

- **C1(c)**: *"…contain none of `live_seconds`, `load_live_worked_seconds`, `total_working_seconds`.
  **Expected ∅ / ∅**, **as a committed test** (§9: absence criteria ship as tests, never as a session
  grep)."*
- **C13(c)**: *"**absence, L4, root = repository root, terms stated**: no private copy of the
  excluded-state predicate remains. Search terms: `SKIPPED`, `CANCELLED`, `FAILED`,
  `EXCLUDED_STEP_STATES`, `_step_state_is_excluded`."* Master plan §10 names this row specifically as
  *"an absence criterion that ships as a committed test walking the repository (plan 4 C13(c)) is an
  **L1 test** with a repo-wide claim"* — i.e. the plan already anticipated a committed test and even
  budgeted for it.

Neither exists. Round 1's blocking **B2** was raised for exactly this class ("three criteria have no
committed test") and closed for C8/C10/C11; C1(c) and C13(c) were never in B2's list, so nobody
looked. Master plan §9, earned in plan 1: *"Plan 1's C4(c) and C17 were both re-measured **correct**
at review — **the defect was the form**: nothing in the suite went red, so later phases inherited an
unguarded claim."* Plan 5 inherits both claims.

*Evidence gathered at source — the substance is true, only the form is missing:*

- C1(c): `live_seconds`, `load_live_worked_seconds`, `total_working_seconds` → **∅ / ∅ / ∅** in
  `app/beyo_manager/domain/item_economics/typical_filters.py`.
- C13(c), repo root, `grep -rn --include='*.py' -E "EXCLUDED_STEP_STATES|_step_state_is_excluded" .`
  → 8 hits in `budget_division.py` (definition + call sites + `__all__`), 2 in
  `get_task_price_scenario.py` (`:14` import, `:134` use of the **shared** predicate), 5 in
  `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`
  (`:11`, `:181`, `:1078`, `:1094`, `:1151`). Private frozensets naming the excluded states outside
  `budget_division.py`: **∅**. **No private copy exists.**

*Correction.* Ship both as committed tests in this phase's perimeter, each asserting **non-emptiness
of its own walk** as a contract (the C0 escape-3 lesson) before asserting the term set — and pin
C13(c)'s exceptions **by name**, including the two `get_task_price_scenario.py` lines, so removing an
exception cannot silently widen the claim. See N8: C13(c)'s stated expectation needs one word changed
before it can be transcribed.

### SHOULD-FIX

**S1 — should-fix — `_step_result` carries an unreachable production branch that publishes a
contract-violating triple, and nothing asserts it.**

*Location:* `app/beyo_manager/domain/item_economics/budget_division.py:270-278`.

```python
elif selected is not None:
    # Keep the pure helper tolerant of old unit-call shapes while all service
    # callers use SelectedTypical as the contract requires.
    typical_worker_seconds = selected
    typical_basis = "section_wide" if selected is not None else "insufficient_sample"
    sample_count = 0
```

*What is wrong.* Three things, in ascending order of importance.

1. The conditional is a tautology: inside `elif selected is not None:` the `else "insufficient_sample"`
   arm is unreachable.
2. The branch publishes `(value, "section_wide", 0)`. That triple is **impossible** under the
   reconciliation contract: `section_wide` is count-gated at `section_sample_count >=
   TYPICAL_MIN_SAMPLE_SIZE` (`typical_filters.py:149-150`), and §3B B3 requires `sample_count` to be
   that count. So a basis claim ships with no sample behind it.
3. It exists to avoid updating the 23 int-valued third-argument literals in
   `test_budget_division.py` — the surface §5 task 4 explicitly named as the one to convert:
   *"there are **24** `divide_production_budget(` call sites in the same file, whose int/`None`-valued
   third argument (**23** typicals-shaped dict literals) **becomes `Mapping[str, SelectedTypical]`**
   once task 1 changes the parameter."* The divergence is undeclared — neither handoff mentions it;
   the code comment is the only record (charter rule 14).

Its cost is that a service regressing to the pre-phase int shape would keep working and publish
plausible-looking rows instead of failing. C3's contract (§3B B4) covers a **missing key**, not a
**wrong-typed value**.

*Evidence.* Mutation, same site: `typical_basis = "item_narrowed"`, `sample_count = 99`. Scope
`tests/integration/services/queries/item_economics` + `tests/unit/domain/item_economics` +
`tests/unit/routers/api_v1` + `tests/unit/services/queries/item_economics` → **494 passed**. The
fabricated triple is asserted by nothing.

*Correction.* Convert the 23 literals in `test_budget_division.py` to `SelectedTypical` (the phase
file's own `selected()` helper at `test_narrowed_task_economics.py:51-53` is the pattern) and delete
the branch, so the annotation `Mapping[str, SelectedTypical]` is load-bearing. If the branch is kept
deliberately, it needs its own criterion row and a declared divergence sentence.

---

**S2 — should-fix — `test_item_economics_domain_walk_is_recursive` is `f(x) == f(x)` and cannot detect
the escape it is named for.**

*Location:* `app/tests/unit/domain/item_economics/test_domain_purity.py:31`.

```python
def test_item_economics_domain_walk_is_recursive():
    assert _domain_modules() == sorted(PACKAGE_ROOT.rglob("*.py"))
```

`_domain_modules()` **is** `sorted(PACKAGE_ROOT.rglob("*.py"))` plus an assert, so the right-hand side
is a re-implementation of the left. Master plan §9: *"**Prefer an exact literal over an equality
between two calls.** `f(a) == f(b)` throws away the discriminating power."*

*Evidence.* Mutation, C0 escape 1 re-applied **alone** — `rglob` → `glob` in `_domain_modules`, no
leak file created — `tests/unit/domain/item_economics/test_domain_purity.py` → **4 passed**. The guard
is green under the defect it names. It reddens only under the *combination* of the glob revert **and**
a subpackage existing, and the package has no subpackage (measured at the projection fold, and
confirmed: `find app/beyo_manager/domain/item_economics -type d` returns the package and
`__pycache__` only).

This is escape 3's shape — *"a guard that walks a directory needs a row proving the walk found
something"* — reproduced one level up, inside the file written to close it. `_domain_modules`'s
`assert modules` is correct and does close escape 3; it is escape 1's new guard that does not bite.

*Correction.* Have the test create a subpackage under `tmp_path`, point `PACKAGE_ROOT` at it
(the sibling test already shows the `monkeypatch.setitem(globals(), …)` idiom), and assert the walk
**finds the nested module** — a positive claim about a fixture the test controls, not an equality with
the implementation.

---

**S3 — should-fix — C2's production-time half has no exact-literal assertion; both committed literals
are on budget-allocations.**

*Location:* `app/tests/integration/services/queries/item_economics/test_production_time_query.py:205`
and `:207`.

C2 requires the literal *"on production-time's task block **and** on every budget-allocations task
entry."* In that test `e2 = get_task_budget_allocations(...)` and `e3 = get_task_production_time(...)`.
Both v2 assertions read `e2`:

- `:205` `assert all(row["allocation_method"] == "static_proportional_section_v2" for row in e2["budget_allocations"])`
- `:207` `assert e2_row["allocation_method"] == ALLOCATION_METHOD == "static_proportional_section_v2"` where `e2_row = e2["budget_allocations"][0]`

`grep -rn "static_proportional_section_v2" tests/` returns exactly these two assertions plus the two
goldens. **Production-time's `data.allocation_method` is pinned only by the byte-golden.**

Why this survived: round 1's S2 said *"the exact-literal v2 assertion exists for production-time
(`test_production_time_query.py:206`)"* — but `:206`/`:207` is `e2_row`, a **budget-allocations** row.
S2's premise mis-read the variable, so the fix round added a **second** budget-allocations assertion
and the uncovered half stayed uncovered. Master plan §9, *"a measurement at one site is not a
measurement of the surface"*, applied to a variable name.

*Not silently unguarded:* ledger row 6 shows the C2 mutation reddening
`test_prechange_payloads_match_byte_golden_files`, and I confirmed both goldens carry v2 as a value.
So the claim cannot regress silently — but C2's stated instrument is absent, and the coordinator's
closure row for S2 is inaccurate.

*Correction.* One line: `assert e3["allocation_method"] == "static_proportional_section_v2"`. Then
re-run C2's mutation and record **both** failing ids.

---

**S4 — should-fix — the mutation ledger is two rows short of the plan's mutation count, and three
artifacts state that count wrongly.**

Re-derived from `plans/plan_4.md` §6 at source, one row per *named* mutation:

| criterion | named mutations | in the 22-row ledger |
|---|---:|---|
| C0 (3 escapes + 2 standing regression probes) | 5 | rows 1–3, 17–18 |
| C1 (i)(ii) | 2 | rows 4–5 |
| C2 | 1 | row 6 |
| C3 | 1 | row 7 |
| C4 | 1 | row 8 |
| C5 (i)(ii) | 2 | rows 9–10 |
| C6 | 1 | row 11 |
| C7 (i)(ii) | 2 | rows 12–13 |
| **C8** | **1** | **absent** |
| C9 (i)(ii) | 2 | rows 14, 19 |
| C10 (i)(ii) | 2 | rows 20–21 |
| **C11** | **1** | **absent** |
| C12 | 1 | row 15 |
| C13 | 1 | row 16 |
| **total** | **23** | 21 + 1 anti-regression = 22 |

`master_plan.md` §4 row 4, `plans/plan_4.md` §8's consumption entry and the correction2 handoff all
say *"the 21 named"*. The 21 is round 1's B3 arithmetic (16 ledger rows + 5 identified absent),
computed against a round in which **C8 and C11 had no test at all**, so their mutations were never
counted. When B2 forced C8/C11 into existence, the count was carried forward from the finding instead
of re-derived from the plan — master plan §9, *"enumerate a mutation's bite set from the code **after**
the repair, never from the finding that requested it"*, and the count-in-a-sentence class, **fifth**
instance in this phase.

*Evidence — I ran both, and both bite:*

- **C8's mutation**, verbatim (`get_task_production_time`, call site — guard the evidence/reconcile
  block with the budget status condition):
  `if section_ids:` → `if section_ids and status.status in {EconomicsStatusEnum.OK, EconomicsStatusEnum.INFEASIBLE}:`
  → **1 failed / 10 passed**,
  `test_c8_no_budget_branch_reconciles_before_the_early_return` at **`:198`**,
  `assert 'section_wide_uniform' == 'item_narrowed_uniform'`.
- **C11's mutation**, verbatim (`get_task_budget_allocations`, call site — resolve typicals locally,
  taking `section_typical_worker_seconds` unconditionally) → **2 failed / 9 passed**,
  `test_c11_both_consumers_publish_the_same_literal_typical_triples` at **`:290`**,
  `(540, 'section_wide', 7) != (540, 'item_narrowed', 7)` on **both** sections; collateral bite on
  `test_c10_…` at `:246`, `assert [27] == [7]`.

*Correction.* Add these two rows to the ledger with the observed ids and assert lines above, and fix
the count to **23** in the three artifacts. No re-run is owed — the evidence is in this handoff, taken
on this tree.

---

**S5 — should-fix — C1's rows (a)/(b) are asserted as an equality between two calls, with no exact
literals and no non-emptiness guard, against a criterion that demands exact literals.**

*Location:* `test_narrowed_task_economics.py:369-383`. C1 row (a) reads *"every `allowance_seconds` is
identical across the two calls, **asserted as exact literals per section**"*; row (b) *"the same
equality, asserted separately."* The test asserts
`[(section, allowance) for … rows[0]] == [(section, allowance) for … rows[1]]` on both surfaces —
`f(a) == f(b)`, the form master plan §9 names twice (*"Prefer an exact literal over an equality
between two calls… This killed four inert checks in the lineage"*), and the form the criterion's own
closing sentence forbids (§9: *"a criterion's closing sentence is a criterion"*).

Second half: neither comparison is preceded by a non-emptiness assertion, so both would pass on
`[] == []`. C13's test, four functions above, does guard this (`assert production["sections"]`).
The fixture is not currently empty, so this is latent, not live — but it is the C0 escape-3 shape.

*What the equality cannot see:* a defect that makes **both** calls wrong identically — typicals
derived from a constant-but-wrong source. Exact literals per section would catch that; this form
cannot. Critical rank 5 is the wrong row to leave in the weaker form.

*Correction.* Assert `allowance_seconds` per section as exact literals on **both** `ctx.now` calls and
on both surfaces, and add the non-emptiness assertion. Then re-run C1(i)/(ii) — see reality check 9
for the siting that makes them bite.

### NOTES

**N1 — `plans/plan_4.md` has no §6A.** `## 6B`'s own title, §8's consumption table row C-3, §8's
provenance note and this review's prompt all cite "§6A". Plan 2 gave its projection fold a real
`## 6A` section; plan 4 folded the amendments **in place** into §6 instead, so "§6A" means "§6 as
amended". Harmless here because §6B exists and the gate keyed on it — but a citation to a section that
does not exist is the charter's *"amendments never renumber sections other documents cite"* rule
pointing the other way. Either add a `## 6A` pointer stub naming what it refers to, or rewrite the
four citations as "§6 as amended at the projection fold".

**N2 — task 11's living-docs-guard record is still owed in §8.** Task 11: *"**Run the living-docs
guard** … and **record the result in §8**"*; master plan §5: *"the record of having checked is still
owed."* §8 has no such record — the guard appears only inside the correction2 handoff's `422 passed`
aggregate. Measured standalone on this tree: `PYTHONPATH=. pytest tests/unit/docs -q` → **59 passed**,
matching master plan §10's stated 59. Record that line and the obligation is discharged.

**N3 — `serialize_typical_resolution`'s no-selection default hardcodes two version strings.**
`division_serializers.py:110-111` writes `"uniform_basis_v1"` and `"primary_item_category_v1"` as
literals rather than importing `RECONCILIATION_METHOD` / `COMPARABILITY_PROFILE` from
`typical_filters` (both already imported into that module's namespace via `TaskTypicalSelection`). A
future bump of either constant would leave this branch publishing the old value on every payload with
no selection — including both regenerated goldens. Tests asserting the literal are correct per rule
13; **production** should read the constant.

**N4 — dead scaffolding: `test_budget_division.py`'s `step()` helper keeps an unused `typical=None`
parameter** (`:13`) after task 4 removed `typical_worker_seconds=typical` from its body, and callers
still pass it (e.g. `:97` `step("c", typical=1)`). Charter rule 4. Remove with S1's conversion.

**N5 — C6's implemented distribution differs from the criterion's, and the agreement clause is implied
rather than asserted.** C6 specifies `sections_by_basis == {"item_narrowed": 0, "section_wide": 2,
"insufficient_sample": 1}` with `participating_section_count == 3`, *"and that the two agree:
`sum(sections_by_basis.values()) == participating_section_count`"*. `:102-103` asserts `{1, 1, 1}` and
`3`. Discriminating power is equivalent (the mutation gives `{2,1,1}` summing to 4), so this is not a
defect — but the `sum(...) == participating_section_count` line is a criterion clause with no
assertion, and 1+1+1 = 3 makes the agreement true by coincidence of the chosen numbers.

**N6 — C10's `:242` is unreachable, and the coordinator's N2 attribution is wrong about the lines.**
`:242` `assert len(captured_specs[0]) == 3` can never fail without `:238`'s exact 3-tuple comparison
failing first, so row (b)'s designated instrument is subsumed by the stronger assertion above it (no
loss of coverage). And N2 inferred that the three C10 mutations *"must have failed at `:242`, `:246`
and `:250`"*; measured, C10(i) (dedupe by `id(spec)`) fails at **`:238`**, not `:242`. This is exactly
why N2 asked for observed rather than inferred attribution — the inference was wrong in the same note
that flagged it as an inference.

**N7 — dead conditionals in the budget-allocations mixed-batch branch.** In
`get_task_budget_allocations.py`'s `elif specs:` arm, `task_spec_index is not None` is always true —
the `spec_index is None` case `continue`s above it. Residue from before the correction2 fix; harmless,
but it reads as if the arm still handles a case it cannot receive.

**N8 — C13(c)'s stated expectation is false as written, before it is even transcribed.** The row
expects *"every hit outside `budget_division.py` and the enum definitions is a **test** fixture."*
Measured, `get_task_price_scenario.py:14`/`:134` are production hits — a legitimate **import** of the
shared `_step_state_is_excluded`, not a private copy, and price-scenario is explicitly plan 5's (§1).
Correct the row to "…is a test fixture **or a documented import of the shared predicate**, enumerated
by name" before B2's committed test is written, or the test cannot be made green honestly.

**N9 — the recorded graph delta names different nodes than §7 expected.** Plan §7 expected
`projection-item-economics-task-production-time`,
`projection-item-economics-task-budget-allocations` and `source-file-item-economics-budget-division`;
the round-1 handoff records source links for *"the production-time contract test, budget-allocation
contract test, and `budget_division.participating_sections`"*, and correction2 recorded no delta. The
coordinator verified the **policy** (three links, `path` + `symbol` + `contentHash`, **zero spans** —
correct under master plan §8's interim policy) on this same tree, which I consume by citation rather
than re-measure. What is unverified is whether the two **projection** nodes' changed contracts were
recorded at all. **Routed to the owner, not acted on** — agents never promote, reject or edit a review
item.

**N10 — C0 escape 2's fix drops the prescribed `count(...) == 1` pin.** The plan says *"strip only the
pinned occurrence; **keep the `count(...) == 1` pin**"*; the implementation uses
`source.replace('"config_fingerprint": scenario["config_fingerprint"]', "", 1)` with no count
assertion. The direction is safe — a reworded pinned line makes `replace` a no-op and the term
survives, so the test fails closed — and it is arguably stronger than the prescription. Recorded as an
**undeclared** divergence (charter rule 14): the reasoning belongs in the handoff, not only in the
diff.

**N11 — both narrowing fixtures are uniform within each category.** `seed_categorized_two_section_task`
seeds 7 groups at 540 and 7 at 600; `seed_batch_dedupe_fixture` seeds 7×600, 9×900, 11×1200. In every
case median == mean and the value is invariant under duplication and ordering — master plan §9's
*"a uniform fixture is an inert fixture… the median must not equal the mean, and must not be invariant
under duplication."* It costs nothing for the rows actually asserted here (C10 discriminates on
**counts**, which are distinct 7/9/11; C11 discriminates on the **basis string**), and the statement's
median arithmetic is phase 2's territory. Routed to **plan 5**, which reuses both fixtures: any plan-5
row asserting a *typical value* needs a non-uniform group multiset first.

---

## Reality checks — verified correct, do not re-verify

1. **Perimeter is exact, name for name.** `git diff --name-status 353a8c9 HEAD -- app/` returns 14
   paths: the 4 production files, `routers/README.md`, the 6 tests/goldens and the 3 new files, exactly
   as §4 declares (11 modified + 3 new). No undeclared write. `.archgraph/` untouched by the pipeline.
2. **The prompt's live question is answered: the 21-ID set is composition-stable in serial.**
   `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e' -n 0 -p no:randomly` (redis `PONG` first) →
   `21 failed, 2686 passed, 2 skipped, 1 deselected` in 134.30s; collected 2710 / 1 deselected / 2709
   selected. Programmatic diff against the published block in
   `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7: **actual − published = ∅,
   published − actual = ∅.** So the serial and parallel failing sets are **identical** on a tree
   carrying three more integration tests than the tree phase 2 established that on. The count delta
   against the parallel stamp (2686/2 vs 2687/1) reconciles exactly: `-n 0` skips
   `tests/integration/infrastructure/test_database_isolation.py:118`, whose own skip reason is
   *"serial comparator deliberately overrides the shipped parallel default."* Nothing moved.
3. **C12's review half passes, by an instrument nobody has used.** Rather than re-count the
   coordinator's keys and values, I extracted every leaf path from both goldens at `353a8c9` and at
   `HEAD` and compared the sets: **0 leaves removed**, **0 pre-existing *numeric* leaves changed**, and
   exactly **4** value changes across both files — `allocation_method`
   `static_proportional_section_v1` → `…_v2`, twice per file, under `frozen_no_drift` and
   `idle_no_result`. `golden_production_time.json` +22 added leaves, `golden_budget_allocations.json`
   +20, all additions. **The refactor did not move a number** — the safety property this phase exists
   to preserve, confirmed on the gate's own accept condition.
4. **C9(a)'s snapshot is honest and not vacuous** (prompt probe 3, both halves).
   (i) It has **no `typical_resolution`** at any depth, so its shape is pre-refactor.
   (ii) The read is `assert SNAPSHOT.exists()` at `:154` with no write branch — B1 is closed and
   biting.
   (iii) `assert_preexisting_numeric` compares **24** numeric/`None` leaves, and they are the
   quantities the refactor rewrites: `typical_worker_seconds = 1200` on three surfaces (both
   budget-allocation steps and production-time's section `typical` block),
   `typical.sample_count = 5`, `allowance_seconds = 4800`, `left_seconds = 3600`/`4800`,
   `worked_seconds = 1200`/`0`, `actual_worker_seconds = 1200`, `step_count = 2`,
   `min_sample_size = 5`, `window_days = 90`. Not "keys that are trivially equal".
   (iv) Its `e7b2c41` re-capture changed **only** the fixture's random `uuid4` tokens
   (`wsec_a2d848a481` → `wsec_2b0c82a99a` etc.) — every number byte-identical. That is why strings are
   uncompared: the ids differ on every run by construction.
   *Bounded caveat, not a finding:* strings fall through all three branches, so `share_state` and
   `status` are uncompared on this surface. Faithful to the criterion's word "numeric"; C12's gate
   covers `share_state` on the goldens, and I verified ∅ there.
5. **The `spec_index is None` fix is correct under all three attacks** (prompt probe 1),
   `get_task_budget_allocations.py:274-289`.
   (a) *A section with no row at index 0 (C3(c)'s soft-deleted shape):* the branch guards with
   `if row is None:` and constructs `SectionTypicalEvidence(section_id, None, 0, None, 0)` → the
   honest `insufficient_sample` terminal. The guard is right.
   (b) *Is `(section_id, 0)` guaranteed when `K >= 1`?* Yes for every **live** section — the statement
   emits one row per live section × spec_index — and exactly the non-live case is what (a) guards. No
   fabricated key is inserted into `typical_rows`.
   (c) *Does the new `continue` change `K == 0`?* No. It sits inside `if specs and task_spec_index is
   None:`; with `specs == ()` that condition is false and control falls through to
   `typical_rows.get((section_id, None))`, byte-for-byte the pre-fix path.
   And the narrowed slots are hard-set `None, 0`, so no spec-0 population can be attributed to a
   category-less task — the Critical rank 2 hazard.
6. **C11 is written correctly** (prompt probe 6): `:286-293` asserts two **exact-literal dicts**,
   `{section_a: (540, "item_narrowed", 7), section_b: (600, "item_narrowed", 7)}`, once against
   production-time and once against budget-allocations. It is **not** `production == allocations`.
   `:285` asserts `task_typical_basis == "item_narrowed_uniform"`, discharging charter rule 10. Its
   named mutation bites (S4).
7. **C8's fixture honours §6A's precondition** (prompt probe 4).
   `seed_categorized_two_section_task` creates exactly **two** sections and gives each **7**
   same-category completed groups — both above `TYPICAL_MIN_SAMPLE_SIZE`. The third, thin section from
   master plan §6.9's seed is not in the task's steps. Better than a documented precondition: the test
   asserts `participating_section_count == 2` and `task_typical_basis == "item_narrowed_uniform"`, so a
   fixture that drifted onto the thin section would fail loudly rather than pass for the wrong reason.
8. **C10's fixture arithmetic discriminates, and rows (c)/(d) are armed.** `category_specs =
   (("chair", 7, 600), ("table", 9, 900), ("stool", 11, 1200))` — **distinct counts** (7/9/11) and
   **distinct medians** (600/900/1200), which is what the coordinator's fold demanded. Under
   `(spec_index + 1) % K` the chair task reads the table population and `:246` flips `[7]` → `[9]`.
   Row (c)'s subject is pinned (`fixture["tasks"][0]`) and its literal is exact. Row (d)'s
   `tasks[45:]` are the category-less tasks by construction (`task_index >= 45` → `category_name =
   None`). The section-wide count is **27** (7+9+11 in one section), independently confirmed by
   probe B's collateral red `assert [27] == [7]` — matching fix round 2's measurement.
9. **C1's three fixture preconditions all hold, and C1(i) bites when sited per precondition 2.**
   `_seed_two_section_allocation` yields **two** participating sections (base section with
   `tsp_live` PENDING + `tsp_failed` FAILED, plus `wsec_second_…` with `tsp_second_live` PENDING);
   the test installs a WORKING `StepStateRecord` on **every** PENDING step, so both sections carry an
   open record; and the two `ctx.now` values are 1 day apart with history closed 1 day back, well
   inside one 90-day window. C1(i) applied verbatim in `get_task_production_time` — substituting the
   accruing open step's `live_seconds` into that section's `SelectedTypical.typical_worker_seconds` —
   gives **2 failed / 9 passed**: `test_c1_…` reddens on the allowance comparison
   (`3840` vs `4709`), with a collateral bite on `test_c11_…`. **See refutation 3: my first attempt at
   this probe was mis-sited and went green.**
10. **The weight-ladder delegation is arithmetically identical to the code it replaced.**
    `apply_business_fallback(values, terminal=Fraction(1,1))` computes
    `usable = [Fraction(v) for v in values if v is not None and v > 0]`,
    `fallback = median(usable) if usable else terminal`, and returns each value's own fraction or the
    fallback — term for term the deleted inline ladder. `zip(allocated_groups, resolved_values)` cannot
    truncate: both lists are built from `allocated_groups` in one pass. The `Fraction(1,1)` terminal's
    second job holds — C4's mutation reddens by raising `ZeroDivisionError`, as ledger row 8 records.
11. **§3B B3's `sample_count == section_sample_count` is genuinely guarded.** Mutation:
    `reconcile_task_typicals`'s participating non-narrowed branch reports `0` instead of
    `section_evidence.section_sample_count`. L2 → **5 failed / 341 passed**, including phase 1's
    `test_typical_filters.py::test_reconciliation_row_c_has_a_below_floor_participant_fixture` — which
    is C5(a)'s shape at the domain layer — and C9's snapshot. The contract is protected; B1 is about
    the **wire** rows C5 claims, not about this.
12. **Task 9c is done and accurate.** `routers/README.md` gains 24 rows and I checked each against the
    serializer actually written: `serialize_task_production_time`'s `typical_resolution` and
    `serialize_production_time_section`'s eight-key `typical` block match field for field;
    `serialize_budget_allocation`'s `typical_resolution` + six sub-fields and
    `serialize_budget_step`'s `typical_basis` / `sample_count` match. `applied_filter` marked
    Required = "No" is correct under this file's own convention (nullable-but-always-present fields
    such as `typical_worker_seconds` and `data.final` are marked the same way). Nothing else was
    flipped. *Small gap, not worth a round:* `sections_by_basis` is documented as `object` without its
    fixed three keys, while `typical_resolution` one level up is enumerated.
13. **`participating_sections` is genuinely the single implementation, and C13(a)'s observable works.**
    `divide_production_budget` now derives `allocated_groups` from
    `participating_sections(live_steps)` (`:334-335`) and both services call
    `budget_division.participating_sections(...)`, so all three resolve through one module attribute —
    which is exactly what makes `monkeypatch.setattr(budget_division, "participating_sections", …)` at
    `test_c13_…:302` move all three at once.
14. **Handoff N1's phantom literal confirmed harmless.** `uniform_basis_v2` occurs nowhere in the
    repository; the assertions correctly use `static_proportional_section_v2`. Prose only.
15. **Docs guard green on this tree:** 59 passed (see N2).
16. **C0 escape 3's fix is correct and rule-13-clean:** `_domain_modules` asserts non-emptiness as a
    **contract** (`assert modules`), never `== 10`, and `test_…_requires_a_nonempty_package` verifies
    the assert fires. The C0 probe left no residue — the domain package contains no `sub/` directory.

## Refutations — things I set out to break and could not

1. **`sections_by_basis` under-summing `participating_section_count`.** I expected a participating
   section absent from the statement result (a soft-deleted section named by a step) to be missing
   from `selection.selected`, so `serialize_typical_resolution`'s
   `for section_id in selection.participating_section_ids: … if basis is not None` would skip it and
   the sum would fall below the count, breaking §7.2's stated invariant on C3(c)'s shape. **Refuted at
   source:** `reconcile_task_typicals` materializes `_zero_evidence(section_id)` for **every** id in
   `section_ids` (`typical_filters.py:290-293`) and writes a `SelectedTypical` for every one of them,
   and both services pass `section_ids` derived from the steps — a superset of the participating set.
   `selected` therefore always covers `participating_section_ids`, and the sum cannot fall short.
2. **§3B B3's `sample_count` being unguarded** because C5(a) has no fixture. Refuted by measurement —
   reality check 11, 5 tests bite. This is why B1 is scoped to the wire rows and not written as a
   contract defect.
3. **My own C1(i) probe produced a false green, and it was my error, not the suite's.** My first
   attempt chose the victim section with `setdefault` over `division_steps` ordered by `client_id`, so
   it picked `tsp_failed_…` — a **settled** FAILED step whose live seconds are constant at both
   `ctx.now` values. The substituted typical therefore did not move and `test_c1_…` passed. That is
   precisely C1's fixture precondition 2 (*"if that section's steps are all settled, `live_seconds` is
   identical at both values and the mutation moves nothing"*) and master plan §9's *"a probe that lands
   in the wrong place measures nothing, and its green is the most dangerous result available."*
   Re-sited on the accruing open step, it bites (reality check 9). Recorded in full because a reviewer's
   mis-sited green is the same defect as an implementer's.
4. **`zip(allocated_groups, resolved_values)` silently dropping a section.** Refuted structurally —
   equal lengths by construction (reality check 10).
5. **C10 row (c) being satisfiable by a uniform fixture.** Refuted — the three categories carry
   distinct counts, which is the quantity the row asserts (reality check 8). The uniformity that *does*
   exist is within each category's values, and is routed as N11 rather than as a finding.

## Carry-forward dispositions

Not applicable — the verdict is `CHANGES_REQUESTED`, so every note above returns with the fix cycle.
Two notes are explicitly **not** this phase's to close and are routed now so they cannot evaporate:

| item | destination |
|---|---|
| N9 — graph delta node identity | **owner**, next graph session; agents never adjudicate |
| N11 — uniform fixture multisets | **plan 5**, which reuses both narrowing fixtures |
| N8 — C13(c) wording | must be corrected **before** B2's committed test is written |

## Mutation-probe declaration

Every probe applied and reverted in this session; every file verified byte-identical afterwards
against checksums taken **before** the first probe.

| probe | file touched | md5 before | md5 after |
|---|---|---|---|
| A — C8's named mutation | `beyo_manager/services/queries/item_economics/get_task_production_time.py` | `aff094ded01e15235865bf06c378d8bd` | `aff094ded01e15235865bf06c378d8bd` |
| B — C11's named mutation | `beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` | `c484abc692ea7899e86a622c14e15c89` | `c484abc692ea7899e86a622c14e15c89` |
| C — §3B B3 `sample_count` | `beyo_manager/domain/item_economics/typical_filters.py` | `c888e3d24748edfa6fe22a0c24605b45` | `c888e3d24748edfa6fe22a0c24605b45` |
| D — C5 row (b) zero form | `beyo_manager/domain/item_economics/typical_filters.py` | `c888e3d24748edfa6fe22a0c24605b45` | `c888e3d24748edfa6fe22a0c24605b45` |
| E — C0 escape 1 alone | `tests/unit/domain/item_economics/test_domain_purity.py` | `f4aa971ab6c87c359185f682d27f3440` | `f4aa971ab6c87c359185f682d27f3440` |
| F — tolerance-branch triple | `beyo_manager/domain/item_economics/budget_division.py` | `c4b92b4c860f775ab5310ff8b90e8eee` | `c4b92b4c860f775ab5310ff8b90e8eee` |
| G / G2 — C1(i), mis-sited then re-sited | `beyo_manager/services/queries/item_economics/get_task_production_time.py` | `aff094ded01e15235865bf06c378d8bd` | `aff094ded01e15235865bf06c378d8bd` |

**No file was created.** No `sub/` directory or leak module was produced (C0's escape 1 was measured
by reverting `rglob` alone, deliberately, which is what found S2). **Database and state side effects:**
none beyond what the tests' own `try/finally` fixtures create and delete; every probe ran through the
committed test fixtures, which own their teardown. `git status --porcelain -- app/` is **empty** at
exit, and the phase file plus `tests/unit/domain/item_economics` are green again (**218 passed**).

## Evidence budget

**L4: exactly 1 run, spent on variation, with the question stated before the run** — the serial
comparator against a tree carrying three new integration files (reality check 2). The implementer's
parallel stamp on `9693a26` was **not** re-run; it is consumed by citation, its tree matching mine
(`git diff HEAD -- app/` empty). All mutation probes ran at L1 (the phase file) or L2 (C5's own
declared bite set) per master plan §10. C13(c)'s and C1(c)'s substance was established by repository
greps, which master plan §10 states are a different axis from a suite run and consume no stamp.

## Lessons for the plans, routed by artifact

**To `master_plan.md` §9 (new standing rules):**
1. **A mutation count is re-derived from the plan after every criterion is added, never carried from
   the finding that added it.** B3 computed "21" as *round 1's ledger + what round 1 was missing*, on a
   round where two criteria had no test. Two rounds later three artifacts still say 21 against a plan
   that names 23, and C8's and C11's mutations reached a review unrun. The existing rule ("the ledger's
   row count must match the plan's mutation count") assumed someone had counted the plan; nobody had.
   **Cheap enforcement: the fix prompt states the count and names the criteria it summed.**
2. **A closure claim that names a `file:line` names the variable too.** Round 1's S2 asserted the
   production-time v2 literal existed at `test_production_time_query.py:206`; the line is real and the
   assertion is on `e2_row`, a **budget-allocations** row. The premise was wrong, so the fix doubled
   the covered half and left the uncovered half uncovered (S3). This is *"a measurement at one site is
   not a measurement of the surface"* at the granularity of an identifier.
3. **A guard written to close a vacuity must not be an equality with its own implementation.** C0's
   escape 3 was closed correctly (`assert modules`), and escape 1's replacement guard is
   `assert _domain_modules() == sorted(PACKAGE_ROOT.rglob("*.py"))` — `f(x) == f(x)`, green under the
   glob revert (S2). Third generation of one shape in one small file. **When a fix round writes a new
   guard, mutate the guard, not only the code it guards.**
4. **A criterion's "reachable form" clause is a fixture obligation.** §4C exists solely to say that
   T16b′'s testable shape is `section_wide` + `0`, and no fixture produces it (B1). A clause that
   identifies which of two shapes is reachable is naming the fixture that must be built; without one it
   converts into a serializer pass-through on a hand-built dict.

**To `plans/plan_4.md`:**
- §6 C5: rows (a)/(b)/(c) need fixtures and the mutation observables the projection fold demanded (B1).
- §6 C1: rows (a)/(b) need exact literals per section plus a non-emptiness assertion, and the row
  should record the siting that makes (i)/(ii) bite — the accruing open step, not merely "one
  section's typical" (S5, refutation 3).
- §6 C13(c): correct the expectation to admit the shared-predicate import (N8).
- §6 C2: state which surface each literal is asserted on, since one test holds both (S3).
- §6 C6: either restore the `{0, 2, 1}` distribution or record why `{1, 1, 1}` replaced it, and assert
  the `sum(...) == participating_section_count` clause (N5).
- §6 C10: drop or re-purpose `:242`, whose claim `:238` already subsumes (N6).
- §6B / §8 / §6's own title: resolve the "§6A" citations (N1).
- §8: record the living-docs guard result (N2, measured 59 passed).

**To `master_plan.md` §4 and the correction2 handoff:** the mutation count is 23, not 21 (S4).

**Process, for the coordinator:** this round's two most useful findings (B1, B2) are both *criteria
with no committed test*, the same class as round 1's blocking B2. B2's list was assembled by reading
the new test file and asking "which criteria are missing?", which finds criteria with **no** test but
not criteria whose test asserts something weaker, and not criteria whose rows are absence claims with
no test file to be missing from. **A completeness pass over §6 that walks every criterion and every
row letter — including absence rows — would have caught all five of this round's findings before
dispatch.**
