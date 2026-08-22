---
plan: 1
role: reviewer
round: 0 (projection — gate, mandatory)
state: PROJECTED
verdict: AMENDMENTS_REQUIRED
date: 2026-08-16
pipeline: simple_production_budget_division
actor: Claude Opus 5 (1M context)
---

# Projection round 0 — plan 1 (typical times + budget allocations)

## Summary

The plan is buildable and the two mechanisms are sound — I ran the real typical-times
query against the live workshop database and it produced sensible per-section numbers
in two milliseconds, so nothing here needs a database change or a performance rescue.
But the plan is not yet safe to hand to an implementer: twenty-two things it leaves
undecided would each be settled silently in code, and four of them are the kind of
silent that ships wrong numbers. One decision genuinely needs you — everything else
the coordinator can settle from the recommendations below. Verdict:
**AMENDMENTS_REQUIRED**; the implementer prompt should wait for the ledger to be routed.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — May the new allocations endpoint live inside the item-cost surface?

**Question.** Mount the allocations endpoint alongside the existing item-cost
endpoints (touching three closed v1 files), or give it its own separate address?

**Story.** You told us this feature must stay independent — deleting it should leave
zero trace. The natural address for it sits inside the item-cost family, and that
family is guarded: a test written during v1 counts exactly twenty-three addresses and
fails the moment a twenty-fourth appears. So the natural address costs three small
edits to closed v1 files. The separate address costs nothing there, but the frontend
then learns two unrelated URLs for one task card, and the day someone asks "where do
step allowances come from?" the answer stops being obvious.

**Branches.**
- *Inside item-cost* — one new URL in the family the frontend already calls; three
  added lines in v1 files, each removable in one edit if the feature is ever deleted.
- *Separate address* — v1 stays byte-untouched; the frontend carries a second base URL
  forever, and the published contract changes before it ships.

**Recommendation.** Inside item-cost. The v1 test's own note says adding a route is
*meant* to require editing those three places — that friction is the design, not a
wall — and the additions are three lines, not a coupling.

**On silence.** The gate holds; the implementer prompt is not compiled. No guess.

**Trace.** intention HC-1 and §5 (E2), master plan §4 routes, plan_1 T5, finding B1.

## Write perimeter (full, declared)

- **Documents written:** exactly this file.
- **Code written:** none.
- **Tool-recorded state:** none. `archgraph_status` + two `archgraph_search_nodes`
  calls for the §8 orientation only (read-only; graph revision unchanged at
  `a0667c77…`, 176 nodes / 265 edges, 0 stale, 6 pending reviews pre-existing and
  untouched). No `apply_changes` — a projection ships no delta.
- **Database:** read-only. `SELECT` and `EXPLAIN (ANALYZE)` against the configured
  `beyo_manager` database only; no writes, no DDL, no fixtures created.
- Nothing in `planning/`, `plans/`, `master_plan.md`, or `app/` was modified.

## Decision ledger

| id | severity | decision the artifacts do not determine | classification | routing |
|---|---|---|---|---|
| B1 | BLOCKING | E2's mount forces edits to three closed v1 files; HC-1 forbids them | intention gap | owner card 1 → intention HC-1 + §5 |
| B2 | BLOCKING | `B_seconds` is fractional; P-SUM unsatisfiable as contracted | intention gap (no contract) | intention §4 (M2) + new criterion |
| B3 | BLOCKING | M2 undefined when `Σw = 0` (empty allocated set; all-zero typicals) | intention gap (no contract) | intention §4 (M2) + new criteria |
| B4 | BLOCKING | fallback median undefined for even sibling counts; arithmetic type unpinned | intention gap (no contract) | intention §4 (M2) |
| P1 | PLAN-FIX | C9/C9b/C9c/C10 pin values the min-sample rule forces to NULL | plan gap | plan_1 criteria |
| P2 | PLAN-FIX | `round_half_even` has no criterion and a `::numeric` trap | plan gap + intention pin | plan_1 + intention §3 (M1) |
| P3 | PLAN-FIX | C9 cannot discriminate `percentile_cont` from `percentile_disc` | plan gap | plan_1 C9 |
| P4 | PLAN-FIX | no criterion proves the 90-day window *excludes* | plan gap | plan_1 M1 criteria |
| P5 | PLAN-FIX | C7's named mutation cannot bite (median == mean for two values) | plan gap | plan_1 C7 |
| P6 | PLAN-FIX | C5 misses the tie case that is 100% of production; unsafe sort key | plan gap | plan_1 C5 |
| P7 | PLAN-FIX | E1 is shadowed by an existing parameterized route | plan gap | plan_1 T5 + master plan §4 |
| P8 | PLAN-FIX | two DB-backed test files misfiled under `tests/unit/` | plan gap | master plan §4 |
| P9 | PLAN-FIX | T3's status path narrower than the branch it must mirror | plan gap | plan_1 T3 |
| P10 | PLAN-FIX | C14's named fixture is broken; one fixture cannot prove constancy | plan gap | plan_1 C14 |
| P11 | PLAN-FIX | `routers/README.md` updates owned by no task | plan gap | plan_1 T5 |
| P12 | PLAN-FIX | repeatable query params have zero precedent in this repo | free choice | delegate explicitly in master plan §4 |
| N1–N12 | NOTE | see below | mixed | coordinator judgement |

---

## BLOCKING findings

### B1 — E2's mount collides with a v1 tripwire; HC-1 cannot hold as written

Adding `GET /tasks/budget-allocations` to `app/beyo_manager/routers/api_v1/item_economics.py`
turns an existing, currently-green test red the moment the decorator lands:
`app/tests/unit/routers/test_phase9_item_economics_route_mirror.py:118`
(`test_router_source_matches_the_hand_written_route_and_role_set`) parses the router
source's `@router.<verb>` decorators and asserts set-equality against a hand-written
23-row literal at `:34-63`.

Repairing it cascades: adding the row makes `:126-131`
(`test_the_registry_ships_twenty_three_routes`, `assert len(_EXPECTED_ROUTES) == 23`)
red, and `:112` (`test_readme_quick_index_mirrors_every_shipped_route`) demands a
matching Quick Index row in `app/beyo_manager/routers/README.md`. That is three edits
to closed-v1 and hand-maintained artifacts, against intention HC-1 ("no change to …
the item-cost-calculation v1 surfaces closed on 2026-08-15"), plan_1's "zero edits to
closed v1 modules", and master plan §4's "Tests (new files only)".

The collision is real and unavoidable at the contracted URL — but it is *designed*.
The mirror test's own docstring (`:6-8`) reads: "Adding a route means editing three
places — the router, the README, and this list — and that friction is the point."
So the v1 authors anticipated exactly this; what is missing is the authorization.
Owner card 1. The working-sections router has no equivalent mirror, so E1 is unaffected.

### B2 — `B_seconds` is not an integer, so P-SUM is unsatisfiable as contracted

`allowed_worker_minutes` is `Numeric(12, 2)`
(`app/beyo_manager/models/tables/item_economics/item_cost_evaluation.py:39`), written
by `calculate_allowed_worker_minutes` which quantizes to `0.01` with `ROUND_HALF_EVEN`
(`domain/item_economics/calculator.py:296-299`). Intention §4's `B_seconds =
allowed_worker_minutes × 60` therefore has a fractional part whenever the cents value
is not a multiple of 5 — roughly 60% of possible values; `195.01 → 11700.60`.

M2 then requires `Σ allowance_i = D_seconds exactly` with integer allowances. Against a
fractional `D` that is arithmetically impossible, and P-SUM — the phase's headline
property — cannot be stated, let alone tested. No contract says where the quantization
happens or with which rounding.

**Recommended contract (intention §4, M2 inputs):** `B_seconds` is
`(Decimal(allowed_worker_minutes) * 60).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)`
as an `int`, computed **before** `C` is subtracted, matching the house rounding used by
every function in `calculator.py`. Add a criterion whose evaluation carries
`allowed_worker_minutes = 195.01` (→ `B_seconds = 11701`) so the quantization is pinned
by a test; no current criterion uses a value with a fractional second (C4 explicitly
chooses `B` "so no rounding residue").

### B3 — M2 is undefined when `Σ w_j = 0`

Two independently reachable routes:

**(a) Empty allocated set with `D > 0`.** `force_task_ready` skips every *open* step
(`services/commands/tasks/force_task_ready.py:74-79,155-173`) — a task where nothing
had been completed lands with every non-deleted step in the excluded set. A task whose
steps were all removed is the same shape with an empty universe. Then `r_i = D × w_i /
Σ w_j` divides by zero, and P-SUM ("allowances sum to `D`") is false against an empty
sum. Intention §4 says nothing about this case.

**(b) All allocated typicals resolve to 0.** `typical_worker_seconds` is a rounded
median of group sums; a section whose median group total is 0 yields a legal `0`. Every
weight is then 0 and `Σ w_j = 0` again — but this time the weight-fallback ladder never
fires, because the typicals are *not* NULL.

**Recommended contract (intention §4, M2 weights + P-SUM):**
1. Read the first weight rule as `w_i = t_i if t_i is not NULL **and t_i > 0**` — this
   folds case (b) into the existing median/equal-split fallbacks with no new branch.
2. State that with an empty allocated set no allowances are produced and `D` remains
   undistributed, and restate P-SUM as holding *when the allocated set is non-empty*.
3. Add criteria for both: a task with only excluded steps and `B > 0`, and a task whose
   every allocated typical is 0 (must degrade to the equal split, not divide by zero).

### B4 — the fallback median is undefined for even sibling counts, and the arithmetic type is unpinned

Intention §4: `w_i = median of the allocated set's non-NULL t_j`. With an even number of
known siblings — two known typicals is the *common* case — "median" is ambiguous between
the interpolated mean of the two middles and the lower middle. Unspecified.

More dangerous: nothing pins the arithmetic type of the weight/raw-share/fractional-part
computation. C5 is the phase's rule-6 heart and turns on *exactly equal* fractional
parts. In IEEE-754 doubles, two mathematically equal fractions can differ in the last
bit, so the `(sequence_order, client_id)` tie-break would fire or not depending on
values — P-DET becomes untestable and C5 becomes nondeterministic.

**Recommended contract (intention §4, M2):** weights, raw shares and fractional parts
are computed in exact rational arithmetic (`fractions.Fraction`) — no float anywhere;
weights are not rounded (only allowances are). Under that arithmetic, define the
even-count fallback median as the interpolated mean of the two middle values.

---

## PLAN-FIX findings

### P1 — four M1 criteria pin values the min-sample rule forces to NULL

`TYPICAL_MIN_SAMPLE_SIZE = 5` (master plan §4; intention §3: "NULL if sample_count < 5").
But C9 expects `1200` from three groups, C9b expects `4200` from one group, C9c expects
a full sum from one group, and C10's exclusion rows are implicitly small. Every one of
those fixtures returns `typical_worker_seconds: null` under M1 as contracted, so none of
the four criteria can be written as stated.

**Recommendation.** Pad each fixture to ≥5 qualifying groups with a shared filler helper,
choosing filler values so the group under test *is* the median — then the assertion still
pins the exact quantity the criterion is about. Worked example for C9b: fillers
`{1000, 2000, 5000, 6000}` plus the target group (3600 first pass + 600 rework in one
task+section) → sorted `{1000, 2000, 4200, 5000, 6000}` → median `4200`. The named RED
mutation (drop the `(task_id, working_section_id)` GROUP BY) splits the target into 3600
and 600 → six samples → median `(2000+3600)/2 = 2800 ≠ 4200`, so the mutation still bites.

### P2 — the `round_half_even` clause has no criterion and one silent trap

Measured on the configured database (PostgreSQL 18.4):

- `percentile_cont(0.5)` over integer input returns **`double precision`**, not numeric.
- `round(900.5::double precision) = 900`, `round(901.5::double precision) = 902` — PostgreSQL's
  double `round` **is** half-even.
- `round(900.5::numeric) = 901`, `round(901.5::numeric) = 902` — numeric `round` is
  half-away-from-zero.
- Python's `round()` is half-even.

So SQL-on-double and Python both satisfy the contract, and a `::numeric` cast — a natural
reflex in a repo whose serialization contract is decimal-to-string — silently changes the
tie behaviour by one second. No criterion exercises an interpolated `.5` at all (C9's
three-value set is odd, so no interpolation and no rounding happens).

**Recommendation.** Pin in intention §3 (M1): round the `double precision` value with SQL
`round()` or Python `round()`; never via `::numeric`. Add a criterion with ≥6 qualifying
groups whose two middle values differ by an odd number of seconds, so the median lands on
`.5` and half-even is pinned by a test. That fixture also resolves P3.

### P3 — C9 cannot discriminate `percentile_cont` from `percentile_disc`

Measured: over `{600, 1200, 6000}` both return `1200`; they diverge only on even counts
(over `{600, 1200}`, cont → `900`, disc → `600`). C9's only named mutation is `avg`,
which does bite (2600 ≠ 1200) — but an accidental swap to `percentile_disc` sails
through. The even-count fixture from P2 closes this.

**On the prompt's cont-vs-disc question:** keep `percentile_cont`. The interpolated value
is a legitimate median, and M2 consumes typicals only as *ratios*, where interpolation is
strictly better behaved than the lower-middle bias of `disc`. No change to M1's wording is
needed beyond P2's rounding pin.

### P4 — no criterion proves the 90-day window *excludes*

C9c proves an old-first-pass group is *admitted* through group-level `MAX(closed_at)`.
Nothing asserts the negative: a group whose latest close falls outside the window must
vanish entirely and must not appear in `sample_count`. Intention §9 explicitly asks for a
"window edge" fixture. Add the negative row.

### P5 — C7's named mutation cannot bite

C7: "one step's section typical `null` among two known ⇒ its weight is the median of the
known two. RED: substitute mean for median." For two values the median *is* the mean, so
the mutation leaves the test green — charter rule 11 decoration. Use ≥3 known siblings
(odd count): `{600, 1200, 6000}` → median `1200`, mean `2600`.

### P6 — C5's tie-break fixture misses the case that is 100% of production

Measured on the configured database: `sequence_order` is NULL on **3032 of 3032**
`task_steps` rows. The contract tie order `(sequence_order ASC NULLS LAST, client_id ASC)`
therefore degenerates to `client_id ASC` for every real task today, and C5 as written
(which implies a fixture that *sets* `sequence_order`) would exercise a branch production
never reaches.

Worse, the natural Python sort key `(step.sequence_order, step.client_id)` sorts correctly
when every value is NULL — tuple comparison short-circuits on `None == None` — and raises
`TypeError: '<' not supported between instances of 'int' and 'NoneType'` the first time a
manager orders steps. Verified both behaviours directly. A defect that is invisible in
production today and detonates on first use is exactly the rule-6 class this gate exists
for.

**Recommendation.** Enumerate C5 over two rows: (a) both `sequence_order` NULL → the
remainder unit lands by `client_id`; (b) one set, one NULL → the non-NULL sorts first
regardless of `client_id`. Name a mutation per row (reverse to `client_id DESC` bites (a);
dropping NULLS-LAST handling bites (b)). Name the safe key shape in T1:
`(seq is None, seq if seq is not None else 0, client_id)`.

### P7 — E1 is shadowed by an existing parameterized route

`app/beyo_manager/routers/api_v1/working_sections.py:128` declares
`@router.get("/{working_section_id}")`. FastAPI matches in declaration order, so a
`GET /typical-times` declared *after* line 128 resolves to `get_working_section_route`
with `working_section_id="typical-times"` and returns 404.

Master plan §4 and plan_1 T5 carry a declaration-order note for **E2**, where I confirmed
no collision exists today (`item_economics.py` has no two-segment `GET /tasks/{param}`
route — its `/tasks/…` routes are all three-segment). They carry no note for **E1**, where
a live collision does exist. E1 must be declared above line 128; the in-file precedent is
`/me` (`:93`) and `/steps/user-last-active` (`:111`), both placed before the param route
for this reason.

### P8 — the naming registry misfiles two DB-backed test files under `tests/unit/`

`app/pytest.ini` runs `--strict-markers` with distinct `unit` / `integration` markers, and
`tests/unit` is DB-free by convention (`tests/unit/services/queries/item_economics/test_phase9_committed_filter_structure.py`
drives a `SimpleNamespace` fake session). Master plan §4 places
`test_typical_times_query.py` and `test_budget_allocations_query.py` under
`tests/unit/services/queries/…`, but plan_1's criteria header requires them to run against
the configured DB. They belong under `app/tests/integration/services/queries/…`.

The other two files are correctly placed: `test_budget_division.py` tests a pure function,
and the route tests follow `tests/unit/routers/api_v1/test_item_economics_router.py:55-95`,
which is genuinely DB-free (TestClient + `dependency_overrides[get_jwt_claims]` +
monkeypatched `run_service`) and is the exact precedent for C15/C16.

### P9 — T3's status path is narrower than the branch it must mirror

`get_task_budget_status` returns `NOT_EVALUATED` *without calling*
`resolve_item_economics_status` when the task has no PRIMARY item
(`services/queries/item_economics/get_task_budget_status.py:112-114`). T3 says only
"resolve the twelve-value status … via the existing `resolve_item_economics_status` read
path"; followed literally, a task with no primary item produces a wrong status or an
exception. T3 must mirror `get_task_budget_status.py:111-125` in full — item-less →
`NOT_EVALUATED`; otherwise selection + valuation + terms → `resolve_item_economics_status`.

### P10 — C14's named fixture is broken, and one fixture cannot prove constancy

**(a)** The shared `count_queries` fixture (`app/tests/conftest.py:63-76`) binds a
session-scoped engine that resolves before `init_db()` creates it and **raises on first
use** — documented verbatim at
`app/tests/integration/services/queries/users/test_list_users_floor_identification.py:177-179`
("it has no other consumers in the suite"). The working precedent is the *local*
`executed_statements` fixture (same file `:173-193`, and
`tests/integration/services/queries/task_step_acknowledgments/test_reassigned_steps_integration.py:86-100`).
C14 must name the local pattern, not the shared fixture.

**(b)** A single 3-id fixture can only pin a magic number, which any refactor breaks
without meaning. Assert the statement count is **equal** between a 1-task call and a
3-task call, each including an evaluation-less task so the status path runs in both.

### P11 — `routers/README.md` updates are owned by no task

`app/beyo_manager/routers/README.md:3` states it is hand-maintained, that no generator
exists, and that "A route added without editing this file silently rots it". It carries a
Quick Index row *and* a per-route detail section per endpoint. Both E1 and E2 need rows;
for E2 the mirror test enforces it loudly (B1), for E1 nothing does, so it rots silently.
No plan_1 task lists this file. Add it to T5.

### P12 — repeatable query parameters have no precedent in this repo

`grep` over `beyo_manager/routers/` finds **zero** `list[str] = Query(...)` parameters;
every multi-value filter is a comma-separated string parsed in the service layer
(`_split_csv` idiom — e.g. `services/queries/tasks/tasks.py:47`,
`count_task_post_handling_states.py:12`, `list_task_coordination_threads.py:28`).
Intention §5 specifies both `working_section_ids` and `task_ids` as repeatable.

This is a free choice the plan does not grant explicitly. **Recommendation:** keep
repeatable, and record it in master plan §4 as a deliberate first-of-kind so the reviewer
does not file it as a convention break. Reasons: FastAPI validates natively, so C16's cap
is a clean `len(task_ids) > 50`; a CSV parser would add its own untested edges (empty
segments, trailing commas, whitespace). Also pin the degenerate case: `?task_ids=` yields
`[""]`, one unknown id, omitted from the response per §5's batch-read semantics.

---

## NOTES

- **N1 — client-id prefixes in §5's payload examples are wrong.**
  `TaskStep.CLIENT_ID_PREFIX = "tsp"` (`models/tables/tasks/task_step.py:43`), not
  `tstp_`; `WorkingSection.CLIENT_ID_PREFIX = "wsec"`
  (`models/tables/working_sections/working_section.py:11`), not `ws_`. These examples feed
  the two frontend handoffs at closeout (intention §8).
- **N2 — `working_section_name_snapshot` is nullable** (`task_step.py:84`) though 0 of
  3032 rows are NULL today (both writers set it: `commands/tasks/create_task.py:466`,
  `commands/task_steps/add_task_steps.py:130`). Type E2's `section_name_snapshot` as
  `string | null` or coalesce in the serializer — deliberately, either way.
- **N3 — E1/E2 name divergence after a rename is real but harmless to the numbers.**
  E1 serves the live `working_sections.name`; E2 serves the per-step snapshot. Components
  join on `working_section_id`, so nothing numeric skews — only the displayed label can
  differ between the widget and the card. §6's consistency story (about seconds) stays
  coherent; add one line to the frontend handoff.
- **N4 — no new index is needed; measured, not assumed.** The full D9 query on the
  configured database (3032 steps → 1438 groups, 14 sections) runs in **2.2 ms** /
  470 shared buffers via a seq scan + HashAggregate. `ix_task_steps_workspace_task_state`
  does **not** cover M1 — it leads `(workspace_id, task_id)` and M1 has no `task_id`
  predicate — and is not needed. HC-2's migration ban holds with no exception. Re-measure
  if `task_steps` passes ~100k rows.
- **N5 — a `completed` step with `closed_at IS NULL` silently never contributes**
  (`MAX(closed_at) >= cutoff` is NULL, so HAVING drops the group). 0 of 1703 completed
  rows are affected today. Consistent with M1 as literally written; worth one explicit
  sentence so it is a decision rather than an accident.
- **N6 — the `infeasible` / negative-budget path is specified, not accidental.**
  `allowed <= 0 → INFEASIBLE` (`get_task_budget_status.py:150`), and `D = max(0, B − C)`
  clamps a negative `B` to zero: every allocated allowance 0, zero-worked steps
  `on_track`, worked steps `over_share`. Confirmed coherent as contracted — no change
  needed beyond B2's integer pin.
- **N7 — a closeout tripwire, not an implementer one.**
  `tests/unit/docs/test_item_economics_handoff_accuracy.py:179` asserts that no
  `/api/v1/item-economics/…` path appearing in the two v1 frontend handoffs or in
  `docs/domains/item_economics/{api,README}.md` falls outside the 23-route set. The
  production-time handoff that intention §8 targets is **not** scanned, so the planned fold
  is safe — but documenting E2 in the item-economics living-docs folder would turn it red.
- **N8 — `_load_preview_inputs` cannot be reused per task.** It issues 3–4 workspace-wide
  queries per call (`services/commands/item_economics/_common.py:172-216`) → 3N–4N for N
  tasks, defeating T3's constant-query-count requirement. Its three loads are
  item-independent, and `terms` depends only on `applicable_models[0]`, which is likewise
  workspace-level — so hoisting the loads and calling `resolve_economics_selection` per
  item in Python yields a genuinely constant count. Reuse the *pure* functions, not the
  loader. Keep the loader's exact query shape (notably its absence of `ORDER BY`) so E2 and
  budget-status can never select different versions for the same item.
- **N9 — batched evaluation loads are safe.** `uix_item_cost_evaluations_current`
  (`models/tables/item_economics/item_cost_evaluation.py:56`) is unique on `task_id` under
  the committed-current predicate, so `.in_(task_ids)` yields at most one row per task.
- **N10 — fixture precedents to name in the implementer prompt** (there is no shared
  factory module; every helper is local to its file):
  E2 → `tests/integration/services/commands/item_economics/test_phase8_status_results.py:60-84`
  (`_prepared`: real `commit_item_cost_evaluation`, section + step with
  `total_working_seconds` set directly, `commit()`, and an explicit `_cleanup_phase8`
  teardown at `:51-58` — charter rule 11½ done right).
  Step/section shapes → `test_reassigned_steps_integration.py:104-115`.
  Config chain → `test_phase4_fix_coverage.py` local `_actor` / `_group` / `_basis`.
  Routes → `tests/unit/routers/api_v1/test_item_economics_router.py:55-95`.
- **N11 — C13's two doors are constructible without invoking the services, and invoking
  them is expensive.** `remove_task_step` never touches `total_working_seconds` — it closes
  the open state record directly (`:140-148`) and imports no recompute — so a removed step
  retains its fixture value, exactly as C13 assumes. `force_task_ready` requires an open
  `StepStateRecord` for *every* open step or it raises (`:148-152`), and its transition
  emits an async outbox task rather than recomputing inline
  (`_step_transition_core.py:156`), so totals survive there too. Both end-states are
  therefore reproducible as plain rows. Decide deliberately: the cheap path is
  row-constructed fixtures for the E2 assertions **plus** one service-invoking test pinning
  the door mapping (remove → `SKIPPED` + `is_deleted=True`) — without it, C13's name
  outlives the behaviour it claims to guard.
- **N12 — `working_sections.py` is tab-indented**, unlike `item_economics.py` (4 spaces).
  E1's handler must match its own file.

---

## Inventory sweep (waived mechanism-inventory gate, master plan §9)

Every mechanism this phase ships, against the intention's contracts. Three have **no**
contract — the waiver's stated condition fires.

| # | Mechanism | Contract |
|---|---|---|
| 1 | contributing-step predicate (4 exclusions) | ✓ §3 M1 |
| 2 | (task, section) grouping | ✓ §3 M1 (D9) |
| 3 | group value = SUM of contributing steps | ✓ §3 M1 |
| 4 | group window admission on `MAX(closed_at)` | ✓ §3 M1 |
| 5 | admission when `closed_at` is NULL | ✗ → N5 |
| 6 | `sample_count` = COUNT(qualifying groups) | ✓ §3 M1 |
| 7 | min-sample NULL rule | ✓ §3 M1 |
| 8 | median statistic (`percentile_cont`) | ✓ §3 M1 |
| 9 | median → int rounding mode **and locus** | ~ partial → **P2** |
| 10 | section enumeration (all non-deleted) | ✓ §5 E1 |
| 11 | `working_section_ids` filter / unknown ids | ✓ §5 E1 (D5) |
| 12 | `B_seconds` derivation from Decimal minutes | ✗ **B2** |
| 13 | allocated / excluded partition | ✓ §4 M2 (D8) |
| 14 | deletion ≠ exclusion | ✓ §4 M2 + §2.5 |
| 15 | charged `C`, distributable `D`, clamp | ✓ §4 M2 |
| 16 | weight resolution + fallback ladder | ~ partial → **B3**, **B4** |
| 17 | behaviour when `Σw = 0` | ✗ **B3** |
| 18 | arithmetic type / exactness | ✗ **B4** |
| 19 | largest-remainder rounding | ✓ §4 M2 |
| 20 | tie order | ✓ §4 M2 (NULL handling → P6) |
| 21 | `share_state` vocabulary | ✓ §4 M2 |
| 22 | status resolution for evaluation-less tasks | ~ partial → P9 |
| 23 | batch semantics (omission, 50-id cap) | ✓ §5 E2 |
| 24 | serialization (decimal→string, seconds→int) | ✓ §5 + `46_serialization_local.md` |
| 25 | query-param cardinality style | ✗ → P12 |

## Reality checks — citations verified independently

Every intention §2 citation I could check resolves and says what it claims:

- `task_step.py` — `state` :52, `sequence_order` :64, `working_section_id` :65,
  `recorded_time_marked_wrong` :73, `closed_at` :95, `is_deleted` :122, index :129. ✓
  `total_working_seconds` is `Integer NOT NULL default 0`
  (`models/base/aggregate_metrics.py:6`) — no NULL handling needed in SUM.
- `remove_task_step.py:131-138` — `state=SKIPPED`, `closed_at`, `is_deleted=True` in one
  write ✓; open state records closed at `:140-148` ✓.
- `force_task_ready.py:74-79` (skip transitions), `:155-173` (one terminal hop per open
  step) ✓ — §2.5's `:75-78,162` resolves to the same mechanism.
- `get_task_budget_status.py:102-110` (committed-current filter) ✓, `:138-147`
  (non-deleted step sum) ✓.
- `configuration.py:129-169` — `resolve_item_economics_status` ✓ (pure, reusable).
- `routers/http/response.py` envelope, `require_roles` (`routers/utils/jwt_dep.py:41-49`,
  403 on mismatch) ✓.
- Router mounts: `item_economics` at `/api/v1/item-economics`, `working_sections` at
  `/api/v1/working-sections` (`routers/api_v1/__init__.py:74,78-82`) ✓ — intention §5's
  round-3 mount correction is right.
- PostgreSQL **18.4** confirmed on the configured database; `percentile_cont` available ✓.

Two citation corrections, both minor: intention §2.1 attributes the settled-records
docstring to `process_step_transition.py:161` — the mechanism is there, but the projection
did not re-verify the exact line; and §2.5's `remove_task_step.py:131-138` vs the prompt's
`:131-148` describe the same two blocks.

---

## Appendix — non-authoritative

*Measured evidence only. This is not implementation guidance; the implementer derives
their own artifacts from the amended plan.*

The D9 query shape, run read-only against the configured database, returned one row per
non-deleted section — including `weaving` at `sample_count = 0` with a NULL typical, which
is C12's left-join requirement demonstrated on real data — and produced plausible
per-section medians (`cleaning wood` 889 s over 179 groups; `structural repair` 8591 s
over 67). `EXPLAIN (ANALYZE)` on the same statement: 2.2 ms, 470 shared buffers,
seq scan → HashAggregate → hash right join. Raw group counts: 1438 qualifying groups from
1474 contributing steps across 14 sections.

Step-state census used above: 1703 `completed` (229 marked wrong, 0 with NULL
`closed_at`), 1050 `pending`, 253 `skipped`, 26 `paused`; `sequence_order` NULL on all
3032 rows; `working_section_name_snapshot` NULL on none.
