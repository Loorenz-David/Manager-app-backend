# Plan 2 — The statement: spec → predicate, the K-spec result shape, HC-4, and §12

```
plan: plan_2
project: narrow_typical_work_times
state: NOT_STARTED
projection_gate: MANDATORY
acceptance: CONDITIONAL on planning/query_cost_measurements.md carrying all ten rows
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
8. **The §12 measurement matrix — all ten.** Seed a representative 90-day history on a
   disposable database. Measure with `EXPLAIN ANALYZE` (or equivalent) the **current**
   statement and the **new** statement at five shapes: single task; batch of 50 tasks ×
   5 distinct primary-item categories; × 10; × 20; and the no-spec shape (expected:
   identical plan, since C1 pins identical SQL). Write plans, timings and the chosen
   internal strategy per shape into `planning/query_cost_measurements.md`.
   **§12 states no count; ten is the count. A silent subset is a gate failure.**
   If a measurement embarrasses a strategy, the strategy is swapped **behind
   `typical_times_statement`** — the domain objects, resolution semantics and every §7
   response contract stay unchanged. **No caching layer is the remedy.**
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
(i) drop the `IS NOT NULL` conjunct from the range rows → **rows (c), (d), (e)** flip their
NULL entries out → in.
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

*(empty — append-only; shared by implementer and reviewer)*
