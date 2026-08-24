---
plan: plan_5
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-24
actor: Opus 5
---

# Plan 5 review round 1 — price-scenario: the explicit clock, the shared reconciliation, `is_estimated`

**Verdict: `CHANGES_REQUESTED`.** 2 blocking / 1 should-fix / 5 notes / **0 owner cards**.

Nothing needs the owner. The graph item §7A opened is **closed** (D31, verified by the coordinator
at source before this prompt was dispatched); I did not read, re-verify, re-anchor or touch
`.archgraph/` at any point.

The production code is right. Both blocking findings are about **what is watching it**: one seam
that no test in the repository observes, and one criterion that ships unable to fail in the half it
was rewritten to arm. Phase 6 forbids test-behaviour change, so neither can be repaired later.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Both blocking findings route to the coordinator as a fix round.

## Gate check

`plans/plan_5.md` header `state: IMPLEMENTED` ✓ · master plan §4 row 5 `IMPLEMENTED` ✓ ·
`planning/intention.md` header **`RATIFIED`** (round 10, owner, 2026-08-24), read at source ✓ ·
`git status --porcelain -- app/` empty from `backend/` ✓ · `redis-cli ping` → `PONG` ✓ ·
`.archgraph/` not gated on, per the prompt.

**Tree identity.** HEAD `86bf894`, `app/` clean. `git diff 0daf0c9 HEAD -- app/` is **empty**, so the
fix round's stamp (**2707 passed / 21 failed / 1 skipped**, 21-ID set unchanged) describes this tree
and is **consumed by citation, not re-run**. `git diff 8a4a1cb HEAD -- app/beyo_manager/` is also
empty, independently confirming the coordinator's byte-identity claim.

## Evidence budget — what I spent and why

**L4 runs: 1.** Authorization line, written before the run: *narrower evidence is insufficient
because the hypothesis is an absence claim over the whole repository — "no test anywhere reddens
when `get_task_price_scenario` stops passing the derived spec into `_typical_block`". Master plan
§10 makes repository-rooted absence claims L4 by construction; L2 cannot see the router, unit or
cross-domain trees.* Every other run was **variation** — a mutant shape, a site or a condition
nobody in this phase has tried. No run reproduced a green ledger.

| # | hypothesis | scope | result |
|---|---|---|---|
| P1 | C1(i) (`now=` dropped at the price call site) — **which assertion in `test_c1b` reddens** | L1 phase file | 2 failed / 13 passed; `test_c1b` fails at **`:139`**, the byte-identity assertion at `:136-138` **passed** → **B2** |
| P2 | `serialize_typical_resolution`: `len(participating_section_ids)` → `len(selected)` — does **C6** see it? | L2 `unit/domain/item_economics` + `integration/.../item_economics` | 1 failed / 365 passed. **C6 stayed green**; caught by phase 4's `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections:124` → **N2** |
| P3 | delete `.where(WorkingSection.client_id.in_(participating_ids))` — does anything guard §2B S-7's statement scope? | L2, same set | **366 passed** — nothing guards it → **S1** |
| P4 | `get_task_price_scenario.py:234-238`: `budget_status.typical_filter_spec` → `None` | L2, then **L4** | L2 **366 passed**; L4 **21 failed / 2707 passed / 1 skipped**, 21-ID set ∅/∅ → **B1** |
| P5 | condition variation: the phase file under `TZ=Pacific/Kiritimati` (UTC+14) and `TZ=Pacific/Midway` (UTC-11) | L1 phase file | **15 passed** at both. No naive/aware sensitivity — master plan §10's TZ rule discharged for this phase |

Command form throughout: `BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest <paths> -n 0 -p no:randomly -q`;
the L4 run was `BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest -m 'not e2e' -q` (pytest.ini's
`-n 6 --dist loadfile`).

---

## Findings

### ★ BLOCKING — B1. The derived spec never reaches `_typical_block` in any test, so price-scenario can stop narrowing with the whole repository green

**Where:** `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py:234-238`
(the only site that supplies `spec`), against `plans/plan_5.md` §5A task 2 (**S13**: *"the spec comes
from `budget_status.typical_filter_spec`"*) and intention §1A **M1**.

**Measured.** Replacing the third argument with `None`:

```python
typical = await _typical_block(ctx, task.client_id, None)   # was budget_status.typical_filter_spec
```

L2 item-economics: **366 passed**. Full suite: **21 failed / 2707 passed / 1 skipped**, the exact
21-ID baseline, **no failure-ID delta in either direction**. Probe reverted; md5 restored to
`213a38a03f7ffaafe954bae68d4da16a` and `git status --porcelain -- app/` empty.

**Why nothing sees it.** Every row that exercises narrowing — C5 and C8, the two DB-backed rows —
calls `module._typical_block(...)` **directly** and hands it a spec the test derived itself
(`derive_spec_from_primary_item(item)` at `test_narrowed_price_scenario.py:265` and `:399`). The four
`_run_scenario`-family tests that do call the service monkeypatch `_typical_block` away
(`test_price_scenario_query.py:577`, `:974`, `:1117`, `:1277`) and their widened `fake_status` returns
`typical_filter_spec=None`. So the one production edge that carries the task's item category into this
consumer — the edge phase 5 exists to build — is observed by nothing.

**Failure scenario.** A later refactor of `get_task_budget_status`'s return shape, a defaulted
keyword, or a merge that drops the argument, and every price-scenario answer silently reverts to
section-wide. The payload keeps publishing `typical_resolution` with
`task_typical_basis: "section_wide_uniform"` and `applied_filter: null` — a well-formed, plausible,
wrong answer, with no error and no red test.

**This is not the note the coordinator already settled.** That note is about *downstream* reach —
C8 asserting `_typical_block`'s dict rather than the serialized payload, equal by the pass-through at
`serializers.py:364`. This is *upstream*: **who supplies the spec**. Different seam, and the
pass-through argument does not reach it.

**It is also a plan gap.** §5A S13 pinned the source as a **task**; no §6A row covers it, and the
manifest's reverse-trace check cannot see a missing edge that no row claims. M1's own defect family is
*"the feature ships inert"*, and this is the shape it takes on the fourth consumer.

**Suggested correction** (cheapest form that bites): one row on C5 or C8 that installs a spy on
`module._typical_block` and asserts it receives the spec `get_task_budget_status` derived — or, if the
fixture supports the full service, drives `get_task_price_scenario(ctx)` end to end for one row and
asserts `typical.total_seconds == 600` there. Name the mutation as *pass `None` at
`get_task_price_scenario.py:237` (call site)* and record the observed red.

---

### ★ BLOCKING — B2. C1(b) shipped inert in the half it was rewritten to arm, and its prescribed instrument was replaced without declaration

**Where:** `app/tests/integration/services/queries/item_economics/test_narrowed_price_scenario.py:97-140`
(`test_c1b_same_frozen_context_produces_byte_identical_typicals`), against `plans/plan_5.md` §6A
**C1(b)** and intention §1A **M7**.

**What §6A C1(b) prescribes, verbatim in substance:** monkeypatch
`…get_working_section_typical_times.datetime` with a fake whose `now()` returns `ctx.now - 1s` then
`ctx.now + 1s`; pin one group at `max(closed_at) == ctx.now - 90 days`, exactly the window boundary;
assert **contract** — both calls byte-identical, the boundary group **in** both, `total_seconds` at a
stated literal — and **mutation (i)** — the two calls differ, group **in** then **out**, both totals
stated as exact literals.

**What shipped:** two calls against two `_TypicalSession` instances built from identical hand-supplied
rows. `_TypicalSession.execute(self, _statement)` **discards the statement** — the fake the plan's own
⚠ fixture rule names in bold. There is no fake `datetime`, no boundary group, no 90-day pin, and no
SQL. The two calls are a pure function of identical inputs, so
`json.dumps(public(first)) == json.dumps(public(second))` is `f(x) == f(x)` and cannot fail under any
mutation of the clock path.

**Measured (P1).** Under the row's own named mutation C1(i):

```
2 failed, 13 passed
FAILED …::test_c1b_same_frozen_context_produces_byte_identical_typicals
  test_narrowed_price_scenario.py:139: assert captured == [frozen, frozen]
  E  assert [None, None] == [datetime.datetime(2026, 8, 24, 12, 0, tzinfo=utc)]
```

The red is at **`:139`** — the spy's kwarg list, which is the same observable `test_c1a` already
asserts at `:92`. The byte-identity assertion at `:136-138` **executed and passed** under total loss of
the injected clock. Charter rule 12: a named mutation must be shown to reach **every** sub-check; here
it reaches one, and the one it misses is the row's entire distinguishing content — M7's stated
observable, *"the same task over identical database state serves byte-identical typicals at two
different wall-clock instants."*

**The divergence was not declared** (charter rule 14 / master plan §9), and the implementation
handoff's Task-0 coverage map claims C1(b) covers *"exact repeated injected `now`, **boundary
inclusion**, byte-identical payload"* — **`closed_at`, `90`, `timedelta` and a fake `datetime` appear
nowhere in this file's C1 block.** A coverage claim asserting a property its test does not contain is
the failure mode the project's own reviewer-model record was written about.

**What is still guarded, stated so the correction is scoped and not over-bought.** C1(a) proves
`now=ctx.now` reaches the statement, and phase 2's approved
`test_c11_typicals_statement_uses_the_request_clock_when_supplied`
(`test_phase2_live_surfaces.py:983-989`) proves the statement turns that `now` into `now - 90 days` as
the bound cutoff. So M7's chain holds link by link. What no row anywhere observes is the two links
composed: **a group at the boundary moving in or out because the injected clock moved.**

**Suggested correction:** implement §6A C1(b) as written — it is already specified to the line — or, if
the fake-`datetime` route is unworkable, replace it with a DB-backed row on
`seed_divergent_category_task` seeded with one group at `now - 90 days` and one at `now - 91 days`,
asserting two exact `total_seconds` literals at two `ctx.now` values one day apart. Either way the row
must redden on a **number**, not on the kwarg list, and the named mutation must be re-derived from the
shipped code afterwards.

---

### SHOULD-FIX — S1. §6A C5(b) names §2B S-7 as the contract it guards; the statement's scoping has no guard at all

**Where:** `plans/plan_5.md` §6A C5(b) (*"§2B S-7 is the contract being guarded … and widening the
scope is what the mutation reddens"*) against
`get_task_price_scenario.py:146-153`.

**Measured (P3).** Deleting the scoping clause outright —

```python
result = await ctx.session.execute(
    typical_times_statement(ctx.workspace_id, now=ctx.now, specs=specs)   # .where(...) removed
)
```

— leaves the L2 item-economics surface at **366 passed**. Reverted, md5 `213a38a0…`, tree clean.

**Why it cannot be seen:** extra rows land in `evidence_by_section`, and `reconcile_task_typicals`
builds its `evidence` dict by iterating `section_ids` (`typical_filters.py:272-275`), so foreign
sections are ignored. The scope is a query-cost decision with **no wire observable**.

C5's mutation (i) is fine and does bite (`600` → `750`, cited from `8a4a1cb`) — but it mutates the
**participating-set computation**, not the statement's `.where`. Two different mechanisms, one
sentence claiming both. Master plan §9: *"Designating a guard is a claim about an instrument, and it is
checkable the same way any other criterion is."*

**Suggested correction — restate, do not test.** A criterion that cannot fail must not be invented to
close this. §6A C5(b)'s sentence should say what the mutation actually proves (the participating set is
computed through `participating_sections`, and widening **that** moves the published total) and record
that §2B S-7's SQL scoping is a cost property with no behavioural observable, so no row owns it.

---

### Notes

**N1 — C4(a) asserts one of its two stated observables.** §6A C4(a) reads *"no usable typical anywhere
in the task → `total_seconds: 0` **and** `is_estimated: true`"*.
`test_c4_price_terminal_and_median_are_duration_values` asserts `total_seconds` only
(`test_narrowed_price_scenario.py:239`). No coverage is actually lost — reasoning from the code, an
`is_estimated` that dropped the `sections_without_sample > 0` disjunct reddens C2(b) and C2(c), which
expect `True` at `sections_total == 2` — but the row's own closing observable is unasserted, and
master plan §9 makes a criterion's closing sentence a criterion. → coordinator fold.

**N2 — C6 runs on a hand-built selection, not the seed its row names, and re-imports the literal S1
removed.** §6A C6 names `seed_categorized_two_section_task`; `test_c6…` builds a local
`TaskTypicalSelection` with `SimpleNamespace` rows and `category_id="icat_chair"` — the exact literal
§6A **S1** deleted on the ground that *"`"icat_chair"` is not producible by any seed in this
repository."* Row (c)'s three value assertions therefore read back constants the test supplied one
screen earlier. Its fixture also carries **2** participating ids and **2** entries in `selected`, so it
cannot tell `len(participating_section_ids)` from `len(selected)`.
**Measured (P2):** that mutant is caught — by phase 4's
`test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections:124` (`assert 4 == 3`),
**not** by C6, which stayed green. The class is covered by APPROVED work, so this is a note. What C6
genuinely earns is rows (a)/(b) — both surfaces through the real serializers, and its named mutation
(a private builder omitting `comparability_profile`) does bite there.

**N3 — C8(b) reads a different surface than the row names, undeclared.** §6A C8(b): the section-wide
value *"asserted from production-time's `sections[].typical` triple on `plain_task`"*. Shipped:
`assert plain["total_seconds"] == 375` off `_typical_block` (`:404`). The section-wide **basis** and
**sample_count** are unasserted, and the derivation is bypassed — the test passes `None` rather than a
spec derived from `plain_task`'s category-less item. Contained: a branch swap in
`typical_filters.py:281` reddens C8(a), and §3B B1 is guarded by phase 4's
`test_narrowed_task_economics.py:275-276`. Still a divergence from a named observable on a named
surface, with no declaration.

**N4 — `test_c1c`'s absence assertion is true of `{}`.** `assert "now" not in captured` (`:157`).
Measured at source: `get_working_section_typical_times.py:192` calls
`typical_times_statement(ctx.workspace_id)` with **no keyword arguments at all**, so on the contract
path `captured` is `{}` — and `"now" not in {}` is equally true if the spy is never invoked. The fix
round's F4 probe did plant `now=ctx.now` and observe the red, so charter rule 15 is discharged for the
named mutation; the residue is that the row would also survive the call disappearing. One line closes
it (assert the spy was called, or assert the positional args). Low probability — dropping that call
reddens most of the working-sections tree — hence a note, not a should-fix.

**N5 — `section_ids` diverges from §5A task 4 B3, silently and harmlessly.** B3 pins
`frozenset(step.working_section_id for step in steps)`; shipped is
`frozenset(group["working_section_id"] for group in groups)` (`:142`). Behaviourally identical on the
production path — the step query already filters `is_deleted.is_(False)` and
`group_steps_by_section` skips exactly the deleted steps — and strictly better against the fake
sessions, which can inject deleted steps the SQL would have removed. No finding against the code;
recorded because an undeclared divergence from a code block the plan pins costs the next reviewer a
finding on correct work.

---

## What I verified correct, specifically

- **Production is right.** `_typical_block` (`get_task_price_scenario.py:105-218`) implements §6B
  verbatim (`is_estimated = sections_total == 0 or sections_without_sample > 0`, `:211`),
  `sections_total := len(participating_ids)` (`:208`), and `sections_without_sample` as *participating
  sections whose **selected** typical is `None` or `<= 0`* (`:203-207`) — not the "without a narrowed
  sample" misreading §6B and §5A task 6 warn about. `terminal=Fraction(0, 1)` (`:198`).
- **No behavioural regression on the pre-existing path**, verified by reading the old and new bodies
  side by side: the old `participating` groups and the new `participating_sections(steps)` select the
  same sections; group order is preserved for the sum; the old `_median(usable)` and
  `apply_business_fallback` compute the same fallback; a participating section with no evidence row
  still yields `None` → counted → fallback. The three inherited arithmetic rows (`200`, `41`, `35`)
  still pass.
- **§6D is honoured.** No criterion asserts a before/after on the payload; C2 asserts the definition on
  pinned fixtures. Checked every row.
- **§4C's consequence holds by construction:** under `item_narrowed_uniform` every participating
  section `has_usable_narrowed`, so `sections_without_sample` is 0 and `is_estimated` False — §6D's
  "the flag moves, and that is M1 succeeding".
- **`typical_resolution` is always present and non-null on the wire** (§7's standing frontend
  requirement): `serialize_typical_resolution(None)` returns the full six-key default
  (`division_serializers.py:113-120`), which is what the four legacy `fake_typical` doubles now exercise.
- **The citation discipline the prompt asked me to check is honest.** `git diff 8a4a1cb HEAD` on the
  phase test file touches exactly two regions — `test_c1c` rewritten, `test_c8_narrowing…` deleted. The
  two named mutations bound to them (C1(ii), C8) were **re-run**; every other retained row's assertion
  body is byte-unchanged, so the 14 citations from `8a4a1cb` hold. No expired retention.
- **Orphan sweep, done by counting not by prose.** `test_narrowed_price_scenario.py` holds **12** test
  functions (15 cases with parametrization); all 12 map to a §6A row. `test_price_scenario_query.py`'s
  29 changed lines are arity widening and `typical_filter_spec=None` on the four fakes — **no test added
  or removed**. `test_narrowed_task_economics.py` carries only `:542`'s `2` → `0` and its restated
  comment. `_narrowing_fixture.py` is additive; both new helpers have callers in this phase. **Zero
  orphans.**
- **Perimeter.** `git diff 9bad5a3 HEAD -- app/` is exactly the seven files §4/§4A authorize, and
  `budget_division.py` carries only the two authorized deletions (`:19` `median,` and `:25-26`).
- **The two text-scanning guards §4A names are satisfied**, not merely unbroken:
  `test_domain_purity.py`'s six forbidden substrings appear in neither changed domain file, and
  `test_c13c…`'s new `== 0` is true (`_step_state_is_excluded` is gone from price-scenario).
- **C7(b)'s sweep root is correct and complete** — `parents[6]` resolves to `backend/`, and neither
  swept directory has a sub-package, so the non-recursive `glob("*.py")` is not the blind non-recursive
  walk phase 1 paid for. The equality to a non-empty set also entails §9's "the walk found something",
  so the missing explicit `assert files` costs nothing.
- **`routers/README.md` checked against plan-4's C-1 lesson** (hand-maintained, guarded by no test):
  its price-scenario section carries prose only, no field table, so this phase's added key rots
  nothing. No action.
- **TZ independence measured** at UTC+14 and UTC-11 (P5).

## Where my evidence ends

- **I did not re-derive the five facts the prompt fenced off** — perimeter exactness, the stamp,
  §6A.F's medians, C1(c)'s spy being a genuine delegating spy, C8's corrected mutation site. I consumed
  them by citation and corroborated two of them cheaply as a side effect (the `8a4a1cb` byte-identity,
  and the test-file diff shape).
- **I did not re-run the 14 cited mutations.** I verified the *citations' validity* (which tests the
  fix round edited) rather than the reds. If a cited red was mis-attributed at `8a4a1cb`, this round
  would not catch it.
- **I did not touch `.archgraph/`** — not read for review purposes, not verified, not repaired.
  Per the prompt's amendment the graph is closed and out of scope.
- **I did not exercise `get_task_price_scenario` end to end against a database.** B1 is established by
  mutation-and-absence (L4, ∅/∅), which proves nothing observes the seam; it does not prove the seam is
  currently *wrong*. Reading `:232-238` says it is currently right.
- **`sections_by_basis`'s values are unasserted for price-scenario anywhere.** I did not file it: the
  object is produced by the same `serialize_typical_resolution` from the same `TaskTypicalSelection`
  that phase 4's approved rows pin for production-time, and C6's shared-import mutation covers the
  "second implementation" hazard. If the coordinator disagrees, it belongs to the same fix round as B1.
- **I did not measure query counts or cost.** §12's matrix is phase 2's and S1 makes the scoping
  behaviourally invisible, so a scope regression would show up as cost, not as a red — outside what any
  criterion in this phase can see.

## Write perimeter

Documents only, all inside this implementation folder:

- `handoffs/reviewer/20260824_plan5_review_round1_handoff.md` (this file)
- `plans/plan_5.md` — §8 Review log entry appended, and the `state:` header
- `master_plan.md` — §4 tracker row 5 only

**No `app/` write.** No production or test file was left changed. No `.archgraph/` write. No commit,
no push, no `git add`.

## Mutation-probe declaration

Every probe applied, observed, reverted, and checksum-verified byte-identical. `git status --porcelain
-- app/` is empty after the last revert.

| file | final md5 | matches |
|---|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | `213a38a03f7ffaafe954bae68d4da16a` | the fix-round-2 handoff's published value ✓ |
| `app/beyo_manager/domain/item_economics/division_serializers.py` | `b462988498000a0db94524e11f6b7462` | pre-probe capture ✓ (and `git status` clean) |

Probes P1, P3, P4 touched `get_task_price_scenario.py`; P2 touched `division_serializers.py`; P5
touched no file. **Database side effects: none beyond ordinary suite residue** — the two DB-backed
phase rows clean up in `finally` via `cleanup_divergent_category_fixture`, every pytest process built
and dropped its own `beyo_test_main_*` database, and the configured `beyo_manager` development
database was never a target.

## Lessons for the plans (coordinator folds these upstream)

1. **A phase that onboards a consumer owes a criterion on the edge that feeds it, not only on the
   function it feeds.** Every row here tested `_typical_block`; nothing tested who calls it with what.
   The trace chain checks *criterion → test* and *test → criterion*, and both were clean — a missing
   **edge** is invisible to a manifest whose links are all rows that exist. Candidate lint command:
   for each production call site the plan's tasks pin by name, grep the phase's tests for that call
   site and require one hit.
2. **A row rewritten to escape the cannot-fail family is the row most likely to re-enter it.** C1(b)
   was repaired at the projection *because* it was inert, and shipped inert in the same half, on the
   fake the plan's own bold-face rule names. The repair prescribed an instrument; the round substituted
   a cheaper one and the coverage map described the prescribed one. **When a plan prescribes an
   instrument to the line, the ledger row for that criterion states which prescribed element it
   implemented** — the fake, the boundary group, the two literals — one cell each.
3. **A criterion that names a contract must name the mechanism that contract lives in.** C5(b) claimed
   §2B S-7's SQL scope and mutated the participating-set computation. The general form of §9's
   hazard-ownership rule, one altitude up: not "does the guard read the column", but "is the guard's
   mutation applied to the mechanism the sentence names".
4. **Some contracts have no observable, and saying so is the correct outcome.** §2B S-7's scoping is
   one. The plan should record it as a cost property with no row, rather than leaving a sentence that
   invites the next round to build a test that cannot fail — the fifth-generation shape this project
   keeps producing.
5. **`_TypicalSession` should be quarantined by name in plan 6's read-first.** Three rounds of this
   phase produced two rows built on it that could not observe their own subject (the deleted C8 test,
   and C1(b)). The plan's bold-face warning was correct and was read; it did not bind because it names
   a *check* ("check that it issues SQL") rather than a *rule* ("a row tracing to M1 or M7 runs on
   `db_session`").
