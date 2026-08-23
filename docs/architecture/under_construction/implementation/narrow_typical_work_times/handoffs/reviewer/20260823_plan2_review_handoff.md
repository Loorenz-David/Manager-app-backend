---
plan: plan_2
role: reviewer
round: 1
date: 2026-08-23
actor: Opus 5
verdict: CHANGES_REQUESTED
---

# Plan 2 review handoff — `typical_times_statement` extended for K specs

**Verdict: `CHANGES_REQUESTED`.** 0 blocking · 5 should-fix · 5 recorded · 2 owner cards — **card 1 ANSWERED 2026-08-23 (phase 3), card 2 open**.

**The production code is correct and I found no defect in it.** The K-spec statement
implements §4A K2/K3/K4 exactly, the no-spec branch is byte-identical, the fan-out-free
claim holds at the database (measured, not read off the model), and the §12 conditional
acceptance is met. The round is owed for **instruments, not behaviour**: three separate
guards cannot fail. I deleted the entire `K ≥ 1` population definition — four independent
filters, one at a time — and the phase's full L2 bite set stayed green (62 passed) every
time. I mis-keyed the `narrowed_typical_worker_seconds` column across spec indices and
nothing reddened, while the same mutation on the count column reddened three tests. And
C0's bare-string enum row passes with its own guard deleted, which is precisely the defect
that row exists to close.

Each fix is small: four seeded rows, one test, one `match=` string, one reconciliation,
one paragraph.

---

## ⚠ OWNER DECISIONS REQUIRED (1 open, 1 answered)

### Card 1 — the database rule nobody tests — **ANSWERED 2026-08-23: phase 3**

> **Owner ruling, 2026-08-23.** *"Card 1 will be executed by phase 3."* The criterion row
> is bought in phase 3, the phase where the first real surface reads the narrowed number.
> Recommendation followed. Coordinator: fold as an owner decision and add the row to
> `plans/plan_3.md` §6 — see the carry-forward table for the row's exact shape.

**Question.** Buy the one test for the "one active primary item per task" database rule
now in phase 2, or when the first surface actually uses item-narrowed typicals (phase 3)?

**Story.** A task carries one primary item — the chair being reupholstered — and that is
what decides which history a typical is measured over. Two independent guards refuse a
second one: `add_item_to_task` raises `ConflictError("Task already has an active primary
item.")`, and the database index is the race backstop. **Neither has a test** — no test
file in the repo references `add_item_to_task` at all. If a future database
change quietly removes that rule, a task with two primaries would be counted twice, and a
section's "typical time" would drift upward with no error anywhere — you would simply
start quoting longer jobs than the history supports.

**Branches.**
- *Now (phase 2):* ~8 lines, in the phase whose central join depends on the rule.
- *Phase 3:* same cost, one phase later, and phase 3 is the first phase where a real
  surface reads the narrowed number.

**Recommendation.** Phase 3 — I read the rule out of the live migrated database this
session and it is present and correct, so nothing can ship wrong from phase 2.

**On silence.** It is routed to phase 3 as a carry-forward with a named row; the gate holds.

**Trace.** plan 2 §6A "Recorded, not fixed here" (L33/R10) · §3A C5 · plan 3.

### Card 2 — the architecture graph queue

**Question.** May the graph entries this pipeline has recorded be adjudicated, and may the
one with a wrong line reference be rejected so it can be re-recorded correctly?

**Story.** The graph is the map of the system agents read before touching it. Seven
entries from phases 1 and 2 are sitting unreviewed, and one of them points at lines
199–224 of a test file where that test no longer lives — a later round moved it to 232.
An agent reading the map to find the test that proves the new query's row shape lands on a
different test. Only you can approve, reject or edit these entries; no agent may.

**Branches.**
- *Adjudicate now:* the queue clears and the wrong reference is re-recorded correctly.
- *Leave:* the queue grows across phases 3–6 and the wrong reference stays.

**Recommendation.** Reject the one stale entry so the fix round re-records it; the other
six are accurate as written.

**On silence.** Nothing is changed by any agent; the gate holds.

**Trace.** master plan §8 (tool protocols) · plan 2 round-1 graph delta (`d07028b`).

---

## Review history and scope

Two implementation rounds precede this review. Round 1 (`d07028b`) built the phase
tests-first; the coordinator's consumption round sent it back before it reached me for
seven unrun named mutations and two fixtures that could not fail. Round 2 (`a371e8e`)
closed all seventeen items **without touching production code** — I re-measured that
myself rather than accepting it: `git diff d5731c3 HEAD -- app/beyo_manager/` returns
nothing.

This is therefore a **full first review** of the phase, not a delta re-review.

---

## Findings

### Should-fix

#### S1 — the `K ≥ 1` branch's population definition is guarded by nothing

`typical_times_statement` and `_no_spec_typical_times_statement` each declare their **own**
`grouped_steps` subquery, restating the same four filters (`workspace_id`, `state ==
COMPLETED`, `is_deleted IS FALSE`, `recorded_time_marked_wrong IS FALSE`) and the same
90-day `qualifying` cutoff. C1 freezes the no-spec branch's SQL *shape*. **Nothing
constrains the `K ≥ 1` branch's copy at all.**

C5 looks like the guard — it asserts `section_sample_count == 20` at every `spec_index`
*and* against the `K == 0` call's `sample_count`, a genuine cross-branch equality. But
every fixture in `test_typical_times_narrowing.py` seeds only steps that are `COMPLETED`,
not deleted, not marked wrong, and closed one day ago. There is nothing for the equality
to discriminate.

**Measured — four probes, one per sub-check, L2, tree `90c2490` clean, contract side the
round-2 cited baseline (62 passed / 1 skipped):**

| mutation (definition, `get_working_section_typical_times.py`, `K ≥ 1` branch only) | result |
|---|---|
| delete `TaskStep.recorded_time_marked_wrong.is_(False)` (`:52`) | **62 passed, 1 skipped — no bite** |
| delete `TaskStep.state == TaskStepStateEnum.COMPLETED` (`:51`) | **62 passed, 1 skipped — no bite** |
| delete `TaskStep.is_deleted.is_(False)` (`:52`) | **62 passed, 1 skipped — no bite** |
| `qualifying = latest_closed_at >= cutoff` → `true()` (`:94`) | **62 passed, 1 skipped — no bite** |

Command each time:
`BEYO_TEST_SLOT=<slot> PYTHONPATH=. pytest tests/unit/services/queries/working_sections/ tests/integration/services/queries/working_sections/`

**Authority.** plan 2 §6 C5 ("equal to the `K == 0` call's `sample_count` for the same
section"); master plan §9 rule 2's companion; §9 "A uniform fixture is an inert fixture";
§9 "Name the criterion that owns a hazard, then check that it can *see* the hazard's
observable" — the same rule this phase earned five days' work ago, firing on the same
criterion from the other side.

**What breaks observably.** After phases 3–4 wire the narrowing consumers, the two
branches answer the same product question through different code. Any later edit to one
branch's population — a new step state, a soft-delete rule change, a window change —
applies to `/working-sections/typical-times` and not to the task-scoped surfaces, or the
reverse. The same section then reports two different typicals with no error and no red
test. That is HC-2's shape reached through the duplicated builder.

**Correction.** Add discriminating rows to C5's fixture: one step with
`recorded_time_marked_wrong=True`, one `is_deleted=True`, one non-`COMPLETED`, and one
`closed_at` outside the 90-day window — so that `section_sample_count == 20` at every index
*and* `== base.sample_count` becomes a real divergence assertion. Name the four mutations
above, one per sub-check, with their bite ids.

#### S2 — `narrowed_typical_worker_seconds` is never asserted at any `spec_index ≥ 1`

For `K ≥ 2` both narrowed columns are built as
`coalesce(case(index == 0, …), case(index == 1, …), …)`. The **count** column is pinned per
index; the **value** column is not. Across the whole file
`narrowed_typical_worker_seconds` is asserted non-`None` only at `spec_index == 0`
(`test_primary_join_is_fanout_free…` → `100`) and on `K == 1` paths.

**Measured — the contrasting pair, L2, same tree, same command:**

| mutation (definition, `:126` / `:131`) | result |
|---|---|
| `case((index == position, typical))` → `case((index == 0, typical))` — the **typical** coalesce | **62 passed, 1 skipped — no bite** |
| the same mutation on the **count** coalesce | **3 failed, 59 passed** — `test_cardinality…`, `test_spec_index…`, `test_primary_join_is_fanout_free…` |

**Authority.** intention §4A K2 (`spec_index` positionally indexes the caller's sequence;
domain mapping `(client_id, spec_index) → SectionTypicalEvidence`); plan 2 §6 C4, whose
*Defect caught* is "a mis-keyed row silently attributes one item category's history to
another task — Critical rank 2 of the inventory".

**What breaks observably.** Under the mutant, a section's narrowed median at
`spec_index ≥ 1` returns `NULL` — the task silently falls back to the section-wide typical
— **and** `spec_index 0` inherits a *later* spec's median whenever its own count is below
`TYPICAL_MIN_SAMPLE_SIZE`. A chair's typical published as a table's, on the count column
that says `0`.

**Correction.** One `K = 2` row where **both** indices clear `TYPICAL_MIN_SAMPLE_SIZE` with
**different** medians, asserting each index's literal `narrowed_typical_worker_seconds`
(master plan §9: "Prefer an exact literal over an equality between two calls"). The
existing C4 fixture cannot be reused as-is — its index 1 has 2 groups by contract.

#### S3 — C0's bare-string enum row cannot tell an explicit rejection from an accidental one

C0's *Contract* is explicit: "the enum family rejects a bare `str` **explicitly**, never by
accident of member length." The row `{"major_categories": "wood"}` asserts
`pytest.raises(ValidationError, match="major_categories")`. Both the explicit guard's
message (`"major_categories must be a sequence of values."`) and the accidental path's
message (`"major_categories contains an unknown value."`) contain the family name.

**Measured — L1, `tests/unit/domain/item_economics/test_typical_filters.py`:**
remove `str` from `_optional_categories`'s
`isinstance(raw, (str, bytes, bytearray, memoryview, Mapping))` guard →
**43 passed — no bite.** With the guard gone, `"wood"` iterates character-wise,
`ItemMajorCategoryEnum("w")` raises `ValueError`, and the `except` arm raises the
*other* `ValidationError`, which the `match=` still accepts.

**Compounding: C0's second named mutation was never run.** §6 C0 names two ("remove the
`can_have_upholstery` type check"; "shorten a test enum member to one character"). Round
1's ledger row ran one. Round 2 declined the second as "justified by round-1 tree-bound
ledger row" — the round-1 row does not cover it. That is master plan §9's "'Mutations, one
per sub-check' is a count, and the ledger is checkable against it", firing a second time
inside the same phase, and charter rule 14 (a declared divergence whose stated reason does
not hold).

**Correction.** Pin the message, not the family: `match="must be a sequence of values"`.
The accidental path does not produce it. The same change arms the
`{"major_categories": {"wood": 1}}` row, which currently bites for the right reason by
luck of ordering.

#### S4 — the shipped `K ≥ 1` column order is the reverse of intention §4A K2's, and C2 pins the shipped order

| | tuple |
|---|---|
| intention §4A K2 | `client_id, name, spec_index, section_sample_count, section_typical_worker_seconds, narrowed_sample_count, narrowed_typical_worker_seconds` |
| shipped + asserted by C2 | `client_id, name, spec_index, narrowed_sample_count, narrowed_typical_worker_seconds, section_sample_count, section_typical_worker_seconds` |

Plan §6 C2 requires "asserting the **exact column-name tuple** each time". The tuple
asserted is not the authority's. Nothing is wrong on the wire — every consumer binds by
name — but a phase-3/4 implementer trusting §4A K2's written order for any positional read
would swap the two populations, publishing a section-wide median as `item_narrowed`.

**Correction — coordinator's routing call.** Either reorder the `select()` (K ≥ 1 only, C1
unaffected), or amend §4A K2 with a lettered note to the shipped order. **Recommend the
amendment plus one explicit sentence that column order is not contractual and consumers
bind by name** — positional construction is impossible against `SectionTypicalEvidence`
under either order, since its own field order is
`narrowed_typical, narrowed_count, section_typical, section_count`. Silent drift between a
Critical-ranked mechanism's contract and its implementation is the part that must not stand.

#### S5 — the measurement document reads as eleven isolated measurements; it is eleven cumulative ones

`collect_measurement_matrix` (`_narrowing_seed.py`) loops all eleven cases on **one**
`db_session` with no cleanup between them. Each row is measured against a table holding
every previous row's seed; by the last row `task_steps` carries 232 seeded rows across
eleven workspaces, plus whatever the shared test database already held. The document's
opening — "Seed cardinalities are exact for every row" — is true of each workspace's own
seed and not of the table the planner and executor saw.

The consequence is visible in the document's own numbers: the new no-spec row (position
10) measures **0.087 ms** for the *same query* the current/no-spec row (position 5)
measured at **0.060 ms**; the 50 × 20 ceiling row (position 11, **2.758 ms**) is 1.9× the
20 × 20 row (position 9, **1.466 ms**) for 2.5× the tasks. Whether that ratio is spec
fan-out or table growth is undecidable from the document.

Two smaller gaps: `cost` is **16.42** for both the 1-task and the 20-task seed of the
identical query, and the document does not say what the column means (the plain reading is
that statistics were never refreshed, so it is a default-estimate, not seed-sensitive); and
the harness requests `BUFFERS` and records none.

**No re-measurement is required** — D26 sets no threshold and the §12 conditional
acceptance is otherwise met in full (eleven rows, five copies disclosed, exact seed
cardinalities, chosen strategy per shape, no threshold claimed). What is owed is **one
paragraph**: cumulative seeding with row positions, no `ANALYZE`, `BUFFERS` dropped.

### Recorded

- **N1 — `uix_task_items_primary_active`: deferral judged acceptable, and I measured why.**
  Confirmed untested repo-wide (model `task_item.py:53`, two migrations, four docs, **zero
  tests**). I read the index out of the migrated test template rather than the model:
  `CREATE UNIQUE INDEX uix_task_items_primary_active ON public.task_items USING btree
  (workspace_id, task_id) WHERE ((role = 'primary'::task_item_role_enum) AND (removed_at IS
  NULL))` — an exact match for §3A C5's `ON` clause, so plan §2's fan-out-free claim is true
  **at the database right now**. The one migration that could have broken it
  (`ddc5bf50153b`, enum lowercase rename) explicitly drops and recreates it with the
  lowercase label; `7d92a90e6282` had created it as `'PRIMARY'`. Phase 2 ships no consumer
  and the two code-side mutations (C7(ii), C8) already bite.
  **Added after the card was first written (owner asked, 2026-08-23):** the rule has a
  *second*, app-level guard — `add_item_to_task.py:46-57` pre-checks for an active primary
  and raises `ConflictError("Task already has an active primary item.")`. **That guard has no
  test either**: no test file in the repo references `add_item_to_task`, and the message
  appears only in production code. So the rule is unguarded at **both** layers, not one. The
  app-level gap is pre-existing and outside this pipeline's perimeter — recorded here because
  it changes the shape of the row plan 3 should buy, not because phase 2 caused it.
  **Owner ruling 2026-08-23: executed by phase 3.** See owner card 1.
- **N2 — C13(b)'s coverage claim: true, imprecise as written, now independently confirmed.**
  The L2 run covered one of the six named suites; the other five are under
  `tests/integration/services/queries/item_economics/`. My serial L4 confirms all six green
  on my tree under a **different runner topology**: none of the 21 failures is in
  `working_sections/` or `item_economics/`. Wording only.
- **N3 — C11's conversion trigger is well stated but not routed.** It names three concrete
  syntactic conditions (`NOT item_match`, `is_(False)` on it, an `ANSWER_AS_ASKED`
  complement query) and the criterion row it converts into — better than most such clauses
  — and master plan §9 carries the standing rule pointing at it. But **no downstream plan's
  Read-first list includes intention §3A or plan 2 C11**, and plan 6, the one plan whose
  scope names `ANSWER_AS_ASKED`, is among them. A trigger nobody is routed to read cannot
  fire. Cheap fix: add intention §3A C3 and the C11 trigger to plans 3 and 6 Read-first.
- **N4 — C10 row (c)'s NULL entry was not transcribed.** The plan lists three out-values for
  `width_cm=(60,80)` — 59, 81 and `NULL`; the test seeds 59 and 81 only. C10's mutation (i)
  therefore cannot bite on row (c); it bites on (d), (e) and (h), so the mutation itself is
  covered and the row's own enumeration is not. Charter rule 2.
- **N5 — the graph's test evidence span drifted in round 2.** The phase-2 delta pins
  `test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized`
  at `test_typical_times_narrowing.py:199-224`; the test now begins at **line 232** and
  199–224 falls inside a different test. Round 2's "Architecture Graph: no delta" is right
  about production and wrong about the cited span. I touched nothing. See owner card 2.

### Judgment calls assessed (doctrine rule 6)

- **C8 option (b) — accepted here, flagged for the next phase that edits the file.** The
  count assertion bites hard under the shipped outer attachment (6 → 17 rows), the median is
  documented as a control, and §6A authorised the choice. But master plan §9 already carries
  "A uniform fixture is an inert fixture", and six identical `100`s is that fixture.
  Recommend the median line be **either armed (five distinct group values) or deleted** by
  whichever phase next edits this file — a decorative assertion inside an armed criterion is
  how the next reviewer loses a round.
- **§3D (the `ItemCategory` join asymmetry) — code matches the record; not re-litigated.**
  One addition to the record: it **cannot fan out**. `client_id` is the primary key
  (`IdentityMixin`), so the workspace-less join is 1:1. §3D's scope is purely semantic
  (a soft-deleted category still satisfies `major_categories`), exactly as written.

---

## What I verified correct

- **Perimeter.** `git diff --stat a9ed846 HEAD -- app/` is exactly plan §4's declared paths
  and no others (8 files). The snapshot `typical_times_no_spec_sql.txt` is **untouched**.
  Production diff across the fix cycle re-measured empty.
- **§4A K4 transcribed exactly.** Per-population `count`/`percentile_cont` FILTERs,
  per-population `CASE` thresholds, and the narrowed `CASE` reads `narrowed_count` — not the
  copy-paste the plan warned about.
- **§6A's mandated K-shape.** Outer `VALUES` cross join with `spec_index` in the outer
  `GROUP BY`, so `section_sample_count` is constant across indices **by construction** and
  §6A's K-multiplication failure mode is structurally unreachable.
- **The `K == 1` bypass is sound.** The `VALUES` clause has one row, so the
  `spec_index == 0` FILTER is total and the bare aggregate equals the coalesce path.
  `count(...) FILTER` returns `0`, never `NULL`, so the count-0/NULL boundary through the
  coalesce is correct — and it **is** exercised at `K = 2` by `test_cardinality…` (no
  history) and `test_primary_join_is_fanout_free…` (history present, spec matches nothing).
  This half of depth area 3 is refuted as a hazard.
- **Fan-out freedom, structurally and at the database.** All three joins are 1:1: the
  `TaskItem` `ON` clause matches `uix_task_items_primary_active`'s columns and predicate
  exactly, and `Item`/`ItemCategory` join on primary keys.
- **`build_item_match`'s two falsy traps.** `can_have_upholstery is not None` → `.is_(False)`
  survives, and `if minimum is not None` keeps a zero lower bound. Both carry integration
  rows (`upholstery-false`, `test_zero_lower_bound_is_a_real_range_value`).
- **C0's five parser rows landed**; four of the five bite (S3 is the fifth).
- **C12's corrected instrument** counts `LEFT OUTER JOIN item_categories`, and row (a)'s two
  specs both narrow on another field — not vacuous.
- **C13(a) is a real bound-value guard.** The literal payload pins `typical_worker_seconds:
  1200` over groups `[600, 1000, 1200, 6000, 7000]`; `percentile_cont(0.5) → 0.6` moves it
  to 3120. C1's boxed limitation is genuinely closed for the no-spec branch. The `K ≥ 1`
  branch's percentile is separately pinned by C5's literal `76` and C2's literal `30`.
- **`needs_category_join` is now asserted directly** in the unit file, closing §6A's
  "Delegated in writing" gap.
- **L27's delegated choice** (`workspace_id` as a bound parameter in the `TaskItem` `ON`) was
  taken; C1's three snapshot rows are green, so C1 is unaffected as predicted.
- **The graph delta was committed** (`d07028b`, `.archgraph/architecture.yml`, +87 lines);
  the production evidence spans (`typical_times_statement` 28–142, `build_item_match`
  13–49) are accurate. Only the test span drifted (N5).

---

## Depth areas — confirmed and refuted

| # | area | result |
|---|---|---|
| 1 | two branches, two `grouped_steps` | **CONFIRMED → S1.** Nothing guards them against divergence; four deletions measured green. |
| 2 | `uix_task_items_primary_active` untested | **CONFIRMED as fact; deferral judged acceptable → N1 + card 1**, with a database measurement that lowers the risk the projection assigned it. |
| 3 | `K ≥ 2` coalesce and the `K == 1` bypass | **SPLIT. Confirmed → S2** for the value column; **refuted** for the bypass and the count-0/NULL boundary, both sound and covered. |
| 4 | C11's conversion trigger | **PARTLY REFUTED → N3.** Stated well enough to fire; not *routed* to anyone who would fire it. |
| 5 | C8 option (b) | **JUDGED.** Right call here; the median line should be armed or deleted by the next phase that edits the file. |
| 6 | C13(b)'s loose coverage claim | **CONFIRMED and CLOSED → N2**, independently at L4 under a different topology. |
| 7 | `ItemCategory` join asymmetry | **CONFIRMED** — code matches §3D exactly. Added: it cannot fan out, so §3D's scope is semantic only. |
| 8 | measurement-document honesty | **CONFIRMED, new mechanism → S5.** The gap is not the numbers' size; it is eleven cumulative measurements presented as eleven isolated ones. |

---

## Evidence taken

**Consumed by citation** (tree identity matches mine — checkpoint `a371e8e`, everything
after it docs-only): round 2's focused baseline (23 passed / 1 skipped), its L2 baseline
(62 passed / 1 skipped), and its parallel L4 stamp (2660 passed / 21 failed / 1 skipped,
∅/∅). Not re-run — over-evidence on a matching SHA.

**My one L4, spent on variation.** *Authorization line, written before the run:* narrower
evidence is insufficient because the hypothesis — "the failing-ID set is scheduling-
dependent, so the serial partition yields a different set than the parallel one" — is
repository-wide by construction, and `-n 0`, the comparator master plan §10 names, has
never been run on this tree.

- Command: `PYTHONPATH=. pytest -m 'not e2e' -n 0 -q` from `backend/app/`, documented
  default `BEYO_TEST_SLOT=main`. Redis pre-check `redis-cli ping` → `PONG`.
- Tree identity: `90c2490`, `git status --porcelain` = `?? .archgraph/contexts/` only, all
  three production files checksum-verified against pre-probe values.
- Result: **21 failed, 2659 passed, 2 skipped, 1 deselected, 129.80 s.**
- **Delta against the approved 21-ID baseline: added ∅, removed ∅** (diffed
  programmatically against §7 of the frontend handoff, not by eye).
- The extra skip versus the parallel stamp is `test_database_isolation.py:118`, which skips
  by design under `-n 0`. Serial is 2.5× the parallel ~52 s.

**Result — the prompt's framing needs one correction.** The clean ∅/∅ of round 2 was **not
scheduling luck.** The failing-ID set is *identical* at `-n 0` and at `-n 6 --dist
loadfile`. Combined with the trio failing 3/3 *in isolation* and in **neither** full run,
the diagnosis sharpens: those three tests fail when run **alone** (their `_two_workspaces`
helper needs leaked state that a full run supplies and an isolated run does not), and round
1's 24-failure stamp is the outlier, not round 2's 21. My hypothesis was refuted, which is
the result. Free datapoint for `test_isolation_xdist` phase 3: **the 21-ID set is stable
across worker topologies on this tree.**

**Mutations — 7 probes, all shapes nobody had run**, at L2 (`tests/unit/services/queries/
working_sections/` + `tests/integration/services/queries/working_sections/`) except the C0
probe at L1. Contract side is the cited round-2 baseline. Results are in S1, S2 and S3.

---

## Mutation-probe declaration

Files touched by probes, **applied and reverted, checksum-verified byte-identical**:

| file | SHA-256 before and after |
|---|---|
| `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` | `4e79395dba92dae5bce27525927890639a1ce94d692353ac370d517a78a20384` |
| `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py` | `0822b3bf8079f9f3be1286e5f6969fcf7e4da1db8e4b731feb0da504f058a499` (read only; never modified) |
| `app/beyo_manager/domain/item_economics/typical_filters.py` | `7f65025565fd452cdbe14ee3451b439d504e43aa93ad0a579e86b013e7dc5076` |

`git diff HEAD` is empty and `git status --porcelain` is `?? .archgraph/contexts/` at close.

**State side effects:** each probe ran under its own `BEYO_TEST_SLOT` (`revm1`, `revm2state`,
`revm3del`, `revm4window`, `revm5typ`, `revm6cnt`, `revm7`); pytest drops its per-process
databases at session end. The serial L4 used the default `main` slot. One read-only
`psql` query against `beyo_test_main_template` (`pg_indexes`) — no writes. Architecture
graph: read-only (`archgraph_status`, `archgraph_list_pending_reviews`); nothing promoted,
rejected or edited.

---

## Carry-forward dispositions

| item | destination |
|---|---|
| N1 — the one-active-primary rule, unguarded at **both** layers | **plan 3 — owner-ruled 2026-08-23.** Two rows, not one: (a) the DB backstop — a second active `TaskItem` with `role=PRIMARY`, `removed_at IS NULL` on the same `(workspace_id, task_id)` raises `IntegrityError`; (b) the app guard — `add_item_to_task` with a second primary raises `ConflictError`. Named mutation per row: drop the index / delete the pre-check. |
| N3 — route intention §3A C3 + C11's trigger into Read-first | **plans 3 and 6** (coordinator fold) |
| C8's decorative median line — arm or delete | **whichever phase next edits `test_typical_times_narrowing.py`** |
| N5 — stale graph evidence span | **owner adjudication** (card 2), then re-record in the fix round |
| §3D `ItemCategory` `workspace_id` / `is_deleted` | unchanged; converts on its own recorded trigger |

---

## Lessons for the plans

1. **Duplicated branches need a criterion that names the duplication.** HC-4's byte-identity
   requirement forces two builders; the plan then wrote no criterion over the *second* one's
   population. A phase that deliberately duplicates a definition owes one row asserting the
   copies agree, on a fixture where they could disagree. Candidate for master plan §9.
2. **"The criterion asserts a cross-call equality" is not the same as "the criterion can see
   a difference."** §9's hazard-ownership rule already says: name the mutation, name the
   column, confirm the guard reads that column. Extend it — **confirm the fixture contains a
   row the mutation moves.** S1, S2 and S3 are all this rule, at three different layers.
3. **A `match=` on an exception is an assertion and gets the same enumeration discipline as
   any other.** S3 passed under its own defect because the substring it matched appears in
   both the right message and the wrong one. Pin the message that only the correct path
   produces.
4. **A measurement harness that seeds cumulatively must say so.** "Exact seed cardinalities"
   described the workspace, not the table. The document is otherwise the model of what §12
   asked for.
5. **Tests-first closed the missing-row class; the surviving class is now "the row exists,
   the fixture is uniform, the assertion matches too loosely."** Round 2 fixed three
   instances of it and this review found three more. A tests-first prompt should ask, per
   row, for the fixture arithmetic *and* the assertion's discriminating power.

---

## Human-authorization backlog

- **Architecture graph: 7 pending review items, 2 stale nodes** (measured this session:
  198 nodes / 299 edges, revision `46154ec9…`, 0 diagnostics). Four are plan 1's, three are
  plan 2's. Master plan §8's recorded "0 pending / 0 stale" predates both. One of the three
  plan-2 items carries the stale evidence span of N5. **Owner card 2.**
- ~~N1's deferral, third round running. Owner card 1.~~ **Closed 2026-08-23 — owner ruled phase 3.** Coordinator: fold as an owner decision in `planning/owner_decisions.md` and add the two rows to `plans/plan_3.md` §6.
