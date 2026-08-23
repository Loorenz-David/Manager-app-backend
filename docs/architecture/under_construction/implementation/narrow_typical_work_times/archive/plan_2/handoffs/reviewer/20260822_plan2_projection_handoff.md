---
plan: plan_2
role: projection
round: 0
date: 2026-08-22
verdict: AMENDMENTS_REQUIRED
actor: Opus 5 (plan-projection, fresh session)
---

# Plan-2 projection — the statement extension

## 1. Opening

I did the implementer's first hour of phase 2 on paper: I wrote out the SQL the plan
implies, then tried to turn each of its fourteen acceptance criteria into a real test.
The design itself holds up — the two-population arithmetic, the item join and the
promise that the old query stays byte-identical are all sound, and I found no reason to
reopen a settled decision. What does not hold up yet is the criteria table: nine of the
fourteen criteria cannot be written as tests exactly as worded, and because this is the
first phase that writes its tests before its code, the implementer would hit every one
of them in the first hour. The commonest problem is a test whose example is too small to
show the thing it is checking — a single task where the rule only switches on at five.
One thing needs you personally: nobody has said how slow is too slow for the new query,
so as written the performance gate can be passed by a query that is ten times slower.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — What counts as an acceptable query cost?

**Question.** Do you want a speed ceiling fixed *before* the measurements are taken, or
will you judge the numbers when you see them?

**Story.** The typical-time query runs behind the budget screen and the task cards.
Today one query serves a batch of fifty tasks. After this change that same batch can
fan out across twenty different item categories. At 40 ms nobody notices; at 400 ms a
manager working through a morning's tasks watches the screen hesitate, every time. The
plan measures ten cases and writes them all down — but nothing in it says which numbers
are too slow, so a slow result would be recorded, filed, and shipped.

**Branches.**
- *Ceiling fixed now* (e.g. the new query at twenty categories within 3× today's): a
  breach stops the phase and comes back to you.
- *Left undefined*: the phase passes on paperwork; speed is discovered in production.
- *Judged after the numbers arrive*: the phase pauses mid-way and waits for you.

**Recommendation.** Fix the ceiling now — a threshold chosen after seeing the numbers is
the one that always turns out to have been met.

**On silence.** The gate holds. The phase may implement and measure; it cannot be
accepted.

**Trace.** intention §12; plan 2 §5 task 8 and §12; master plan §7 constraint 2.

## 2. Decision ledger

Blocking = the implementer cannot proceed without inventing a contract that is
observable in the finished product (a perimeter, an expected value, a fixture the
criterion's own claim depends on).

| # | Decision point | Classification | Proposed routing | Blocking |
|---|---|---|---|---|
| L1 | C0 requires guards in `typical_filters.py` and rows in `test_typical_filters.py`; §4 lists neither under **Modified** | plan gap | add both paths to §4 | **yes** |
| L2 | C0's table gives each input's *today* value, not its required outcome; the *Contract* sentence under it does not decide the `dict` or the `bytearray`/`memoryview` rows (both are non-`str` iterables of scalars) | plan gap | state the expected outcome per row | **yes** |
| L3 | C0 names mutations for two of its five rows; rows 1, 2 and 4 have none (charter rule 12) | plan gap | one mutation per row | no |
| L4 | C0's "This phase builds the route" — phase 2 builds no route (§6.8 defers it; plan §1 forbids consumer changes) | plan gap | reword to "builds the spec→SQL path" | no |
| L5 | C1's mutation ("make the item joins unconditional") cannot redden a `len(specs)==0` early-return branch, which task 3 mandates | plan gap | mutation becomes "delete the `len(specs)==0` branch" | **yes** (evidence) |
| L6 | C1 adds a third row to `test_typical_times_sql_identity.py`; §4 lists it nowhere (not Modified, not read-only) | plan gap | add to §4 **Modified** | **yes** |
| L7 | C1's three rows live in one test function as sequential asserts; the first failure hides the other two ("all three rows go red" is unobservable) | plan gap | parametrize, or three functions | no |
| L8 | C3's history-less section is "no qualifying history at all"; if it has *old* steps the inner-join mutation leaves it present and the mutation is inert | plan gap | "no COMPLETED task_steps at all" | no |
| L9 | C8 row (a)'s fixture is one task; the narrowed median is `NULL` below `TYPICAL_MIN_SAMPLE_SIZE`, and even at five groups one tripled group does not move the median | plan gap | enumerate the fixture (five same-shape groups) | **yes** |
| L10 | C8's closing claim "the median assertion bites under either" is false: under outer attachment the median stays `S` and only the count moves | plan gap | restate which assertion bites on which strategy | no |
| L11 | C9 has the same floor problem, and its `specs=()` half cannot bite (no item joins exist on that branch) | plan gap | enumerate the fixture; label the `specs=()` half a control | **yes** |
| L12 | C10 has no `can_have_upholstery=False` row — a *set* field that is falsy, so `if spec.can_have_upholstery:` drops the conjunct silently. Same shape for a zero lower bound | plan gap | add the row(s) | no (high value) |
| L13 | C10 rows (b), (f), (g) have no named mutation | plan gap | one mutation per field | no |
| L14 | C10's both-sides are `narrowed_sample_count` literals, so C10 is an integration criterion; the plan never says which criteria land in the unit file, whose only enumerated content is then C11 | plan gap | one line assigning criteria to files | no |
| L15 | C12's instrument is the substring `item_categories`, which also appears inside the predicate (`item_categories.major_category IN …`); "present **once**" is false for rows (b) and (c) | plan gap | count `LEFT OUTER JOIN item_categories` | **yes** |
| L16 | C12 row (a) ("K=2, neither sets `major_categories`") is satisfied by two *empty* specs, which emit no joins at all — vacuous | plan gap | require both specs narrowing on another field | no |
| L17 | C13(a) asserts the payload is "unchanged key-for-key and value-for-value" with no stated baseline, and does not require the seeded workspace to produce a **non-NULL** typical — so it cannot discriminate the bound-value changes C1's own boxed limitation defers to it | plan gap | pin the expected payload; require ≥ `TYPICAL_MIN_SAMPLE_SIZE` groups | **yes** |
| L18 | C13(b) omits `test_phase2_live_surfaces.py`, which calls `typical_times_statement` directly (`:986`, `:1377`) and monkeypatches the module's bound `datetime` (`:1394`) | plan gap | add to C13(b)'s list | no |
| L19 | §12 defines no acceptance threshold; plan §12 reduces the gate to "ten rows present" | intention gap | **owner card 1** | at the gate |
| L20 | §12's seeding + `EXPLAIN ANALYZE` harness has no home; §4 lists no file for it, so it is either uncommitted (unreproducible) or an undeclared perimeter entry | plan gap | name the harness file in §4, or record it as deliberately throwaway with the doc carrying the seed script verbatim | **yes** |
| L21 | "a representative 90-day history" is unquantified — an adjective for a mechanism (charter rule 5). Seed cardinality decides the plan shape | plan gap | fix sections / tasks / steps / categories counts | **yes** |
| L22 | Five of §12's ten rows measure the *same* query: the current statement is spec-blind, so its cost is identical at all five shapes, and the no-spec *new* row equals it by C1 | plan gap | keep ten rows, but state which are constant by construction | no |
| L23 | Task 6 offers §4.2's axis (`bool_or` pairs vs GROUPING SETS) while C8/C9's both-sides are stated on §4A K4's axis (inner vs outer attachment). Two taxonomies, used interchangeably | plan gap | one line naming K4's axis as the one the criteria bind | no |
| L24 | GROUPING SETS as named cannot produce K2's total cardinality (a section with no rows for a category emits no row); it needs an outer cross join + LEFT JOIN, which the plan does not describe | plan gap | drop the option for V1, or state the extra machinery. C3 is the guard either way | no |
| L25 | Task 6 and §12 say "the chosen internal strategy **per shape**" — if more than one strategy ships, only the one the tests' spec profile triggers is covered (charter rule 10) | plan gap | delegate explicitly: one strategy this phase, or a criterion per strategy | no |
| L26 | Phase 2's integration criteria need item-aware seeding; master plan §6.9 assigns `seed_narrowing_history` / `_narrowing_fixture.py` to **phase 4** | master-plan gap | register a phase-2 home, or move the fixture's creation to phase 2 | no |
| L27 | Under outer attachment the `TaskItem` `ON` clause needs `workspace_id`, which `grouped_steps` does not select | free choice | delegate in writing (bound parameter, or add the column — K≥1 only, so C1 is unaffected) | no |
| L28 | §3A C5's `ItemCategory` `ON` carries neither `workspace_id` nor `is_deleted IS FALSE`, though both columns exist (`item_category.py:19-21`, `:41`). A soft-deleted category still matches `major_categories` | intention gap | route upstream as a note; C5 is determinate as written, so the implementer is not blocked | no |
| L29 | C4's mutation (ii) is an absence assertion, not a mutation, and is module-scoped where §6.6 says "anywhere in this pipeline" | plan gap | restate as its own criterion row with root + term set | no |
| L30 | C0 requires plan 1 rows (o)(p)(q) to keep passing; §2's read-first names only plan 1 §6 **C15**, and those rows are in **C14** (`plan_1.md:502-513`) | plan gap | add "§6 C14" to §2 | no |
| L31 | §7 says to run the docs guard before writing `query_cost_measurements.md`; the guard's roots are `docs/domains/item_economics` (`test_item_economics_docs.py:20`) and the app/backend roots (`test_item_economics_handoff_accuracy.py:22-23`) — neither covers `docs/architecture/under_construction/` | plan gap | drop the line, or say it is a no-op kept for habit | no |
| L32 | C2 row (d) asserts `narrowed_* == section_*` — an equality between two computed values, where master plan §9 prefers two exact literals | plan gap | assert both against the literal count | no |
| L33 | Nothing in the repository tests `uix_task_items_primary_active` (repo-wide: the model, two migrations, docs — no test). It is a database guarantee load-bearing plan §2's fan-out-free claim | plan gap | one criterion row (a second active primary raises `IntegrityError`, or the index is present with its `WHERE`), or an explicit deferral record | no |

## 3. Reality-check findings

Every path in §4 resolves. `_typical_item_filter.py`, `test_typical_item_filter.py`,
`test_typical_times_narrowing.py` and `planning/query_cost_measurements.md` do not exist
and are correctly marked new; their parent directories all exist (including
`app/tests/integration/services/queries/working_sections/`).
`get_working_section_typical_times.py` and the snapshot file exist.

**R1 — the file list is short by three (L1, L6).** C0 changes production code
(`app/beyo_manager/domain/item_economics/typical_filters.py`, the per-family guards) and
its test file (`app/tests/unit/domain/item_economics/test_typical_filters.py`); C1
changes `app/tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py`.
None appears in plan 2 §4. Under master plan §3's explicit-paths checkpoint rule and the
charter's perimeter check, three undeclared files in the diff are automatic findings
against a session that did exactly what the plan asked.

**R2 — C1's mutation is inert against the branch task 3 mandates.** Task 3
(`plan_2.md:57-59`) requires `len(specs) == 0` to take a branch returning today's
statement "character for character … a branch producing the old statement, not a
convention." C1's mutation is "make the item joins unconditional." Item joins only exist
on the `K >= 1` path; the early branch returns before reaching them, so the mutation
leaves all three rows green. This is §11A's own T11 repair reappearing one phase later.
The mutation that bites is *delete the `len(specs) == 0` branch*, which sends the
no-spec call through the general builder. Plan 1's C15 mutation (delete
`WorkingSection.is_deleted.is_(False)`, `plan_1.md:534-535`) still bites and should be
kept as the structural control.

**R3 — C1's rows short-circuit.** `test_typical_times_sql_identity.py:24-28` is one
function with two sequential asserts. Adding a third makes three. "all three rows go
red" (`plan_2.md`, C1 *Both sides*) cannot be observed: the first failing assert returns
and the other two never execute. Charter rule 12, exactly.

**R4 — C12's instrument counts the wrong thing.** The compiled string for a spec with
`major_categories` contains `item_categories` in the `LEFT OUTER JOIN` **and** in
`item_categories.major_category IN (…)`. Rows (b) and (c) assert "present **once**",
which is false under the contract, not only under the mutation. The row is not
transcribable until the instrument names the join.

**R5 — two criteria assert a median that the sample floor makes unreachable.** C8 row
(a) and C9 both describe a single task and then assert a median (`S` vs `3S`, `S` vs
`2S`). `narrowed_typical` / `section_typical` are `NULL` below `TYPICAL_MIN_SAMPLE_SIZE`
(`get_working_section_typical_times.py:49-52`), so a one-task fixture yields `None` on
both sides. And at exactly five groups, tripling **one** of them leaves the median where
it was — `median({S,S,S,S,3S}) = S`. Both rows need their fixture enumerated (e.g. five
qualifying groups all carrying the fan-out shape) before the stated both-sides is true.

**R6 — C8's strategy claim is wrong in one direction.** C8 says "the median assertion
bites under either". Under outer attachment the three joined `task_items` rows multiply
the *row count*, not `group_seconds`: the median over three equal values is still `S`,
and it is the **count** assertion (1 → 3) that bites. Under inner attachment it is the
median (S → 3S) and the count is unchanged. Row (a) is safe — it asserts both — but the
ledger claim must name which assertion bites on which strategy (charter rule 12's second
half).

**R7 — C9's `specs=()` half cannot fail.** With `specs=()` the statement emits no item
joins at all (HC-4), so dropping `removed_at IS NULL` from an `ON` clause that does not
exist on that branch changes nothing. That half is a control, which is legitimate; the
criterion should say so rather than read as two biting sub-checks.

**R8 — C13(a) is the only thing standing behind C1's boxed limitation, and it cannot
carry the weight.** C1's box (`plan_2.md`) records that a green snapshot proves shape,
not behaviour — the percentile, the sample floor, the step-state filter and the cutoff
all render as `%(…)s` and cannot move the frozen string. The plan then says any change
to a bound value must be "covered with an integration row against real rows". C13(a) is
that row. As written it (i) names no baseline to compare against and (ii) does not
require the seeded workspace to clear the sample floor — a workspace with four
qualifying groups yields `typical_worker_seconds: null` for every section, and a
`percentile_cont(0.5) → 0.6` mutation leaves the payload identical. This is phase 1's C7
shape: two populations equal by construction, so no row can tell the branches apart.

**R9 — one existing consumer of the changed function is missing from C13(b).**
`app/tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py`
imports `typical_times_statement` (`:37`), calls it with a frozen clock and asserts on
its compiled params (`:986-989`), executes it against a real session and reads
`row.sample_count` / `row.typical_worker_seconds` (`:1377-1380`), and monkeypatches the
module's bound `datetime` name (`:1394`, `monkeypatch.setattr(typicals_module,
"datetime", NoClock)`). Any refactor that moves the cutoff computation out of the
module's own `datetime` reference reddens it. It belongs in C13(b)'s list.

**R10 — the fan-out guarantee is untested (depth area 4).** Repo-wide,
`uix_task_items_primary_active` appears in `app/beyo_manager/models/tables/tasks/task_item.py:53`,
in two migrations (`7d92a90e6282:685` creating it with the pre-rename uppercase label;
`ddc5bf50153b:492-499` dropping and recreating it as `role = 'primary' AND removed_at IS
NULL`, matching the model), and in docs. **No test references it.** Its shape does match
§3A C5's `ON` clause exactly — `(workspace_id, task_id)` unique where role is primary and
`removed_at IS NULL` — so plan §2's claim is true today; it is simply unguarded. C8 and
C9 test the *consequence* (no fan-out) and would catch a code change; neither would
catch the index being dropped.

**R11 — the docs-guard instruction in §7 is a no-op.** The guard's roots are
`docs/domains/item_economics` and the app/backend roots; `query_cost_measurements.md`
lands under `docs/architecture/under_construction/`, outside both.

**R12 — §3A C5's `ItemCategory` join is asymmetric with the `Item` join.** `Item` is
joined with `workspace_id` and `is_deleted IS FALSE`; `ItemCategory` with neither, though
`item_categories` carries both columns (`item_category.py:19-21`, `:41`). A soft-deleted
category therefore still satisfies `major_categories`. The contract is determinate, so
this is a note for the coordinator to route upstream, not an implementer blocker. C10 row
(b) has no soft-deleted-category row either way.

**R13 — citations that hold.** §4A K1's signature matches the shipped one exactly
(`get_working_section_typical_times.py:21-27`: `workspace_id`, keyword-only `now:
datetime | None = None`). §3A C2's "`can_have_upholstery` column is `nullable=False`"
holds (`item.py:40`). `ItemMajorCategoryEnum` is `WOOD | SEAT` (`domain/items/enums.py:17-19`)
— both multi-character, so C0's "the bare-`str` rejection is accidental" reading is
sound. C0's *today* column is consistent with `typical_filters.py:76-86` (`_optional_values`
rejects `str`/`bytes` and non-iterables, then does `frozenset(str(v) for v in raw)`) and
`:120` (`can_have_upholstery=params.get(...)`, no type check at all). `task_item.py` has
no `is_deleted` column, so §3A C5's `TaskItem` `ON` clause is complete as written. The
`db_session` fixture (`tests/conftest.py:107-110`) yields a real session and rolls back —
phase 2's integration criteria issue real SQL, and the `_TypicalSession` blind spot master
plan §9 warns about does not reach them (depth area 6).

## 4. Depth-area conclusions

**1 — the two-population `FILTER` arithmetic across K specs.** Worked out on paper, both
attachments are constructible and neither multiplies the section-wide aggregates,
*provided* `spec_index` is materialised as a cross join placed in the **outer** select
and added to its `GROUP BY` — `FROM working_sections CROSS JOIN (VALUES (0),(1),…) AS
s(spec_index) LEFT OUTER JOIN grouped_steps … GROUP BY ws.client_id, ws.name,
s.spec_index`. Every `(section, spec_index)` group then sees the same `grouped_steps`
rows, so `section_sample_count` is constant across indices by construction. The failure
mode is introducing `spec_index` *inside* `grouped_steps` without adding it to that
subquery's `GROUP BY`, which multiplies `SUM(total_working_seconds)` by K. **C5 is the
guard**: it pins `section_sample_count == 20` at every index *and* against the `K == 0`
call, so a K-multiplication reddens it. That is worth stating in the plan so the
implementer knows which criterion owns this hazard. `match_k` reaches the outer aggregate
as `bool_or(match_k)` selected in `grouped_steps` (inner) or directly off the joined
`task_items` row (outer), exactly as §4A K4 describes.

**2 — `specs=()` versus K=1 non-narrowing.** Both claims hold simultaneously, and what
enforces it is task 3's early branch on `len(specs)`, not a shared builder: C1 pins the
K=0 compiled string, C2(b) pins the K=1 column tuple, and nothing forces them to agree.
The risk is not that they conflict — it is that C1 cannot see a bound-value change, and
the criterion the plan nominates to cover that (C13(a)) is currently unable to
discriminate one. See R8; that is the load-bearing finding of this area.

**3 — `build_item_match`'s `(bool, predicate | None)`.** The bool carries no information
the caller lacks: `needs_category_join` is `spec.major_categories is not None`, and the
caller holds the spec. It is *not* derivable from the predicate without walking the
expression tree, which is the point — it keeps the "only module that knows Task →
primary TaskItem → Item" boundary (§4.2) intact instead of making the statement
introspect a predicate. The two components are jointly consistent: a non-narrowing spec
has every field `None`, so `predicate is None` and `needs_category_join is False`
together. **Keep the tuple; no ledger row.** One gap: no criterion asserts the bool
directly — C12 asserts its observable consequence at statement level only.

**4 — fan-out freedom.** See R10. The database guarantee is real and matches the `ON`
clause, and nothing tests it.

**5 — §12's ten measurements.** Enumerable from the artifacts: {single task, 50×5,
50×10, 50×20, no-spec} × {current, new}. Three things are not: what "acceptable" means
(**owner card 1**, L19), where the harness lives (L20), and how big "representative" is
(L21). One structural observation the doc must carry: the *current* statement is
spec-blind, so its cost is the same query in all five of its rows, and the no-spec *new*
row is that same query again by C1 — five of the ten cells are constant by construction.
Recorded honestly that is fine; unrecorded, a reviewer cannot tell a measurement from a
copy.

**6 — do the integration criteria issue SQL?** Yes. `test_typical_times_narrowing.py`
lands beside `test_typical_times_query.py`, which uses the real rollback-scoped
`db_session`. The `_TypicalSession` fake that discards statements lives in
`test_price_scenario_query.py` and is phase 5's problem, not this phase's. The one
criterion at risk of proving nothing is C13(a) — not because it fakes SQL, but because
its fixture may not clear the sample floor (R8).

## 5. Criteria decidability, per criterion

| Criterion | Verdict | What is missing |
|---|---|---|
| **C0** | **not transcribable** | Three of five rows state no expected outcome and the *Contract* sentence does not imply one (L2); three rows have no mutation (L3); the perimeter omits both files it edits (L1); read-first omits plan 1 C14 (L30) |
| **C1** | transcribable after amendment | Mutation is inert against the mandated branch (L5); the third row edits a file §4 does not list (L6); three asserts in one function (L7) |
| **C2** | transcribable as-is | Row (d) would be sharper as two literals (L32) — not blocking |
| **C3** | transcribable after a one-line amendment | "no qualifying history at all" → "no COMPLETED task_steps at all", else the mutation is inert (L8) |
| **C4** | transcribable as-is | Mutation (ii) is an absence claim wearing a mutation's label; scope narrower than §6.6 (L29) |
| **C5** | transcribable as-is | — (and it is the guard for depth area 1; say so in the plan) |
| **C6** | transcribable as-is | — |
| **C7** | transcribable as-is | Mutation (iii) needs its own fixture; the plan says so |
| **C8** | **not transcribable** | Row (a)'s fixture cannot produce a median at all (L9); the "bites under either" claim is wrong (L10) |
| **C9** | **not transcribable** | Same fixture problem (L11); the `specs=()` half is a control, not a sub-check (R7) |
| **C10** | transcribable after amendment | No `can_have_upholstery=False` row (L12); rows (b)/(f)/(g) unmutated (L13); file assignment unstated (L14) |
| **C11** | transcribable as-is | — |
| **C12** | **rows (b)/(c) not transcribable** | The instrument counts a substring the predicate also contains (L15); row (a) is vacuously satisfiable (L16) |
| **C13** | **(a) not transcribable** | No baseline for "unchanged", and no floor-clearing seed (L17); (b) omits an existing consumer (L18) |
| **§12** | not enumerable as a gate | No threshold (owner card 1), no harness home (L20), no seed size (L21) |

Six criteria are transcribable exactly as written — C2, C4, C5, C6, C7, C11 — with C2,
C4 and C11 carrying non-blocking notes. Four cannot be written at all today: C0, C8, C9
and C13(a), plus two of C12's three rows.

## 6. Write perimeter

`git status --porcelain` at session end, on `main` at `89883a0`, read off the
command and not retyped:

```
?? .archgraph/contexts/
?? docs/architecture/under_construction/implementation/narrow_typical_work_times/handoffs/reviewer/20260822_plan2_projection_handoff.md
```

`.archgraph/contexts/` was already untracked at session start and this session neither
created nor touched it. The second line is this handoff, the only file this session
wrote. No plan, intention, master plan, code, test or graph state was modified. No skeleton is attached — it was discarded, per
doctrine; §4 above carries only the conclusions it produced.

**L4 runs: 0; tests executed: 0.**
