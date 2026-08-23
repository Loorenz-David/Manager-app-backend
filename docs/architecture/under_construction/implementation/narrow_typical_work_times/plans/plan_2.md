# Plan 2 — The statement: spec → predicate, the K-spec result shape, HC-4, and §12

```
plan: plan_2
project: narrow_typical_work_times
state: APPROVED
projection_gate: MANDATORY
acceptance: CONDITIONAL on planning/query_cost_measurements.md carrying all ten rows
            (+ the 50x20 ceiling row). NO performance threshold - D26 / intention 12A.
```

## 1. Goal

Extend `typical_times_statement` to compute **both populations in one pass** for K distinct
specs, translate a spec into an item-match predicate in **one** new query-layer module, and
keep the no-spec form **byte-identical**. Measure the query cost per §12 and record it.

**Explicitly NOT in this phase:** no consumer passes a spec yet — all four callers keep
their current call form, so **no payload changes anywhere** and **no golden regenerates**.
No change to `divide_production_budget`, to `ALLOCATION_METHOD`, to `TaskBudgetStatus`, or
to any serializer. No new domain object (plan 1 shipped them all). **The snapshot file
committed in plan 1 is read-only in this phase — a change to it is an automatic finding.**

## 2. Read first

- Master plan §§4, 6.1, 6.3, 6.6, 7, 9, 10.
- Intention **header**, then §2.2 F-B / F-I / F-J, §2B (S-2, S-7, S-8 and the address-drift
  table), §4.1, §4.2 (**superseded on signature and result shape by §4A — read §4A first**),
  **§3A** in full, **§4A** K1–K5, §4B, §11.1 rows T11/T18/T19/T20/T22/T25/T26, **§11A** in
  full, **§12**.
- `planning/owner_decisions.md` — D1, D2, D3, D5, D8, D21, D24.
- Gate handoff §2 rows 1, 2, 4, 10, 11, 13 and §5.
- `plans/plan_1.md` §6 C15 and its Review log (the snapshot's provenance).
- Code: `get_working_section_typical_times.py` (the whole file);
  `models/tables/tasks/task_item.py:52-58` (the `uix_task_items_primary_active` partial
  unique index — this is what makes the join fan-out-free); `models/tables/items/item.py`;
  `item_category.py`.

## 3. Dependencies

**Gate: plan 1 `APPROVED`.** This phase imports `TypicalFilterSpec` and
`TYPICAL_MIN_SAMPLE_SIZE`, and its C1 rests on the snapshot plan 1 captured.

## 4. Files expected to change

**New**
- `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py`
- `app/tests/unit/services/queries/working_sections/test_typical_item_filter.py`
- `app/tests/integration/services/queries/working_sections/test_typical_times_narrowing.py`
- `docs/architecture/under_construction/implementation/narrow_typical_work_times/planning/query_cost_measurements.md`

**Modified**
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  — `typical_times_statement` only. `get_working_section_typical_times` (the service) keeps
  its current call form.
- `app/beyo_manager/domain/item_economics/typical_filters.py` — **C0 only** (the
  per-family parser guards). No other production edit to this file. *(Projection L1: C0
  was folded in from plan 1's re-review and its two files were never added here — three
  undeclared paths in the diff would be automatic findings against a session that did
  exactly what the plan asked.)*
- `app/tests/unit/domain/item_economics/test_typical_filters.py` — C0's rows (L1).
- `app/tests/unit/services/queries/working_sections/test_typical_times_sql_identity.py` —
  C1's third row (L6). **The snapshot file it reads stays read-only** (below).
- `app/tests/integration/services/queries/working_sections/_narrowing_seed.py` **(new)** —
  the §12 seeding + `EXPLAIN ANALYZE` harness, committed so the measurements are
  reproducible (L20). Master plan §6.9 assigns `seed_narrowing_history` /
  `_narrowing_fixture.py` to **phase 4**; this is a *separate, phase-2-local* harness and
  does not pre-empt it (L26). If phase 4's fixture can absorb it later, that is phase 4's
  call to make.

**Read-only, and a change is a finding**
- `app/tests/unit/services/queries/working_sections/snapshots/typical_times_no_spec_sql.txt`

## 5. Ordered tasks

1. `_typical_item_filter.build_item_match(spec)` per **§3A C2–C5**. The per-field predicate
   table with each field's NULL/unknown row; `needs_category_join` is
   `spec.major_categories is not None`; the conjunction is **`coalesce(<conjunction>,
   FALSE)`** at the top; **join predicates live in `ON`, never in the statement's `WHERE`**.
   `predicate is None` exactly when `spec.is_narrowing` is `False`.
   The explicit `IS NOT NULL` in the range rows is load-bearing: it is what makes
   `(None, None)` mean "the dimension is recorded". Write that in the function's docstring.
2. `typical_times_statement` gains `specs: Sequence[TypicalFilterSpec] = ()` as a second
   keyword-only parameter. **`now` keeps its existing name, position among keywords and
   default** (§4A K1) — this signature is what four callers already compile against.
3. **`len(specs) == 0` takes a branch that returns today's statement, character for
   character** (HC-4). This is a branch producing the old statement, not a convention. No
   joins, no extra columns, no narrowed aggregates.
4. `len(specs) == K >= 1` returns the keyed shape of **§4A K2** — seven columns, `spec_index`
   positionally indexing the caller's sequence, **exactly one row per (live non-deleted
   working section × spec_index)**, sections with no qualifying history included with counts
   `0` and seconds `NULL`.
   **Shape is a function of `K`, never of `is_narrowing`** (§4A K3): a non-narrowing spec at
   index `k` gets the constant `TRUE` match, emits no item joins of its own, and yields
   `narrowed_* == section_*`.
5. The two-population `FILTER` arithmetic of **§4A K4**, composed exactly as written. **The
   min-sample rule is applied per population, against that population's own count** — today
   the module has one `sample_count` local reused by both the count column and the `CASE`
   threshold (`get_working_section_typical_times.py:47, :50`), and the obvious copy-paste is
   to reuse it for the narrowed `CASE` too. That copy-paste is C6's mutation.
6. Choose an internal execution strategy (§4.2: K× `bool_or`+FILTER pairs, or GROUPING SETS
   where every spec is a pure single-column equality — exactly the V1 profile). **Neither
   strategy name appears in any domain object or API.** If a spec-count ceiling forces
   chunking, `log()` the split — never a silent cap. Record the chosen strategy per shape in
   the measurement doc.
   Whichever attachment you pick, the same three behavioural obligations bind (§4A K4):
   section columns invariant to specs (C5), per-group `SUM` invariant to specs (C9), a
   primary-less task in `section_*` and not in `narrowed_*` (C7).
7. `emit the ItemCategory join iff any spec needs it`, and only those specs' predicates
   reference it (§3A C4).
8. **The §12 measurement matrix — corrected shapes, and no acceptance threshold**
   (**D26 / intention §12A**, owner ruling 2026-08-22).
   **Batch size: 20 tasks, not 50.** 50 is the API cap
   (`get_task_budget_allocations._MAX_TASK_IDS`); the **frontend paginates task queries at
   20**, so 20 is the operating point and 50 is a ceiling nobody currently reaches.
   Measure the **current** and the **new** statement at five shapes: single task;
   **20 tasks × 5** distinct primary-item categories; **× 10**; **× 20**; and the no-spec
   shape (expected: identical plan, since C1 pins identical SQL). **That is the ten.**
   Plus **one extra row, new statement only: 50 × 20**, labelled *API ceiling, not a
   realistic page* — recorded for the freezing decision, not compared against anything.
   **Seed size (L21 — "representative" is an adjective for a mechanism, charter rule 5):**
   the harness fixes and records exact cardinalities — sections, tasks per section, steps
   per task, distinct item categories, and the span of `latest_closed_at` across the
   90-day window — with **every section clearing `TYPICAL_MIN_SAMPLE_SIZE`**, or the
   measured query returns `NULL` typicals and measures the wrong plan.
   **State which cells are constant by construction** (L22, §12A): the *current* statement
   is spec-blind, so its cost is the same query in all five of its rows, and the *new*
   no-spec row equals it by C1 — **five of the ten cells are copies, and unrecorded a
   reviewer cannot tell a measurement from a copy.**
   Write plans, timings, seed cardinalities and the chosen internal strategy per shape into
   `planning/query_cost_measurements.md`. The harness lives at
   `app/tests/integration/services/queries/working_sections/_narrowing_seed.py` and is
   **committed** — an uncommitted harness makes the numbers unreproducible (L20).
   **Acceptance: no number blocks this phase** (D26). The gate is that all ten cells are
   present, honestly labelled, and reproducible. But a result an **order of magnitude
   outside expectation is surfaced to the owner as information** — not gated, not silently
   filed. If a measurement embarrasses a strategy, the strategy is swapped **behind
   `typical_times_statement`** — domain objects, resolution semantics and every §7 response
   contract stay unchanged. **No caching layer is the remedy** *within this pipeline*; the
   owner's frozen-snapshot direction is a later, separate piece of work (§12A).
9. Tests per §6. Update the tracker row and the Review log.

## 6. Tests / acceptance criteria

### C0 — inherited: close the parser boundary for the families phase 1 left open

**Carried here from phase 1's re-review (N7).** Phase 1's S2 fix closed
`_optional_values` for **scalars** — `str`, `bytes`, `int`, `float`, `bool` all raise
`ValidationError`. This phase builds the route, so the parser stops being a deferred
surface and becomes a public contract; the same *"structurally satisfies the annotation"*
reasoning that produced S2 applies to what remains. **Measured on the approved phase-1
tree — none of these is reachable through master plan §6.8's typed-router grammar today,
which is why they were not a phase-1 defect:**

| input | today | why it matters here |
|---|---|---|
| `bytearray(b"ab")`, `memoryview(b"ab")` | `frozenset({'97','98'})` | the byte-wise analogue of exactly the defect S2 closed |
| `{"cat_a": 1, "cat_b": 2}` | `frozenset({'cat_a','cat_b'})` — iterates keys | a dict silently reads as its keys |
| `{"can_have_upholstery": "yes"}` | a **narrowing** spec whose field is the string `"yes"` | this family takes **any object verbatim** — no guard at all |
| `{"major_categories": {"wood": 1}}` | `frozenset({WOOD})` from a dict's keys | — |
| `{"major_categories": "wood"}` | `ValidationError` — but **only accidentally** | every `ItemMajorCategoryEnum` value is multi-character; **add a one-character member and the round-1 defect silently reopens on this family** |

*Contract:* every parameter family rejects what it cannot legitimately receive, and the
boundary is stated **per family** — `can_have_upholstery` accepts only `bool | None`;
the repeatable families accept only a non-`str`/`bytes` iterable of scalars; the enum
family rejects a bare `str` **explicitly**, never by accident of member length.
*Rows:* one per shape in the table above, plus the phase-1 rows (o)(p)(q) which must
continue to pass.
*Mutation:* remove the `can_have_upholstery` type check → the `"yes"` row flips from
`ValidationError` to a narrowing spec; shorten a test enum member to one character in the
`major_categories` row's fixture → the bare-`str` row flips from `ValidationError` to a
silently narrowed spec.
*Standing rule this earned (master plan §9):* **"reject the malformed input" is
per-family, and families drift apart.** A criterion fixing a boundary for one family
enumerates the others and says which are in scope and which are deferred.

---

Hypothesis scope for mutations: L1 = `test_typical_item_filter.py` /
`test_typical_times_narrowing.py` / `test_typical_times_sql_identity.py`. C7, C8 and C9 name
cross-file bite sets and run at L2 (`tests/unit/services/queries/working_sections/` +
`tests/integration/services/queries/working_sections/`).

**C1 — HC-4: the no-spec form still compiles to the committed snapshot, at both clock forms
(T11).** Plan 1's `test_typical_times_sql_identity.py` runs unchanged, plus a third row:
`typical_times_statement("ws_snapshot", specs=())` equals the same snapshot.
*Mutation* — `typical_times_statement` (definition): make the item joins unconditional.
*Both sides* — contract: all three strings equal the snapshot; mutation: each gains
`LEFT OUTER JOIN task_items …` and `LEFT OUTER JOIN items …`, and all three rows go red.
*Perimeter*: the snapshot file itself is unchanged in this phase's `git diff`. Verified by
the reviewer's perimeter check, not by a test.

> **⚠ What a green C1 does and does not prove (plan-1 review, S3, measured 2026-08-22).**
> The snapshot is compiled **without `literal_binds`** — correct, because with it the
> 90-day cutoff inlines and the assertion becomes a clock race. The consequence is that
> **every bound value is invisible to this instrument**: the percentile, the sample
> floor, the cutoff, the step-state filter and the workspace id all render as `%(...)s`
> placeholders. Measured on the plan-1 tree: changing `func.percentile_cont(0.5)` to
> `0.6` leaves the compiled string **byte-identical** and C15 passes; the control
> (`latest_closed_at >= cutoff` → `> cutoff`, a structural change) reddens it.
> So a green C1 means **"the no-spec branch's SQL *shape* is unchanged"** — not "the
> no-spec branch behaves identically". "The typical is a median" and "the population is
> COMPLETED steps" are guarded by **nothing** in phases 1–2.
> `TYPICAL_WINDOW_DAYS` / `TYPICAL_MIN_SAMPLE_SIZE` are separately guarded by plan 1's
> C16(b); the percentile and the state filter are not.
> **Therefore:** if this phase touches the percentile, the state filter or any bound
> value of the no-spec branch, C1 will not catch it — say so in the Review log and cover
> it with an integration row against real rows, never with C1 alone.

**C2 — the result shape is a function of `K`, never of `is_narrowing` (§4A K3).**
Rows, asserting the **exact column-name tuple** each time:
(a) `specs=()` → `("client_id", "name", "sample_count", "typical_worker_seconds")`.
(b) `specs=(TypicalFilterSpec(),)` (non-narrowing, K=1) → the seven-column tuple.
(c) `specs=(narrowing,)` → the seven-column tuple.
(d) row (b)'s `narrowed_sample_count == section_sample_count` and
`narrowed_typical_worker_seconds == section_typical_worker_seconds` for every section.
*Mutation* — `typical_times_statement` (definition): branch the shape on
`any(s.is_narrowing for s in specs)` instead of `len(specs)`.
*Both sides* — contract row (b): 7 columns; mutation: 4 columns, and the row raises when the
test reads `spec_index`.
*Defect caught*: a caller that dedupes 50 tasks' specs would take a different parsing branch
on a data-dependent condition — whether every derived spec happened to be empty. A
first-order silent failure.

**C3 — row cardinality is total.** Fixture: 3 live sections (one with no qualifying
history at all) + 1 soft-deleted section, `K = 2`.
Assert exactly `6` rows; `{(r.client_id, r.spec_index) for r in rows}` has 6 members; the
soft-deleted section appears in **none**; the history-less section appears **twice** with
`section_sample_count == 0`, `narrowed_sample_count == 0` and both seconds `None`.
*Mutation* — `typical_times_statement` (definition): change the outer join from
`WorkingSection` into an inner join on `grouped_steps`.
*Both sides* — contract `6` rows and the history-less section present; mutation `4` rows and
that section absent.
*Defect caught*: today's outer-join-from-`WorkingSection` behaviour, silently lost per index.

**C4 — `spec_index` positionally indexes the caller's own sequence.**
Fixture: `specs = (chair_spec, table_spec)`; history has 6 qualifying chair groups and 2
table groups in section A.
Assert `spec_index` values are exactly `{0, 1}`; the row at `spec_index == 0` has
`narrowed_sample_count == 6`; at `spec_index == 1`, `== 2`.
*Mutations*:
(i) `typical_times_statement` (definition): emit the specs in reverse order → contract
`spec_index 0 → 6`; mutation `spec_index 0 → 2`.
(ii) **absence, module-scoped, terms stated**: neither `_typical_item_filter.py` nor the
statement's source contains `hashlib`, `sha1`, `sha256`, `md5`, `fingerprint` or `digest`.
*Defect caught*: a mis-keyed row silently attributes one item category's history to another
task — Critical rank 2 of the inventory.

**C5 — the `section_*` columns are spec-independent (T25).** Fixture: narrowed population
6, section population 20 in one section, `K = 2` with two different narrowing specs.
Assert `section_sample_count == 20` at **every** `spec_index`, and equal to the `K == 0`
call's `sample_count` for the same section; likewise `section_typical_worker_seconds`.
*Mutation* — `typical_times_statement` (definition): apply the item match as a `WHERE`
instead of inside the aggregate `FILTER`.
*Both sides* — contract `20` at every index; mutation `6`.
*Defect caught*: the observable form of §4.2's "FILTER, never WHERE" rule, and what makes
§4B's subset claim true. T18 today covers only the primary-less-task case; this is the
general form.

**C6 — the narrowed `CASE` threshold reads the narrowed count (T22, §4A K4).**
Rows: (a) section population 70, narrowed 2 → `narrowed_typical_worker_seconds is None` and
`section_typical_worker_seconds` is an `int`. (b) narrowed count exactly
`TYPICAL_MIN_SAMPLE_SIZE` → non-`None`. (c) narrowed count `TYPICAL_MIN_SAMPLE_SIZE - 1` →
`None`.
*Mutations, one per sub-check*:
(i) `typical_times_statement` (definition): compare `section_sample_count >=
TYPICAL_MIN_SAMPLE_SIZE` inside the narrowed `CASE` → **row (a)** flips `None` → a
two-sample median (an `int`). Rows (b), (c) do not bite.
(ii) same (definition): `>=` → `>` in the narrowed `CASE` → **row (b)** flips non-`None` →
`None`. Row (c) does not.
*Defect caught*: a narrowed median published from 2 samples is exactly the HC-3 violation
this feature exists to prevent. This is the SQL-layer sibling of plan 1 C7's policy-branch
mutation.

**C7 — LEFT-not-INNER, and join predicates confined to `ON` (T18, T18b, §3A C5).**
Fixture: history in section A containing `N` qualifying tasks, exactly one of which has **no
active primary item**.
Assert `section_sample_count == N` **with** a narrowing spec and **without** one, and
`narrowed_sample_count == N - 1`.
*Mutations, one per sub-check* — all in the statement / `_typical_item_filter` (definition):
(i) `outerjoin` → `join` on `TaskItem` → contract `section_sample_count = N`; mutation `N-1`.
(ii) move `role == PRIMARY` from the `ON` clause into the statement's `WHERE` → contract
`N`; mutation `N-1`.
(iii) move `removed_at IS NULL` from the `ON` clause into the `WHERE` → contract `N`;
mutation `N-1` on a fixture whose one primary-less task instead has a **removed** primary.
*Defect caught*: converting the LEFT into an effective INNER silently drops primary-less
tasks from the **section-wide** population as well. T18's own `outerjoin → join` mutation
does not produce forms (ii) and (iii), which are the likelier slips.

**C8 — no fan-out (T19, repaired).** F-B's partial unique index makes at most one active
primary per task; the criterion asserts the **value**, not only the count, because with the
item joins inside the `grouped_steps` subquery the count stays `1` under the defect.
Rows: (a) a task with one PRIMARY + **two secondary items of the same category** as the
primary → `narrowed_sample_count` counts it once **and** the section's narrowed median is
`S`, not `3S`. (b) a task with one PRIMARY + **one secondary of a different category** →
membership is decided by the primary alone: the task is in the primary's category population
and **not** in the secondary's.
*Mutation* — `_typical_item_filter` / the statement (definition): drop the `role == PRIMARY`
predicate from the `TaskItem` `ON` clause.
*Both sides* — contract (a): count `1`, median `S`; mutation: median `3S` under the
inner-attachment strategy, count `3` under the outer one — **the median assertion bites
under either**. Contract (b): the task is absent from the other category's narrowed
population; mutation: present.
*Note*: the original T19 ("counts once in both populations") was inert under
inner-attachment. Do not re-introduce it.

**C9 — the per-group `SUM` is identical with and without specs (T26).**
Fixture: a task with one **removed** primary item and one current one, its section total `S`.
Assert the group's contribution to the section median is `S` and `section_sample_count`
counts it once, with `specs=()` and with `K=1`.
*Mutation* — the statement / `_typical_item_filter` (definition): drop `removed_at IS NULL`
from the `TaskItem` `ON` clause.
*Both sides* — contract: group sum `S`, count `1`; mutation: `2S` under inner attachment,
`count(task_id) = 2` under outer attachment. **Bites under either strategy — which is why
this row exists.**

**C10 — the per-field predicate table, one row per field, each with its NULL/unknown row
(§3A C2, T20).** Each row's fixture makes its own predicate the ONLY reason its outcome
holds.
| # | spec field | in the narrowed population | out |
|---|---|---|---|
| a | `item_category_ids={chair}` | chair item | table item · item with `item_category_id IS NULL` |
| b | `major_categories={SEAT}` | item whose category is SEAT | item whose category is WOOD · item with **no** category (outer-joined `ItemCategory` is NULL) |
| c | `width_cm=(60, 80)` | width 60 · width 80 | width 59 · width 81 · width `NULL` |
| d | `height_cm=(60, 80)` | height 70 | height `NULL` |
| e | `depth_cm=(60, 80)` | depth 70 | depth `NULL` |
| f | `can_have_upholstery=True` | `True` | `False` |
| g | `designers={"Aalto"}` | designer `Aalto` | designer `Eames` · designer `NULL` |
| h | `width_cm=(None, None)` | item with **any recorded** width | item with width `NULL` |
| i | `item_category_ids={chair,stool}` **and** `width_cm=(60,80)` | chair, width 70 | chair, width 90 (AND across fields) · sofa, width 70 |
Rows (a)/(g)/(i) also assert the OR-within-a-collection half: a `stool` item is **in** under
row (i)'s spec.
*Mutations, one per sub-check* — all in `_typical_item_filter.build_item_match` (definition):
(i) drop the `IS NOT NULL` conjunct from the range rows.
**⚠ CORRECTED 2026-08-23 (re-review N-d) — the bite set written here was wrong, and this
mutation had never been run by any round.** Measured: dropping `column.is_not(None)` from
`_range_predicate` reddens **row (h)** (`assert 0 == 5`) and the unit structural row
`test_recorded_dimension_range_requires_a_non_null_dimension` — **rows (c), (d) and (e)
stay green.** Why: `column.is_not(None)` on a NULL column evaluates to **FALSE, not NULL**,
so for a *bounded* range the conjunction is already definitely FALSE with or without the
conjunct, and the `coalesce` never sees a NULL to convert. **The conjunct is load-bearing
only for the unbounded `(None, None)` case** — exactly what `build_item_match`'s docstring
says and exactly what row (h) tests. Rows (c)/(d)/(e)'s NULL entries are **enumeration of
the contract, held structurally at the unit layer**, not mutation-discriminating; a fixture
cannot separate the explicit conjunct from SQL's three-valued logic for a bounded range.
*(The control: `coalesce(<conjunction>, FALSE)` → `TRUE` reddens nine rows — every one whose
"out" entry is a missing item or missing category — and (c)/(d)/(e) stay green there too.)*
(ii) emit `TRUE` for `(None, None)` instead of `IS NOT NULL` → **row (h)** flips its
NULL-width entry out → in, and that section's `narrowed_sample_count` doubles from the
recorded-width count to the whole population.
(iii) join the fields with `or_` instead of `and_` → **row (i)** flips `sofa, width 70`
out → in.
(iv) `IN` → `NOT IN` on `item_category_ids` → **row (a)** flips both directions.
*Both sides* are exact-literal `narrowed_sample_count` values per row.

**C11 — `coalesce(<conjunction>, FALSE)` — STRUCTURALLY HELD.**
The behavioural clause **cannot be observed today**: three-valued logic gives the same answer
as `FALSE` inside `count(...) FILTER (WHERE …)`, so no fixture can separate them. It stops
giving the right answer the first time anyone writes `NOT item_match`, and nothing would
fail.
*Interim instrument (automated)*: assert the compiled predicate returned by
`build_item_match` for a narrowing spec is a `coalesce` over the conjunction — i.e. the
string `coalesce` appears in `str(predicate.compile(dialect=postgresql.dialect()))`.
*Named trigger that converts this into a real assertion*: **the first predicate anywhere
that negates the item match** (a `NOT item_match`, an `is_(False)` on it, or an
`ANSWER_AS_ASKED` complement query). At that moment this criterion gains a behavioural row:
a primary-less task must be **excluded** from the negated population too, not included via
`NULL`.
*Both sides for the interim instrument* — contract: `coalesce` present; mutation (remove the
wrapper, definition): absent.

**C12 — the `ItemCategory` join is emitted iff some spec needs it (§3A C4).**
Rows, over the compiled string: (a) `K=2`, neither spec sets `major_categories` →
`"item_categories"` absent. (b) one of the two sets it → present **once**. (c) both set it →
present **once**.
*Mutation* — `typical_times_statement` (definition): emit the `ItemCategory` join
unconditionally → **row (a)** flips absent → present.
*Defect caught*: an unconditional third join on every narrowed call, which §12's measurement
would then be measuring instead of the design.

**C13 — the four existing consumers are untouched in this phase.**
(a) `get_working_section_typical_times` calls the statement with **no `specs` argument**, and
its serialized payload for a seeded workspace is unchanged key-for-key and value-for-value
(D24).
(b) The existing suites `test_typical_times_query.py`, `test_production_time_query.py`,
`test_budget_allocations_query.py`, `test_price_scenario_query.py` and
`test_live_clock_goldens.py` are green with **no edits**.
*Mutation* — `get_working_section_typical_times` (call site): pass a narrowing spec from the
service → the statement returns the K≥1 shape and the service's `row.sample_count` read
raises `AttributeError`.
*Both sides* — contract: the 7-key payload rows; mutation: `AttributeError`. A raise is a
legitimate bite, and it is recorded as one.

### §12 — conditional acceptance (NOT a criterion)

Charter rule 1 says acceptance criteria are met by automated tests. The §12 measurement is
**not** dressed up as one: it is a **conditional-acceptance gate the reviewer checks against
the document**. `planning/query_cost_measurements.md` must carry **all ten** measurements —
five shapes × {current statement, new statement} — each with its plan, its timing, and the
chosen internal strategy for that shape. Fewer than ten rows, or ten rows that do not name
their shape and statement, is a gate failure. The automated companion already exists: C1
pins the no-spec SQL identically, which is why the no-spec shape is expected to show an
identical plan.

---

## 6A. Projection fold — criteria corrections (2026-08-22)

The plan-2 projection (AMENDMENTS_REQUIRED, 33 ledger rows, 13 reality checks, 1 owner
card) tried to turn every §6 criterion into a test and found **nine of fourteen not
writable as worded**. Because this is the **first tests-first phase**, the implementer
hits each of these in the first hour — which is exactly the value the decidability check
was supposed to pay out, cashed one step earlier than usual.

**These corrections win over §6 wherever they differ.** Six criteria are untouched and
transcribable as written: **C2, C4, C5, C6, C7, C11**.

### The recurring defect: a fixture too small to show the thing it checks

**C8 row (a), C9 and C13(a) all assert a median that their own fixture cannot produce.**
`narrowed_typical` / `section_typical` are `NULL` below `TYPICAL_MIN_SAMPLE_SIZE`
(`get_working_section_typical_times.py:49-52`), so a **one-task** fixture yields `None`
on both the contract and the mutation side. And at exactly five groups, tripling **one**
of them leaves the median where it was — `median({S,S,S,S,3S}) = S`.
**Every fixture in this phase that asserts a typical value enumerates its groups, clears
the floor, and states why the mutation moves the median.** Recommended shape: five
qualifying groups all carrying the fan-out shape, so the mutation moves every element.

### Per criterion

| # | Correction |
|---|---|
| **C0** | *(the criterion I folded in from plan 1's re-review — my text, and the weakest in the table.)* Its table gives each input's value **today**, not its required **outcome**, and the *Contract* sentence does not decide two of the rows: a `dict` and a `bytearray`/`memoryview` are both non-`str` iterables of scalars (L2). **Decide them: `bytearray`/`memoryview` → `ValidationError`** (they are the byte-wise analogue of the defect S2 closed); **a bare `dict` → `ValidationError`** (silently reading a mapping as its keys is the same class of accident). State the expected outcome per row, and give rows 1, 2 and 4 a named mutation each (L3). Reword "This phase builds the route" → **"builds the spec→SQL path"** — §6.8 defers the route and §1 forbids consumer changes (L4). Add **§6 C14** of plan 1 to §2's read-first: C0 requires rows (o)(p)(q) to keep passing and they live there, not in C15 (L30). |
| **C1** | The mutation *"make the item joins unconditional"* **cannot redden** the branch task 3 mandates: item joins exist only on the `K ≥ 1` path, and `len(specs) == 0` returns before reaching them. This is §11A's T11 repair reappearing one phase later. **The mutation becomes "delete the `len(specs) == 0` branch"**, sending the no-spec call through the general builder (L5). Keep plan 1's C15 mutation (delete `WorkingSection.is_deleted.is_(False)`) as the structural control. **Parametrize the three rows** — they are currently sequential asserts in one function, so "all three go red" is unobservable; the first failure hides the rest (L7, charter rule 12). |
| **C3** | "no qualifying history at all" → **"no COMPLETED task_steps at all"**. With merely *old* steps the section survives the inner-join mutation and the mutation is inert (L8). |
| **C8** | Enumerate row (a)'s fixture per the floor rule above (L9). **The closing claim "the median assertion bites under either" is false** (L10): under **outer** attachment the three joined `task_items` rows multiply the *row count*, not `group_seconds` — the median over three equal values is still `S`, and the **count** assertion (1 → 3) is what bites; under **inner** attachment the median moves (S → 3S) and the count does not. Row (a) asserts both and is safe, but say which assertion bites on which strategy. |
| **C9** | Same fixture enumeration (L11). **Label the `specs=()` half a control, not a sub-check**: with no specs the statement emits no item joins, so dropping `removed_at IS NULL` from an `ON` clause that does not exist changes nothing (R7). A control is legitimate; reading as two biting sub-checks is not. |
| **C10** | Add a **`can_have_upholstery=False`** row — a *set* field that is falsy, so `if spec.can_have_upholstery:` drops the conjunct silently; same shape for a **zero lower bound** on a range (L12). This is the highest-value non-blocking row in the ledger. Give rows (b), (f), (g) one mutation each (L13). Add one line assigning criteria to files: C10's both-sides are `narrowed_sample_count` literals, so it is an **integration** criterion, and the unit file's only enumerated content is otherwise C11 (L14). |
| **C12** | **The instrument counts the wrong thing** (L15): the substring `item_categories` appears in the `LEFT OUTER JOIN` **and** inside `item_categories.major_category IN (…)`, so "present **once**" is false under the *contract*, not only under the mutation. **Count `LEFT OUTER JOIN item_categories`.** Row (a) ("K=2, neither sets `major_categories`") is satisfiable by two **empty** specs that emit no joins at all — vacuous; **require both specs to narrow on another field** (L16). |
| **C13** | **(a) is the load-bearing repair in this fold.** C1's boxed limitation defers every bound-value change to an integration row, and C13(a) is that row — but it names **no baseline** for "unchanged key-for-key and value-for-value", and does not require the seeded workspace to **clear the sample floor**. A workspace with four qualifying groups answers `typical_worker_seconds: null` for every section, and a `percentile_cont(0.5) → 0.6` mutation leaves the payload identical (L17, R8). **Pin the expected payload explicitly, and require ≥ `TYPICAL_MIN_SAMPLE_SIZE` qualifying groups.** (b) omits an existing consumer: `test_phase2_live_surfaces.py` imports `typical_times_statement` (`:37`), asserts on its compiled params (`:986-989`), executes it against a real session (`:1377-1380`) and monkeypatches the module's bound `datetime` (`:1394`) — **add it** (L18, R9). |
| **C4** | Mutation (ii) is an **absence assertion wearing a mutation's label**, and it is module-scoped where §6.6 claims "anywhere in this pipeline". Restate it as its own criterion row with root and term set (L29). |
| **C2** | Row (d) asserts `narrowed_* == section_*` — an equality between two computed values. Assert **both against the literal count** (master plan §9; L32). Non-blocking. |

### Strategy taxonomy — one axis, not two

Task 6 offers §4.2's axis (`bool_or` pairs vs GROUPING SETS) while C8/C9's both-sides are
stated on **§4A K4's** axis (inner vs outer attachment). **K4's axis is the one the
criteria bind** (L23). Two further consequences:

- **GROUPING SETS as named cannot produce K2's total cardinality** — a section with no
  rows for a category emits no row; it needs an outer cross join plus a `LEFT JOIN`, which
  the plan does not describe. **Drop the option for V1**, or state the extra machinery.
  C3 is the guard either way (L24).
- **Ship one strategy this phase.** "The chosen internal strategy *per shape*" means that
  if more than one ships, only the one the tests' spec profile triggers is covered
  (charter rule 10). One strategy, or a criterion per strategy (L25).

### Where the K-multiplication hazard actually lives — and which criterion owns it

Worked out on paper by the projection: both attachments are constructible and neither
multiplies the section-wide aggregates, **provided `spec_index` is materialised as a cross
join in the OUTER select and added to its `GROUP BY`** —
`FROM working_sections CROSS JOIN (VALUES (0),(1),…) AS s(spec_index) LEFT OUTER JOIN
grouped_steps … GROUP BY ws.client_id, ws.name, s.spec_index`. Every `(section,
spec_index)` group then sees the same `grouped_steps` rows, so `section_sample_count` is
constant across indices by construction.
**The failure mode** is introducing `spec_index` *inside* `grouped_steps` without adding
it to that subquery's `GROUP BY`, which multiplies `SUM(total_working_seconds)` by K.
**C5 is the guard** — it pins `section_sample_count == 20` at every index *and* against
the `K == 0` call, so a K-multiplication reddens it. Recorded here so the implementer
knows which criterion owns the phase's sharpest hazard.

### Delegated in writing (free choices, not gaps)

- **`build_item_match`'s `(bool, predicate | None)` tuple stays.** The projection checked
  whether the bool is dead and concluded it is not: `needs_category_join` is not derivable
  from the predicate without walking the expression tree, and keeping it is what preserves
  the "only module that knows Task → primary TaskItem → Item" boundary (§4.2). One gap
  worth closing cheaply: no criterion asserts the bool directly — C12 asserts only its
  statement-level consequence.
- **Under outer attachment the `TaskItem` `ON` clause needs `workspace_id`, which
  `grouped_steps` does not select** (L27). Implementer's choice: pass it as a bound
  parameter, or add the column to the subquery. `K ≥ 1` only, so **C1 is unaffected**
  either way — say which you chose in the handoff.

### Recorded, not fixed here

- **`uix_task_items_primary_active` is untested repo-wide** (L33, R10). It appears in the
  model (`task_item.py:53`), in two migrations, and in docs — **no test references it** —
  yet plan §2's fan-out-free claim rests on it. Its shape does match §3A C5's `ON` clause
  exactly, so the claim is true today; it is simply unguarded, and C8/C9 would catch a
  *code* change but not the index being dropped. **One criterion row** (a second active
  primary raises `IntegrityError`, or the index exists with its `WHERE`) — cheap, and this
  is the phase that depends on it.
- **§7's docs-guard instruction is a no-op** (L31, R11): the guard's roots are
  `docs/domains/item_economics/` and the app/backend roots, and
  `query_cost_measurements.md` lands under `docs/architecture/under_construction/`. Kept
  as harmless habit; do not read a green guard as having checked this doc.
- **Routed upstream, not an implementer blocker:** §3A C5's `ItemCategory` join carries
  neither `workspace_id` nor `is_deleted IS FALSE`, though `Item`'s join carries both and
  `item_categories` has both columns (`item_category.py:19-21`, `:41`) — **a soft-deleted
  category still satisfies `major_categories`** (L28, R12). Folded to intention §3D.

---

## 7. Notes

- **F-B is the boundary of the design, not an incidental fact.** Narrowing is defined
  against the active PRIMARY item only; generalizing to secondary items breaks the
  no-fan-out guarantee and is out of scope by ruling (D8).
- **§2B S-7:** "the task's section ids" means two different sets — production-time scopes
  the statement to **every** step's section; price-scenario to the **participating** sections
  only. That difference belongs to plans 4 and 5; this phase must not narrow the statement's
  own scoping to one of them.
- **§2B S-2** (the published `item_id` and the loaded primary `Item` can differ) is resolved
  in §6A A3 and belongs to plan 3. This phase never derives a spec.
- PostgreSQL permits `FILTER` on ordered-set aggregates and the current statement already
  relies on it, so **no CTE is forced** by K4's composition.
- Before writing `planning/query_cost_measurements.md`, run the docs guard:
  `PYTHONPATH=. pytest tests/unit/docs/`.

## 8. Review log

*(append-only; shared by implementer and reviewer)*

- **2026-08-22 · projection round 0 · Opus 5 · AMENDMENTS_REQUIRED → folded same day.**
  33 ledger rows (9 blocking), 13 reality checks, **1 owner card — answered**
  (`handoffs/reviewer/20260822_plan2_projection_handoff.md`). The design held: the
  two-population arithmetic, the item join and HC-4's byte-identity are all sound and no
  settled decision reopened. **The criteria table did not: nine of fourteen criteria were
  not writable as tests as worded**, and since this is the first tests-first phase the
  implementer would have hit every one in the first hour — the decidability check paying
  out exactly as intended, one step earlier than usual.
  **Owner card → D26:** no acceptance threshold; the card's 50-task premise was wrong
  (the frontend paginates at 20), few categories exist, and the architectural fix is
  scheduler-refreshed frozen typicals. Folded as intention **§12A** + task 8.
  **All 33 rows routed:** intention §12A and **§3D** (the `ItemCategory` join asymmetry,
  recorded with a conversion trigger, §3A C5 unchanged); §4 gains the four undeclared
  paths plus the committed measurement harness; and **§6A** carries the per-criterion
  corrections — chiefly C1's inert mutation (it cannot redden the `len(specs)==0` branch
  task 3 mandates — §11A's T11 repair reappearing one phase later), C12's instrument
  counting a substring the predicate also contains, C13(a) unable to discriminate the
  bound-value changes C1's own limitation defers to it, and the recurring
  fixture-below-the-sample-floor defect in C8/C9/C13. State → `PROJECTED`.
- **2026-08-22 · implementation round 1 · Codex · IMPLEMENTED.** Task 0 transcribed the
  corrected criteria into parser, predicate, snapshot, integration, and measurement
  tests before production edits. Implemented C0 and the outer `spec_index` statement
  with active-primary item matching; focused perimeter and named mutation probes are
  green on the repaired tree. The committed cost document carries all ten matrix cells
  plus the 50×20 API-ceiling row. Checkpoint and handoff follow.
- **2026-08-23 · coordinator consumption of implementation round 1 · CHANGES_REQUESTED
  before review.** The **code is sound and the conditional acceptance is met**: the K-spec
  shape is exactly §6A's mandated form (outer `VALUES` cross join, `spec_index` in the
  outer `GROUP BY`), C1 ships three parametrized rows against the corrected mutation, C0's
  five parser rows all landed, C12's corrected instrument landed, C9 is built as specified,
  and `query_cost_measurements.md` carries all eleven rows with the five copies disclosed
  and no threshold claimed. The snapshot file is untouched in the diff.
  **What did not land is mutation evidence and two fixtures that cannot fail** — seven
  named mutations across C1/C6/C7/C10 were never run, and:
  **(K1, measured)** C5's `section_typical_worker_seconds` half — the plan's closing
  "likewise" clause — was not transcribed, so **the criterion §6A designated as the owner
  of the K-multiplication hazard does not catch it**. Measured by mutating the `K ≥ 1`
  `group_seconds` SUM to `* 2`: three tests in the file reddened and
  `test_spec_index_preserves_input_order_and_section_population_is_constant` was **not**
  among them. The hazard is covered, but accidentally, by C8/C9 — not by its guard.
  **(N1)** C2 row (d) asserts `narrowed_typical == section_typical` on a **one-task**
  fixture, so both sides are `None`: the exact fixture-below-the-floor defect §6A opens
  with, reappearing inside a criterion §6A called transcribable as written.
  **(N2)** C8's median half is inert as §6A predicted (all six groups seed `seconds=100`,
  so a fan-out cannot move the median); the count half bites, and the required
  "say which assertion bites on which strategy" disclosure is absent.
  **Not a phase-2 regression, routed out:** the L4 stamp's three extra failing IDs are in
  `test_user_work_profile_clock_in_code.py` (predates this phase, `b0f35b1`), whose
  `_two_workspaces` helper reads whatever workspaces leaked into its xdist worker. Phase 2
  touched no fixture or conftest; adding one integration **file** re-partitioned
  `--dist loadfile`. **The 21-ID baseline is not stable under adding a test file** — a free
  measured datapoint for `test_isolation_xdist` phase 3's perturbation gate.
  Fix round 2 dispatched; state stays `IMPLEMENTED`.
- **2026-08-23 · fix round 2 · Codex · consumed, → `REVIEWING`.** All seventeen prompt
  items closed: seven named mutations run with both sides and failing ids, C5 reseeded to
  the plan's own fixture (6 narrowed / 20 section, seconds 10…143) asserting **literal**
  count `20` and median `76` at every index *and* against the `K == 0` call, C2(d) reseeded
  to five groups with literal typicals `30`, C3 restored to 3 live + 1 soft-deleted / 6
  rows, C7 gained its removed-primary variant, C10 gained the `True` upholstery row and the
  `80` boundary, and the harness's false `history_span_days: 90` became
  `history_age_days: 1` + `window_days: 90` without re-running the matrix.
  **Verified at source, not from the ledger:** the production diff across the whole fix
  cycle (`git diff d5731c3 HEAD -- app/beyo_manager/`) is **empty** — "tests only" measured,
  never accepted as asserted. **K1's repair independently confirmed with a *different*
  mutant shape than the one the implementer ran:** `percentile_cont(0.5) → 0.9` in the
  `K ≥ 1` section aggregate moves the section median while leaving every count untouched,
  and it reddens `test_spec_index_preserves_input_order_and_section_population_is_constant`
  — the criterion that survived the identical class of mutation in round 1. The guard is
  armed, not merely re-worded.
  **Two disclosures carried into review rather than closed.** (i) C8 took option (b): the
  six-identical-`100`s fixture stands and the median is documented as a control while the
  count assertion bites — authorised, and the reviewer should judge it. (ii) C13(b)'s
  "covered by the L2 run" is imprecise: the L2 run was `working_sections/`, which holds
  **one** of the six consumer suites; the other five are in `item_economics/` and rest on
  the L4 stamp, which is green. True via L4, loosely stated.
  **The L4 nondeterminism is now measured, and it matters more than either stamp.** Round 1
  stamped 24 failed including the clock-in-code trio; round 2 stamped 21 with a ∅/∅ delta
  and the trio absent — **same tree**. At `HEAD` the trio still fails **3/3 in isolation**.
  So the trio's presence in a full-suite run is decided by xdist scheduling, and **round 2's
  clean ∅/∅ delta is partly luck, not evidence of a stable baseline**. Recorded for the
  reviewer and routed to `test_isolation_xdist`.
- **2026-08-23 · review round 1 · Opus 5 · CHANGES_REQUESTED → fix round 3.**
  0 blocking / 5 should-fix / 5 recorded / **2 owner cards, both now answered** (D27, D28).
  **The production code is correct and the reviewer found no defect in it** — §4A K4
  transcribed exactly, the narrowed `CASE` reading its own count, §6A's K-shape making the
  K-multiplication structurally unreachable, the perimeter exactly plan §4's declared paths,
  the snapshot untouched, and fan-out freedom confirmed **at the database** by reading
  `uix_task_items_primary_active` out of the migrated template rather than off the model.
  **The round is owed for instruments, not behaviour — three guards cannot fail:**
  **S1** the `K ≥ 1` branch's population definition is guarded by nothing; C5 *looks* like
  the cross-branch guard but no fixture seeds a step that is deleted, non-`COMPLETED`,
  marked wrong or outside the window, so all four filters were deleted one at a time and the
  L2 set stayed green (62 passed) each time. **S2** `narrowed_typical_worker_seconds` is
  never asserted at any `spec_index ≥ 1`: mis-keying the *typical* coalesce bit nothing,
  while the same mutation on the *count* coalesce reddened three tests — the C4 defect
  ("one item category's history attributed to another task") live on the value column.
  **S3** C0's bare-`str` enum row matches a substring both the explicit and the accidental
  rejection produce, so it passes with its own guard deleted; and C0's **second** named
  mutation was declined in round 2 as "covered by the round-1 ledger row", which it is not.
  **S4 — coordinator routing call, decided:** the shipped `K ≥ 1` column order is the
  reverse of §4A K2's prose. **The shipped order stands**; the intention is amended as
  **§4A K2-a** (column order is not contractual, the set and names are, read by name never
  by position), and plans 3 and 6 now read it. Re-ordering verified production code to match
  prose buys nothing. **S5** the §12 matrix is eleven *cumulative* measurements presented as
  eleven isolated ones — one paragraph owed, no re-measurement (D26 sets no threshold).
  **My own framing was refuted, which is the result.** The reviewer spent its L4 on the
  serial `-n 0` comparator and got the **identical 21-ID set**: the baseline is *not*
  nondeterministic on a fixed tree, round 2's clean delta was not luck, and round **1**'s
  24-failure stamp is the outlier. The trio fails only when run **alone** — it needs leaked
  state a full run supplies. Master plan §9 corrected; the residue for
  `test_isolation_xdist` is composition-dependence, not randomness.
  **Both cards answered same day:** D27 routes the one-active-primary rows to plan 3 (two
  rows — the DB index *and* the untested `add_item_to_task` guard, unguarded at both
  layers); D28 authorizes a scoped maintenance session to adjudicate the seven-item graph
  queue. N3 routed to plans 3 and 6. State → `CHANGES_REQUESTED`.
- **2026-08-23 · fix round 3 · Codex · consumed, → `REVIEWING` (delta re-review).** All
  seven items closed with **no production code change** — re-measured, not accepted:
  `git diff 0107c82 HEAD -- app/beyo_manager/` is empty. C5 gained four non-qualifying rows
  (marked-wrong, deleted, `PENDING`, 91 days old, all with distinctive seconds 200–203) and
  keeps its literals `20`/`76` plus the cross-branch equality; a new
  `test_each_spec_index_selects_its_own_narrowed_typical` pins **distinct literal medians
  30 and 80** at indices 0 and 1; C0's bare-`str` row pins `must be a sequence of values`
  and both enum fixtures now derive from the member value; C8's inert median line was
  **deleted** (count retained, 6 → 17 under fan-out); N4's NULL width seeded; S5's paragraph
  written; S4 correctly left alone.
  **Verified with four probes at shapes nobody had run:**
  (A) *negating* the `K ≥ 1` marked-wrong filter (`is_(False)` → `is_(True)`) rather than
  deleting it — **21 failed**, so S1's population guard holds against inversion too.
  (B) mis-keying the typical coalesce by **reversing** the spec order rather than collapsing
  it to index 0 — **exactly one test failed**, the new S2 guard, and nothing else: the gap
  it was written for is precisely the gap it closes.
  (C) **the contract-side form nobody ran** — shortening `ItemMajorCategoryEnum.WOOD` to one
  character with the explicit guard *left intact*: **43 passed**. That is C0's actual claim
  ("rejects a bare `str` explicitly, never by accident of member length") demonstrated
  positively; the pre-fix defect would have silently narrowed here.
  (D) **a residual of my own, refuted.** I suspected every `K ≥ 1` fixture had median == mean
  (C5's 10…143, C2(d)'s and S2's 10–50 / 60–100), so a `percentile_cont(0.5) → avg()` swap
  would be invisible. Measured on the `K ≥ 1` branch only: **C5's test reddens.** The phase
  does discriminate a median from a mean. Recorded because the suspicion was reasonable and
  the answer is a fact, not an opinion.
  **Graph queue adjudicated in parallel under D28** (`88092c6`, `731cc06`): six approved,
  one rejected and re-recorded, **left pending for the owner** exactly as instructed. Graph
  measured independently by the coordinator: **198 nodes / 298 edges, 1 pending / 2 stale /
  0 diagnostics** — matching the session's report. The two sessions did not interfere: the
  fix checkpoint `8718092` precedes both maintenance commits and the graph delta was not in
  its perimeter. Master plan §8's stale "0 pending / 0 stale" is corrected and dated.
- **2026-08-23 · fix round 2 · Codex · IMPLEMENTED.** Closed the evidence and fixture
  findings without changing production query behavior. C5 now seeds 20 section groups
  (6 narrowed) with a non-flat median and asserts literal `20` / `76` section values at
  every `spec_index` and in the K=0 control; its `group_seconds * 2` probe reddened
  `test_spec_index_preserves_input_order_and_section_population_is_constant` (alongside
  the expected dependent value guards). C2(d) now clears the sample floor and asserts
  literal count `5` and typical `30`. C3 is the enumerated 3-live-plus-1-deleted,
  6-row fixture. C7 gained the removed-primary variant. C10 retains both upholstery
  boolean rows, seeds width `80`, and makes the category NULL case asymmetric so the
  `NOT IN` probe cannot preserve the count. The measurement harness now labels one-day
  history as `history_age_days: 1` alongside `window_days: 90`; the matrix was not rerun.
  The seven previously missing mutations were run at their prescribed L1/L2 scopes with
  both sides and failing IDs recorded in the handoff. C8 chose the accepted outer-
  attachment disclosure: its count assertion bites, while the equal-seconds median is a
  documented control. C13(b)'s five existing suites plus `test_phase2_live_surfaces.py`
  remained green without edits. The known three out-of-perimeter clock-in-code IDs remain
  diagnosed and routed to `test_isolation_xdist`. State remains `IMPLEMENTED` pending
  review; checkpoint and handoff follow.

- **2026-08-23 · review round 1 · Opus 5 · CHANGES_REQUESTED.** 0 blocking / 5 should-fix /
  5 recorded / 2 owner cards
  (`handoffs/reviewer/20260823_plan2_review_handoff.md`). **The production code is correct
  and carries no defect**: §4A K4's arithmetic is transcribed exactly, §6A's mandated
  K-shape (outer `VALUES` cross join, `spec_index` in the outer `GROUP BY`) makes the
  K-multiplication hazard structurally unreachable, the `K == 1` bypass is equivalent to the
  coalesce path and the count-0/NULL boundary through it is exercised at `K = 2`, all three
  joins are 1:1, the perimeter is exactly §4's declared paths, and the snapshot is untouched.
  The round is owed for **instruments, not behaviour** — three guards cannot fail.
  **S1 (should-fix): nothing guards the `K ≥ 1` branch's population definition.** Both
  branches declare their own `grouped_steps`; C1 freezes only the no-spec shape. Four probes
  at L2, one per sub-check, each deleting one filter from the `K ≥ 1` branch alone —
  `recorded_time_marked_wrong`, `state == COMPLETED`, `is_deleted`, and `qualifying →
  true()` — **each returned 62 passed / 1 skipped, no bite**. C5's cross-branch equality
  against the `K == 0` call is the intended guard, but every fixture seeds only qualifying
  steps, so it has nothing to discriminate. Fix: four discriminating rows in C5's fixture,
  four named mutations with bite ids.
  **S2: `narrowed_typical_worker_seconds` is never asserted at any `spec_index ≥ 1`.**
  Mis-keying the **typical** coalesce (`index == position` → `index == 0`) → 62 passed, no
  bite; the same mutation on the **count** coalesce → 3 failed. The count column is pinned
  per index, the value column is not. Under the mutant, index ≥ 1 returns `NULL` and index 0
  inherits a later spec's median whenever its own count is below the floor — C4's own
  *Defect caught*, on the value rather than the key. Fix: one `K = 2` row where both indices
  clear the floor with different medians, asserting literals.
  **S3: C0's `{"major_categories": "wood"}` row cannot tell an explicit rejection from an
  accidental one** — the defect it exists to close. Removing `str` from
  `_optional_categories`'s isinstance guard → **43 passed, no bite**: both messages contain
  the family name the `match=` pins. Compounding — C0 names two mutations, round 1 ran one,
  and round 2's "justified by round-1 tree-bound ledger row" does not cover the second
  (§9's ledger-count rule, second firing this phase; charter rule 14). Fix:
  `match="must be a sequence of values"`.
  **S4: the shipped `K ≥ 1` column order is the reverse of intention §4A K2's**, and C2 —
  which requires "the exact column-name tuple" — pins the shipped one. Nothing wrong on the
  wire; silent drift on a Critical-ranked mechanism's contract. Recommend amending §4A K2 to
  the shipped order plus one line that order is not contractual.
  **S5: `query_cost_measurements.md` reads as eleven isolated measurements; it is eleven
  cumulative ones** — `collect_measurement_matrix` seeds every case on one session with no
  cleanup, so the last row is measured against 232 seeded rows. Visible in its own numbers
  (the same query at position 5 vs 10: 0.060 vs 0.087 ms). No re-measurement — D26 sets no
  threshold and §12's conditional acceptance is otherwise met in full; one disclosure
  paragraph is owed (cumulative positions, no `ANALYZE`, `BUFFERS` dropped).
  **Recorded:** N1 `uix_task_items_primary_active` — deferral **judged acceptable** after
  reading the index out of the migrated template (`role = 'primary' AND removed_at IS NULL`,
  exact match for §3A C5), routed to plan 3; N2 C13(b) confirmed green at L4 under a
  different topology; N3 C11's trigger is well stated but **routed to nobody** — no
  downstream plan's Read-first carries intention §3A or C11; N4 C10 row (c)'s NULL entry not
  transcribed; N5 the graph's test evidence span drifted to a different test in round 2.
  **Owner card 1 answered same day: executed by phase 3.** Asked to explain it, I found the
  rule has a *second* guard — `add_item_to_task` pre-checks and raises `ConflictError` — and
  **no test file in the repo references `add_item_to_task`**, so the one-active-primary rule
  is unguarded at **both** layers. Nothing miscounts today (both guards work; the index was
  read out of the migrated template). Plan 3 buys **two** rows, not one: the `IntegrityError`
  on a second active primary, and the `ConflictError` from the command. Card 2 (graph queue:
  7 pending items, 2 stale nodes, one carrying N5's stale span) stays open.
  **Evidence.** Round 2's stamps consumed by citation (matching SHA). One L4 spent on
  variation per the environment section's named comparator: `pytest -m 'not e2e' -n 0`,
  default slot, Redis `PONG`, tree `90c2490` clean → **21 failed / 2659 passed / 2 skipped
  in 129.80 s, ∅/∅ against the approved 21-ID set**. **The serial and parallel failing sets
  are identical**, so round 2's ∅/∅ was not scheduling luck; the trio fails only when run
  *in isolation*, and round 1's 24 is the outlier. Seven mutation probes, all shapes nobody
  had run, applied-and-reverted, checksums verified. State → `CHANGES_REQUESTED`.

- **2026-08-23 · fix round 3 · Codex · IMPLEMENTED.** Closed review round 1's five
  should-fix items and the enumerated N4/C8 follow-ups without changing production code:
  C5 now contains four independently non-qualifying steps and asserts literal `20` / `76`
  values plus cross-branch equality; a new K=2 row pins narrowed medians `30` and `80` at
  both indices; C0 pins the explicit enum-boundary message and its bare-string fixture is
  derived from the enum member for the one-character mutation; C10 row (c) seeds a NULL
  width; C8 keeps its biting count assertion and deletes its inert equal-100 median line;
  and the measurement document discloses cumulative seeding, default-estimate costs,
  unrecorded buffers, and the undecidable 1.9× explanation. C2's shipped tuple was
  confirmed against §4A K2-a; no column order was changed. Mutation ledger, L4 stamp,
  perimeter, and checkpoint are in the round-3 implementer handoff.

- **2026-08-23 · delta re-review round 2 · Opus 5 · APPROVED.** 0 blocking / 0 should-fix /
  4 notes / 1 owner card (`handoffs/reviewer/20260823_plan2_rereview_handoff.md`).
  **Perimeter verified**: `git diff 0107c82 HEAD` is ten files across three declared write
  perimeters (fix round 3, the D28 maintenance session, the coordinator) and nothing else;
  `-- app/beyo_manager/` empty, and the three probe files' SHA-256 are **byte-identical to
  the round-1 declaration**, so the round-1 production audit stands unrevisited.
  **S1 CLOSED AND BITING FROM BOTH SIDES.** Three rounds mutated only the `K ≥ 1` copy;
  S1's hazard is *divergence between two builders* and is symmetric, so the no-spec copy
  was cut: deleting `TaskStep.is_deleted.is_(False)` from
  `_no_spec_typical_times_statement` alone → **4 failed** — C1's three snapshot rows **and**
  C5 on `assert base.sample_count == 20` → `21 == 20` (base median drifted 76 → 80). The
  duplicated populations are now pinned to each other by literals in both directions.
  *(N-a: the appended `section_sample_count == base.sample_count` line is a tautology given
  the two literals above it — harmless, but it is not the instrument.)*
  **S2 CLOSED AND BITING at a third shape.** Not a mis-key: the narrowed **value** column
  made to publish the **section** median (`case((index == position, section_typical))`) →
  **exactly one test failed**, the new guard, `assert 55 == 30`. That is Critical rank 2's
  literal shape ("a section-wide median published as `item_narrowed`") and before this round
  nothing in the phase caught it.
  **S3 CLOSED.** Both named mutations ran; the coordinator's contract-side probe (one-char
  member, guard intact → 43 passed) demonstrated C0's claim positively. My round-1
  prediction that the same change would arm the `{"wood": 1}` mapping row was **wrong and
  measured wrong**: removing `Mapping` from the guard → **`DID NOT RAISE`**, so that row's
  bite never depended on its `match=` string. Residue not real.
  **S4 CLOSED as decided — §4A K2-a judged sufficient on content** (shipped tuple printed
  verbatim, "read by name never by position", the `SectionTypicalEvidence` third-order
  argument, lettered insertion renumbering nothing). **N-b, routing:** K2-a is named in
  **plan 3's** Read-first — the one plan that never calls the statement (0 `spec_index`,
  0 `narrowed_*`) — while **plan 4** gets it only by adjacency inside "§4A K1–K4" and
  **plan 5**, which calls `typical_times_statement(..., specs=…)`, reads "§4A K1" only and
  is **not covered by either route**. N3's shape recurring on S4's own amendment.
  **S5 CLOSED** — the paragraph carries all four owed disclosures; no re-measurement, per D26.
  **N4 CLOSED as enumeration; the new row CANNOT FAIL, and C10's mutation (i) is wrong.**
  Measured: dropping `column.is_not(None)` from `_range_predicate` → **2 failed**, row (h)
  `recorded-width` and the unit structural row; **rows (c)/(d)/(e) green**. The
  `coalesce(…, FALSE)` → `TRUE` shape → **9 failed**, again none of (c)/(d)/(e). Cause:
  `is_not(None)` on NULL is **FALSE, not NULL**, so for a *bounded* range the conjunction is
  already definitely FALSE and the conjunct is load-bearing only for `(None, None)` — as
  `build_item_match`'s docstring says. §6 C10's mutation (i) claims rows (c)/(d)/(e) flip;
  **it has never been run by any round** (round 2's ledger carries (ii)/(iii)/(iv)) and my
  round-1 N4 restated it from that ledger instead of measuring it. **Note, not should-fix:**
  nothing breaks on the wire, the contract is held structurally by
  `test_recorded_dimension_range_requires_a_non_null_dimension` (which *did* bite), and the
  correction is prose in §6 C10 → **N-d, coordinator fold.**
  **C8 closed by deletion**, correctly — the only assertion removed was one already measured
  inert, and the value column it nominally covered is now pinned by S2's biting test.
  **D27's rows judged: they would catch what N1 describes**, and (a) is stronger than the row
  recommended — it enumerates the index's *partiality* (two removed primaries, primary +
  related, both legal). **N-c → plan 3's projection:** the criterion does not determine
  whether the legal inserts precede the `IntegrityError` or sit in a savepoint; on an aborted
  transaction that decides whether the row proves anything.
  **Graph:** the D28 session executed exactly its authorization and self-approved nothing.
  Two stale nodes diagnosed cheaply and they differ in kind — `typical_filters._optional_values`
  78–88 is **span-accurate, content-changed** (a re-accept), while
  `budget_division._governing_step` 188–208 has **drifted** (the function now starts at 182;
  the window straddles two other functions) and needs a re-anchor; last touched by `f904100`,
  a neighbouring pipeline. Neither is authorized by D28 → **one owner card**; the pending
  re-record needs no second card. Nothing adjudicated by this session.
  **Evidence: L4 runs 0**, authorized because the tree difference is **measured** test-inert
  (no test references `archgraph`; `tests/unit/docs/` reads only the *item_cost_calculation*
  folder). Round-3 stamp consumed by citation and corroborated arithmetically (+1 passed
  = the one added test; L2 62 → 63), and the L2 figure independently reproduced inside the
  probes themselves (4+59 = 63, 1+62 = 63) with no redundant contract-side run. **Five
  mutation probes, every one a shape no prior round ran**, applied-and-reverted,
  checksum-verified. **⚠ The approval-gate L4 is still owed on the tree actually committed
  at the gate** — citing round 3's stamp there would be the mirror-image violation.
  State → `APPROVED`.
- **2026-08-23 · coordinator gate · PHASE 2 APPROVED.** Four re-review notes folded:
  **N-b** — §4A K2-a routed into the Read-first of **plan 4** (named explicitly, not left to
  adjacency) and **plan 5** (a consumer that read only §4A K1 and would have missed it
  entirely). **N-c** — plan 3's C-N1(a) now carries the undetermined question in writing:
  after an `IntegrityError` PostgreSQL aborts the transaction, so the criterion must say
  whether the two legal shapes insert **before** the violating one or inside a savepoint;
  routed to plan 3's mandatory projection. **N-d** — plan 2 §6 C10's mutation (i) prose is
  **corrected in place**: it reddens row (h) and the unit structural row, **not** rows
  (c)/(d)/(e), because `column.is_not(None)` on a NULL yields FALSE rather than NULL and a
  bounded range is already definitely FALSE without it. **N-a** — recorded only: C5's
  trailing `section_sample_count == base.sample_count` is a tautology given the literals
  above it; the literals are the instrument.
  Six standing rules earned into master plan §9 (symmetric hazards mutate both operands; a
  never-run mutation's bite set is a claim that decays; `IS NOT NULL` semantics inside a
  bounded conjunction; route an amendment to its consumers; arm-or-delete with the coverage
  named; plus the corrected baseline reading).
  **Approval-gate L4, run by the coordinator on the tree in this commit** — the reviewer
  correctly flagged that citing round 3's stamp here would be the mirror-image over-evidence
  violation, since the gate commit adds this entry, the tracker row and thirteen archive
  moves. Command `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`,
  Redis pre-check `PONG`. Result **21 failed / 2661 passed / 1 skipped / 2 warnings** in
  48.12 s. **Delta against the approved 21-ID set: added ∅, removed ∅** — diffed
  programmatically (`comm` against §7 of the live-clock frontend handoff), 21/21, not by eye.
  *(A first attempt carried `-p no:logging` and reported 35 errors; the flag removes the
  `caplog` fixture. My instrumentation, not the tree — recorded because a stamp taken with a
  non-authoritative command is exactly the kind of number that would otherwise be explained
  away later.)*
  Thirteen phase-2 rows archived to `archive/plan_2/`. The mechanism-inventory gate rows and
  the D28 maintenance rows stay **live** — the first because §2 cites it as a standing source
  of truth, the second because the graph queue is still open (one entry pending owner
  adjudication, one owner card for the two stale links). State → `APPROVED`.

