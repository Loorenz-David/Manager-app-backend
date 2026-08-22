# Intention: Narrow Typical Work Times (item-aware typicals, one engine, four consumers)

```
status: RESOLVED (round 3, 2026-08-20) — 0 owner cards open. D1–D24 settled
        (card A → D24: typical-times route unchanged in V1; card B → D23: serial,
        live-clock first). Next: **mechanism-inventory gate**.
        **UNBLOCKED 2026-08-22:** D23's precondition is satisfied — every live-clock
        phase touching the shared files is APPROVED and merged (`57d8c25`), and the
        post-live-clock baseline the goldens regenerate against is published. So the
        gate is no longer the only thing that may run; implementation may follow it.
        **⚠ Read §2A first — the grounding drifted while this document waited, and one
        drifted citation is a contract (`typical_times_statement` gained an injected
        clock that §3's proposed signature erases).**
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-19/20 (no raw_intention.md; three
             architecture projection passes, each owner-corrected, preceded this
             document — the corrections are folded, not appended)
date: 2026-08-20
round: 1
```

---

## 1. Objective & hard constraints

Make the **typical work time** of a working section item-aware: history is narrowed
to work comparable to the task at hand (V1: same item category as the task's active
PRIMARY item), through **one centralized engine** that every consumer of typicals
uses — so a worker, a manager, and the budget-division arithmetic can never see three
different "typicals" for the same task and section.

The four hard constraints, in force over every section of this document:

**HC-1 — One definition of "typical".** `typical_times_statement`
(`app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py:21`)
remains the single canonical implementation. No consumer forks, re-implements, or
post-processes the statistic outside the shared domain functions this pipeline adds.

**HC-2 — Cross-service agreement (the hard domain invariant).**
For the same task and section, all task-scoped consumers observe identical
layer-1 statistical evidence and an identical layer-1.5 selected typical —
including identical `None`s. Consumer-specific layer-2 terminals may differ only
where the selected typical is genuinely absent, are never published under
`typical_worker_seconds` or any `*_basis` field, and each consumer's payload makes
the terminal's firing visible on its own surface (§6.4).

**HC-3 — An analytics question is answered as asked.** A narrowed statistical query
must never silently answer with a broader section-wide statistic unless the caller's
resolution policy explicitly permits it. Task economics and analytics share the same
evidence engine and may use different resolution policies because they answer
different questions (§5).

**HC-4 — No-spec behaviour is byte-identical.** With no narrowing spec,
`typical_times_statement` compiles to character-for-character the SQL it compiles to
today, and every consumer that passes no spec produces its current payload
unchanged. This is a branch that produces the old statement, not a convention
(§7.1, test T11).

Non-goals, stated so they are not rediscovered as gaps: no new write path; no
schema migration; no change to `TYPICAL_METHOD`, `TYPICAL_WINDOW_DAYS`, or
`TYPICAL_MIN_SAMPLE_SIZE`; historical-allocation reproducibility explicitly out of
scope (owner ruling, §10 D18); the `/statistics/typical-times` route itself is
deferred with its contract pre-locked (§9).

---

## 2. Grounding (inspected 2026-08-20 — **⚠ SEE §2A: the tree moved on 2026-08-21/22 and one citation below is a contract, not a line number**)

### 2.1 The engine and its four consumers

One query builder exists; three services import it. There is no second typical
implementation anywhere in the codebase.

| Consumer | Call site | Scope applied | Role gate |
|---|---|---|---|
| `GET /working-sections/typical-times` | `routers/api_v1/working_sections.py:131` → `get_working_section_typical_times.py:68` | optional `working_section_ids` | ADMIN, MANAGER, WORKER, SELLER |
| `GET /tasks/{id}/production-time` | `get_task_production_time.py:55` | task's section ids | ADMIN, MANAGER, WORKER, SELLER |
| `GET /tasks/budget-allocations` | `get_task_budget_allocations.py:45` | unfiltered (batch, ≤50 tasks) | ADMIN, MANAGER, WORKER, SELLER |
| `GET /tasks/{id}/price-scenario` | `get_task_price_scenario.py:137` (`_typical_block`) | task's section ids | ADMIN, MANAGER |

The statement (`get_working_section_typical_times.py:21-63`): one sample = one
task's summed `total_working_seconds` in one section (`group_by(working_section_id,
task_id)`), COMPLETED + not-deleted + not-marked-wrong steps only, 90-day window as
an aggregate `FILTER` on `max(closed_at)`, `percentile_cont(0.5)` continuous median
rounded to whole seconds, NULL under 5 qualifying groups. Constants at
`domain/item_economics/budget_division.py:15-17`
(`TYPICAL_METHOD = "median_completed_section_totals"`).

### 2.2 Facts this design leans on (each verified in code)

- **F-A: the primary item is already in hand everywhere.**
  `get_task_budget_status._load_task_and_item` (`get_task_budget_status.py:51-78`)
  loads the active PRIMARY `Item` and discards it (`TaskBudgetStatus` carries only
  `item_id`, `:47`). `production-time` calls that service (`:26`); `price-scenario`
  calls it AND re-loads the item itself (`:194-195`, documented duplication);
  `budget-allocations` builds `primary_by_task` / `item_by_id` (`:74-94`). Deriving
  the spec costs **zero additional queries in every consumer**.
- **F-B: at most one active primary item per task**, by partial unique index
  `uix_task_items_primary_active` (`models/tables/tasks/task_item.py:52-58`,
  `role = 'primary' AND removed_at IS NULL`). This is what makes the item join
  fan-out-free; it is a named boundary of the design (§4.2).
- **F-C: the participating-set rule exists three times and agrees by coincidence.**
  Identical step loads (`workspace_id`, `task_id`/`task_id.in_`,
  `is_deleted.is_(False)`) at `production_time.py:28-38`,
  `budget_allocations.py:110-118`, `price_scenario.py:119-121`; identical
  non-excluded-step predicate at `price_scenario.py:128-132` and inside
  `divide_production_budget` (`budget_division.py:309-312`,
  `EXCLUDED_STEP_STATES = {SKIPPED, CANCELLED, FAILED}` at `:19-25`). Layer 1.5's
  correctness depends on this agreement, so it becomes one shared function (§6.1).
- **F-D: reconciliation cannot live inside `divide_production_budget`.** The
  `allowed_worker_minutes is None` branch returns early (`:285-305`) computing no
  participating set, yet production-time still renders sections; and price-scenario
  never calls division at all. Layer 1.5 runs in the services, before division (§6.2).
- **F-E: excluded sections' typicals are display-only.** `budget_division.py:349-359`
  renders excluded groups (`share_state: "excluded"`, `allowance_seconds: None`);
  their typicals appear in zero computations (weights iterate `allocated_groups`
  only, `:317-333`; price-scenario drops them before its sum; allocations charge
  their *worked* seconds, never their typical).
- **F-F: `DivisionStep.typical_worker_seconds` is provably not a snapshot.** No DB
  column exists (`TaskStep` has none; `ItemCostResult` persists actuals and
  `calculation_version` only, `item_cost_result.py:23-32`). Both fallback reads
  (`budget_division.py:264`, `:324`) receive ORM `TaskStep` rows lacking the
  attribute → always `None` in production. Present since the file's origin commit
  `0b85701` as a test-input convenience; its only constructors are 8 test call
  sites plus fakes.
- **F-G: two layer-2 rules already exist and differ deliberately.**
  `budget_division.py:332`: in-task median of usable typicals, terminal
  `Fraction(1,1)` (a weight — 0 would starve a section).
  `price_scenario.py:157`: in-task median, terminal `Fraction(0,1)` (a duration —
  a fabricated average would inflate an estimate). "Usable" excludes `None` and
  `<= 0` in both. These survive as one implementation with two named terminals (§8).
- **F-H: byte-exact goldens cover two of the four payloads.**
  `test_live_clock_goldens.py:325-332` asserts `json.dumps(payload) == golden` for
  production-time, budget-status and budget-allocations (commit `1081a2b`, the
  live-clock pipeline's pre-change baseline). Its fixture deliberately has no
  COMPLETED steps, so its typicals block is `null`/0 at any run date (`:1-8`).
- **F-I: item fields available for narrowing** (`models/tables/items/item.py`):
  `item_category_id` (`:30`, nullable FK), `quantity` (`:33`), `designer` (`:34`),
  `height_in_cm`/`width_in_cm`/`depth_in_cm` (`:35-37`, nullable),
  `can_have_upholstery` (`:40`, non-null). `ItemCategory.major_category`
  (`item_category.py:24`, enum WOOD | SEAT). `item_category_snapshot` is a **name**
  captured at item write (`_create_item_in_session.py:82`) — narrowing uses
  `Item.item_category_id`, never the snapshot.
- **F-J: the domain is SQL-free.** Zero `sqlalchemy`/`models.tables` imports across
  all eight `domain/item_economics/` files. The spec and resolution stay pure; the
  join translation lives in the query layer (§4.2).


### 2A. Grounding drift, measured 2026-08-22 (amendment — nothing above renumbers)

**§2's header said "all paths current". That was true on 2026-08-20 and is false now.**
Between then and 2026-08-22 the `live_clock_for_working_time_economics` pipeline shipped
phases 2 and 3 (APPROVED 2026-08-21, merged to `main` as `57d8c25`) into the exact files
§2 cites, and the test runner changed underneath the whole repo. This section records what
was **measured**, by whom, and what is still owed. Written by the outgoing live-clock
coordinator at closeout, because a fresh session cannot know it and the fact expires.

#### The one that is a contract, not a line number — read this before §3

`typical_times_statement` **gained a parameter**, and the four consumers **deliberately
split** over it:

```
def typical_times_statement(workspace_id, *, now: datetime | None = None)
```

| Consumer | Call today | Clock |
|---|---|---|
| `get_task_production_time.py:81` | `typical_times_statement(ctx.workspace_id, now=ctx.now)` | **injected** |
| `get_task_budget_allocations.py:46` | `typical_times_statement(ctx.workspace_id, now=ctx.now)` | **injected** |
| `get_working_section_typical_times.py:74` | `typical_times_statement(ctx.workspace_id)` | own wall-clock read |
| `get_task_price_scenario.py:140` | `typical_times_statement(ctx.workspace_id)` | own wall-clock read |

The source comment states the split verbatim: *"The optional request clock keeps the
working-sections and price-scenario callers on their existing clock read while E-P/E-A
share `ctx.now`."*

**§3 proposes `typical_times_statement(workspace_id, *, specs: Sequence[TypicalFilterSpec] = ())`
and §5's call form `typical_times_statement(ws, specs)` — both written before that
parameter existed. Taken literally they erase the parameter AND the two-clock split.**

Why that is not cosmetic: the cutoff is derived as
`(now if now is not None else datetime.now(timezone.utc)) - timedelta(days=TYPICAL_WINDOW_DAYS)`.
Dropping `now` returns E-P and E-A to a wall-clock read on the request path, which is the
live-clock intention's **HC-3A** violation by construction — the contract that two
executions over identical database state with a frozen clock produce byte-identical
payloads, guarded by that pipeline's T1 byte-identity tests. The refactor would compile,
pass a casual read, and redden goldens for a reason nobody would connect to typicals.

**This is not a ruling on what narrow should do.** Keeping the split, collapsing it
deliberately, or threading the spec alongside the clock are all open designs — it is a
**mechanism the inventory gate must contract**, and §3/§5 must be reconciled against the
real signature before the planner sees them.

#### Line-number drift — sampled, not swept

Five citations checked at source on 2026-08-22:

| §2 citation | Today | |
|---|---|---|
| `get_working_section_typical_times.py:21` (HC-1's anchor) | **21** | holds |
| `get_working_section_typical_times.py:68` | **74** | moved |
| `get_task_production_time.py:55` | **81** | moved |
| `get_task_budget_allocations.py:45` | **46** | moved |
| `get_task_price_scenario.py:137` (`_typical_block`) | **140** | moved |
| `get_task_budget_status.py:51-78` (F-A `_load_task_and_item`) | def at **54** | moved |

**Four of five call sites moved; the HC-1 anchor held.** F-H's golden assertion is still
inside its cited `:325-332` (the `json.dumps` is at `:330`), though §2 paraphrases it as
`json.dumps(payload) == golden` where the code passes `sort_keys=True,
separators=(",", ":")`.

**This is a sample and is labelled as one.** The remaining ~30 citations in §2.2 and §§4–11
were **not** re-verified. Do not read this table as "everything else is current" — read it
as evidence that §2's own header cannot be trusted and that **re-grounding is owed before
the planner runs**. The mechanism-inventory gate is the natural place; §13 step 2 already
sits there.

#### What else moved that §2 does not mention

- **The test runner.** `pytest -m 'not e2e'` now runs **six xdist workers** with
  `--dist loadfile` from `app/pytest.ini`'s `addopts`, each process on its own database
  cloned from `beyo_test_main_template`, and **Redis must be reachable** or the count is
  23 failed / 2 errors instead of 21. Nothing in the invocation announces this.
- **D23's precondition is now SATISFIED.** "Implementation starts after the live-clock
  phases touching the shared files are APPROVED" — all four phases are APPROVED and merged.
  **The post-live-clock baseline D23 says the goldens regenerate against is published**, with
  its runner, in `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md`
  §7: **21 failed / 2576 passed**, collection 2597, on `dc76db8`'s `app/` tree. Two named
  intermittent tests are **not** members of that 21; a third, unrecoverable, **is** — so the
  set can shrink as well as grow, and **a single run is not evidence**.
- **The live-clock pipeline's own artifacts moved** to
  `docs/architecture/archives/live_clock_for_working_time_economics/`. Its intention §2.5A
  (the eight-row settled-consumer inventory) and §4.3A (the typicals path as a third
  worked-seconds→allowance route) are the two sections most worth reading before this
  document's §6.

**Standing lesson this instance re-earns:** a grounded fact is a claim with a shelf life,
and a header asserting "all paths current" ages worse than the citations under it, because
it is the sentence nobody re-checks. Date the grounding, and re-ground at the gate.

---

## 3. Domain model & vocabulary

All new pure objects live in `domain/item_economics/typical_filters.py` (new file).
All are `@dataclass(frozen=True)`; the spec is hashable (frozensets/tuples only).

### 3.1 `TypicalFilterSpec` — what population was requested

```
TypicalFilterSpec(
    item_category_ids: frozenset[str] | None = None,
    major_categories:  frozenset[ItemMajorCategoryEnum] | None = None,
    width_cm:  tuple[int | None, int | None] | None = None,   # inclusive (min, max)
    height_cm: tuple[int | None, int | None] | None = None,
    depth_cm:  tuple[int | None, int | None] | None = None,
    can_have_upholstery: bool | None = None,
    designers: frozenset[str] | None = None,
)
.is_narrowing -> bool     # any field set; empty spec ≡ no spec (HC-4 holds for both)
```

**Combination semantics (fixed here, inherited by every surface):** AND across
fields; OR within a collection field; **unknown never matches** — an item with
`width_in_cm IS NULL` does not match a width range; an item with no category does
not match a category filter; a task with no active primary item matches no narrowing
predicate. A narrowed population is therefore always a strict subset of the
section-wide population (the invariant §4.4 rests on).

The spec describes a population and nothing else. It carries no policy, no
thresholds, no join knowledge.

### 3.2 `COMPARABILITY_PROFILE` — what task economics automatically narrows by

```
COMPARABILITY_PROFILE = "primary_item_category_v1"

derive_spec_from_primary_item(item) -> TypicalFilterSpec
    item is None or item.item_category_id is None -> TypicalFilterSpec()  # empty
    else -> TypicalFilterSpec(item_category_ids={item.item_category_id})
```

The two extension axes are deliberately separate and separately versioned:
**filter capability** (fields of `TypicalFilterSpec` — powers explicit analytics;
adding one CANNOT reach task economics) vs **automatic economics policy**
(`COMPARABILITY_PROFILE` — category-only in V1; a future
`primary_item_category_dimensions_v2` must define its own policies such as
dimensional bands, and its adoption is a deliberate versioned act). Adding a column
to `Item` must not silently change economics; under this split it structurally
cannot.

### 3.3 `SectionTypicalEvidence` — layer-1 facts, task-independent

```
SectionTypicalEvidence(
    working_section_id, 
    narrowed_typical_worker_seconds: int | None, narrowed_sample_count: int,
    section_typical_worker_seconds:  int | None, section_sample_count:  int,
)
.has_narrowed -> narrowed_sample_count >= TYPICAL_MIN_SAMPLE_SIZE
.has_section  -> section_sample_count  >= TYPICAL_MIN_SAMPLE_SIZE
```

Raw statistics and threshold predicates ONLY — **no basis property of any kind**
(this is where the earlier `evidence_basis` ambiguity was closed at the source).
Both populations are always gathered regardless of policy: the query gathers facts;
the domain decides what they mean.

### 3.4 `TypicalResolutionPolicy` — what a thin requested population resolves to

```
TypicalResolutionPolicy.BROADEN_TO_SECTION   # task economics: usable value preferred
TypicalResolutionPolicy.ANSWER_AS_ASKED      # analytics: the filtered answer or an honest null

resolve_section_typical(evidence, spec, policy) -> SelectedTypical
```

| | narrowed ≥ floor | else section ≥ floor | else |
|---|---|---|---|
| `BROADEN_TO_SECTION` | narrowed | section-wide | insufficient |
| `ANSWER_AS_ASKED` | narrowed | **insufficient** | insufficient |
| spec not narrowing | — | section-wide is simply the requested statistic; policies coincide by construction | insufficient |

The statistical sample floor is the existing `TYPICAL_MIN_SAMPLE_SIZE = 5` for both
populations (owner ruling: "existing minimum").

**Type separation from layer 2 (deliberate, load-bearing):** policy is an enum
argument of `resolve_section_typical`; the business terminal is a `Fraction`
argument named `terminal` of `apply_business_fallback` (§8). No function accepts
both; no boolean exists anywhere in either signature; a confused hand-off is a
`TypeError`, not a semantic bug.

### 3.5 `SelectedTypical` and `TaskTypicalSelection` — layer-1.5 output

```
SelectedTypical(
    working_section_id,
    typical_worker_seconds: int | None,   # None ⇒ layer 2 territory
    typical_basis: str,                   # item_narrowed | section_wide | insufficient_sample
    evidence: SectionTypicalEvidence,     # carried, never re-resolved
    participates: bool,
)

TaskTypicalSelection(
    task_typical_basis: str,              # item_narrowed_uniform | section_wide_uniform
    reconciliation_method: str,           # RECONCILIATION_METHOD = "uniform_basis_v1"
    comparability_profile: str,           # COMPARABILITY_PROFILE
    applied_filter: TypicalFilterSpec,
    participating_section_ids: frozenset[str],
    selected: Mapping[str, SelectedTypical],   # EVERY section in the task, incl. excluded
)
```

### 3.6 The naming rule (contract-grade, applies to every wire object)

> **Every basis field describes the value it sits next to. "Best available but
> unused" is never a field — it is derivable** (`narrowed_sample_count >=
> min_sample_size` while `typical_basis == "section_wide"`), and the *why* lives at
> task level in `typical_resolution.task_typical_basis`.

Two disjoint vocabularies, never mixed: per-section `typical_basis` ∈
{`item_narrowed`, `section_wide`, `insufficient_sample`}; per-task
`task_typical_basis` ∈ {`item_narrowed_uniform`, `section_wide_uniform`}. The unused
narrowed *seconds* value is never published on task surfaces (it invites UIs to
render a second "real" number; its magnitude is the statistics endpoint's business).

`sample_count` on the wire = the count of the population `typical_basis` names.
For `insufficient_sample` it is the count of the population the policy would have
answered from: `section_sample_count` under `BROADEN_TO_SECTION`,
`narrowed_sample_count` under `ANSWER_AS_ASKED`.

### 3.7 Versioned method constants (complete set after this pipeline)

| Constant | Value after V1 | Changes? |
|---|---|---|
| `TYPICAL_METHOD` | `median_completed_section_totals` | **no** — the algorithm is unchanged; the population is described by `comparability_profile` + `applied_filter` |
| `TYPICAL_WINDOW_DAYS` / `TYPICAL_MIN_SAMPLE_SIZE` | 90 / 5 | no |
| `ALLOCATION_METHOD` | `static_proportional_section_v2` | **yes** (§6.3) |
| `COMPARABILITY_PROFILE` | `primary_item_category_v1` | new |
| `RECONCILIATION_METHOD` | `uniform_basis_v1` | new |

---

## 4. The three layers (exact semantics)

### 4.1 Layer 1 — statistical resolution (per section, task-free)

For each (section, spec): compute both populations in one pass; resolve per §3.4.
Both populations are always computed — strict mode discards nothing at the SQL
layer; policy is applied purely, after the facts are in hand (§2 F-J, §5).

### 4.2 The query mechanism (facts only, policy-blind)

`typical_times_statement(workspace_id, *, specs: Sequence[TypicalFilterSpec] = ())`.

- **No spec / empty specs ⇒ HC-4**: no joins, no extra columns, no narrowed
  aggregates — today's statement, character for character.
- **With narrowing specs**: LEFT OUTER join `TaskItem`
  (`task_id`, `workspace_id`, `role == PRIMARY`, `removed_at IS NULL`) and
  LEFT OUTER join `Item` (`is_deleted IS FALSE`); `ItemCategory` joins only when a
  spec requires `major_categories`. The item-match predicate is used **only inside
  aggregate FILTERs** — never as a WHERE — so the section-wide population is
  untouched (an INNER join would silently drop primary-less tasks from the
  section-wide statistic too; tested by T-join).
- **Group key is unchanged** (`(working_section_id, task_id)`): the sample unit
  never changes; item-awareness enters as `bool_or(item_match)` per group.
  F-B is what makes `bool_or` collapse a single-valued fact — **narrowing is
  defined against the active PRIMARY item only; generalizing to secondary items
  breaks the no-fan-out guarantee and is out of scope by ruling** (§10 D8).
- **Spec → predicate translation** lives in ONE new query-layer module,
  `services/queries/working_sections/_typical_item_filter.py`
  (`build_item_match(spec) -> (needs_category_join, predicate | None)`). It is the
  only module that knows Task → primary TaskItem → Item. Higher services see specs.
- **Internal strategy is not contract.** For K distinct specs, candidate execution
  strategies (K× `bool_or` + FILTER aggregate pairs; GROUPING SETS over
  `item_category_id` when every spec is a pure single-column equality — exactly the
  V1 profile) are selected behind the statement by spec shape. Neither strategy
  name appears in any domain object or API. If a spec-count ceiling forces
  chunking, the split is `log()`ed — never a silent cap. Acceptance is conditional
  on measurement (§12).

### 4.3 Layer 1.5 — task reconciliation (`uniform_basis_v1`)

Inputs: evidence for every section in the task; the participating set from the
single shared `participating_sections(steps)` (§6.1).

```
participating non-empty AND every participating section has_narrowed
    -> task_typical_basis = item_narrowed_uniform
otherwise (including the empty participating set)
    -> task_typical_basis = section_wide_uniform
```

- **Participating sections** take the uniform basis's value: `narrowed_typical`
  under `item_narrowed_uniform`; `section_typical` under `section_wide_uniform`
  (which may be `None` → layer 2; basis `insufficient_sample`).
- **Excluded sections resolve independently** via
  `resolve_section_typical(evidence, spec, BROADEN_TO_SECTION)` and **never
  influence the task basis** (owner ruling; grounded in F-E: their typicals are
  display-only). Consequence, stated so it is never reported as a bug: an excluded
  row's `typical_basis` may differ from the participating rows' uniform basis, in
  either direction.
- **No pace factor, no scaled values, no raw mixed ratios** (owner ruling): every
  emitted `typical_worker_seconds` is identically an integer produced by the SQL —
  never a product or ratio of two of them (T5 asserts this property).

### 4.4 The reachability invariant

Narrowed ⊆ section-wide (per §3.1 unknown-never-matches) ⇒ `has_narrowed ⇒
has_section` ⇒ under `item_narrowed_uniform` **no participating section can reach
layer 2**. Layer 2 is reachable only under `section_wide_uniform` (or on excluded
sections whose ladder bottoms out). Test T10.

### 4.5 Layer 2 — terminal business fallback (per consumer; §8)

Applied only where `SelectedTypical.typical_worker_seconds` is `None` **or `<= 0`**
(zero typicals are unusable today — `test_c3_zero_typical_is_not_usable...` — and
this pipeline preserves that): in-task median of the usable selected values;
terminal only when no usable value exists in the task. Division: `terminal =
Fraction(1,1)` (weight-neutral). Price-scenario: `terminal = Fraction(0,1)`
(contribution-neutral). Never serialized (§6.4).

---

## 5. Task economics vs analytics (the two pathways)

```
                    typical_times_statement(ws, specs)        ← facts, policy-blind
                                 │
                     SectionTypicalEvidence (both populations, always)
                                 │
          ┌──────────────────────┴───────────────────────┐
task-scoped services                        /statistics/typical-times (DEFERRED, §9)
spec := derive_spec_from_primary_item       spec := parse_spec_from_query_params
policy := BROADEN_TO_SECTION                policy := ANSWER_AS_ASKED (locked; no
                                            route override — owner ruling)
          │                                               │
participating_sections → reconcile_task_typicals          resolve per row; no task,
(uniform_basis_v1) → TaskTypicalSelection                 no reconciliation, no layer 2;
          │                                               diagnostics = counts only,
excluded sections: BROADEN_TO_SECTION,                    never the unused broader
independent (§4.3)                                        seconds (owner ruling)
          │
production-time ── budget-allocations ── price-scenario
          │
layer 2 per consumer, only where selected is null/<=0
```

Task routes accept **no filter parameters** — a client cannot make a chair task use
a table filter; divergence is structurally impossible, not policed. The same
evidence can legitimately produce `540` for task economics and `null` for
analytics: different questions, both honest, each payload naming its own rules
(`typical_resolution` vs `resolution_policy`).

---

## 6. Consumer integration

### 6.1 One participating-set rule

New shared function (home: `domain/item_economics/` beside the division, since the
predicate is already domain vocabulary — `EXCLUDED_STEP_STATES`):
`participating_sections(steps) -> frozenset[str]` = sections with ≥ 1 step outside
`EXCLUDED_STEP_STATES`, over non-deleted steps. All three task services AND
`divide_production_budget`'s internal `allocated_groups` predicate resolve to this
one implementation (F-C). T7 asserts the three services agree on a mixed fixture.

### 6.2 Per consumer (all four; no consumer issues more queries than today)

| Consumer | Spec entry | Integration |
|---|---|---|
| `get_task_budget_status` | — | `TaskBudgetStatus` stops discarding the loaded primary `Item` (F-A): carries it (or the derived spec) for downstream reuse. No payload change; `golden_budget_status.json` untouched. |
| `get_task_production_time` | from budget-status's item | evidence → `reconcile_task_typicals` **before** division (F-D; the no-budget branch also gets a complete reconciled block) → the SAME `SelectedTypical`s feed display and weights → `typical_resolution` at task level |
| `get_task_budget_allocations` | per task from `item_by_id`/`primary_by_task` (already loaded) | dedupe specs (hashable) → one statement call for the batch → per-task reconciliation → division |
| `get_task_price_scenario` | from its `item` (`:195`) | `_typical_block` keeps its step query + participating computation (now via §6.1), consumes the shared reconciliation, drops its private ladder as a rule, keeps `terminal=0` (§8) |
| `get_working_section_typical_times` | none in V1 (D24) | passes no spec ⇒ HC-4; route and payload byte-identical |
| `divide_production_budget` | — | third parameter becomes `Mapping[str, SelectedTypical]`; `_step_result` and section rows emit `typical_basis` + `sample_count`; internal exclusion predicate delegates to §6.1; **`DivisionStep.typical_worker_seconds` and both fallback reads (`:264`, `:324`) removed** (owner ruling; F-F) |

### 6.3 `ALLOCATION_METHOD` versioning — precise behavioural statement

`static_proportional_section_v1 → static_proportional_section_v2`. Every task is
now evaluated under the new rule; allowances are **eligible** to change wherever
item-category narrowing changes the relative section weights. Many tasks remain
numerically identical: primary items with no `item_category_id` (empty spec);
tasks reconciling to `section_wide_uniform`; categories whose narrowed ratios
coincide with the section-wide ratios. **The contract changes even where an
individual numeric result does not.** This wording is normative for the frontend
handoff (§11.3).

### 6.4 Layer-2 visibility (HC-2's third clause, per surface)

- Division surfaces: a null-selected section publishes `typical_worker_seconds:
  null, typical_basis: "insufficient_sample"` **with its computed
  `allowance_seconds` beside it** — that adjacency is the disclosure. The neutral
  weight is a `Fraction` in ratio space with no duration meaning and is never
  serialized as seconds. Task level: `sections_by_basis.insufficient_sample ≥ 1`.
- Price-scenario: `is_estimated` means exactly **"layer 2 fired for ≥ 1
  participating section"** — and specifically does NOT become true merely because
  the task reconciled to `section_wide_uniform`. This is a semantic clarification
  to an approved contract and gets an explicit line in the handoff (§11.3).

---

## 7. Response contracts (current → proposed, all surfaces)

Every new field is **non-nullable with an explicit default, always present**
(standing frontend requirement from
`HANDOFF_TO_BACKEND_production_time_live_budget_clock_20260819.md`; nullable-
then-absent fields have taken the frontend down twice).

### 7.1 `/working-sections/typical-times`

**Unchanged in V1** — ruled, D24 (2026-08-20). No narrowing params ⇒ nothing to
disclose; today's `typical_worker_seconds: null` under 5 samples already encodes
insufficient-vs-section-wide. The rejected branch (params under
`BROADEN_TO_SECTION`) is recorded in D24 so it is not reopened: it would be
exactly the silently-broadened analytics answer HC-3 forbids, on a WORKER-visible
route.

### 7.2 `production-time` — `sections[].typical`

```jsonc
// CURRENT: { typical_worker_seconds, sample_count, method, window_days, min_sample_size }
// PROPOSED (Cutting under section_wide_uniform, narrowed evidence existed):
{ "typical_worker_seconds": 600,
  "sample_count": 61,                    // population named by typical_basis (§3.6)
  "typical_basis": "section_wide",       // NEW — describes THIS value, nothing else
  "narrowed_sample_count": 14,           // NEW — raw evidence (default 0)
  "section_sample_count": 61,            // NEW — raw evidence (default 0)
  "method": "median_completed_section_totals", "window_days": 90, "min_sample_size": 5 }
```

Task level, beside `allocation_method`:

```jsonc
"typical_resolution": {
  "task_typical_basis": "section_wide_uniform",
  "reconciliation_method": "uniform_basis_v1",
  "comparability_profile": "primary_item_category_v1",
  "applied_filter": {"item_category_ids": ["icat_chair"]},   // null when spec empty
  "participating_section_count": 3,
  "sections_by_basis": {"item_narrowed": 0, "section_wide": 2, "insufficient_sample": 1}
}
```

`sections_by_basis` counts **participating** sections (excluded rows resolve
independently and would blur the reconciliation story it tells).

### 7.3 `budget-allocations` — `steps[]` and per-task

```jsonc
// steps[] CURRENT: { step_id, working_section_id, section_name_snapshot,
//   typical_worker_seconds, allowance_seconds, worked_seconds, left_seconds, share_state }
// PROPOSED: + "typical_basis", + "sample_count"
```

plus the identical `typical_resolution` object per task entry.
`narrowed_sample_count`/`section_sample_count` are deliberately **omitted** here
(50 tasks × N steps of diagnostic weight the list view cannot render; the deep view
is one production-time request away). `typical_basis` + `sample_count` are the
minimum that distinguishes the three origins without reverse-engineering the query.

### 7.4 `price-scenario` — `typical`

```jsonc
// CURRENT: { total_seconds, is_estimated, sections_without_sample, sections_total,
//            method, window_days, min_sample_size }
// PROPOSED: + "typical_resolution": { ...same object as §7.2... }
```

`is_estimated` semantics per §6.4. Serialized through the existing pass-through at
`domain/item_economics/serializers.py:353`.

### 7.5 Future `/statistics/typical-times` (deferred; contract pre-locked, §9)

```jsonc
{ "working_section_id": "wsec_cutting",
  "typical_worker_seconds": null,
  "typical_basis": "insufficient_sample",
  "sample_count": 2,                       // the population ASKED about (§3.6)
  "narrowed_sample_count": 2,
  "section_sample_count": 70,              // diagnostic COUNT only — the unused
                                           // broader seconds are never exposed (ruling)
  "applied_filter": {"item_category_ids": ["icat_chair"], "width_cm": [60, 80]},
  "resolution_policy": "answer_as_asked",  // locked; no route override (ruling)
  "method": "...", "window_days": 90, "min_sample_size": 5 }
```

---

## 8. Layer-2 terminals (kept distinct by ruling)

One implementation, two named terminals, never merged:

```
apply_business_fallback(selected_values, *, terminal: Fraction) -> resolved values
    usable  = selected values that are not None and > 0
    filled  = median(usable) if usable else terminal
```

| Caller | `terminal` | Why this terminal is correct |
|---|---|---|
| `divide_production_budget` | `Fraction(1, 1)` | a weight; 0 starves the section of allowance; 1 with all-equal weights = divide evenly when nothing is known |
| `price_scenario._typical_block` | `Fraction(0, 1)` | a duration; averaging would fabricate time inside a number managers read as an estimate; 0 + `is_estimated: true` is the honest answer |

The docstring records that the difference is intentional and must not converge.
Output of this function never reaches a serializer (§6.4).

---

## 9. Scope ladder

**Must ship (V1):** `typical_filters.py` (spec, profile, evidence, policy,
resolution, reconciliation, business fallback); `_typical_item_filter.py`;
statement extension with HC-4; the shared participating-set function; all four
consumers integrated per §6; division signature + provenance + `ALLOCATION_METHOD`
v2; `DivisionStep.typical_worker_seconds` removal; response contracts §7.2–7.4;
goldens per §11.2; performance measurement per §12; frontend handoff per §11.3.

**Only if cheap:** none identified — the cut points below are deliberate, not
budget-driven.

**Explicitly deferred, with return paths:**
- `/statistics/typical-times` route — contract pre-locked (§7.5: `ANSWER_AS_ASKED`,
  no policy override, counts-only diagnostics); ships later as
  `parse_spec_from_query_params` + a route + a serializer over the same engine.
  The `ANSWER_AS_ASKED` branch and the parser still ship NOW with full unit
  coverage (charter rule 4 is satisfied by test callers; retrofitting policy later
  would re-open `resolve_section_typical`'s contract).
- `COMPARABILITY_PROFILE` v2 (dimensions etc.) — requires its own banding policy
  and a version bump; adding `TypicalFilterSpec` fields alone cannot reach
  economics (§3.2).
- Pace-factor / scale-corrected reconciliation — rejected for V1 by ruling (a new
  predictive model, not a fallback); the versioned `reconciliation_method` is its
  return path if data ever validates a stable cross-section effect.
- Secondary/non-primary item narrowing — breaks F-B's no-fan-out guarantee (§4.2).
- Persisting `TaskTypicalSelection` at task close (allocation reproducibility) —
  explicitly out of scope by ruling; noted as the future home of an audit need.
- `Item.quantity` normalization — typicals remain batch-size-blind; item-aware
  values will look more precise while still ignoring quantity; recorded so the
  added precision is not over-trusted.

---

## 10. Owner decisions

All settled decisions D1–D22 are recorded verbatim in
`planning/owner_decisions.md`. Digest: D1 one canonical statement · D2 filtering
not dimensioning · D3 narrowing inside the statement · D4 one frozen spec ·
D5 both populations one pass · D6 ladder at the existing floor · D7 provenance
mandatory · D8 PRIMARY item only · D9 all four consumers now; same semantics ≠
same HTTP params; task routes derive implicitly · D10 goldens are part of the
refactor · D11 `primary_item_category_v1`; capability ≠ policy · D12
`uniform_basis_v1`; no raw mixing; no pace factor · D13 evidence vs selected as
two objects · D14 HC-2 including the layer-2 visibility clause · D15
`TypicalResolutionPolicy` orthogonal to the spec; type-separated from terminals ·
D16 excluded sections resolve independently · D17 strict diagnostics counts only ·
D18 remove `DivisionStep.typical_worker_seconds`; reproducibility out of scope ·
D19 statistics locked to `ANSWER_AS_ASKED`, no route override · D20
`ALLOCATION_METHOD` v2 with §6.3's exact phrasing · D21 conditional acceptance on
measured query cost · D22 two distinct layer-2 terminals.

**None open.** Card A answered 2026-08-20 → **D24**: `/working-sections/typical-times`
is byte-identical in V1 — no params, no response change; explicit filtered
questions wait for the strict statistics surface. Card B answered 2026-08-20 →
**D23**: serial, live-clock first — implementation starts after the live-clock
phases touching the shared files are APPROVED; goldens regenerate once, on the
post-live-clock baseline.

---

## 11. Testing priorities, goldens, and handoff

### 11.1 Test matrix (each row: one fixture predicate is the ONLY reason the
outcome holds; named mutations state file + definition-vs-call-site)

| # | Case | Asserts | Named mutation that must turn it red |
|---|---|---|---|
| T1 | all participating sections narrowed | `item_narrowed_uniform`; three consumers agree on seconds/basis/count; layer 2 never fires | in `typical_filters.reconcile_task_typicals` (definition), replace the narrowed value with the section value for one section |
| T2 | one section under-sampled | `section_wide_uniform`; **no narrowed value appears as any weight**; narrowed evidence still visible in counts | in `reconcile_task_typicals` (definition), change `all(...)` to `any(...)` |
| T3 | no category on the primary item | empty spec; all four surfaces numerically identical to pre-refactor | in `derive_spec_from_primary_item` (definition), return a non-empty spec for category-less items |
| T4 | section-wide also insufficient | division fills weight via median-else-1; price-scenario contributes 0 and sets `is_estimated` — asserted as two separate rows, one per terminal | swap the two `terminal=` arguments at the two call sites (each row bites on its own) |
| T5 | no hidden pace model | every emitted `typical_worker_seconds` is byte-equal to a value the SQL returned | in `reconcile_task_typicals` (definition), multiply a fallback value by any ratio of two others |
| T6 | cross-service agreement | per participating section: production-time seconds/basis/count == budget-allocations step's; `price_scenario.total_seconds == Σ` over the **participating** set (the set restriction itself asserted — division renders excluded groups, price-scenario does not) | in one consumer, resolve typicals locally instead of via the shared selection |
| T7 | participating-set identity | three services select the same set on a fixture mixing COMPLETED/WORKING/SKIPPED/CANCELLED/deleted steps | reintroduce a private predicate in one service (call site) |
| T8 | no-budget branch reconciles | task outside `{OK, INFEASIBLE}` still returns a complete `typical_resolution` | move reconciliation inside `divide_production_budget` (call site) — the early-return branch loses it |
| T9 | excluded independence, both directions | thin excluded section + all-narrowed participating ⇒ basis stays `item_narrowed_uniform` AND the excluded row shows its section-wide value; mirrored case | include excluded ids in the `all(...)` quantifier (definition) |
| T10 | narrowed ⊆ section-wide reachability | under `item_narrowed_uniform` no participating section reaches layer 2 | in `resolve_section_typical` (definition), let `has_narrowed` pass while `narrowed_typical` is None |
| T11 | HC-4 SQL identity | `typical_times_statement(ws)` compiles to today's SQL string | make the item joins unconditional (definition, `typical_times_statement`) |
| T12 | policy divergence on identical evidence | narrowed 2 / section 70: `ANSWER_AS_ASKED` → null + `insufficient_sample`; `BROADEN_TO_SECTION` → section value; same evidence object both calls | collapse the two policy branches (definition, `resolve_section_typical`) |
| T13 | strict never broadens (property-style over evidence grids) | under `ANSWER_AS_ASKED` + narrowing spec, output is narrowed-or-null | same mutation as T12 (recorded: T12 bites on the branch, T13 on the sweep) |
| T14 | policy/terminal isolation | switching policy never changes a terminal outcome; terminals fire only on null/`<=0` selected | pass a policy where a terminal belongs (must be `TypeError`, asserted) |
| T15 | strict diagnostic honesty | strict-insufficient object contains `section_sample_count` and NO section-wide seconds anywhere | serialize the unused section typical into the strict object (serializer definition) |
| T16 | layer-2 visibility | null-selected division row: `typical_basis: "insufficient_sample"`, null seconds, allowance present; neutral weight nowhere as seconds | emit the filled weight as `typical_worker_seconds` (in `_step_result`) |
| T17 | no-narrowing convergence | empty spec: both policies return identical objects | give the empty spec a narrowing meaning (definition, `is_narrowing`) |
| T18 | LEFT-not-INNER (T-join) | history containing a task with no active primary item: section-wide statistics identical with and without a narrowing spec in the request | change `outerjoin` to `join` (statement definition) |
| T19 | no fan-out | seeded task with one PRIMARY + two secondary items counts once in both populations | drop the `role == PRIMARY` predicate (in `_typical_item_filter`, definition) |
| T20 | unknown never matches | null-width item excluded from a width-band population; null-category item from a category population; each its own row with a single-cause fixture | make NULL comparisons match (predicate translation) |
| T21 | zero-typical unusable preserved | selected value 0 flows to layer 2 in both consumers (extends existing `test_c3_zero_typical...`) | treat 0 as usable in `apply_business_fallback` (definition) |

Mechanical: the 8 `DivisionStep(typical_worker_seconds=…)` test constructors in
`app/tests/unit/domain/item_economics/test_budget_division.py` move their typicals
into the selection mapping. A new seeded integration fixture (chair category; ≥5
same-category completed groups in two sections, <5 in a third; one task with no
primary item in history for T18) drives T1/T2/T4/T5/T6/T9/T10/T19.

### 11.2 Goldens (owner ruling: part of the refactor, regenerated deliberately)

| Golden | Change | Criterion |
|---|---|---|
| `golden_budget_status.json` | **none** | live-clock baseline fully intact |
| `golden_production_time.json` | keys only | see below |
| `golden_budget_allocations.json` | keys only | see below |

The live-clock fixture has no COMPLETED steps (F-H), so post-refactor it yields
counts 0 / basis `insufficient_sample` / `section_wide_uniform` and — one section —
an unchanged allowance. **Regeneration is approved only if the diff adds keys.**
Any changed `allowance_seconds`, `left_seconds`, `share_state`, `worked_seconds`,
or budget figure means the refactor moved something it was not supposed to move.
The live-clock fixture is NOT taught to narrow; item-aware cases live in the new
fixture (§11.1).

### 11.3 Frontend handoff (closeout obligation)

One new dated handoff (never an edit to a published one — standing rule) covering:
`ALLOCATION_METHOD` v2 with §6.3's exact eligibility phrasing; every new field
non-nullable with explicit defaults; the `is_estimated` clarification (§6.4); the
statistics-vs-task numeric difference (§5) once the statistics endpoint ships; and
per D24, the statement that `/working-sections/typical-times` is unchanged.

**Worker-card re-pointing (round 4; supersedes one instruction of
`HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818` §Worker task-step
cards).** That handoff instructs the cards to join a bootstrap-cached
`typical-times` response as the no-budget fallback figure. Post-refactor that join
would pair a generic cached typical with item-aware card figures and contradict
production-time's degraded state for the same task+section — a client-side cache
surviving as the last source of cross-surface disagreement. The new handoff
instructs: the cards' fallback typical comes from `budget-allocations`
`steps[].typical_worker_seconds` (already present in the `no_budget` state, and
item-aware after this pipeline); the bootstrap `typical-times` fetch/cache/join is
deleted from the card path. One batched call per feed page (≤50 task ids) remains
the cards' single economics source. `typical-times` stays a task-free benchmark
surface per D24.

---

## 12. Performance acceptance condition (conditional acceptance, owner ruling)

"1 query" is not "same cost." Before the implementation plan is accepted:

- **Harness:** seeded representative 90-day history (disposable DB), measured via
  `EXPLAIN ANALYZE` (or equivalent) — current statement vs new statement at:
  single task; batch of 50 tasks × {5, 10, 20} distinct primary-item categories;
  and the no-spec shape (expected: identical plan, since T11 pins identical SQL).
- **Recorded:** a measurement doc beside this intention
  (`planning/query_cost_measurements.md`) with plans, timings, and the chosen
  internal strategy per shape.
- **Rule:** if measurements embarrass a strategy, the strategy is swapped **behind
  `typical_times_statement`** — the domain objects, resolution semantics, and every
  response contract in §7 remain unchanged. No caching layer is the remedy.

---

## 13. Pre-implementation protocol

1. Ledger empty (D23, D24 — both cards answered 2026-08-20); status RESOLVED. ✓
   **D23's precondition satisfied 2026-08-22** (live-clock APPROVED and merged, baseline
   published). ✓
1a. **Re-ground §2 before the planner runs — NOT optional (§2A, 2026-08-22).** The
   document was grounded 2026-08-20 and the shared files moved on 2026-08-21/22; a
   sample of five call-site citations found four had drifted, and one drift is a
   signature change, not a line number. The inventory gate is the natural place to do
   it, and §2A is deliberately a **sample**, not a sweep.
2. Mechanism-inventory gate on this document (silent-failure mechanisms to
   contract-grade: the spec→predicate translation incl. NULL semantics; the
   two-population FILTER arithmetic; the reconciliation quantifier; the
   sample_count-naming rule §3.6; the layer-2 terminals; HC-4).
3. Implementation-planner; phase boundaries must respect card B's sequencing
   ruling and §12's measurement gate.
4. Archgraph: sessions orient at start; the phase delta (new domain module, new
   query module, changed division contract) is recorded at implementation time,
   one batched apply_changes per session — never during shaping.

---

## 14. Shaping changelog

- **Round 1 (2026-08-20).** Shaped from the three-pass projection conversation of
  2026-08-19/20. Key resolutions folded rather than re-litigated: four consumers
  (not three — price-scenario found during grounding); economics adoption now (not
  a display-only V1 — owner correction); uniform basis over raw-mixed and
  pace-factor (owner ruling with the 2×-item worked example as evidence);
  evidence/selected split into two objects after the `evidence_basis` ambiguity;
  policy abstraction added for strict analytics; excluded-section independence
  (B) from the display-only trace; `DivisionStep.typical_worker_seconds` removal
  proven safe (F-F). Cards A and B opened.
- **Round 2 (2026-08-20).** Card B answered by the owner: serial sequencing,
  live-clock first (recorded as D23; folded into §10, §13). Card A remains open.
- **Round 3 (2026-08-20).** Card A answered by the owner ("no" — after a
  plain-language walkthrough): recorded as D24, folded into §6.2, §7.1, §10,
  §11.3, §13. Ledger empty; status RESOLVED. Next gate: mechanism-inventory.
- **Round 4 (2026-08-20).** Owner question on the worker task-step cards traced
  the 2026-08-18 handoff's card recipe: allowances via `budget-allocations`
  (covered — consumer of this pipeline, HC-2/T6) plus a bootstrap-cached
  `typical-times` join as the no-budget fallback (gap — a generic cached typical
  beside item-aware figures would contradict production-time's degraded state).
  §11.3 gains the worker-card re-pointing instruction: fallback typicals come from
  `budget-allocations` steps; the cached join is deleted from the card path. No
  backend scope change; no new decision — a recorded consequence of D24 + HC-2.
