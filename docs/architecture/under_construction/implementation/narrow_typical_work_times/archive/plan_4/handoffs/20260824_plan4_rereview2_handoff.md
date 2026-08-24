---
plan: plan_4
role: reviewer
round: 3 (final delta re-review)
date: 2026-08-24
actor: Opus 5
verdict: APPROVED
---

# Final delta re-review — phase 4, `narrow_typical_work_times`

**Verdict: `APPROVED`.** 0 blocking / 0 should-fix / 3 notes / 0 owner cards.

**Tree:** `5d60d68 docs(narrow-typicals): dispatch the final delta re-review for phase 4`,
`git status --porcelain -- app/` **empty**.

## Gate check

| gate | result |
|---|---|
| `git merge-base --is-ancestor 24af53a HEAD` | passes |
| `plans/plan_4.md` header / `master_plan.md` §4 row 4 | both **`IMPLEMENTED`** |
| `plans/plan_4.md` §8 last entry | *"2026-08-24 — graph meaning session consumed (coordinator, D30)"* |
| `git status --porcelain -- app/` | empty |
| `redis-cli ping` | `PONG` |

**Perimeter verified.** `git diff --stat 8670d1b HEAD -- app/` → 3 test files, 51 insertions /
13 deletions. **No production file changed** — confirmed twice over: by the diff, and
independently by md5, since `get_task_production_time.py` (`aff094de…`),
`get_task_price_scenario.py` (`8a261d76…`) and `typical_filters.py` (`c888e3d2…`) are
**byte-identical to the values I recorded in the round-2 handoff**. Every changed hunk is
declared in the fix handoff (S1/S2/S3 + N1 C2(c) per-root, N7 indentation, N2 top-level module);
nothing in the diff is undeclared.

## Evidence

**L4 run: 0.** `git diff 97aeaa6 HEAD -- app/` is **empty**, and `97aeaa6` is the checkpoint on
which fix round 4 ran the approval-gate stamp — **21 failed / 2692 passed / 1 skipped**, failing
set `actual − published: ∅`, `published − actual: ∅` against the 21-ID block. That stamp
describes the tree I opened and is consumed by citation, not re-run (charter, test-evidence
reuse; re-running it would be the over-evidence anti-pattern).

Everything below is **L1** — named test IDs and the two small phase test files — and every run
is **variation**: a mutant shape or site no prior record used.

## Delta ledger — the four named checks

| # | check | result |
|---|---|---|
| **S1** | C13(c) guard vs. a faithful private copy | **closed and BITING** — my own round-2 probe now reddens. Residual blind spot found by variation → **note N1** |
| **S2** | inconsistent basis/count still writable? | **closed** — no call site passes an explicit pair; the derivation is total over every caller. Residual affordance → **note N2** |
| **S3** | renamed C1(c) honest and biting? | **closed and BITING on both halves**, each on its own line |
| **N2** | recursive-walk mutant reaches its sub-check? | **closed and BITING** — now fails at `assert nested in modules`, not at the helper precondition |

### S1 — closed and biting

I re-ran **my** round-2 probe verbatim: in `get_task_price_scenario.py`, drop the import of the
shared `_step_state_is_excluded` and add a faithful local definition, preserving the file's
occurrence count at 2. Round 2: **green, the guard did not see it.** Now:

```
FAILED …::test_c13c_excluded_state_logic_has_one_shared_production_owner
test_narrowed_task_economics.py:540: AssertionError
```

`:540` is the line the fix added. The hole I measured is shut, and it fails on the exact
assertion written to shut it.

### S2 — closed

All 24 `selected(...)` call sites in `test_budget_division.py` pass `(section, value)` only —
**not one** passes an explicit `basis`/`count` pair. Through the derivation, `basis` is
`section_wide` iff the value is non-null and `count` is then `TYPICAL_MIN_SAMPLE_SIZE = 5`;
`insufficient_sample` pairs with `0`. **No reachable combination yields `section_wide` with a
count below the floor.** The impossible triple cannot be written by any caller that exists.

### S3 — closed and biting, on both halves separately

Two mutants, two distinct lines — rule 12 satisfied (neither sub-check is shadowed by the other):

| mutant | fires at | line |
|---|---|---|
| add `total_working_seconds` to `typical_filters.py` | `assert not any(term in source for term in terms), path` | `:521` |
| point `roots` at `typical_filterz.py` (stale path) | `assert all(path.exists() for path in roots)` | `:513` |

The name no longer promises a guard over the evidence helper, and the precondition that replaced
`assert roots` is the one that catches the path going stale — the failure mode the old
one-literal list could not see.

### N2 — closed and biting

`rglob` → `glob` in `_domain_modules`:

```
test_domain_purity.py:38: AssertionError
assert PosixPath('…/nested/module.py') in [PosixPath('…/top_level.py')]
FAILED …::test_item_economics_domain_walk_is_recursive — 1 failed, 3 passed
```

Round 2 it died at `assert modules` inside the helper (`:13`) and never reached `:38`. The
added top-level module moved the failure onto the test's own recursion claim.

### N1 (the round's C2(c) strengthening) — closed and biting

Not one of the four, but it is inside the 51 lines, so I applied the lens. Mutant: the goldens
root goes stale (`goldens` → `goldenz`). Under the old flattened `assert files` this was masked
by the production root's files; now:

```
assert files, root
E  AssertionError: PosixPath('…/item_economics/goldenz')
E  assert []
test_narrowed_task_economics.py:92
```

It reddens **and names the offending root**.

## Findings

### N1 — note — the C13(c) different-name claim fires on a string form this codebase never writes

**This is my own round-2 prescription being wrong, and the implementer implemented it exactly
as I wrote it.** The plan's amended C13(c) requires *"the separately-measured claim that 0 files
under `app/beyo_manager/` contain a set/frozenset literal naming two or more of the three state
names."* That shipped at `:544` as an AST sweep matching `ast.Constant` **strings** in
`{"SKIPPED", "CANCELLED", "FAILED"}`.

**Measured three ways, all reverted:**

| probe | private copy planted in `get_task_production_time.py` | C13(c) |
|---|---|---|
| A | `frozenset({TaskStepStateEnum.SKIPPED, …})` + `_step_state_is_dropped` — the codebase's own idiom | **green (missed)** |
| I | `frozenset({"skipped", "cancelled", "failed"})` — the enum **values**, which is what production compares against | **green (missed)** |
| B | `frozenset({"SKIPPED", "CANCELLED", "FAILED"})` — uppercase member names as strings | **red (caught)** |

The form it catches is the one form nobody writes. `_step_state_is_excluded` compares
`_state_value(...)` against `{state.value for state in EXCLUDED_STEP_STATES}` — **lowercase**
values — and every state set in this repository (`budget_division.py:30`,
`task_steps/constants.py:4`, `get_worker_working_sections.py:21`) is built from **enum
members**. The uppercase member name never appears as a string literal anywhere in
`app/beyo_manager/`. So the claim "0 files contain such a literal" is true, and stays true under
a faithful copy, for a reason unrelated to the property it is meant to guard.

**Why this is a note and not a should-fix.** The shipped test conforms to the criterion as
amended; the weakness is in the criterion, and plan complaints are lessons, not blockers
(plan-reviewer doctrine). The half of C13(c) that was ever *measured* to have a hole — the
same-name copy — is closed and biting (S1 above). Nothing in the tree today is a private copy;
`hits <= allowed` still holds and would catch any copy that reuses either name.

**Correction, for whoever picks it up:** match all three writings, not one — the enum-member
form (`ast.Attribute` whose `attr` is in the three names, on a `Name` whose id is
`TaskStepStateEnum`), the lowercase-value form, and the uppercase-name form — with
`budget_division.py` as the single exception. **Route: plan 5, before its price-scenario ladder
lands.** That is the phase that grows a second private surface over the same predicate, which is
the exact condition this guard exists for.

**Authority:** `plans/plan_4.md` §6 C13(c) as amended at review round 1 (N8) and round 2; charter
rule 11.

### N2 — note — `selected()`'s `basis`/`count` parameters now have zero callers

The S2 repair kept `basis=None, count=None` as overrides. No test passes either. They are the
only remaining route by which an inconsistent pair can be constructed, and they are dead
scaffolding by charter rule 4 (added affordance, no caller in the phase). Dropping them to
`def selected(section, value)` would make the impossible triple unconstructible rather than
merely unconstructed. **Route: plan 5**, which reuses this helper.

Related, and not a defect: nothing in `test_budget_division.py` asserts `typical_basis` or a
sample count — I mutated the derivation to `count = 0` always (recreating the impossible triple)
and the file stayed **17 passed**. The repair is fixture honesty, structural by construction;
it is not, and does not claim to be, an observed invariant.

### N3 — note — PEP 8 blank lines lost between the two rewritten tests

Removing `assert not any(term in helper_source …)` also removed the two blank lines separating
`test_c1c_typical_filters_does_not_import_live_clock_terms` from
`test_c13c_excluded_state_logic_has_one_shared_production_owner` — `def test_c13c…` now sits
directly under the loop body at `:522`. Both tests still collect and run (verified individually).
Cosmetic only: no ruff configuration is present in `backend/`, and E302 is not in ruff's default
rule set. **Route: opportunistic, any phase touching the file.**

## Carry-forward dispositions

| note | destination | why there |
|---|---|---|
| N1 — C13(c) name claim blind to both natural copy forms | **plan 5, task 0** | plan 5 adds price-scenario's private ladder over the same predicate |
| N2 — dead `basis`/`count` overrides on `selected()` | **plan 5** | plan 5 reuses `test_budget_division.py`'s helper |
| N3 — blank lines | opportunistic | cosmetic, no gate |

Round-1 and round-2 notes N1–N11 remain routed as recorded in their own handoffs; nothing in
this round changes their destinations.

## Round-1 and re-review findings — closed *and biting*

| finding | status | how I know it bites |
|---|---|---|
| **B1** C5(a)/(b)/(c) | closed and biting | coordinator's tree-matched 346 passed → 1 failed / 350 passed, consumed by citation; reconciled against my round-1 L2 of 351 |
| **B2** C1(c) + C13(c) | **closed and biting — both halves, now measured by me** | C1(c): two mutants, `:521` and `:513`. C13(c): my own round-2 faithful-copy probe now reddens at `:540`. This is the finding whose closure round 2 could not confirm; it is confirmed |
| **r2-S1** faithful private copy | closed and biting | probe C, `:540` — see above. Residual shape → N1 |
| **r2-S2** impossible triple in fixtures | closed | derivation total over all 24 call sites; no `section_wide` below the floor is reachable |
| **r2-S3** C1(c) test dishonest | closed and biting | renamed, `helper_source` gone, and the replacement precondition fires on a stale path |
| **r2-S4** ledger count | closed | 25 rows, every row sited; the round self-reported a mis-sited C10(ii) probe and re-sited it |
| **r2-S5** C1(a)/(b) | closed | verified round 2 |
| **r2-N1** C2(c) per-root non-emptiness | closed and biting | probe H, `:92`, names the stale root |
| **r2-N2** recursive-walk sub-check | closed and biting | probe D, `:38` |
| **r2-N7** over-indented dict entries | closed | verified at source, semantically inert |
| **C8 / C11** mutations | closed and biting | coordinator, tree-matched, consumed by citation |

## Where this phase's evidence ends — for plan 5 and plan 6

Extends, and does not replace, the same section in `20260824_plan4_rereview_handoff.md`. All
five boundaries stated there **still hold on this tree** — round 4 touched no fixture:

- **The byte-goldens protect the degenerate case only.** Every `typical_basis` in them is
  `insufficient_sample`, every `typical_worker_seconds` null, every `applied_filter` null. They
  are blind to `item_narrowed`, to `section_wide`, to any non-null typical or filter, and to any
  non-zero sample count. **Never cite them as protecting the narrowing payloads.**
- **`item_narrowed` is asserted at exactly zero on the C6 fixture.** No test in the changed seam
  asserts a *participating* section resolving to `item_narrowed` at the serializer level; C11 and
  C10 carry the narrowed basis on the wire.
- **Both narrowing fixtures are uniform within each category** (round-1 N11): a narrowed median
  equal to the section median cannot discriminate a wrong-rung defect.
- **The C5 fixtures cover the floor boundary from below only** (4 → red, 5 → green measured;
  3 → insufficient by the test). Nothing exercises count > floor with a zero median, and nothing
  exercises a *narrowed* zero at count ≥ floor. D25 makes that unreachable on task surfaces —
  **plan 5's price-scenario ladder is a different surface and must not assume it.**
- **`sample_count` is unasserted throughout `test_budget_division.py`.** The unit layer proves
  arithmetic, never disclosure. Re-measured this round: mutating the derivation to `count = 0`
  leaves the file 17 passed.

**Added this round:**

- **`selected()` in `test_budget_division.py` now emits exactly two shapes** — `(value,
  section_wide, 5)` and `(None, insufficient_sample, 0)`. Plan 5 inherits a helper that **cannot
  produce a below-floor `section_wide`**, so any plan-5 case needing a sub-floor participating
  typical must construct it explicitly rather than through this helper. The integration file's
  own `selected()` (`test_narrowed_task_economics.py:53`) is **unchanged** and still takes
  explicit pairs — the two helpers now diverge, which is a trap for anyone reading one and
  editing the other.
- **C13(c)'s structural guard covers same-name copies only** (N1). Plan 5 must not treat it as
  proof that no private excluded-state predicate exists.

## For the phase-5 reviewer

1. **The two `selected()` helpers have diverged.** Same name, same file tree, different
   contracts. Check which one a plan-5 fixture is calling before reasoning about its basis.
2. **C13(c) is the guard to re-measure the moment price-scenario grows its private ladder.**
   Plant a copy in the codebase's own idiom (enum members), not in string literals — the string
   probe is the one that gives a false positive result.
3. **This phase's mutation ledger is 25 rows and every row names its site.** It also records a
   self-caught mis-sited probe (a C10(ii) mutation planted at the definition, green, discarded,
   re-sited at the `typical_rows.get` call site where it reddens). When a phase-5 ledger row
   reads green-then-red without a site, that is the shape to distrust.
4. **Four "rows that cannot fail" were found in this phase, each written to close the previous
   one.** N1 above is the fifth in the family and the first authored by the reviewer rather than
   the implementer. The prior on this class is high; budget for it.

## Lessons for the plans

1. **An absence claim over a literal must be written in the idiom the codebase actually uses.**
   C13(c)'s name claim was measured true when written — and it was true because no production
   file writes state sets as strings at all, not because no private copy exists. *Measuring an
   absence proves the absence; it does not prove the instrument can ever observe the presence.*
   The companion check is the missing one: **before shipping an absence row, plant the thing it
   forbids and confirm the row reddens** — the same discipline rule 11 already demands of safety
   tests, applied to absence rows.
2. **A reviewer-prescribed instrument is not exempt from the reviewer's own lens.** Round 2
   handed the implementer a three-line correction; the implementer executed it exactly and
   declared the divergence properly. The defect entered through the prescription. A prescription
   precise enough to be transcribed literally must be measured as literally as it is written.
3. **Carried from round 2, still standing:** a criterion's term list is load-bearing and its
   feasibility must be measured when it is written, not when it is transcribed.

## Mutation-probe declaration

Nine probes across six files, every one applied and reverted, every file **md5-verified
byte-identical** to its pre-probe state, and `git status --porcelain -- app/` **empty** at the
close. Three of the six md5s also match the values published in the round-2 handoff.

| probe | file | mutation | md5 before = after |
|---|---|---|---|
| A | `services/queries/item_economics/get_task_production_time.py` | faithful private copy, enum-member idiom | `aff094ded01e15235865bf06c378d8bd` |
| B | same | private copy, uppercase string literals | `aff094ded01e15235865bf06c378d8bd` |
| I | same | private copy, lowercase enum-value literals | `aff094ded01e15235865bf06c378d8bd` |
| C | `services/queries/item_economics/get_task_price_scenario.py` | round-2 probe re-run: drop the shared import, add a same-name local `def`, count preserved at 2 | `8a261d763b3a6414554c84083f1a7396` |
| D | `tests/unit/domain/item_economics/test_domain_purity.py` | `rglob` → `glob` in `_domain_modules` | `c9cefc3954a0f9acf8f74a7aac0d261b` |
| E | `domain/item_economics/typical_filters.py` | add a `total_working_seconds` reference | `c888e3d24748edfa6fe22a0c24605b45` |
| F | `tests/integration/…/test_narrowed_task_economics.py` | C1(c) root → `typical_filterz.py` (stale path) | `26a2129f860a6e2e5e4a8b0c82713e6b` |
| H | same | C2(c) goldens root → `goldenz` (stale root) | `26a2129f860a6e2e5e4a8b0c82713e6b` |
| G | `tests/unit/domain/item_economics/test_budget_division.py` | `selected()` derivation → `count = 0` always | `8aa1c2c62c8db82e7255901ec2066766` |

**Database and state side effects: none.** Every probed test is a file-sweep or pure-unit test —
C13(c), C1(c) and C2(c) read the tree, `test_budget_division.py` is in-memory, and
`test_domain_purity.py` writes only under `tmp_path`. No row was committed and no fixture data
was seeded, so nothing needed restoring.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. The three notes are routed to plan 5 and to opportunistic cleanup; none
of them needs a decision, only a destination, and each has one.
