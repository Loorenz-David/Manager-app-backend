---
plan: plan_4
role: reviewer
round: 2 (delta re-review)
date: 2026-08-24
actor: Opus 5
verdict: CHANGES_REQUESTED
---

# Plan 4 — delta re-review (round 2)

**Tree:** `24af53a docs(narrow-typicals): dispatch the plan-4 delta re-review`
`app/` clean at entry and exit (`git status --porcelain -- app/` empty both times;
`git diff HEAD -- app/` empty at exit).

**Verdict: `CHANGES_REQUESTED` — 0 blocking / 3 should-fix / 7 notes / 0 owner cards.**

**Both round-1 blocking findings are closed, and B1 is closed and biting.** The production
engineering was settled in round 1 and is not re-derived here. What is owed is entirely in
test and fixture code: three guards shipped this round are weaker than the criterion they
discharge, and one of them (C13(c)) is blind to the exact defect it names — measured, not
argued. No production change is requested. Fix round 4 is three test-file edits.

## Gate check — all four pass

1. `git merge-base --is-ancestor 748e709 HEAD` → succeeds. `HEAD` not pinned.
2. `plans/plan_4.md` header `state: REVIEWING`; `master_plan.md` §4 row 4 agrees.
3. §8 ends with *"2026-08-24 — fix round 3 consumed → delta re-review (coordinator)"*.
4. `git status --porcelain -- app/` empty. Outside `app/`: the owner's `.archgraph/` work
   (expected) **plus one stray edit — see N6.**

`redis-cli ping` → `PONG` before any run.

## Step 1 — verified perimeter: exact, 8/8

`git diff --name-status 748e709 HEAD -- app/` returns exactly the eight declared paths, name
for name, `M` on all eight (+290/−78). **No undeclared write.**

**Coordinator probe residue: none.** Of the three files the coordinator probed on this tree,
`typical_filters.py` and `get_task_production_time.py` show **no diff at all** from `748e709`,
and `get_task_budget_allocations.py`'s 4 changed lines are round 3's declared N7 cleanup, not
probe residue (verified semantically — see reality check 3). The two md5s I measured at exit
match the values the coordinator recorded for its own reverts: `typical_filters.py`
`c888e3d24748edfa6fe22a0c24605b45` (coordinator: `c888e3d2…`), `get_task_production_time.py`
`aff094ded01e15235865bf06c378d8bd` (coordinator: `aff094de…`). Same tree, same bytes.

## Step 2 — round-1 findings: closure and bite

| finding | status | evidence |
|---|---|---|
| **B1** C5(a)/(b)/(c) | **closed and BITING** | coordinator's tree-matched measurement (346 passed → 1 failed / 350 passed) consumed by citation; my L2 baseline of **351 passed** reconciles with its 350+1 exactly. Independently strengthened by variation — see reality check 1 |
| **B2** C1(c) + C13(c) | **closed in form; both halves are weaker than the row** | C1(c)'s surviving root **bites** (measured, RC-2); C13(c) **does not bite on the shape it names** (measured, S1) |
| **S1** tolerance branch | **closed, and the annotation is load-bearing** | branch gone; `divide_production_budget(..., {"s": 1})` now raises `AttributeError: 'int' object has no attribute 'typical_worker_seconds'` (measured). But the conversion re-created the impossible triple in the fixtures — S2 |
| **S2** recursive-walk guard | **closed and BITING** | `rglob`→`glob` alone → **1 failed / 3 passed** (was 4 passed). Fails at `test_domain_purity.py:13` — see N2 |
| **S3** C2 production-time | **closed** | `test_production_time_query.py:206` asserts on `e3`, verified at source; C2's mutation re-measured through ledger row 24 |
| **S4** ledger count | **record now adequate — but only because the coordinator measured it** | the handoff's sentence is false against its own 26-row table (C8/C11 absent). The coordinator re-measured both on THIS tree with sites, observed asserts and md5s, and wrote them into §8. That record is tree-correct; the published handoff is not rewritten. No further round owed on this |
| **S5** C1(a)/(b) | **closed** | exact `3200`/`1600` per section, both clock values, both surfaces, plus a DB re-read of the open steps. Non-emptiness: `assert expected_allowances` is a two-key literal and cannot fail, but the `next(...)` above it raises `StopIteration` if the second section is missing, and both consumer assertions are dict equalities against a non-empty literal — a fixture that produced nothing reddens. Adequate |
| **N1–N10** | closed | N3 verified at source (`division_serializers.py:115-116` reads `RECONCILIATION_METHOD` / `COMPARABILITY_PROFILE`); N5's `sum(...)` clause present and its mutation re-measured (RC-4); N6's dead `:242` assertion replaced; N7's dead conditionals gone and inert (RC-3) |

## Step 3 — the open finding (C1(c)): the row should never have had a second root

**Adjudication: striking the void root is correct, and it is not quite the whole fix.**

The coordinator's diagnosis is right in every particular. The evidence is built inline in both
services; both **must** carry `total_working_seconds=live_seconds[step.client_id]`; so the
second root was void as a symbol and unsatisfiable as a claim. L9 narrowed a semantic claim to
an instrument that could not decide it, and the honest answer is that **the row should never
have had a second root** — not that round 3 implemented it badly.

**What is still owed is in the test, not the criterion** (finding S3 below): the shipped test
still *contains* the struck half (`inspect.getsource(selected)` — the test file's own helper),
still carries `assert roots` on a one-literal list, and is still **named**
`test_c1c_typicals_and_evidence_helper_do_not_import_live_clock_terms`. A future reader takes
that name as a guard over the evidence builder. There is no such guard, and the plan now says
so; the test must stop claiming otherwise.

**Is any mechanically checkable absence claim over the two services available? Yes, exactly
one, and it is narrower than L9 wanted.** `live_seconds` is legitimate in the `DivisionStep`
construction and in the `actual_seconds` sum, and illegitimate in the evidence path. Those are
distinguishable by span, not by file: assert that `live_seconds` does not occur inside the
`SectionTypicalEvidence(...)` / `reconcile_task_typicals(...)` argument spans of either
service. That is the honest form of L9's intent and it is checkable. **My recommendation is to
not require it**: C1's mutations (i)/(ii) already discriminate the same hazard behaviourally
and I re-measured (i) biting on this tree (RC-5), so the structural guard buys defence in
depth against a fixture that might one day stop discriminating — worth a plan-5 note, not a
plan-4 round. What plan 4 owes is the deletion of the void half.

## Findings

### S1 — should-fix — C13(c) admits a faithful private copy in the one file it enumerates as its exception

**Measured.** In `get_task_price_scenario.py` I removed the import of the shared
`_step_state_is_excluded` and added a faithful local definition (same `getattr`-unwrap, same
three state values), preserving the file's occurrence count at 2:

- L2 (`tests/integration/services/queries/item_economics/` + `tests/unit/domain/item_economics/`)
  → **351 passed**. `test_c13c` green. **The guard does not see it.**
- A *disagreeing* copy (comparing the enum object to lowercase strings) → **3 failed / 348
  passed**, all three in `test_price_scenario_query.py::test_c5_each_excluded_state_removes_its_section`.
  So the disagreeing shape is caught by behaviour, which is exactly what C13's own note says:
  *"a faithful copy is what an implementer writes, and a faithful copy agrees."* **The shape
  the structural row exists to catch is the one it misses.**

Both probes reverted; `get_task_price_scenario.py` md5 `8a261d763b3a6414554c84083f1a7396`
identical before and after each.

**Why it misses.** The test asserts `hits <= allowed` and pins
`price_scenario.read_text().count("_step_state_is_excluded") == 2`. A local `def` plus its call
site is also 2. So all three assertions hold over a private copy. The criterion's own words —
*"a documented **import** of the shared predicate"* — are the part not made mechanical.

**Second half of the same finding: an undeclared divergence (charter rule 14).** C13(c) states
five terms (`SKIPPED`, `CANCELLED`, `FAILED`, `EXCLUDED_STEP_STATES`,
`_step_state_is_excluded`) and the repository root; the shipped test uses two terms and the
production root, and the handoff does not say so. **The narrowing is substantively right** — I
measured **40** files under `app/beyo_manager/` mentioning the three state names, so a
name-enumerated allowlist over them would be a rule-13 time bomb — but rule 14 exists because
an undeclared divergence costs the next reviewer a finding on a non-defect.

**Correction (both halves, three lines):**
1. `assert "def _step_state_is_excluded" not in path.read_text()` for every hit except
   `budget_division.py` — bites on my probe, and it is the criterion's own "documented import"
   made mechanical.
2. Keep the two-term sweep, and close the different-name hole with the claim I measured
   available: **0** files under `app/beyo_manager/` contain a set/frozenset literal naming two
   or more of `SKIPPED`/`CANCELLED`/`FAILED`, so that absence is assertable today.
3. Declare the term/root narrowing in the round's divergence section (rule 14).

**Authority:** plan_4 §6 C13(c); charter rules 11 (a safety guard that survives its own defect
is decoration) and 14.

### S2 — should-fix — the `SelectedTypical` conversion re-created, in the fixtures, the impossible triple round-1 S1 deleted from production

Round-1 S1's complaint was that `_step_result`'s tolerance branch published the impossible
triple `(value, "section_wide", 0)`. The branch is gone. The conversion then hand-built the
same triple 23 times.

**Measured, both ways, on the production path:**

```
{"s": 1}                    -> AttributeError                       (fail-loud: good, S1 closed)
{"missing": None}           -> (None, 'insufficient_sample', 0)     (production handles it by design)
{"missing": selected(None)} -> (None, 'section_wide', 0)            (what the fixtures now say)
```

`selected()` in `test_budget_division.py` defaults `basis="section_wide"`, so every row that
used to pass a bare `None` now publishes `typical_basis: "section_wide"` with a null value,
and every row that passed an int now publishes `section_wide` with `sample_count: 0` — a state
production cannot reach (the floor is `TYPICAL_MIN_SAMPLE_SIZE = 5`). **Nothing in that file
asserts `typical_basis`, so the drift is invisible**, and no criterion is currently weakened.
It is still a fixture that asserts arithmetic through an unreachable domain state, in the file
§5 task 4 named, introduced by the round raised to remove that very triple.

**Correction:** for the None-valued rows either keep the bare `None` mapping value (the
`selected is None` branch handles it — measured above) or pass
`basis="insufficient_sample"`; and give the helper a `count` consistent with its basis
(`>= TYPICAL_MIN_SAMPLE_SIZE` for `section_wide`), or derive the basis from the value.

**Authority:** charter rule 3 (invariants proven on production-shaped state) and round-1 S1.

### S3 — should-fix — C1(c)'s test still carries the root the plan struck

Per step 3. The surviving half is real and bites: inserting a `live_seconds` reference into
`typical_filters.py` → **1 failed / 222 passed**, failing at
`test_narrowed_task_economics.py:514` with the offending path in the message (probe reverted,
md5 `c888e3d24748edfa6fe22a0c24605b45` identical).

**Correction:** delete `helper_source` and its assertion; delete `assert roots` or replace it
with something that can fail (`assert all(path.exists() for path in roots)`); rename the test
to what it now guards (`test_c1c_typical_filters_does_not_import_live_clock_terms`). No new
assertion is required — see step 3 for why the structural claim over the two services is a
plan-5 note rather than a plan-4 obligation.

**Authority:** plan_4 §6 C1(c) as amended 2026-08-24; charter rule 4 (no dead scaffolding).

## Notes

- **N1 — `test_c2c`'s two roots are pooled, so the goldens root's precondition is unasserted.**
  `files` is built from `beyo_manager` **and** the goldens directory in one comprehension, so
  `assert files` is satisfied by the first root alone: a wrong or renamed goldens path scans
  nothing and the test stays green. The path is correct today (three golden files present, a
  superset of C2(c)'s two). Assert non-emptiness **per root**. Fifth instance of "a guard whose
  own preconditions are unasserted" in this phase.
- **N2 — the recursive-walk mutation still does not reach the sub-check it was written for.**
  Under `rglob`→`glob` the red is at `test_domain_purity.py:13` — `assert modules` inside the
  helper — because the fixture's `tmp_path` holds **only** the nested module, so the walk
  returns `[]` before the test's own `assert nested in modules` executes. The bite is genuine
  and for the right cause, but per charter rule 12 the row's discriminating assertion is still
  unexecuted. Write one `.py` at the top of `tmp_path` as well: then `glob` leaves the helper
  green and `assert nested in modules` is the assertion that fires. Third generation of this
  shape; the fix is one line.
- **N3 — C5(c) is a disjunction (`insufficient_sample >= 1`) where the fixture makes it exactly
  2.** Charter rule 2 requires each row to assert its one exact expected outcome. The weak form
  is the **plan's**, not the implementer's — routed as a lesson, not a fix.
- **N4 — ledger rows 25/26 (and 4/5, 9/10) name a mutation without its site.** Rule 11's second
  half wants file plus definition-vs-call-site; rows 20–22 do it properly ("at exact tuple
  assertion"), rows 25/26 say only "selected value → 1". This is the residue of round 2's N2,
  one level down: the *row* is now attributable, the *site* is not.
- **N5 — the round-3 handoff's C8/C11 sentence is false against its own table**, as the
  coordinator recorded (S4). Judged **adequate** because the coordinator measured both on this
  tree and wrote sites, observed asserts and md5s into §8. Fourth instance in this project of a
  handoff sentence that its own artifact contradicts.
- **N6 — a stray edit sits in the working tree, in nobody's perimeter.**
  `prompts/implementer/20260823_plan4_fix_round2_prompt.md` line 1 reads `3---` instead of
  `---`, which breaks that row's frontmatter. Outside `app/`, so gate check 4 passes and it is
  not a perimeter violation by any session — it looks like a stray keystroke in the owner's
  tree. Reported under the passing-glance clause; I did not touch it.
- **N7 — cosmetic:** the two converted dict entries in
  `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections` are
  over-indented relative to their siblings.

## Reality checks — new ones only (do not re-verify)

1. **C5(b)'s zero is a real median over a real population, proven two ways.** Structurally:
   `section_count` and `section_percentile` share one `filter (qualifying)` predicate
   (`get_working_section_typical_times.py:95-96`), so an empty population cannot yield count 5,
   and `section_typical` is gated by `case(section_count >= TYPICAL_MIN_SAMPLE_SIZE, …)` — the
   published `0` is `round(percentile_cont(0.5))` over five zero-second groups, not a
   coalesce. By variation: dropping the zero fixture's history from 5 groups to 4 gives
   `assert (None, 'insufficient_sample', 4) == (0, 'section_wide', 5)`, exactly one test red.
   So the disclosed count is the seeded population, and the boundary is exactly the floor.
   Fixture reverted, md5 `a44a0472e7ef0d303870ddd991171d54` identical.
2. **C1(c)'s surviving root bites** — 1 failed / 222 passed, at `:514`, path in the message.
3. **N7's dead-conditional removal is semantically inert, verified at source.** The
   `if specs and task_spec_index is None:` branch above `continue`s, so `elif specs:` is
   reachable only when `task_spec_index is not None` — the two removed guards were tautologies.
   The `K == 0` path and the narrowed branch are untouched.
4. **C6's named mutation bites on the NEW {0,2,1} fixture** —
   `participating_section_ids` → `selected` gives **1 failed / 350 passed** at
   `test_narrowed_task_economics.py:115`, on the `sections_by_basis` dict. Ledger row 11 was
   measured against the old `{1,2,1}` fixture, which round 3 replaced; re-measured here because
   that is exactly the stale-citation class S4 was raised for. `division_serializers.py` md5
   `b462988498000a0db94524e11f6b7462` identical.
5. **C1(i) bites on the REWRITTEN C1 test** — substituting a live-derived value into one
   section's `SelectedTypical` at `get_task_production_time`'s call site gives **7 failed / 9
   passed**, `test_c1_both_consumers_keep_settled_typicals_when_live_clock_moves` among them.
   Ledger rows 4/5 were measured against the old `f(a) == f(b)` form; the exact-literal form is
   strictly stronger and still bites. md5 `aff094ded01e15235865bf06c378d8bd` identical.
6. **The `Mapping[str, SelectedTypical]` annotation is load-bearing** — an int raises
   `AttributeError` at `_step_result`; the old shape is no longer silently tolerated. A `None`
   *value* is still handled by design (`insufficient_sample`, count 0).
7. **TZ variation, required by master plan §10 for datetime work and never run on these
   fixtures.** The two new C5 fixtures anchor `closed_at` to the real clock while `ctx.now` is a
   fixed literal, so the 90-day cutoff is in play. L2 → **351 passed** at `TZ=UTC`,
   `TZ=Pacific/Kiritimati` (+14) and `TZ=Pacific/Niue` (−11); host is CEST (+2). The one-sided
   `latest_closed_at >= cutoff` predicate makes them clock-order-independent, and no naive
   datetime is involved. **No time bomb.**
8. **C5(a)'s fixture satisfies the projection's unmet L12 instruction.** Both sections are
   below floor (counts 3 and 0), so no participating section has a usable typical, which pins
   mutation (i)'s observable to exactly `1` — and the handoff states it. The counts sit on the
   right side of `TYPICAL_MIN_SAMPLE_SIZE = 5` (3 below, 5 at the boundary), and the fixture
   soft-deletes the base steps so the seeded history is the **only** population — the row's
   predicate is the only reason its outcome holds.
9. **Teardown holds (charter rule 11½).** `_cleanup` deletes `TaskStep`, `Task` and
   `WorkingSection` by `workspace_id`, so the new seeder's second section and its history rows
   are covered; both new tests wrap their assertions in `try/finally`.
10. **The C10 assertion round 3 replaced was genuinely dead.** `assert len(captured_specs[0])
    == 3` sat directly below an exact 3-tuple equality that subsumes it; `assert captured_specs[0]`
    is redundant but harmless. N6 of round 1 was discharged, not weakened.
11. **L2 baseline on this tree: 351 passed**, and it reconciles with the coordinator's cited
    B1 measurement (1 failed / 350 passed) exactly.

## Refutations — 2

- **My first C13(c) probe went green for the wrong reason and I nearly filed it as the
  finding.** The copy I wrote first compared the enum object to lowercase strings, so it
  *disagreed* with the shared predicate and three behavioural tests caught it (3 failed / 348
  passed). Had I stopped there I would have reported "the class is guarded". The faithful copy
  is the hazard, and only the second probe measured it. Round 1's lesson — *a probe that lands
  in the wrong place measures nothing* — restated at the level of mutant **fidelity** rather
  than site: **a mutant that is not the shape the criterion names measures a different
  criterion.**
- **I suspected `test_c2c` might be scanning nothing and it is not.** Both roots exist and the
  goldens directory holds three files; only the *precondition* is unasserted (N1). The
  substance holds — no v1 literal in production or in the goldens.

## Evidence budget — L4 runs: 0, deliberately, with the stamp consumed by citation

`git diff --name-only 3f8677c HEAD -- app/` is **empty** and `git status --porcelain -- app/`
was empty at entry and exit, so the round-3 closing stamp — **2692 passed / 21 failed / 1
skipped**, failing set `∅ / ∅` against the published 21-ID block — describes this tree byte for
byte and is consumed by citation (charter, test-evidence reuse: tree-matched evidence is
citable implementer → reviewer). Re-running it would be the named over-evidence anti-pattern.
Round 1's serial `-n 0` comparator was not repeated.

My budget went to **variation** instead: 8 probes over 6 files, a 3-point `TZ` matrix, one
fixture-population variation, and two mutations re-measured because round 3 moved the tests
they were recorded against. The prompt's mandated closing L4 with the programmatic 21-ID diff
belongs to the **approval gate**, which this verdict does not reach; it is owed on the tree that
closes fix round 4, per phase 3's precedent (*"the approval-gate L4 was RUN on this gate tree,
not cited"*) and phase 2's counter-example.

## Mutation-probe declaration

Every probe applied and reverted; md5 verified byte-identical to the pre-probe value after each
revert. No file or directory created. No database or state side effect (all probe runs are
`try/finally` fixtures on the disposable per-process test databases). `git status --porcelain
-- app/` empty at exit; L2 re-verified green at **351 passed** after the last revert.

| # | file | mutation | md5 after revert |
|---:|---|---|---|
| P1 | — (no file touched) | in-process call with `{"s": 1}` and `{"s": None}` | n/a |
| P2 | `services/queries/item_economics/get_task_price_scenario.py` | private copy of `_step_state_is_excluded`, **disagreeing** form | `8a261d763b3a6414554c84083f1a7396` |
| P3 | same | private copy, **faithful** form, occurrence count preserved at 2 | `8a261d763b3a6414554c84083f1a7396` |
| P4 | `domain/item_economics/typical_filters.py` | add a `live_seconds` reference | `c888e3d24748edfa6fe22a0c24605b45` |
| P5 | `tests/integration/…/_narrowing_fixture.py` | zero-section history 5 → 4 groups | `a44a0472e7ef0d303870ddd991171d54` |
| P6 | `services/queries/item_economics/get_task_production_time.py` | C1(i): live value into one section's `SelectedTypical` at the call site | `aff094ded01e15235865bf06c378d8bd` |
| P7 | `domain/item_economics/division_serializers.py` | C6: count `selection.selected` instead of `participating_section_ids` | `b462988498000a0db94524e11f6b7462` |
| P8 | `tests/unit/domain/item_economics/test_domain_purity.py` | S2: `rglob` → `glob` | `70964abcbbfb95ee9697748802b33ecc` |

## Where this phase's evidence ends — for plan 5 and plan 6

Stated even though the verdict is not `APPROVED`, because plan 5 reuses these fixtures.

- **The byte-goldens protect the degenerate case only.** Every `typical_basis` in them is
  `insufficient_sample`, every `typical_worker_seconds` is null, every `applied_filter` is
  null (coordinator, measured, by design — task 10 does not teach the live-clock fixture to
  narrow). *"The refactor did not move a number"* is proven on a fixture whose every typical is
  null. The goldens are blind to `item_narrowed`, to `section_wide`, to any non-null typical or
  filter, and to any non-zero sample count. **Never cite them as protecting the narrowing
  payloads.**
- **`item_narrowed` is now asserted at exactly zero on the C6 fixture.** After round 3's
  `{0,2,1}` change, no test in the changed seam asserts a *participating* section resolving to
  `item_narrowed` at the serializer level; C11 and C10 carry the narrowed basis on the wire.
- **Both narrowing fixtures remain uniform within each category** (round-1 N11, routed to plan
  5): a narrowed median equal to the section median cannot discriminate a wrong-rung defect.
- **The two new C5 fixtures cover the floor boundary from below only** (4 → red, 5 → green
  measured by me; 3 → insufficient by the test). Nothing exercises count > floor with a zero
  median, and nothing exercises a *narrowed* zero at count ≥ floor — D25 makes that unreachable
  on task surfaces, which is why §4C exists, but plan 5's price-scenario ladder is a different
  surface and must not assume it.
- **`sample_count` is unasserted throughout `test_budget_division.py`** (see S2), so the unit
  layer proves arithmetic, never disclosure.

## Lessons for the plans

1. **An absence row must name the shape it is blind to.** C13(c) enumerated an exception file
   and pinned an occurrence count as a proxy for "it is an import". The proxy admits a
   definition. When a row's allowlist names a file, the row states *why* that file is allowed in
   a form a test can check — "imports the shared symbol", not "mentions it twice".
2. **A criterion's term list is load-bearing and its feasibility must be measured when it is
   written, not when it is transcribed.** C13(c)'s five terms could not become a test at the
   repository root (40 production files carry three of them). The plan should have said which
   terms are structural claims and which are prose review — the implementer had to make that
   call silently, and rule 14 then made the silence a finding.
3. **A conversion that changes a default changes a published field.** §5 task 4 said "convert
   the 23 literals". Converting `None` to a helper whose default basis is `section_wide`
   changed a payload field no assertion covered. A conversion task should name the invariant
   the conversion must preserve, per field.
4. **Retained ledger rows expire when the round edits their test.** The coordinator caught this
   for C8/C11 (`:198`/`:290` → `:277`/`:351`); the same expiry applies to C6's row 11 and C1's
   rows 4/5, whose tests round 3 also rewrote. Rule: **a fix round re-runs every retained
   ledger row whose test file it touched**, or states per row why the citation survives.
   Nobody asked for these two; I measured them because S4's class demanded it and both hold.
5. **`>= n` in a criterion is a disjunction** (charter rule 2). C5(c) should read `== 2` against
   its own fixture.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. One item is still owner-owned from round 1 and unchanged by this
round: **N9 — the graph delta records this phase's contract tests rather than §7's two
projection nodes.** Agents never adjudicate graph review state, so it stays with the owner; it
is not a decision this review needs answered to proceed.
