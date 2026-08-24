---
plan: plan_5
role: reviewer
round: 0
date: 2026-08-24
actor: Opus 5 (plan-projection, round 0)
verdict: AMENDMENTS_REQUIRED
---

# Projection — phase 5, `narrow_typical_work_times`

## Opening (owner-readable)

I ran phase 5's plan forward against the real code without building anything, asking of each
row whether someone could execute it exactly as written and whether the result would be
decidable. It cannot be executed as written. The clearest problem I measured: the change the
plan asks for in its third task makes an existing test fail, and that test lives in a file the
plan does not permit anyone to touch — so the phase could not finish green. A second measured
one: the plan's very first task says "delete exactly one line, and any other edit here is a
mistake", and deleting that line leaves the file failing the project's own code linter, so the
instruction contradicts itself. Beyond those I found nineteen further rows that are either
unexecutable, unmeasurable, or green under the very defect they exist to catch — including two
of the highest-cost kind this project keeps paying for. Every correction is written out
concretely. One thing does need you, and it arrived while I was working: the rule change you
made to the shared doctrine this morning asks that each test be purchased against a declared
outcome, and it has to be answered before this plan is amended rather than after.

## ⚠ OWNER DECISIONS REQUIRED (1)

**Card 1 — Backfill the measurement ledger before phase 5's plan is amended, or defer it?**

**Story.** Phase 5's plan was written before the trace chain landed in the charter this
morning. Its seven criteria trace to nothing: every one becomes a test somebody writes, a
reviewer mutation-probes, and every future full-suite run pays for — and not one of them names
the outcome it exists to prove. The phase beside it in the neighbouring project reached 1389
lines of test file exactly that way. Phase 5 is the last phase in this project that touches
production code; phase 6 is closeout.

**Branches.**
- *Backfill first* — a new lettered section in the intention, 3–7 named outcomes, your review;
  the fold then adds one trace cell per criterion row. Costs roughly one session before
  dispatch.
- *Defer to phase 6* — phase 5 dispatches with untraced rows. Orphan tests are still caught at
  implementation and review, but nothing checks whether the rows themselves were worth writing.

**Recommendation.** Backfill first — a ledger written after phase 5 can never have shaped
phase 5, and this is the last phase where it could.

**On silence.** The gate holds. The coordinator amends nothing and phase 5 is not dispatched.

**Trace.** Charter "trace chain", in-flight adoption clause; intention (new lettered section);
plan 5 §6 C1–C7. Finding **B6**.

## Verdict

**`AMENDMENTS_REQUIRED`** — 6 blocking, 14 should-fix, 5 notes.

> **Doctrine moved during this session.** `pipeline-charter.md` and `plan-projection.md` were
> both edited on disk while I was projecting: the phase manifest grew a fifth property, and the
> projection procedure grew a sixth step (**trace verification, both directions**). I re-read
> both and ran the new step; it produced **B6**. Everything above B6 was derived under the
> version in force at session start and is unaffected — the earlier properties are unchanged.

---

## Ledger

### B1 — blocking — task 3 reddens a test in a file §4 does not permit, and the phase cannot close green

**Where:** §5 task 3; §4 "Files expected to change".

**What is wrong.** Task 3 replaces price-scenario's inline
`any(not _step_state_is_excluded(step) …)` with a call to `participating_sections`. That
removes both occurrences of `_step_state_is_excluded` from
`get_task_price_scenario.py` (measured: the import at `:13-14` and the call at `:134` are the
only two). Phase 4's C13(c) guard hard-codes that number:

```
tests/integration/services/queries/item_economics/test_narrowed_task_economics.py:541-542
    price_scenario = root / "app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py"
    assert price_scenario.read_text().count("_step_state_is_excluded") == 2
```

`test_narrowed_task_economics.py` appears in **neither** of §4's lists — not as modifiable, not
as read-only.

**Evidence gathered at source.** Baseline, tree `9bad5a3`, `app/` clean:
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest tests/integration/services/queries/item_economics/test_narrowed_task_economics.py -n 0 -p no:randomly`
→ **16 passed in 2.67s**. I then applied task 3's change faithfully (import
`participating_sections`, drop `_step_state_is_excluded`, filter the groups by the shared set),
asserted by `inspect.getsource` that the edit landed **inside `_typical_block`**, and re-ran the
same command → **1 failed / 15 passed in 2.02s**, the single failure being
`test_c13c_excluded_state_logic_has_one_shared_production_owner` at `:542` with
`assert 0 == 2`. Reverted; md5 identical before and after (§ probe declaration).

**Correction.** Add `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`
to §4 **Modified — tests**, with the edit named exactly: delete `:541-542` (the two
`price_scenario` count lines) and remove
`"app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py"` from the
`allowed` set at `:535`, leaving `allowed == {"app/beyo_manager/domain/item_economics/budget_division.py"}`.
The loop at `:539-540` (`assert "def _step_state_is_excluded" not in …`) already carries the
mechanical form plan 4's own re-review amendment required, so nothing is lost and the row gets
*stronger*: after task 3, `budget_division.py` is the sole owner. Add the edit to a criterion
row so it is a declared act, not an undeclared perimeter breach.

---

### B2 — blocking — task 0's "exactly one deletion" is unsatisfiable; it leaves the file failing CI lint

**Where:** §4 "Modified" (`budget_division.py` — *exactly one deletion … any other edit to this
file is still a finding*); §5 task 0.

**What is wrong.** `median` is imported into `budget_division.py` **only** to build the bridge.
Measured: `grep -n "median" beyo_manager/domain/item_economics/budget_division.py` returns
exactly two lines — `:19` (`median,` inside the `typical_filters` import block) and `:26`
(`_median = median`). Deleting `:26` orphans `:19`.

**Evidence gathered at source.** `python3 -m ruff check beyo_manager/domain/item_economics/budget_division.py`
→ **1 error** before (a pre-existing `F821` on `datetime` at `:48`); after deleting the bridge
line and its comment → **2 errors**, the new one
`budget_division.py:19:5: F401 [*] beyo_manager.domain.item_economics.typical_filters.median imported but unused`.
`app/Makefile:103-104` defines `lint: python -m ruff check .`, and `.github/workflows/ci.yml:9,18`
runs `make lint` as its own job. Reverted; md5 identical.

**Correction.** §4 authorizes **two** deletions in `budget_division.py`: the `_median = median`
line with its comment (`:25-26`), and `median,` from the `typical_filters` import block (`:19`).
Record the measurement that makes the second safe: no importer of `budget_division.median`
exists anywhere (measured repo-wide over `beyo_manager/` and `tests/`), and `__all__` (`:413-422`)
does not list it.

---

### B3 — blocking — the plan never says what `section_ids` receives, and two mutations are inert or wrong because of it

**Where:** §5 task 4; §6 C3 mutation (i); §6 C5 first mutation.

**What is wrong.** `reconcile_task_typicals(evidence_by_section, spec, participating_section_ids,
section_ids)` takes a **fourth** argument that §6.2 defines as "the task's **full** section set
(§3.5: `selected` covers every section in the task, including excluded)". Task 4 says only
"Build `SectionTypicalEvidence`, call `reconcile_task_typicals`" — it never says what goes in
that slot, while task 3 scopes the *statement* to the participating sections only (§2B S-7).
Two criteria's mutations depend on the answer:

- **C3 mutation (i)** — "count every section in `selected` for `sections_total` → contract `3`;
  mutation `4`". If the implementer passes the participating set (the natural reading, since
  that is the only set it has evidence for), `selected` holds three entries and the mutation is
  a **no-op**: the row is green under the very defect it names.
- **C5 first mutation** — "compute over all of `selected` instead of the participating set →
  contract `1500`; mutation `2100`". This cannot yield `2100` under any reading. If `section_ids`
  is the participating set, the mutation is a no-op (`1500`). If it is the full set but the
  statement is scoped to participating sections, the excluded section carries `_zero_evidence`
  (`typical_filters.py:261-262`), so its selected value is `None` and
  `apply_business_fallback` gives it the in-task median `750` → **`2250`**, not `2100`. `2100`
  is only reachable if the *statement* covers the excluded section too — which is exactly what
  C5(b) exists to forbid.

**Evidence gathered at source.** `typical_filters.py:265-326` (`reconcile_task_typicals` fills
`evidence` for every id in `section_ids` via `.get(section_id, _zero_evidence(section_id))`);
`typical_filters.py:329-336` (`apply_business_fallback` substitutes `median(usable)`);
`get_task_production_time.py:69,111-117` (the comparator: production-time passes
`{step.working_section_id for step in steps}`, the full set).

**Correction.** Two parts.
1. §5 task 4 states the call explicitly:
   `reconcile_task_typicals(evidence_by_section, spec if specs else None, participating_ids, frozenset(step.working_section_id for step in steps))`
   — the full task section set, per §6.2, while the statement stays scoped to
   `participating_ids` per §2B S-7. C3(i)'s mutant is then `4` as stated. Note in the task that
   non-participating sections resolve to `insufficient_sample` on zero evidence and that this
   reaches no published field, so §2B S-7 and §6.2 do not conflict.
2. Replace C5's first mutation with one that mutates the **participating computation**, not the
   summation: `_typical_block` (call site) — `frozenset(step.working_section_id for step in steps)`
   in place of `participating_sections(steps)`. The excluded section then participates, its
   evidence enters scope, and the sum is `600 + 900 + 600 == 2100` exactly as the plan states,
   against a contract of `1500`. This is also the realistic drift shape (an exclusion predicate
   dropped), which "compute over all of `selected`" is not.

---

### B4 — blocking — C5's second mutation names a bite it cannot produce, and its literals come from a hand-built unit object

**Where:** §6 C5, *Second mutation*.

**What is wrong.** Two separate defects in one line.

1. **The bite set is impossible.** "`get_task_price_scenario` (call site): resolve typicals
   locally instead of through the shared selection → **rows (a), (c)** flip". Row (c) is
   *budget-allocations'* step row. `get_task_budget_allocations` never calls, imports or reads
   price-scenario (measured: the only test-visible coupling between the two is C13(c)'s text
   scan, B1 above). A mutation confined to price-scenario cannot move a budget-allocations row.
2. **The literals are from the wrong kind of fixture.** "contract `(540, "item_narrowed", 7)`;
   mutation `(600, "section_wide", 61)`". `(600, 61)` appears in this repository exactly once:
   `test_narrowed_task_economics.py:223`,
   `narrowed = lambda section: SectionTypicalEvidence(section, 540, 7, 600, 61)` — a **hand-built
   dataclass in a pure-unit test**, not a seeded population. On the only fixture that produces
   `(540, "item_narrowed", 7)` — `seed_categorized_two_section_task` — the section's *entire*
   completed population **is** those same 7 chair groups at 540 seconds
   (`_narrowing_fixture.py:95-121`), because `_seed` contributes only `FAILED`, `PENDING` and a
   deleted `SKIPPED` step (`test_budget_allocations_query.py:61-63`) and nothing `COMPLETED`.
   The section-wide pair is therefore `(540, 7)`, identical to the narrowed pair, and the
   mutation moves **only `typical_basis`**. This is N11's uniform-fixture lesson one level up:
   the two populations are not merely uniform, they are the same rows.

**Correction.** (a) Restrict the mutation's stated bite to price-scenario's own observable
(see B5 for what that observable must be), and give budget-allocations' row (c) a mutation
sited in a service it actually reads. (b) Either seed a section-wide population that differs
from the narrowed one — e.g. add five completed groups with no primary item category at a
different value in each section, and state both pairs — or state the mutant literal honestly as
`(540, "section_wide", 7)` and make `typical_basis` a first-class part of the assertion, since
it is the only field that moves.

---

### B5 — blocking — C5(a) asserts an observable price-scenario does not publish

**Where:** §6 C5 row (a).

**What is wrong.** "per participating section, price-scenario's contribution and
production-time's `(typical_worker_seconds, typical_basis, sample_count)` agree — exact literals
on both sides". Price-scenario publishes **no per-section typical anywhere**. Measured: its
`typical` block is built at `get_task_price_scenario.py:173-181` as
`{total_seconds, is_estimated, sections_without_sample, sections_total, method, window_days,
min_sample_size}`, and `serializers.py:364` is a whole-dict pass-through (`"typical":
scenario["typical"]`), so §7.4's addition makes it that dict plus `typical_resolution`. There is
no section-keyed structure to compare, and the criterion does not name an internal to reach for
instead. As written the row cannot be turned into an assertion from the artifacts alone.

**Correction.** Name the observable. The cheapest honest form: build the fixture with **one**
participating section, assert production-time's and budget-allocations' triples as exact
literals, and assert price-scenario's `typical.total_seconds` equals that same
`typical_worker_seconds` literal — one number, three surfaces, no equality-between-two-calls.
If per-section agreement over more than one section is wanted, the criterion must name the
accessor (the `TaskTypicalSelection` `_typical_block` builds) and say the row asserts against a
returned object rather than a payload — and then §7's "no criterion IDs or bare line numbers in
production comments" note applies to nothing, but §4 must say whether `_typical_block`'s return
shape changes to expose it.

---

### B6 — blocking — no criterion row traces to a declared measurement, and the fold that consumes this handoff is the act the backfill must precede

**Where:** §6 C1–C7 (every row); intention (no measurement ledger exists). **See owner card 1.**

**What is wrong.** The charter's new **trace chain** makes `measurement objective → criterion
row → test → named mutation` checkable in both directions, and manifest property **5** requires
each criterion row to carry a trace cell naming the intention's measurement-ledger ID or the
mechanism contract it serves. Measured: `plans/plan_5.md` contains the string "trace" **zero**
times, and `planning/intention.md` has no measurement ledger — no `M1`…-style IDs and no section
declaring one (its fourteen top-level sections are unchanged since the round-6 fold).

The in-flight adoption clause is what makes this a dispatch-order question rather than a
retroactive defect:

> *links 3–4 bind immediately … Link 1 is backfilled as a lettered intention section (never
> renumber), owner-reviewed, **before the project's next planning act**; link 2 then applies to
> every plan authored or amended after the backfill.*

**Consuming this handoff amends plan 5 — that is the project's next planning act.** So the
ordering is forced: either the ledger is backfilled first and the fold adds trace cells to all
seven criteria while it is already rewriting them, or the owner records a deferral. Doing the
fold first and the backfill after produces the one outcome the clause exists to prevent — the
project's last production phase planned against no declared objective, with the ledger written
afterwards where it cannot shape anything.

**Two consequences that bind regardless of the card's answer**, because links 3–4 are immediate:

1. **§5 task 8 owes the reverse half.** It reads "Tests per §6." The executor's Task 0 must now
   also map **every test back to a row**, and a test with no row is either not shipped or
   declared in the Review log as a *candidate criterion* naming the defect it catches. Say so in
   the task; an implementer working from "Tests per §6" will not infer it.
2. **Orphan tests are a reviewer finding of the same class as an uncovered row.** Phase 5 rewrites
   nine existing `_typical_block` call sites (S13) and adds a new file. The plan should state that
   the rewritten rows keep their existing criterion attribution — otherwise the first reviewer
   meets eight tests that trace to phase-3 and phase-5-of-the-*previous*-project criteria and must
   reconstruct the mapping from scratch.

**Correction.** Route card 1 to the owner before the fold. On *backfill first*: add the lettered
intention section (3–7 outcomes with IDs and the defect family each guards), then give every C1–C7
row a trace cell in the same edit that applies B1–B5 and S1–S13. On *defer*: record the deferral
in master plan §4's row 5 note with the reason, and apply the two immediate consequences above
regardless.

---

### S1 — should-fix — C6(c)'s three literals are transcribed from a documentation example, not measured

**Where:** §6 C6 row (c).

**What is wrong.** `task_typical_basis == "item_narrowed_uniform"`,
`applied_filter == {"item_category_ids": ["icat_chair"]}`, `participating_section_count == 3`.
All three appear together in master plan §6.5's illustrative JSON. Measured against the only
narrowed integration fixture: `seed_categorized_two_section_task` seeds **two** sections
(`_narrowing_fixture.py:90,95`), and its category client_id is
`f"itc_narrowing_chair_{uuid4().hex[:10]}"` (`:74`) — `"icat_chair"` is not producible by any
seed in the repository. The honest forms already exist twelve lines away in the same directory:
`test_narrowed_task_economics.py:302-303` asserts
`applied_filter == {"item_category_ids": [category_id]}` and `participating_section_count == 2`.

**Correction.** Either assert `2` and `[category_id]` on the existing fixture, or declare a new
three-section narrowed fixture in §4 (see S2) and derive the count from it. Keep
`"item_narrowed_uniform"` as an exact literal — §9 exempts version strings the frontend keys on.

---

### S2 — should-fix — every criterion needs a fixture that does not exist, and §4 forbids the file that would hold it

**Where:** §4 "Modified — tests"; §6 C2–C6.

**What is wrong.** C2 needs four distinct tasks (empty participating set; one selected-`None`
beside one usable; one selected-`0`; all usable on a `section_wide_uniform` task); C3 needs
3 participating + 1 excluded with a specific usable/`None`/`0` split; C4 needs 3 participating
with no usable typical and a mixed `600/900/None`; C5 needs a participating and an excluded
section both carrying typicals; C6 needs a narrowed multi-section task. **None** of these
exists. The three seeds in `_narrowing_fixture.py` were built for phase 4's counts-and-basis
rows, and master plan §6.9 lists that file as "4 (created), **5 (reused)**". §4 does not list it
as modifiable, so adding a seed there is a perimeter breach and putting six seeds in the new
test file is unstated.

**Correction.** Add `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`
to §4 **Modified — tests**, or state that every new seed is local to
`test_narrowed_price_scenario.py`. Say which, and update master plan §6.9's "5 (reused)" if it
becomes "5 (extended)".

---

### S3 — should-fix — C2 row (c) is green under its own mutation; it is the sibling of the defect the lint fixed

**Where:** §6 C2 row (c), and mutation (iii).

**What is wrong.** The fixture line reads "**≥1** participating section whose **selected**
typical is `0`". Nothing forbids a second unusable section. If one is `None`, mutation (iii)
(`<= 0` → `< 0`) leaves the `is None` half firing, `sections_without_sample` stays `> 0`, and
the row stays **true** — green under the defect it exists to catch. The lint corrected exactly
this looseness in row (b)'s *assertion* (`>= 1` → `1` exact) and left the identical looseness in
row (c)'s *fixture*.

**Correction.** "**Exactly one** participating section whose selected typical is `0`, and
**every other participating section usable** — the fixture pins both", plus
`sections_without_sample: 1` **(exact)** in the "also" column, matching row (b)'s repaired form.

---

### S4 — should-fix — C2(ii) and C3(ii) are the same edit, and the plan does not say what it redefines

**Where:** §6 C2 mutation (ii); §6 C3 mutation (ii).

**What is wrong.** Both read "define/count … as participating sections without a **narrowed**
sample". In production `is_estimated`'s second disjunct is derived from `sections_without_sample`
(`get_task_price_scenario.py:175-176`), so the edit has two possible sites: redefine the
published **count**, or redefine only the **flag's** disjunct. The choice changes the bite set.
If the count is redefined, C2 row (b) also reddens — its `sections_without_sample: 1` becomes
`2` on any fixture without a narrowing spec, since every section is then "narrowed-thin" —
contradicting C2(ii)'s stated "Rows (a)–(c) do not bite". A reviewer running the ledger will
file a finding against a correct implementation.

**Correction.** State the sites separately. C2(ii): "redefine the **flag's** second disjunct
only, leaving `sections_without_sample` computed as §6B specifies → row (d) alone flips."
C3(ii): "redefine the **published count** → C3's `sections_without_sample` `2` → `3`." Then
re-derive both bite sets from the code the edits describe.

---

### S5 — should-fix — C4 mutation (ii) names a site where it cannot be applied

**Where:** §6 C4, *Mutations … both at `_typical_block`'s `apply_business_fallback` call site*.

**What is wrong.** "(ii) return the terminal instead of the median when usable values exist"
is not something a call site can do: the call site supplies `selected_values` and `terminal`
only. The edit is `fallback = median(usable) if usable else terminal` → `fallback = terminal`
at `typical_filters.py:335` — a **definition**, in a different file, shared with the division
path. Charter rule 11 requires file plus definition-vs-call-site, and this states both wrongly.
Mutation (i) (`terminal=Fraction(1, 1)`) genuinely is a call-site edit, so the shared preamble
is wrong for exactly one of the two.

**Correction.** Split the preamble: (i) at `_typical_block`'s `apply_business_fallback` **call
site**; (ii) at `typical_filters.apply_business_fallback` (**definition**, `:335`). Add the note
that (ii) also reddens division tests at L2 and that the ledger records the red observed **in
this phase's own file**, so the bite is attributable. The stated values (`2250` → `1500`) are
correct — I checked the arithmetic against `apply_business_fallback`'s actual behaviour.

---

### S6 — should-fix — C1(b) is a row that cannot fail: nothing in it controls the wall clock

**Where:** §6 C1 row (b), and mutation (i).

**What is wrong.** The row serves the same task twice "at two different wall-clock instants"
with the same frozen `ctx.now`, and asserts byte-identity. Under the **contract** that is
trivially true — `now=ctx.now` means no clock is read at all. Under **mutation (i)** it is
*also* true in practice: dropping `now=` makes the cutoff
`datetime.now(timezone.utc) - timedelta(days=90)` (`get_working_section_typical_times.py:40`
and `:147`), and two in-process calls are microseconds apart, so the boundary group falls on
the same side of both cutoffs unless `max(closed_at)` happens to land inside a microseconds-wide
window that the test cannot aim at — a fixture pinning `closed_at` *before* the first call
always lands outside it. The mutation's red is therefore a race the row loses ~always, and the
guard ships green under the defect it names. This is the highest-prior defect family in this
lineage and the row currently belongs to it.

**Correction.** The row must **control** the wall clock, not hope it moves: monkeypatch
`beyo_manager.services.queries.working_sections.get_working_section_typical_times.datetime`
with a fake whose `now()` returns two instants that straddle the frozen boundary — with
`closed_at == ctx.now - 90 days`, use `ctx.now - 1s` for the first call and `ctx.now + 1s` for
the second — and state the expected `total_seconds` on each side of the mutation (group in /
group out) so both sides are exact literals. `datetime` is imported into that module's namespace
(`:5`), so the patch site is a module attribute. State it in the plan; an implementer will not
invent it.

---

### S7 — should-fix — C7's presence form names two terms whose absence cannot be asserted

**Where:** §6 C7, *Presence form*.

**What is wrong.** "contains … no `Fraction`-median construction, no `percentile` computation and
no comparison against `TYPICAL_MIN_SAMPLE_SIZE`. Asserted by reading the function's source."
Source-reading assertions are a legitimate, established idiom here — `test_production_time_contract.py:6-21`
is one — but two of these three terms cannot be applied:

- `_typical_block` **publishes** `TYPICAL_MIN_SAMPLE_SIZE` in its own return dict
  (`get_task_price_scenario.py:180`), and §7.4 keeps that key, so `"TYPICAL_MIN_SAMPLE_SIZE" not
  in source` can never be green. "Comparison against" is a semantic qualifier a text scan cannot
  make (§9: *a criterion whose instrument cannot return the expected result is undecidable,
  however precise its prose*).
- `Fraction` stays in the function by construction — task 4's
  `apply_business_fallback(..., terminal=Fraction(0, 1))` — so "no `Fraction`-median
  construction" is not a term either.

**Correction.** State the exact term set the assertion uses: `"median" not in source`,
`"percentile" not in source`, and — for the floor — `">= TYPICAL_MIN_SAMPLE_SIZE" not in source`
and `"< TYPICAL_MIN_SAMPLE_SIZE" not in source`, which are the two comparison forms; drop the
`Fraction` clause and let the spy carry it. Also name the spy's install site
(`get_task_price_scenario.apply_business_fallback`, a module attribute after task 4's import)
and require its fixture to have ≥1 participating section — with none, `apply_business_fallback`
is called with an empty sequence or not at all, and "exactly once" becomes ambiguous.

---

### S8 — should-fix — C7's allowlist is derived from the pre-task-0 tree and is wrong after the phase's own tasks

**Where:** §6 C7, *Corrected form … Expected hits, enumerated by name*.

**What is wrong.** Measured at the corrected root
(`domain/item_economics/` + `services/queries/item_economics/`), terms
`percentile_cont` · `_median` · `median(`, tree `9bad5a3`:

| file | hits today |
|---|---|
| `budget_division.py` | `:26` `_median = median` — **its only hit** |
| `typical_filters.py` | `:335` `median(usable)`, `:339` `def median(` |
| `get_task_price_scenario.py` | `:13` `_median,`, `:160` `_median(usable)` |

Task 0 deletes `budget_division.py:26` (and B2 deletes its now-orphan import at `:19`, which is
`median,` with no paren and matches nothing anyway); task 4 deletes both price-scenario hits.
**After this phase the only hit at that root is `typical_filters.py`.** The plan enumerates
three expected hits including `budget_division.py`, which will not hit, and
`get_working_section_typical_times.py`, which lives in `services/queries/working_sections/` —
**outside the stated root** — and therefore can never hit at all. If the row ships as an
equality it fails on green code; if it ships as `hits <= allowed` it silently widens by two
files.

**Correction.** Expected hits = `{typical_filters.py}`, exactly. Assert `hits == expected`
**and** `assert files` (§9's walk rule: a directory guard needs a row proving the walk found
something). Delete `get_working_section_typical_times.py` from the enumeration — the statement's
home is a fact about the codebase, not an allowlist entry — or move the root to include it and
justify the widening in the row.

---

### S9 — should-fix — C7's sweep is budgeted at L4 for a root it no longer has

**Where:** §6 header ("C7's sweep row is an **absence claim** at **L4**").

**What is wrong.** Master plan §10 says L4 is required for "absence claims **whose root really
is the repository**", and its 2026-08-23 correction demoted plan 4's C1 sweep to L2 for exactly
this reason. §10 also says a committed test walking a directory is "an **L1 test** with a
repo-wide *claim* … Do not spend the stamp on it." The lint narrowed C7's root from the
repository to two item-economics directories and did not re-derive the scope, so the plan now
budgets a whole-suite run for a two-directory text scan.

**Correction.** §6's scope line becomes L1 (the phase's own test file). Route an amendment to
master plan §10, whose evidence-budget bullet still reads "*Plan 5 C7's fork sweep still is
one*" — that sentence became false when the lint narrowed the root.

---

### S10 — should-fix — task 0 states an acceptance criterion with no row id, no test home, and no place in the mutation count

**Where:** §5 task 0; §6.

**What is wrong.** "Criterion: `budget_division` no longer defines `_median` (absence,
module-scoped) **and** the full suite collects with zero errors." That is an eighth criterion in
a plan whose criteria table runs C1–C7, so it has no addressable row (charter manifest item 1),
no declared file — §4's test perimeter is the two price-scenario files, while master plan §5's
mirror rule (`architecture/15_testing.md`) puts a `budget_division` module assertion in
`tests/unit/domain/item_economics/test_budget_division.py` — and it is excluded from the
mutation enumeration by construction.

**Correction.** Promote it to **C0** with lettered rows: (a) `not hasattr(budget_division,
"_median")`; (b) the collection check. Name its file, add it to §4 if that file is new to the
perimeter, and name its mutation (restore the alias → row (a) reddens).

---

### S11 — should-fix — §2's N1 probe has no task and no criterion, and its stated premise is wrong

**Where:** §2, routed item **N1**.

**What is wrong.** Two halves.
1. **Placement.** "Plant a copy in the codebase's own idiom … and confirm C13(c) reddens
   *before* you rely on it" is a required rule-15 probe living in a Read-first list. It has no
   task in §5, no criterion in §6, and no line in the mutation enumeration — so nothing will
   count it, which is precisely how the four unrun mutations of plan 2 happened.
2. **Premise.** "**You add price-scenario's private ladder over that same predicate**, so you
   are the phase that makes the hazard real." Measured: plan 5 writes no private copy of the
   excluded-state predicate. `get_task_price_scenario.py` holds no state-set literal at all —
   its only two `_step_state_is_excluded` occurrences are the shared import at `:13-14` and the
   call at `:134`, and task 3 **removes both** (B1). Phase 5 is the phase that makes
   `budget_division.py` the sole owner, not the phase that forks it.

**Correction.** Keep the probe — it is more valuable after task 3, not less, because C13(c)
becomes the only remaining guard — but give it a criterion row, restate the reason, and name the
planted defect concretely: insert
`_EXCLUDED = frozenset({TaskStepStateEnum.SKIPPED, TaskStepStateEnum.CANCELLED, TaskStepStateEnum.FAILED})`
plus a local `def _step_state_is_excluded` into a production file under `app/beyo_manager/`, and
record the observed red (the AST half of the guard at `test_narrowed_task_economics.py:544-570`
handles enum-member set literals; the string-literal half does not — that is the shape N1 is
about).

---

### S12 — should-fix — §7's graph paragraph was to be fixed before dispatch and was not, and half of it contradicts the binding policy

**Where:** §7, last bullet.

**What is wrong.** Master plan §8's D30 lesson says, naming this plan: *"A phase that changes
what a node MEANS owes a description rewrite, and the plan must say which of the two it wants.
**Plans 5 and 6 carry the same ambiguous sentence — fix it there before dispatch.**"* §7 still
says only "Architecture-graph delta expected". Measured, the node needs the description half:
`.archgraph/architecture.yml:5911-5923`,
`projection-item-economics-task-price-scenario`, describes "**median-substituted task typical
time**" and mentions neither narrowing, the shared reconciliation, nor an injected clock — it
describes exactly the private ladder task 4 deletes.

Second half: "symbol anchors preferred over line spans, but never both on one entry" and "**re-derive
its span from the symbol**, never trust the stored one" contradict §8's interim policy, which is
**binding on every session**: *"do not emit `startLine`/`endLine`."* Measured, the node's live
evidence entries already carry `path` + `symbol` and no spans, so the plan instructs a session to
derive a coordinate the policy has removed.

**Correction.** §7 states: **description rewrite plus source links**, quoting the clause to
replace ("median-substituted task typical time" → the narrowed/reconciled/clock-injected
meaning). Replace both span sentences with the policy's form: no `startLine`/`endLine`, symbol
anchors only, one batched `apply_changes`, no counts in evidence summaries.

---

### S13 — should-fix — the fake-widening obligation is conditional on an unmade choice, and it names the smaller of two surfaces

**Where:** §2 (the four `fake_status` fakes); §5 task 2.

**What is wrong.** Task 2 leaves the spec source free: "From the active PRIMARY `Item`
price-scenario already loads (`:195-196`), **or equivalently** from
`budget_status.typical_filter_spec` … Use one source and say which in a comment." Two
consequences:

1. **The widening obligation only exists on one branch.** §2 states flatly that this phase "gets
   an `AttributeError` from every one of them". Measured, that holds only if the implementer
   reads `budget_status.typical_filter_spec` **and** reads it outside `_typical_block` — all four
   tests also monkeypatch `_typical_block` itself (`:578`, `:981`, `:1123`, `:1282`), so a read
   *inside* it never executes. On the `Item` branch, widening all four is dead work (charter rule
   4).
2. **The larger fake surface is unnamed.** §2 enumerates four `fake_status` sites and stops.
   Measured, `module._typical_block(...)` has **nine** call sites — `:128, :147, :164, :185,
   :198, :206, :218, :230, :337` — every one of which changes arity when `_typical_block` gains
   the spec, and eight of them feed `_typical_row` (`:108-113`), a three-attribute
   `SimpleNamespace` in the **no-spec** column shape (`client_id`, `typical_worker_seconds`,
   `sample_count`) that cannot carry `spec_index` / `narrowed_*` / `section_*`. This is §9's
   "a measurement at one site is not a measurement of the surface" repeating one layer out from
   where L15 found it.

**Correction.** §5 task 2 **picks** the source. Recommend `budget_status.typical_filter_spec`,
mirroring `get_task_production_time.py:81-82` so one derivation feeds all task surfaces, and
pin `_typical_block`'s new signature (`_typical_block(ctx, task_id, spec)`) so the read site is
determinate and the four `AttributeError`s are real. §2 then adds the nine `_typical_block` call
sites and `_typical_row`'s column shape to the widening obligation, beside the four
`fake_status` fakes.

---

### S14 — should-fix — the clock does not "move": price-scenario has never read one, and three rows are framed as if it had

**Where:** §5 task 1 ("**The clock moves to `ctx.now`**"); §6 C1 row (b) and its mutation (i);
C1's closing rationale.

**What is wrong.** Measured:
`grep -n "now\|utcnow\|datetime\|timezone\|timedelta" get_task_price_scenario.py` returns **two**
lines, `:82` and `:105`, and both are the English word "now" inside a comment. The file contains
**no clock reference of any kind** — no `datetime`, no `timezone`, no `timedelta`, no
`ctx.now`, no `utcnow`. What price-scenario has today is not a wall-clock *read* but an
inherited *default*: `_typical_block:140` calls `typical_times_statement(ctx.workspace_id)` with
no `now`, and the clock is read one module away, inside the statement
(`get_working_section_typical_times.py:40` and `:147`,
`(now if now is not None else datetime.now(timezone.utc)) - timedelta(days=TYPICAL_WINDOW_DAYS)`).

So task 1 is an **introduction, not a move**, and §1's own wording ("gains an injected clock") is
the accurate one. Three consequences the plan currently mis-frames:

1. **A criterion phrased as preserving current behaviour on the clock axis describes nothing.**
   There is no prior local behaviour to preserve. C1(b)'s determinism row is the one that suffers
   operationally — see **S6**, where it is green under its own mutation — but the framing is what
   let the row be written that way.
2. **C1's rationale is right in effect and wrong in mechanism.** "This phase extends an APPROVED
   pipeline's determinism contract to a fourth surface" is true of the *outcome*; the mechanism is
   that price-scenario stops inheriting a default it never knew it had. That distinction is what
   makes the D24 contrast with `/working-sections/typical-times` legible: that surface is not
   "keeping its clock read" either — it is keeping the same inherited default, at
   `get_working_section_typical_times.py:192`.
3. **Mutation (i)'s description should say what it re-exposes.** "Drop the `now=` argument" does
   not remove a clock read from price-scenario; it hands the cutoff back to the statement's
   default. The observable is unchanged, but a ledger row saying "removed the clock read" would
   be describing an edit nobody made.

**Correction.** Task 1 reads "**The clock becomes explicit: `_typical_block` passes `now=ctx.now`,
so the cutoff stops falling back to the statement's own `datetime.now(timezone.utc)`**", with the
two statement line references. C1's rationale and mutation (i) adopt the same vocabulary. Combine
with **S6**, which repairs the row that this framing produced.

---

### N1 — note — C1(c)'s "payload is unchanged" has no baseline and cannot fail

Phase 5 does not edit `get_working_section_typical_times.py`, and there is no typical-times
golden — measured, the three goldens are `golden_budget_status.json`,
`golden_production_time.json` and `golden_budget_allocations.json`. So the second half of row (c)
is green by construction. §9: *any criterion containing the words "unchanged", "before" or
"pre-refactor" owes a task that writes the baseline down, ordered before the first production
edit.* Either drop the clause and let mutation (ii) carry row (c) through the spy alone, or name
the existing test that pins the payload.

### N2 — note — C1(c) has no declared test home

The row constrains `get_working_section_typical_times`; §4's two test files both mirror
price-scenario, and master plan §5 records `architecture/15_testing.md`'s mirror rule with its
two deliberate deviations. Say where the row lands, and if it is a third deviation, record it as
one.

### N3 — note — C1 mutation (ii) probes a file §4 marks read-only

"`get_working_section_typical_times.py` … a change is a finding" is absolute; a reverted probe is
not a change, but the mutation ledger will list the file. Say the probe is authorized so the
perimeter check reads correctly.

### N4 — note — "the value is unchanged in every case" is exact about the definition and loose about the payload — route upstream

§5 task 5 quotes intention §6B verbatim, correctly. The sentence is true of the *formula* — for
identical evidence, `sections_without_sample` counts the same sections it counts today — and not
of the *payload* once narrowing is live: under `section_wide_uniform` the selected typical is
the section-wide value and `is_estimated` is byte-for-byte today's, but under
`item_narrowed_uniform` it can move. A section with five chair groups at 600 s and twenty
non-chair groups at 0 s publishes `is_estimated: true` today (section-wide median 0, layer 2
fires) and `false` after (narrowed median 600, usable). Route a qualifying clause to intention
§6B — *unchanged under `section_wide_uniform`; moves under `item_narrowed_uniform` wherever the
narrowed and section-wide medians differ in usability* — so no reviewer reads C2 as asserting
pre-phase-5 behaviour. Home-artifact rule: the intention, not the plan.

### N5 — note — C7's absence row does not name the shape it is blind to

Its three terms are literal, so a hand-rolled `ordered[len(ordered) // 2]`, or
`from statistics import median as med`, is invisible to it — the same class as C13(c)'s
string-literal blindness. §9: *an absence row must name the shape it is blind to.* One sentence
in the row.

---

## Reality checks — verified correct, do not re-verify

1. **Gate.** master plan §4 rows 1–4 `APPROVED`, row 5 `PROJECTING`; `plans/plan_5.md` header
   `state: PROJECTING` — the two agree. `git merge-base --is-ancestor e81764b HEAD` → 0.
   `git status --porcelain -- app/` empty. `redis-cli ping` → `PONG`.
2. **§4's references resolve.** All four `app/` paths exist; `test_narrowed_price_scenario.py` is
   correctly absent and declared *New*; every bare filename in §2 resolves.
3. **Task 0's premise holds.** `budget_division.py:26` is the bridge; its **only** importer
   anywhere is `get_task_price_scenario.py:13` (measured repo-wide over `beyo_manager/` and
   `tests/`); no test imports `budget_division.median` or `budget_division._median`.
4. **The lint's three measured counts are correct.** `TYPICAL_MIN_SAMPLE_SIZE` in **7**
   production files; `_median` in **4**, of which `domain/analytics/insights/stats.py:5` and
   `domain/analytics/estimation/strategies.py:6` are `from statistics import median as _median`;
   `median(` matches **12** files including tests. The lint's second `FAIL → fixed` row was right
   in every particular.
5. **Task 2's "equivalently" is true.** `get_task_budget_status.py:120-121` derives the spec from
   the item returned by the same `_load_task_and_item(ctx)` that price-scenario re-loads at
   `:196`. The only divergence is `item is None`, where the carrier is `None` and direct
   derivation gives a non-narrowing `TypicalFilterSpec()` — both produce `specs=()`.
6. **Task 3's substitution is faithful.** `participating_sections` (`budget_division.py:215-220`)
   adds an `is_deleted` guard the current inline predicate lacks, but `group_steps_by_section`
   (`:117-119`) already skips deleted steps and the step query filters them in SQL (`:124`), so
   the participating set is unchanged. Measured: under the substitution, 15 of the 16 tests in
   `test_narrowed_task_economics.py` stayed green; the only red was B1's text-count line.
7. **Task 7's serializer pointer is right.** `serializers.py:364` is `"typical":
   scenario["typical"]`, a whole-dict pass-through; `:353` is the item block's `"label"`, exactly
   as §2B S-6 says.
8. **Intention §7.4 does nest `typical_resolution` inside the `typical` block** (`intention.md:1315-1323`),
   so price-scenario's placement differing from production-time's task-level key is contract, not
   drift. §7.4's own "`serializers.py:353`" is the error S-6 already corrected.
9. **`is_estimated` has exactly one production site** — `get_task_price_scenario.py:175`.
   Everything else is tests (12 references, all in `test_price_scenario_query.py`).
10. **`ctx.now` is always present** — `context.py:24`, `field(default_factory=lambda:
    datetime.now(timezone.utc))` — so task 1 really is a one-argument change.
11. **C1(c)'s premise holds** — `get_working_section_typical_times.py:192` calls
    `typical_times_statement(ctx.workspace_id)` with no `now`.
12. **C2(c)'s zero is reachable.** `section_typical` is
    `case((section_count >= TYPICAL_MIN_SAMPLE_SIZE, cast(round(percentile_cont(0.5)), Integer)),
    else_=None)` (`get_working_section_typical_times.py:97-100`), so five completed groups at
    zero seconds publish `0` with basis `section_wide`.
13. **C2(b)'s `None` is reachable.** Under `section_wide_uniform`, `reconcile_task_typicals`
    hands back `section_typical_worker_seconds` (`typical_filters.py:299`), which the statement
    NULLs below the floor — so a participating section with fewer than five groups selects
    `None` with basis `insufficient_sample`.
14. **§6.2's API is real.** `TypicalFilterSpec`, `SectionTypicalEvidence`,
    `TaskTypicalSelection`, `reconcile_task_typicals`, `apply_business_fallback` and `median` all
    exist in `typical_filters.py` with the stated signatures.
15. **All cited authorities resolve.** `owner_decisions.md` D14/D19/D22/D24; intention §6B, §7.4;
    graph node `projection-item-economics-task-price-scenario` (`.archgraph/architecture.yml:5911`).

**One observation on the doctrine files themselves, since they are being edited today.**
`plan-projection.md` is internally inconsistent about this handoff's `role` column: "Position and
dispatch" says the projection runs "under the **reviewer role** (its queue, its handoff table),
`round: 0`", while "Closing protocol" specifies the frontmatter as `role: projection`. The
dispatch prompt says `role: reviewer`, and the file lives in `handoffs/reviewer/`, so I used
`reviewer` — but the two halves of the doctrine cannot both be right, and the charter's artifact
map treats `role` as the folder's own column. Worth one line either way; not a plan finding.

## Refutations — things I set out to break and could not

1. **I expected phase 5 to rot `beyo_manager/routers/README.md`** — the hand-maintained,
   test-unread surface §9's C-1 lesson names. It does not. Measured: the price-scenario section
   (`:1759-1777`) is prose only and carries no field table, unlike production-time's and
   budget-allocations' (`:1673-1747`), which phase 4 had to extend field by field. Its one
   sentence ("…the task typical…") stays true. **No README task is owed.**
2. **I expected `test_production_time_contract.py`'s `"Fraction" not in source` guard to collide
   with task 4's `terminal=Fraction(0, 1)`.** It does not: the guard (`:9-14`) selects only
   service files containing `divide_production_budget`, and price-scenario is not one. Probe:
   read at source, `importing == {"get_task_budget_allocations", "get_task_production_time"}`.
3. **I expected the docs guard to name a living-doc file for the new wire key.** It does not —
   nothing under `docs/domains/item_economics/` mentions `is_estimated`, `typical_resolution` or
   the price-scenario payload, and `tests/unit/docs/test_item_economics_docs.py` (67 lines) does
   not read them. A green run there proves nothing about this phase (§9), so it is neither a task
   nor a criterion.
4. **I expected an exact key-set assertion on the `typical` block that §7.4's addition would
   trip.** There is none. The four whole-payload tests inject their own `typical` dict by
   monkeypatching `_typical_block` (`:578`, `:981`, `:1123`, `:1282`), and `serializers.py:364`
   echoes it unchanged, so they pass whatever they are given.
5. **I expected the eight fake-session `_typical_block` tests to change value under the shared
   ladder.** They do not. `apply_business_fallback([10, 11, None, None], terminal=Fraction(0, 1))`
   reproduces `test_c4`'s `41` (10 + 11 + 10 + 10, banker's rounding of 10.5) and
   `apply_business_fallback([0, 100], …)` reproduces `test_c3`'s `200` exactly. Only their arity
   and `_typical_row`'s column shape change (S13) — the arithmetic is preserved.

---

## Should the lint have caught it?

The lint ran five checks: sizing ≤ 8 · references resolve · counts derived · exact expected
outcomes · absence rows satisfiable. Its closing paragraph is right that it cannot see a weak
assertion or a guard that cannot fail. But **ten of these twenty blocking and should-fix
findings are mechanical**, and three of them are the checks it already runs, applied one field
further. (B6 is excluded from that count in fairness: the property it fails did not exist when
the lint ran.)

| finding | lint? | the check that would have caught it |
|---|---|---|
| **B1** | no — but a cheap companion exists | Perimeter-vs-guard collision needs the change applied and a run (§9's "a plan's files-expected-to-change is a claim, and a projection can MEASURE it"). **Mechanical companion:** grep the repository for occurrence-count assertions naming any file in the phase's §4 perimeter. One command, and it finds this class every time. |
| **B2** | **yes** | "A deletion task leaves no unused import": apply the stated edit and run `ruff check` on the file. One command. |
| **B3** | no | Semantic — an unnamed argument's effect on two mutants. |
| **B4** | **partly** | Extend "counts derived" to **mutation literals**: every number in a mutation's expected value names the fixture it was read from. `61` and `600` name none, and their only home in the repository is a hand-built unit object. |
| **B5** | **yes** | "Every criterion's observable is a key that exists in the payload it names" — the price-scenario payload is enumerable from `serialize_task_price_scenario`. |
| **B6** | not then — **yes from the next run** | Manifest property **5** did not exist when the lint ran this morning; it does now. The check is mechanical and cheap: every criterion row has a non-empty trace cell, and every declared ledger entry the phase claims is served by ≥1 row. Add it to the lint's list, and add its precondition — refuse to lint a plan whose intention has no measurement ledger. |
| **S1** | **yes** | Same check as B4/B5. `3` and `"icat_chair"` are typed; `test_c8` asserts `2` and `[category_id]` in the same directory. |
| **S2** | **yes** | "References resolve" applied to **fixtures**, not only paths. The lint verified 4 paths and 11 filenames; it never asked whether the seeds the criteria describe exist. |
| **S3** | **yes — and it is the check that already fired** | The lint caught `>= 1` in row (b)'s *assertion* and left the identical `≥1` in row (c)'s *fixture description*. Extend "exact expected outcomes" to fixture cardinalities. |
| **S4** | no | Semantic. |
| **S5** | **yes** | Charter rule 11 already requires file + definition-vs-call-site; "the named site exists and the named edit is applicable there" is checkable for a call-site claim. |
| **S6** | no | The projection's work, as the lint says. |
| **S7** | **partly** | "Absence rows are satisfiable" applied to the **presence** form: run the row's own term scan against the function's current source. `TYPICAL_MIN_SAMPLE_SIZE` is in it, at `:180`. |
| **S8** | **yes** | The lint re-derived C7's allowlist from the tree **as it stands** rather than the tree **after the plan's own task 0**, which sits three sections above the row it corrected. "Run an absence sweep against the post-task tree" is the fix. |
| **S9** | **yes** | "If an absence row's root changes, re-derive its evidence scope from master plan §10." One lookup, and §10 names this row. |
| **S10** | **yes** | Manifest item 1: every acceptance criterion has a row id. Task 0's has none, which is also why the mutation count excludes it. |
| **S11** | **yes** (the missing row) / no (the premise) | Same check as S10, applied to a Read-first instruction that is really an obligation. |
| **S12** | **yes** | "Every standing instruction that names this plan by number has been applied" — master plan §8 says *"Plans 5 and 6 carry the same ambiguous sentence — fix it there before dispatch"*. A grep for `plan 5` / `plans 5 and 6` across the master plan. |
| **S13** | **partly** | "A signature change enumerates its call sites" is mechanical once task 2's choice is made; the choice is not. |
| **S14** | **yes** | "Every verb in a task is true of the code it names": task 1 says the clock *moves*, and the file it names has no clock. One grep over the phase's own perimeter for the mechanism each task claims to change. |
| **N1–N5** | no | |

**And one finding against the lint's own arithmetic.** The entry records "**PASS** — 12 named
mutation markers across C1–C7, counted from the criteria rather than carried from anywhere."
Counted from the criteria: C1 **2**, C2 **4**, C3 **2**, C4 **2**, C5 **2**, C6 **1**, C7 **1**
= **14**, plus C7's required planted-defect probe and §2's N1 probe, which are ledger rows the
round owes and the count omits. This is the check that certifies counts are derived, and it is
the shape §9 records as *"a mutation count is re-derived from the plan after every criterion
exists, never carried from the finding that added one"* — the same defect the lint was
introduced to end, in the lint's own row. **Enforcement worth adopting:** the lint prints the
per-criterion summands, so the arithmetic is auditable in one glance rather than asserted.

**Net read on the new contract.** The lint is worth keeping: both defects it caught were real,
its three measured counts hold up under independent measurement, and it caught them before a
session opened. But it passed a plan with two blocking defects that a single command each would
have found (B1's grep, B2's `ruff check`), and its "counts derived" row is itself underived.
The checklist's reach, not the coordinator's care, is what to extend.

---

## Tree projected against

```
9bad5a3 docs(narrow-typicals): dispatch the phase-5 projection — the first prompt under the new contract
```

`git status --porcelain -- app/` empty at session start and at session end.
Anything under `.archgraph/` is the owner's live work and was not read for state, diffed, or
gated on.

## Write perimeter

- **Documents written:** this handoff only.
- **Production code:** none. Two probes applied and reverted (below).
- **Tests, goldens, plans, master plan:** untouched. No plan or criterion was edited — findings
  route through the coordinator.
- **Tool-recorded state (archgraph):** none. No `archgraph_*` call was made this session; the
  node was read from `.archgraph/architecture.yml` on disk, read-only.
- **Database:** two runs of one existing integration file, which owns its own teardown. No seed
  or fixture was written by this session.

## Mutation-probe declaration

| # | file | md5 before | md5 after revert | probe | result |
|---|---|---|---|---|---|
| P1 | `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | `8a261d763b3a6414554c84083f1a7396` | `8a261d763b3a6414554c84083f1a7396` | Task 3 applied faithfully: import `participating_sections`, drop `_step_state_is_excluded`, filter groups by the shared set. Landing asserted by `inspect.getsource(module._typical_block)` — `participating_sections(steps)` present, `_step_state_is_excluded` absent — **before** the run. | `test_narrowed_task_economics.py` **16 passed → 1 failed / 15 passed**; the failure is `test_c13c_excluded_state_logic_has_one_shared_production_owner` at `:542`, `assert 0 == 2`. **B1.** |
| P2 | `app/beyo_manager/domain/item_economics/budget_division.py` | `4ef43bc25414f62ca694a86b4e362eb7` | `4ef43bc25414f62ca694a86b4e362eb7` | Task 0 applied as written: delete `_median = median` and its comment, nothing else. | `ruff check` on the file **1 error → 2 errors**; the new one is `:19:5 F401 … median imported but unused`. **B2.** |

Command for both runs, per master plan §10:
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest <path> -n 0 -p no:randomly`.
**L4 runs: 0** — nothing is implemented, and no hypothesis this session raised was
repository-wide. Both probes ran at L1 (one file), which is where their hypotheses live.
