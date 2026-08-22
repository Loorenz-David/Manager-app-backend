---
plan: plan_1
role: reviewer
round: 1
date: 2026-08-22
verdict: CHANGES_REQUESTED
actor: Opus 5
---

# Plan 1 review handoff — full review of rounds 1 and 2

The typicals engine itself is right. I re-derived the resolution ladder, the
reconciliation quantifier, the evidence predicates, the fallback and the median
against the intention and found no wrong behaviour at any site I checked; the
pre-refactor SQL snapshot is genuinely pre-refactor and genuinely a literal, and
the constants move is invisible to all six import sites. What does not hold is the
test layer over `reconcile_task_typicals`. Three named contracts — the task-level
non-narrowing short-circuit, and the two fields a participating section publishes
when the task settles on a section-wide basis — have **no test that can fail**, and
I measured that by mutation: three separate defects, each one a false statement on
the wire in phase 4, leave the phase suite at 33 passed. Two of the three are the
same shape as the coordinator's own F1/F3 findings, one level up, in the branch the
consumption pass did not reach.

Verdict: **CHANGES_REQUESTED** — two blocking, three should-fix, four recorded.

## ⚠ OWNER DECISIONS REQUIRED (0)

Zero cards. Nothing in this round needs an owner answer; every finding is a test the
implementer adds and a limitation the coordinator records.

## 1. Findings

### Blocking

**B1 — C8 row (g) is absent, and its mechanism (§3B B1 at task scope) has no test
that can fail.**

`plans/plan_1.md` §6 C8 enumerates row (g), "**non-narrowing** spec → `section_wide_uniform`,
`applied_filter is None`", as a row distinct from row (i) (`spec=None`).
`app/tests/unit/domain/item_economics/test_typical_filters.py:205-216` implements only
row (i): `reconcile_task_typicals` is never called with a non-`None`, non-narrowing spec
anywhere in the phase. `reconcile_task_typicals` carries its **own** copy of the
narrowing decision (`typical_filters.py:265-269`), separate from
`resolve_section_typical`'s, and that copy is what row (g) exists to constrain.

*Measured, L1 whole-file (both sides):*
mutate `typical_filters.py:266` (definition), `effective_spec.is_narrowing` → `(spec is not None)`.
- Contract, on `reconcile({"a": E(600, 7, 900, 61)}, TypicalFilterSpec(), {"a"}, {"a"})`:
  `task_typical_basis = "section_wide_uniform"`, `applied_filter = None`,
  a → `(900, "section_wide", 61)`.
- Mutation, same call: `task_typical_basis = "item_narrowed_uniform"`,
  `applied_filter = None` (unchanged), a → `(600, "item_narrowed", 7)`.
- Suite: **33 passed under the mutation** — no row bites. Row (i) does not bite because
  `spec is None` is false there by construction.

Intention §3B B1 names this exact output as the defect it forbids: "`task_typical_basis
= "item_narrowed_uniform"` — for a task whose `applied_filter` is `null`. Both are false
statements on the wire." It is one of the five Critical-ranked mechanisms (master plan §9,
the settled-basis guard).

*Fix:* add C8 row (g) as written — `spec=TypicalFilterSpec()` (not `None`), every
participant usable-narrowed, asserting `task_typical_basis == "section_wide_uniform"`,
`applied_filter is None`, and each participant's tuple. Record the mutation above as the
row's named mutation; row (i) is its recorded non-biting control.

---

**B2 — C8's per-section tuple assertions are not implemented, so the participating
non-uniform branch may publish the narrowed value and the narrowed count under a
`section_wide` basis.**

`plans/plan_1.md` §6 C8 closes: "*Both sides* are exact-literal assertions on the
`task_typical_basis` **string** and on each section's `(typical_worker_seconds,
typical_basis, sample_count, participates)` tuple (projection L20 adds the fourth
element)." In the tree, only the ghost row (`test_typical_filters.py:141-149`) gets
per-section assertions. Rows (a), (b), (c), (e), (f) and (j) assert the task basis string
and, at most, one excluded section's `typical_basis`. **No test anywhere asserts what a
*participating* section publishes when the task basis is `section_wide_uniform`** —
the branch at `typical_filters.py:285-297`.

*Measured, L1 whole-file, two mutants (both sides), on C8 row (b)'s own fixture
(`test_typical_filters.py:152-162`):*

| mutant (`typical_filters.py`, `reconcile_task_typicals` definition) | contract | mutation | suite |
|---|---|---|---|
| line 288: `section_typical_worker_seconds` → `narrowed_typical_worker_seconds` | zero → `(900, section_wide, 61)`, usable → `(1200, section_wide, 61)` | zero → `(0, section_wide, 61)`, usable → `(600, section_wide, 61)` | **33 passed** |
| line 296: `section_sample_count` → `narrowed_sample_count` | both `sample_count = 61` | zero → `5`, usable → `7` | **33 passed** |

The first mutant is §3.6's naming rule and §3B B2 violated directly — a value drawn from
the narrowed population, labelled `section_wide`, and in row (b)'s case the value is
`0`, i.e. the D25 defect the whole `has_usable_narrowed` predicate exists to prevent,
re-entering one layer down. The second is §3B B3 violated — B3 states the participating
`sample_count` rule *precisely because* participating sections bypass
`resolve_section_typical`, and this is the code it governs. This is the coordinator's
F3 (a row that discloses the wrong seconds) at task scope rather than ghost scope.

*Fix:* implement C8's closing sentence — for rows (a), (b), (e), (f), (j) at minimum,
assert each participating section's full `(typical_worker_seconds, typical_basis,
sample_count, participates)` tuple as an exact literal, and register the two mutants above
as C8's named mutations (viii) and (ix), one per sub-check.

### Should-fix

**S1 — C7 is not total over the predicates its non-narrowing branch reads, and row (m)'s
`SelectedTypical` identity is asserted as a three-field projection.**

Two sub-findings, one criterion.

(a) All thirteen C7 rows are present and every expected value is correct — I checked each
against the code path. But **no row can distinguish which predicate the non-narrowing
branch consults.** Rows (h) and (m) set the narrowed columns equal to the section columns
by construction; row (i) is asymmetric in *values* but both predicates are `False`.
*Measured:* mutate `typical_filters.py:172` (definition), `evidence.has_section` →
`evidence.has_narrowed`. Contract on non-narrowing / narrowed `(61, 600)` / section
`(3, None)`: `("insufficient_sample", None, 3)`. Mutation: `("section_wide", None, 3)`.
Suite: **33 passed**. Add one row with that shape.

(b) C7 row (m) requires "byte-identical `SelectedTypical` to row (h)'s, asserted as two
literal rows". `test_typical_filters.py:126` asserts a 3-tuple
`(typical_basis, typical_worker_seconds, sample_count)`; `participates` and `evidence`
are never asserted in C7. *Measured:* set `participates` to `True` in both returns of the
non-narrowing branch (`typical_filters.py:178,186`) — **33 passed**. The field survives
only because `reconcile_task_typicals` overwrites it with `replace(..., participates=False)`
at the sole call site (`typical_filters.py:299-306`); a phase-2+ consumer calling
`resolve_section_typical` directly inherits an unconstrained field. Assert the whole
dataclass on rows (h) and (m).

**S2 — the parser silently mis-reads a bare `str` for a repeatable family, and its error
boundary is asymmetric across families.**

`typical_filters.py:78-82`, `_optional_values`: `frozenset(str(v) for v in raw)`. A `str`
*is* a `Sequence[str]`, so §3C's grammar does not exclude it, and the result is silent.
Measured, no file mutation:

| input | result |
|---|---|
| `{"item_category_ids": "cat_a"}` | `frozenset({'c','a','t','_'})` — a narrowing spec over a population of zero items |
| `{"designers": "dsg_a"}` | `frozenset({'d','s','g','_','a'})` |
| `{"major_categories": "wood"}` | `ValidationError` |
| `{"item_category_ids": 5}` | bare `TypeError` (HTTP 500) |
| `{"major_categories": 5}` | `ValidationError` (HTTP 422) |

The first two are HC-3's shape reached through the parser: a spec that narrows to nothing,
which `BROADEN_TO_SECTION` then answers section-wide with no signal. The last two are the
§3C boundary applied to one family and not the others. Nothing ships broken today — the
route is deferred (§9) and there is no caller — but §3C binds this parser now, and phase 2
inherits it as a public contract. *Fix:* reject a bare `str` (and any non-sequence) in
`_optional_values` with `ValidationError`, and add C14 rows for both.

**S3 — the C15 snapshot guards SQL *structure* only; every bound value is invisible to it,
and that limitation is nowhere recorded.**

The snapshot is compiled without `literal_binds`, which is correct (with it the assertion
becomes a clock race, and that is why the plan says so). The consequence is that the
percentile, the sample floor, the 90-day cutoff, the step-state filter and the workspace id
all appear as `%(...)s` placeholders and cannot move the frozen string.

*Measured, L1:* mutate `get_working_section_typical_times.py:48` (definition),
`func.percentile_cont(0.5)` → `func.percentile_cont(0.6)`. Contract: compiled string equals
the snapshot. Mutation: compiled string **still** equals the snapshot — `1 passed`. Control,
a structural mutant: `grouped_steps.c.latest_closed_at >= cutoff` → `> cutoff` — `1 failed`.

So "the typical is a median" is not guarded by C15, and neither is "the population is
COMPLETED steps". `TYPICAL_WINDOW_DAYS` and `TYPICAL_MIN_SAMPLE_SIZE` are separately
guarded by C16(b); the percentile and the state filter are guarded by nothing in this
phase. This is not a phase-1 implementation defect — it is a scope limitation of HC-4's
instrument that plan 2 rests on. *Fix:* record it in `plans/plan_2.md` beside the inherited
C15 (and/or master plan §9's snapshot rule) as a stated boundary, so phase 2 does not read
a green C15 as "the no-spec branch is unchanged" when it means "the no-spec branch's
*shape* is unchanged".

### Recorded (notes)

**N1 — C4(c) and C17 are session greps, not tests.** Charter rule 1: acceptance criteria
are met by automated tests, never manual commands; the exemption is environment-lifecycle
checks only, and these are not. Nothing in the committed suite goes red if a later phase
adds `hashlib` or a `models.tables` import under `app/beyo_manager/domain/item_economics/`.
I re-ran both from the repository root and confirm the measurements: C17 returns **nothing**
(clean); C4(c) returns **exactly one** hit,
`app/beyo_manager/domain/item_economics/serializers.py:351 "config_fingerprint"`,
pre-existing and unrelated to spec identity — the round-2 handoff states this correctly and
the round-1 claim ("grep is empty") was wrong, as round 2 already recorded. Pressure on
C17's root is lower than the plan assumed — phase 2's `_typical_item_filter.py` lands under
`services/queries/working_sections/`, outside the root — but phases 4 and 5 do touch this
package. *Lesson for the plans:* an absence criterion in this project should ship as a
committed test that walks the package and asserts the term set, priced at a few lines.

**N2 — C8 row (c) is absent.** "A: narrowed count 3 (below floor); B: usable →
`section_wide_uniform`" has no two-participant fixture. It is the recorded non-biting
control for C8 mutation (ii) (rule 12 bookkeeping), not a detection gap — mutation (ii)
still bites on row (b) (`test_typical_filters.py:152-162`), which I verified by reading the
fixture: `zero` has `narrowed_sample_count = 5 ≥ floor`, so `has_narrowed` is `True` and the
quantifier flips.

**N3 — C8 mutation (vii) bites on a different row than the plan names.** The plan says rows
(e) and (f) flip on `participates=True` for every section; in the tree, `participates` is
asserted only in row (d)'s test (`test_typical_filters.py:174`) and in the ghost row
(`:149`). The mechanism is guarded; the ledger's row attribution is not what the tree shows.
Fold the correction into C8 rather than adding a row.

**N4 — one C8 fixture has two independent sufficient causes.**
`test_reconciliation_uses_uniform_usable_narrowed_basis_and_materializes_missing_rows`
(`:129-149`) reaches `section_wide_uniform` both because `b`'s median is `0` and because
`ghost` is missing. Harmless: the single-cause twin
`test_missing_participant_row_forces_section_wide_uniform_basis` (`:219-226`) exists and is
what makes C8 mutation (vi) bite. Worth naming so the pair is not collapsed later.

**N5 — C15's mutation prose cites the wrong rendering.** The plan says the mutation makes
the string lose `working_sections.is_deleted = false`; the compiled text is
`working_sections.is_deleted IS false`. Prose only.

## 2. Areas checked with nothing found

- **Snapshot honesty (depth area 1).** `git diff dc76db8 8feae38 --
  …/get_working_section_typical_times.py` is **empty** — the statement is byte-identical to
  the D23 baseline, so the frozen string is genuinely pre-refactor. The committed file is
  1336 bytes, last byte `0x65` (`e`, end of `working_sections.name`), no trailing newline —
  measured, matching the round-2 correction. On the circularity: the shared helper
  `compile_typical_times_sql` does mean the test can only compare the file against the same
  incantation, but the committed literal breaks it and I read it — it is PostgreSQL-dialect
  output with every value bound (`%(latest_closed_at_1)s`, `%(param_1)s`), contains no
  literal date, and is identical when compiled for a different workspace id (measured). So
  K5's `now`-independence is measured, not merely reasoned, and the incantation frozen into
  the file is the right one. The helper is the correct call; its residual risk is S3, not
  circularity.
- **The `_median` bridge (depth area 5).** Sound. `typical_filters` imports
  `typical_constants`, `domain.items.enums` and `errors.validation` and never imports
  `budget_division`, so the direction `typical_constants ← typical_filters ← budget_division`
  holds and no cycle exists. The sole cross-module importer of the private name is
  `services/queries/item_economics/get_task_price_scenario.py:13` (I swept
  `app/beyo_manager/` for `_median`; every other hit is `from statistics import median as
  _median` in unrelated analytics modules). The removal is written where phase 5 will read
  it: `plans/plan_5.md` task 0, with a criterion pairing the absence of `_median` in
  `budget_division` with a zero-collection-error suite.
- **The inlined second copy of the basis/count decision (depth area 3).** Contained to one
  branch (`typical_filters.py:285-297`) and correct: it agrees with
  `resolve_section_typical` on §3B B3 — `insufficient_sample` carries `section_sample_count`
  in both — and its divergence (ignoring `has_usable_narrowed` for participating sections) is
  exactly what the uniform-basis rule requires. `applied_filter` is carried by identity:
  `effective_spec is spec` whenever `spec is not None`, so C8 row (j)'s `is spec` holds.
  The defect here is the missing *tests* (B2), not the code.
- **The parser's enum conversion and error boundary** beyond S2: `ValidationError` derives
  from `DomainError(Exception)`, not from `ValueError`, so the `except ValueError` in
  `parse_spec_from_query_params` does not swallow and re-label the `major_categories`
  rejection; row (l)'s message survives. All fourteen C14 rows (a)–(n) are present and
  correct, including the three round-2 additions.
- **Inert mutations (depth area 7), spot-checked by variation rather than reproduction.**
  §3B B1's short-circuit at section scope: I mutated it in a *different* shape than the
  ledger's — `if not spec.is_narrowing:` → `if not spec.is_narrowing and not
  evidence.has_usable_narrowed:` — and got **2 failed** (grid rows (h) and (m)), so C7
  mutation (ii)'s claim survives an independent shape. C15's structural mutation likewise
  reddens (S3's control). C6's five mutations, C11's three, C13's three, C14's four, C18's
  two and C2's three each have a fixture row in the tree that discriminates them; I verified
  by re-deriving each row's value from the code rather than re-running the implementer's
  mutants.
- **C6 row independence.** All eight plan rows are covered by the five fixtures at
  `test_typical_filters.py:87-99`, and each row's outcome has exactly one cause: row (a)
  fails `has_narrowed` on count alone (median `600` is fine), row (c) fails usability on the
  zero median alone (count is at the floor), row (e) fails on `None` alone.
- **C16 and the constants move.** Identity holds for all three names,
  `budget_division.__all__` still exports them (`budget_division.py:409-419`), and the diff
  shows no other executable change beyond the `median` rename, `participating_sections`, and
  the alias.
- **Perimeters.** Every commit matches its declared write perimeter: `a9afb8b` = the seven
  app paths + master plan + plan (9 files); `8ff6ecc` = the alias repair + `.archgraph/
  architecture.yml` + handoff + plan; `dea0272`/`8edd3c3` = docs only; `8feae38` = one test
  file + master plan + plan. The round-2 "tests only" claim is measured: `git diff 8edd3c3
  8feae38 -- app/beyo_manager/` is empty. No file changed outside a declared perimeter.
- **Architecture graph.** The delta at `8ff6ecc` is the one node
  (`domain-item-economics-typical-filters`) and one `contains` relationship the handoff
  declares, left pending human review. I neither promoted, rejected nor edited anything.

## 3. Criteria verdict table

| Criterion | Verdict |
|---|---|
| C1 | verified |
| C2 | verified |
| C3 | verified |
| C4 (a)(b) | verified |
| C4 (c) | accepted-on-ledger — re-measured myself; form is a grep, see N1 |
| C5 | verified (real `Item` instances) |
| C6 | verified — all eight rows, all five mutations discriminated |
| C7 | **partially satisfied** — 13/13 rows present and correct; predicate-totality gap and row (m) projection, see S1 |
| C8 | **not satisfied** — row (g) absent (B1); row (c) absent (N2); the mandated per-section tuple assertions absent (B2) |
| C9 | verified |
| C10 | verified (round-2 fix lands the seconds and all four evidence fields) |
| C11 | verified |
| C12 | verified |
| C13 | verified (real `TaskStep` instances) |
| C14 | verified — all fourteen rows; contract hole at the grammar edge, see S2 |
| C15 | verified, with a recorded scope limitation — see S3 |
| C16 | verified |
| C17 | accepted-on-ledger — re-measured clean; form is a grep, see N1 |
| C18 | verified |

## 4. My evidence

**Tree identity.** HEAD `fb1884a` — docs-only above the code checkpoint `8feae38`;
`git diff 8feae38 fb1884a -- app/` is **empty** (measured), so the application tree under
review is exactly `8feae38`. `git status --porcelain` = `?? .archgraph/contexts/` only —
the same untracked session-context directory present at every stamp in this phase, on no
import path; no tracked modification at any point, before or after my probes.

**L4 runs: 1.** Authorization line, written before the run: *hypothesis — no datetime
handling in this tree, the 90-day typicals cutoff above all, behaves differently under
`TZ=UTC` than under the host's `+0200`; L4 by construction because a `TZ` change is a
repository-wide condition, not a site; variation over the cited round-2 stamp is the clock
condition, never run in this phase; master plan §10 requires it and no session had
discharged it.*

- Command: `TZ=UTC PYTHONPATH=. pytest -m 'not e2e'`, from `backend/app/`, six xdist
  workers per `pytest.ini`.
- Precondition: Redis verified reachable at `settings.redis_url` = `redis://localhost:6379/0`
  (`+PONG`) **before** the run, so 21 vs 23 is a real reading, not the §10 diagnostic.
- Result: **2609 passed / 21 failed / 0 collection errors**, 51.19 s.
- Against the published 21-ID comparator
  (`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7):
  IDs added **∅**, IDs removed **∅**.
- Conclusion: master plan §10's two-`TZ` obligation is discharged for this phase. The
  round-2 stamp (`8feae38`, 2609/21/0, ∅/∅) was **consumed by citation, not re-run** — its
  tree identity matches mine.

**L1 mutation probes** — seven, all whole-file, never `-k`, each applied to a named
definition, run, and reverted before the next. Phase files:
`tests/unit/domain/item_economics/test_typical_filters.py`,
`…/test_participating_sections.py`,
`tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`.
Command: `PYTHONPATH=. .venv/bin/python -m pytest -p no:randomly -n 0 <the three files> -q`.
Baseline: **33 passed**.

| # | site (file · definition) | contract side | mutation side | suite | finding |
|---|---|---|---|---|---|
| M1 | `typical_filters.py:288` · `reconcile_task_typicals` | zero `(900, section_wide, 61)`, usable `(1200, section_wide, 61)` | zero `(0, section_wide, 61)`, usable `(600, section_wide, 61)` | 33 passed | B2 |
| M2 | `typical_filters.py:296` · `reconcile_task_typicals` | both `sample_count 61` | zero `5`, usable `7` | 33 passed | B2 |
| M3 | `typical_filters.py:266` · `reconcile_task_typicals` | `section_wide_uniform`, a `(900, section_wide, 61)` | `item_narrowed_uniform`, a `(600, item_narrowed, 7)`, `applied_filter` still `None` | 33 passed | B1 |
| M4 | `typical_filters.py:178,186` · `resolve_section_typical` | `participates False` | `participates True` | 33 passed | S1(b) |
| M5 | `typical_filters.py:172` · `resolve_section_typical` | `(insufficient_sample, None, 3)` | `(section_wide, None, 3)` | 33 passed | S1(a) |
| M6 | `typical_filters.py:171` · `resolve_section_typical` (variation on the ledger's C7(ii)) | rows (h),(m) `section_wide` | rows (h),(m) `item_narrowed` | **2 failed** | ledger claim holds |
| M7 | `get_working_section_typical_times.py:48` · `typical_times_statement` | compiled == snapshot | compiled == snapshot (percentile is bound) | 1 passed | S3 |
| M7′ | same · control, line 46 `>=` → `>` | compiled == snapshot | compiled ≠ snapshot | **1 failed** | S3 control |

Non-mutating behaviour probes: the parser table in S2 (nine off-grammar inputs); snapshot
independence (`compiled == snapshot` True, workspace-id-independent True, contains a bound
cutoff parameter True, contains a literal date False, 1336 bytes); the two absence greps in N1.

**Mutation-probe declaration.** Files touched by probes, applied and reverted:
`app/beyo_manager/domain/item_economics/typical_filters.py` (M1–M6) and
`app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
(M7, M7′). Both verified byte-identical after reverting — `typical_filters.py` sha256
`3de15a9cea72f779f29bf7fa01f86c9a886656decb2b3d090ef29f98e66f5de1`, unchanged from the
pre-probe checksum, and `git status --porcelain` shows no tracked modification. No database
or state side effects: every probe ran unit-only; the `TZ=UTC` L4 used the per-process
disposable template databases the suite creates and drops, and no probe ran concurrently
with it.

## 5. Write perimeter

- `docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/reviewer/20260822_plan1_review_handoff.md` — this file.

Nothing else. `git status --porcelain` at close: `?? .archgraph/contexts/` (pre-existing,
untracked, not mine).

**Declared divergence from `plan-reviewer.md` (charter rule 14).** The skill's closing
protocol has the reviewer append findings to the plan file's Review log and update the
tracker row. This prompt forbids editing the plan, the master plan and the intention, and
states that the Review log line is written by the coordinator at the fold. I followed the
prompt: neither document was touched. The coordinator owns folding §1 of this handoff into
`plans/plan_1.md` §8 and moving the tracker row to `CHANGES_REQUESTED`.

## 6. Lessons for the plans

1. **A criterion's closing sentence is a criterion.** C8's "*Both sides* are exact-literal
   assertions … on each section's tuple" carried three of this round's findings and was the
   one line no session implemented. When a criterion states its assertion *shape* in prose
   after its row table, that prose needs its own enumerated mutation, or it lapses silently
   — the row table looks complete and the assertions are thinner than the rows.
2. **A row that differs from another only in a field the assertion projects away is a
   duplicate.** C7 rows (h) and (m) are meant to prove policy-independence via a
   byte-identical `SelectedTypical`; the test asserts three of six fields, so the proof is
   of a projection. Criteria that say "identical object" should say which fields the
   assertion compares.
3. **A branch reached only by a short-circuit needs a row where its two candidate
   predicates disagree.** Rows (h)/(m) set narrowed == section by construction and row (i)
   sets both predicates `False`; neither can tell `has_section` from `has_narrowed`. The
   generalisable rule: when a criterion proves "this branch never reads X", at least one row
   must make X's value differ from the value the branch does read.
4. **Absence criteria in this project should ship as tests.** C4(c) and C17 are the two
   criteria satisfied by a command in a session; both re-measured correct, and neither leaves
   anything behind that can go red. Charter rule 1 already says this; the plans wrote the
   greps anyway because the projection wrote them that way.
5. **A snapshot compiled without `literal_binds` freezes structure, not values.** Worth
   stating once in the master plan: it is the right trade (the alternative is a clock race),
   but the instrument's blind spot — the percentile, the state filter — should be written
   down where phase 2 reads C15, not rediscovered.

## 7. Carry-forward dispositions

Not applicable at this verdict — the notes route with the fix cycle. If the coordinator
approves the phase with N1 open, its destination is a plan that touches
`domain/item_economics/` again: **plan 4** (serializers) is the natural home for a committed
package-purity guard covering both C4(c) and C17. S3's recording destination is **plan 2**,
beside the inherited C15.
