# Intention: Narrow Typical Work Times (item-aware typicals, one engine, four consumers)

```
status: RESOLVED (round 9, 2026-08-22) — **0 owner cards open. D1–D26 settled**
        (card A → D24; card B → D23; card C → D25: a narrowed median of zero is not a
        known typical, answered 2026-08-22 and folded as §4C). D23's precondition was
        satisfied 2026-08-22 — every live-clock phase touching the shared files is
        APPROVED and merged (`57d8c25`) and the post-live-clock baseline is published.
        **The mechanism-inventory gate has run and its contracts are written (§2B, §3A,
        §3B, §4A, §4B, §4C, §6A, §6B, §6C, §11A). Next: implementation-planner.**
        Three gate resolutions (§4B, §6B, §4A K1) are listed for owner ratification in
        the gate handoff §5; a veto arrives as a new amendment.
        **⚠ Read §2A and §2B first.** §2A found the drift; §2B is the full sweep and
        supersedes §2's "all paths current" header. One drifted citation is a contract
        (`typical_times_statement` gained an injected clock that §3's proposed
        signature erases) — resolved in §4A K1.
        **⚠ Section-letter precedence:** where a lettered section and the numbered
        section it amends disagree, the letter wins. §4A supersedes the signature and
        call forms in §3.1, §4.2 and §5; §4B supersedes §4.4's stated invariant and its
        proof; §4C (D25) amends §3.4's BROADEN rung, §4.3's quantifier, §4B's residual
        reachability and §11A rows T10b/T16b; §6B supersedes §6.4's `is_estimated`
        definition; §3C (round 8) amends §3A C1's error type at the parser boundary
        only, and §4C's predicate carries a round-8 `is not None` correction;
        §12A (round 9, D26) corrects §12's batch shapes and removes the
        acceptance threshold; §3D (round 9) records the ItemCategory join
        asymmetry without changing §3A C5.
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-19/20 (no raw_intention.md; three
             architecture projection passes, each owner-corrected, preceded this
             document — the corrections are folded, not appended)
date: 2026-08-20 (rounds 1–4) · 2026-08-22 (round 5, mechanism-inventory gate; round 6,
      D25 fold; round 7, planner fold; round 8, plan-1 projection fold; round 9,
      plan-2 projection fold + D26)
round: 9
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


### 2B. Re-grounding sweep, measured 2026-08-22 (mechanism-inventory gate — amendment, nothing above renumbers)

§2A swept **five** citations and labelled itself a sample. This section is the sweep §13
step 1a owes: **every** code citation in §2.1, §2.2 (F-A…F-J) and §§3–12, checked at
source against the tree at `dcfe849` (`app/` byte-identical to the published baseline
tree `dc76db8`). Address AND substance were checked; a line that moved but says the same
thing is drift, a line that says something different is a finding.

#### Citations that hold, address and substance

`get_working_section_typical_times.py:21` (HC-1 anchor) · `budget_division.py:15-17`
(constants) · `budget_division.py:19-25` (`EXCLUDED_STEP_STATES`) ·
`budget_division.py:264` and `:324` (the two fallback reads) · `:285-305` (the
`allowed_worker_minutes is None` early return) · `:309-312` (`allocated_groups`) ·
`:317-333` (weights iterate `allocated_groups` only) · `:332` (`Fraction(1,1)`) ·
`task_item.py:52-58` (`uix_task_items_primary_active`, `role = 'primary' AND removed_at
IS NULL`) · `item.py:30,33,34,35-37,40` (F-I's six item fields, nullabilities as stated)
· `item_category.py:24` (`major_category`) · `item_cost_result.py:23-32` (actuals +
`calculation_version`; no typical column) · `_create_item_in_session.py:82`
(`item_category_snapshot = category.name`) · `test_live_clock_goldens.py:325-332` (the
byte-golden assertion) · commits `0b85701` and `1081a2b` · `working_sections.py:131`
(route) · all **four** role gates in §2.1's table (typical-times, production-time,
budget-allocations ADMIN/MANAGER/WORKER/SELLER; price-scenario ADMIN/MANAGER —
`item_economics.py:350, :374, :388`) · F-J's "zero `sqlalchemy`/`models.tables` imports
across all eight `domain/item_economics/` files" (8 `.py` files, 0 hits).

#### Address drift — substance unchanged

| §2 citation | Today | |
|---|---|---|
| `get_working_section_typical_times.py:21-63` (the statement) | `21-69` | moved |
| `get_task_budget_status.py:51-78` (`_load_task_and_item`) | `54-81` | moved |
| F-A `production-time` calls budget-status `:26` | **`:48`** | moved (`:26` is now the `def`) |
| F-A price-scenario `:194-195` (calls it AND re-loads the item) | `:195-196` | moved |
| F-A `budget_allocations.py:74-94` (`primary_by_task`/`item_by_id`) | `75-96` | moved |
| F-C `production_time.py:28-38` (step load) | `30-41` | moved |
| F-C `budget_allocations.py:110-118` (step load) | `111-119` | moved |
| F-C `price_scenario.py:119-121` (step load) | `122-124` | moved |
| F-C `price_scenario.py:128-132` (non-excluded predicate) | `131-135` | moved |
| F-E `budget_division.py:349-359` (excluded render) | `351-360` | moved |
| F-G `price_scenario.py:157` (`terminal = Fraction(0,1)`) | **`:160`** | moved |
| F-H fixture "no COMPLETED steps" `:1-8` | `1-9` | moved |
| §6.2 price-scenario "from its `item` (`:195`)" | `:196` | moved |
| §2.1 call sites `:68` / `:55` / `:45` / `:137` | `74` / `81` / `46` / `140` | moved (§2A) |

#### Substance changes — each one feeds a contract below

- **S-1 (F-A). `TaskBudgetStatus` no longer "carries only `item_id`".** It carries
  `result: ItemCostResult | None` (`get_task_budget_status.py:51`), added by the
  live-clock pipeline, and `item_id` is at `:50`, not `:47`. Consumed on the wire
  (`get_task_production_time.py:117`). §6.2 row 1's "no payload change" claim now
  applies to a **14-field** dataclass with two construction helpers (corrected from "13"
  at the planner fold, 2026-08-22 — re-counted at source, `get_task_budget_status.py:38-51`;
  the planner caught the gate's own count). → **§6A**.
- **S-2 (F-A). The published `item_id` and the loaded primary `Item` can be different
  items.** On the evaluated path `item_id = evaluation.item_id` (`:198`), and
  `item_binding == "mismatched"` marks exactly the case where it differs from
  `item.client_id` (`:118`). The intention never says which of the two derives the
  narrowing spec. → **§6A**.
- **S-3 (F-A / §6.2). A fifth `TaskBudgetStatus` construction surface exists and appears
  in no table in this document:** `get_task_budget_status_worker.py` (the WORKER/SELLER
  money-redacted face) calls `_load_task_and_item`, `_empty_status` (`:38`, `:48`) and
  `_build_evaluated_status` (`:53`), and its own comment says it "must not inherit a
  future manager change". `_empty_status` has **four** call sites across the two files.
  → **§6A**.
- **S-4 (F-F). `DivisionStep(typical_worker_seconds=…)` now has two PRODUCTION
  constructors.** `get_task_production_time.py:50-62` and
  `get_task_budget_allocations.py:217-229` both build `DivisionStep(...,
  typical_worker_seconds=None, ...)`, introduced by live-clock phase 2 (`e7d65b9`,
  2026-08-20). F-F's "its only constructors are 8 test call sites plus fakes" is false as
  of that commit. F-F's **conclusion** survives — the field is still always `None` in
  production — but its stated **reason** ("both fallback reads receive ORM `TaskStep`
  rows lacking the attribute") is now wrong: production hands `DivisionStep` dataclasses
  that **do** have the attribute, explicitly set to `None`. D18's removal therefore edits
  two production files, not only tests. → **§6C**.
- **S-5 (F-C). The three step loads are no longer identical.** The WHERE predicates still
  agree exactly (`workspace_id`, `task_id`/`task_id.in_`, `is_deleted.is_(False)`), which
  is what §6.1 rests on — but `production_time.py:30-41` now adds
  `selectinload(TaskStep.latest_state_record)` and `.order_by(TaskStep.client_id.asc())`,
  which the other two lack. §6.1's shared function takes `steps` and is unaffected;
  F-C's word "identical" is not.
- **S-6 (§7.4). `serializers.py:353` is not the typical pass-through.** The
  price-scenario typical pass-through is `serializers.py:364` (`"typical":
  scenario["typical"]`); `:353` is now the item block's `"label"`. Also relevant to §7.2
  and §7.3: production-time's section typical and budget-allocations' step rows are **not**
  pass-throughs — `division_serializers.py:102-108` and `:36-47` enumerate their keys
  explicitly, with `typical.get("sample_count", 0)`-style defaults. New fields must be
  added there by name.
- **S-7 (§2.1). "Task's section ids" means two different sets.** Production-time scopes
  the statement to **every** step's section (`get_task_production_time.py:65`);
  price-scenario scopes it to the **participating** sections only
  (`get_task_price_scenario.py:136`). T6 already asserts the restriction; §2.1's table
  blurs it.
- **S-8 (grounding for §4.4). `TaskStep.total_working_seconds` is `Integer, nullable=False,
  default=0`** (`models/base/aggregate_metrics.py:6`). Two consequences: a group's
  `SUM` is never NULL (so a met sample floor implies a non-NULL median), and a group's
  `SUM` **can legitimately be 0**. → **§4B**.

#### Count checks — every counted sentence, both directions

| Counted sentence | Counted thing | Verdict |
|---|---|---|
| §1/title "four consumers" | §2.1 table = 4 rows | ✅ |
| §6.2 header "Per consumer (**all four**…)" | its own table = **6** rows; and 7 surfaces once S-3's worker face is included | ❌ — the header counts a different set from the table under it |
| §2A "**Five** citations checked at source" | its table = **6** rows | ❌ |
| §2A "**Four of five** call sites moved" | the table holds **4** call sites (all moved) + 2 definition anchors (1 moved, 1 held) | ❌ in both readings: 4 of 4 call sites moved; 5 of 6 cited locations moved |
| §2.2 "F-A…F-J" | 10 facts, A–J present | ✅ |
| §8 "two terminals" | table = 2 rows | ✅ |
| §11.1 "T1…T21" | 21 rows | ✅ (but only **19 distinct** mutations — T13 shares T12's, T4 names one swap serving two rows) |
| §11.1 "the **8** `DivisionStep(typical_worker_seconds=…)` test constructors in `test_budget_division.py`" | `DivisionStep(` appears 8× in that file, but only **6** pass the field (1 factory `step()` at `:13-22` + 5 direct at `:245,250,264,269,274`); the real edit surface is the **20** `typical=` argument passes; and **2 production** constructors are unlisted (S-4) | ❌ |
| F-J "all **eight** `domain/item_economics/` files" | 8 `.py` files | ✅ |
| §7.2 `sections_by_basis` {0,2,1} vs `participating_section_count: 3` | 0+2+1 = 3 | ✅ |
| §7.2 `sample_count: 61` under `typical_basis: "section_wide"` vs `section_sample_count: 61` | equal, per §3.6 | ✅ |
| §3.7 "complete set after this pipeline" | 5 rows carrying 6 constants (row 2 carries two) | ✅ |
| §10 "All settled decisions **D1–D22** are recorded verbatim in `owner_decisions.md`" | that file records **D1–D24** verbatim | ❌ — undercount; the following sentence names D23/D24 separately, so the intent is clear and the sentence is still false |
| §10 digest D1…D22 | 22 entries | ✅ |
| Header `round: 1` vs `status: RESOLVED (round 3…)` vs changelog "Round 4" | three different round numbers in one document | ❌ — this amendment makes it round **5** |
| §12 measurement matrix | 5 shapes × 2 statements = **10** measurements; §12 states no count | ⚠️ the planner must enumerate them; an unstated count is where a matrix silently ships at 6 |
| §5 diagram's task-economics branch | names 3 consumers; working-sections is the 4th and is not drawn | ⚠️ not a count claim, but the diagram omits a member the text counts |
| Published baseline "21-ID failing set" (frontend handoff §7) | 21 IDs listed | ✅ |
| F-H "byte-exact goldens cover **two of the four** payloads … for production-time, budget-status and budget-allocations" | the test asserts over **3** payloads; two of them are members of §2.1's four consumers, budget-status is a fifth surface | ⚠️ self-consistent only under that reading — §11.2's 3-row table is the authority; F-H's phrasing is ambiguous, not wrong |

**Nothing found in this sweep invalidates any of D1–D24.**

---

## 3. Domain model & vocabulary

All new pure objects live in `domain/item_economics/typical_filters.py` (new file).
All are `@dataclass(frozen=True)`; the spec is hashable (frozensets/tuples only).

### 3.1 `TypicalFilterSpec` — what population was requested (**⚠ the statement signature quoted here predates the injected clock — see §4A K1; canonicalization and the per-field predicate table are §3A**)

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

### 3.4 `TypicalResolutionPolicy` — what a thin requested population resolves to (**⚠ D25/§4C: the `BROADEN_TO_SECTION` first rung additionally requires a narrowed median `> 0`**)

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


### 3A. `TypicalFilterSpec` — canonicalization and the per-field predicate contract (mechanism-inventory gate, 2026-08-22)

§3.1 states combination semantics in prose ("AND across fields; OR within a collection
field; unknown never matches"). Prose is not a predicate translation, and this object is
also the **dedupe key** for §6.2's batch — a rule-6 mechanism twice over. The contract:

**C1 — canonicalization at construction (`__post_init__`).** Two distinct in-memory
values must never mean the same population, because §6.2 dedupes by value and a
duplicate spec becomes a second, redundant population with a different index.

- A collection field that is set but **empty** (`frozenset()`) is normalized to `None`.
  Consequence: `is_narrowing` is exactly "at least one field is not `None`", and any
  non-`None` collection field is non-empty by construction. (Rejected alternative:
  treating `frozenset()` as "matches nothing" — it is indistinguishable from a
  parse bug in `parse_spec_from_query_params`, and it produces a narrowed population of
  0 that `BROADEN_TO_SECTION` then silently answers section-wide, which is HC-3's shape.)
- A range field `(lo, hi)` with `lo` and `hi` both `None` is **kept** — it is not a
  no-op; see C2.
- A range field with `lo > hi` raises `ValueError` at construction. An empty band would
  otherwise make `narrowed_sample_count = 0` for every section, which under
  `BROADEN_TO_SECTION` answers section-wide with no signal that the question was
  unanswerable.
- Every field's canonical form is fixed so that `__eq__`/`__hash__` (the frozen
  dataclass's own, field-wise) **is** the dedupe key. **No spec hash, digest or
  fingerprint is introduced anywhere in this pipeline** — the founding failure of this
  gate was "a cheap, stable hash", and nothing here needs one.

**C2 — per-field predicate table.** `build_item_match(spec) -> (needs_category_join,
predicate | None)`. `predicate is None` exactly when `spec.is_narrowing` is False.

| Field (when not `None`) | Predicate | Its NULL/unknown row |
|---|---|---|
| `item_category_ids` | `Item.item_category_id IN (ids)` | `item_category_id IS NULL` ⇒ SQL `NULL` ⇒ not TRUE ⇒ excluded |
| `major_categories` | `ItemCategory.major_category IN (values)` | no category ⇒ outer-joined `ItemCategory` is NULL ⇒ excluded |
| `width_cm = (lo, hi)` | `Item.width_in_cm IS NOT NULL AND (>= lo if lo is not None) AND (<= hi if hi is not None)` | NULL width ⇒ FALSE |
| `height_cm`, `depth_cm` | as `width_cm` | as `width_cm` |
| `can_have_upholstery` | `Item.can_have_upholstery IS <value>` (column is `nullable=False`) | no NULL row on the column; absence of the item is handled by C3 |
| `designers` | `Item.designer IN (names)` | `designer IS NULL` ⇒ excluded |

The explicit `IS NOT NULL` in the range rows is load-bearing: it is what makes
`(None, None)` mean **"the dimension is known"** rather than "no constraint".
`(None, None)` sets a field, so `is_narrowing` is True, and the population it selects is
"items whose width is recorded" — a real, non-empty narrowing. State it in the field's
docstring; an implementer reading `(None, None)` as a no-op writes `TRUE` and the
population silently doubles.

**C3 — the conjunction is coalesced to FALSE, not left NULL.** "Unknown never matches"
is implemented once, at the top: the group-level match value is
`coalesce(<conjunction>, FALSE)`. A task with no active PRIMARY `TaskItem`, or whose
`Item` row is deleted, produces `FALSE` — not `NULL`. Three-valued logic happens to give
the right answer inside `count(...) FILTER (WHERE …)` today; it stops giving the right
answer the first time anyone writes `NOT item_match`, and nothing would fail.

**C4 — `needs_category_join`** is `spec.major_categories is not None`, per spec. With K
specs the statement emits the `ItemCategory` join iff **any** spec needs it, and only
those specs' predicates reference it.

**C5 — join predicates live in `ON`, never in the statement's `WHERE`.** LEFT OUTER JOIN
`TaskItem` ON `(task_id, workspace_id, role == PRIMARY, removed_at IS NULL)`; LEFT OUTER
JOIN `Item` ON `(client_id == TaskItem.item_id, workspace_id, is_deleted IS FALSE)`;
LEFT OUTER JOIN `ItemCategory` ON `(client_id == Item.item_category_id)`. Moving any of
those predicates into `WHERE` converts the LEFT into an effective INNER and silently
drops primary-less tasks from the **section-wide** population as well. See §11A for the
named mutation this requires, which T18's current mutation does not produce.

### 3B. Basis and count totality — the rules §3.4/§3.6 leave undecided (mechanism-inventory gate, 2026-08-22)

**B1 — a non-narrowing spec never produces a narrowed basis.** When `spec.is_narrowing`
is False, the narrowed columns are numerically equal to the section columns (§4A, K2), so
a `has_narrowed`-first implementation returns `typical_basis = "item_narrowed"` and, via
§4.3's quantifier, `task_typical_basis = "item_narrowed_uniform"` — for a task whose
`applied_filter` is `null`. Both are false statements on the wire, and §3.6's own rule
("every basis field describes the value it sits next to") forbids them. **Contract:**
`spec.is_narrowing is False` ⇒ `typical_basis ∈ {section_wide, insufficient_sample}` and
`task_typical_basis = "section_wide_uniform"`, unconditionally, without consulting the
narrowed columns. This is the case T3's fixture produces (a primary item with no
category), and no pre-existing test constrains a field that does not exist yet — so
without this row the defect ships green.

**B2 — a zero statistic is a statistic, not an insufficient sample.**
`SelectedTypical.typical_worker_seconds` carries the value the SQL returned, **verbatim,
including `0`**; `typical_basis` names the population it came from. `insufficient_sample`
is reserved for a NULL value (the floor was not met). Layer 2's trigger (`value is None
or value <= 0`, §4.5) is independent of `typical_basis`. Consequence, stated so it is not
reported as a bug: a wire row may read `typical_worker_seconds: 0, typical_basis:
"item_narrowed", sample_count: 7` beside an `allowance_seconds` computed from the neutral
weight. §6.4's disclosure clause therefore reads **"null or zero selected"**, not "null
selected" — see §11A for the second criterion row this implies. (**⚠ D25/§4C:** on task
surfaces the reachable zero form is `section_wide` + `0`; `item_narrowed` + `0` is
unreachable there and remains reachable only on the deferred analytics surface.)

**B3 — `sample_count` for a participating section is `section_sample_count` whenever the
basis is `insufficient_sample`.** §3.6 defers to "the population the policy would have
answered from", but participating sections do not pass through
`resolve_section_typical` at all (§4.3 gives them the uniform basis directly; the policy
argument reaches only excluded sections and the analytics path). Task economics is
`BROADEN_TO_SECTION` by construction (§5), so the answer is `section_sample_count`.
State it, or the rule is undefined on the exact rows where it is read.

**B4 — a section with no evidence row is total, not a `KeyError`.** The statement
outer-joins from `WorkingSection` and therefore returns a row for every live, non-deleted
section — but a task's steps may name a section that is soft-deleted, in which case the
section is absent from both the statement's rows and from production-time's
`section_by_id` (which filters `is_deleted.is_(False)`). **Contract:** a section id
present in the task's steps and absent from the statement's rows yields
`SectionTypicalEvidence(narrowed_sample_count=0, section_sample_count=0, both seconds
None)`, `typical_basis = "insufficient_sample"`, `sample_count = 0` — never a lookup
error. This keeps §7's "always present, non-nullable, explicit default" promise total,
and it replaces the accidental cover that `_step_result`'s two-argument
`typicals.get(section_id, <step attr>)` provides today and that D18's removal deletes
(§6C). Reachability of the soft-deleted-section shape is not proven here; the contract is
total either way and costs one branch.
---

### 3D. The `ItemCategory` join is asymmetric with the `Item` join (plan-2 projection fold, 2026-08-22)

**Routed upstream by the plan-2 projection (L28 / R12), measured, not blocking.** §3A C5
joins `Item` with **both** `workspace_id` and `is_deleted IS FALSE`, and joins
`ItemCategory` with **neither** — though `item_categories` carries both columns
(`item_category.py:19-21`, `:41`).

**Consequence:** a **soft-deleted category still satisfies `major_categories`**. A task
whose item points at a deleted category is narrowed as though the category were live, and
a workspace boundary is enforced on one side of the join and not the other.

**Status: recorded, not changed.** §3A C5 is *determinate* as written, so no implementer
is blocked and phase 2 builds exactly what §3A says. Two reasons to leave it:
`major_categories` has **no V1 producer** — `derive_spec_from_primary_item` emits only
`item_category_ids` (§3.2), so the field is reachable only through the deferred statistics
route — and changing a join predicate is a semantic change to a Critical-ranked mechanism,
which belongs in a phase that owns it with a criterion, not in a fold.

**Trigger that converts this into a real amendment:** the first V1 consumer that populates
`major_categories`, or the statistics route shipping — whichever comes first. At that
point §3A C5 gains `workspace_id` and `is_deleted IS FALSE` on the `ItemCategory` `ON`
clause, with a criterion row per predicate. Whichever phase does that owns the change.

Trace: plan-2 projection L28/R12 · §3A C5 · §3.2 (no V1 producer) · §9 (route deferred).
---

### 3C. Parser error boundary — `ValidationError`, not `ValueError` (plan-1 projection fold, 2026-08-22)

The plan-1 projection found an intention gap (its ledger L15): §3A C1 fixes `ValueError`
for rejected specs, but this repo's convention splits error types by who can trigger them
— `ValidationError` (`errors/validation.py`, HTTP 422) for anything a client can cause,
`ValueError` for programmer preconditions. A parser `ValueError` reaching the deferred
statistics route would turn a user typo (`width_cm_min=81&width_cm_max=80`) into a 500.

**Contract (coordinator resolution, routed upstream per the home-artifact rule):**

- **`TypicalFilterSpec.__post_init__` keeps `ValueError`** — construction is a programmer
  boundary; §3A C1 is unchanged there.
- **`parse_spec_from_query_params` raises `ValidationError`** for every client-triggerable
  rejection: an inverted band (`lo > hi`, whether pre-checked or translated from the
  dataclass's `ValueError`) and an unrecognised `major_categories` value. Silently
  ignoring an unrecognised category is forbidden — it would answer a *different* narrowed
  question than the one asked, HC-3's shape.
- **The parser's input is the router's already-typed dict**, per this repo's universal
  router convention (typed FastAPI `Query(...)` parameters assembled into
  `ctx.query_params: dict`): repeatable families arrive as `Sequence[str] | None`, bounds
  as `int | None`, `can_have_upholstery` as `bool | None`, and **an absent parameter
  arrives as an absent key OR an explicit `None` value — the two are equivalent**.
  String→int coercion and boolean spelling are the future route's FastAPI declarations,
  outside the parser's contract. Unknown *keys* are ignored (§6.8); unknown *values* of a
  known enum family are rejected.
- **A bare `str` is not a sequence of ids, and a non-iterable is not a sequence at all**
  (added at the plan-1 review fold, 2026-08-22, finding S2 — measured, not hypothetical).
  A `str` satisfies `Sequence[str]` structurally, so the round-1 parser iterated it
  character-wise: `{"item_category_ids": "cat_a"}` produced a spec narrowed to
  `{'c','a','t','_'}` — **a narrowing spec over a population of zero items**, which
  `BROADEN_TO_SECTION` then answers section-wide with no signal that the question was
  unanswerable. That is HC-3's shape reached through the parser. **Contract:** for every
  repeatable family, a `str`/`bytes` value and any non-iterable value raise
  `ValidationError`, exactly as an unrecognised enum value does. The error boundary is
  **symmetric across families** — the round-1 asymmetry (a non-iterable
  `major_categories` raised `ValidationError`/422 while a non-iterable
  `item_category_ids` raised a bare `TypeError`/500) is the defect this clause closes.

The route itself remains deferred (§9); this section binds the parser it ships early.

Trace: projection handoff L8/L9/L15 · §3A C1 (unchanged at construction) · §6.8
(parameter names) · `errors/validation.py` · `services/context.py` ·
`routers/api_v1/working_sections.py` (the convention's nearest instance).
---

## 4. The three layers (exact semantics)

### 4.1 Layer 1 — statistical resolution (per section, task-free)

For each (section, spec): compute both populations in one pass; resolve per §3.4.
Both populations are always computed — strict mode discards nothing at the SQL
layer; policy is applied purely, after the facts are in hand (§2 F-J, §5).

### 4.2 The query mechanism (facts only, policy-blind) (**⚠ signature and result shape SUPERSEDED by §4A**)

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

### 4.3 Layer 1.5 — task reconciliation (`uniform_basis_v1`) (**⚠ D25/§4C: the quantifier below quantifies `has_usable_narrowed`, not `has_narrowed`**)

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

### 4.4 The reachability invariant (**⚠ SUPERSEDED by §4B — the invariant below is false in both of its halves; do not build a criterion from it**)

Narrowed ⊆ section-wide (per §3.1 unknown-never-matches) ⇒ `has_narrowed ⇒
has_section` ⇒ under `item_narrowed_uniform` **no participating section can reach
layer 2**. Layer 2 is reachable only under `section_wide_uniform` (or on excluded
sections whose ladder bottoms out). Test T10.

### 4.5 Layer 2 — terminal business fallback (per consumer; §8) (**the `<= 0` clause here is what breaks §4.4 — see §4B**)

Applied only where `SelectedTypical.typical_worker_seconds` is `None` **or `<= 0`**
(zero typicals are unusable today — `test_c3_zero_typical_is_not_usable...` — and
this pipeline preserves that): in-task median of the usable selected values;
terminal only when no usable value exists in the task. Division: `terminal =
Fraction(1,1)` (weight-neutral). Price-scenario: `terminal = Fraction(0,1)`
(contribution-neutral). Never serialized (§6.4).


### 4A. The statement contract — signature, clock, result shape, HC-4 scope (mechanism-inventory gate, 2026-08-22)

**This section supersedes the signature and call forms written in §3.1, §4.2 and §5**,
which were authored before `typical_times_statement` gained its injected clock (§2A). It
adds nothing to them semantically; it makes them compile against the real function and
pins the shape §4.2 deliberately left to "internal strategy".

**K1 — the signature.**

```python
def typical_times_statement(
    workspace_id: str,
    *,
    now: datetime | None = None,
    specs: Sequence[TypicalFilterSpec] = (),
): ...
```

Both parameters keyword-only; `now` keeps its existing name, position among keywords and
default. Per-consumer clock after V1:

| Consumer | `now` | `specs` |
|---|---|---|
| `get_task_production_time` | `ctx.now` — **unchanged** | derived spec (K ≤ 1) |
| `get_task_budget_allocations` | `ctx.now` — **unchanged** | deduped specs (K ≥ 0) |
| `get_task_price_scenario` | **`ctx.now` — CHANGED from its own wall-clock read** | derived spec (K ≤ 1) |
| `get_working_section_typical_times` | default (its own wall-clock read) — **unchanged** | `()` |

**Why price-scenario moves and working-sections does not.** HC-2 requires every
task-scoped consumer to observe *identical* layer-1 evidence for the same task and
section, **including identical counts**. The 90-day cutoff is derived from the clock, so
two surfaces reading the clock at different instants can straddle the boundary for a
group whose `max(closed_at)` sits at it, and disagree on `sample_count` and therefore on
the median. That is an HC-2 violation with no error, and it also makes T6 undecidable:
a test that freezes the clock for production-time but not for price-scenario cannot
assert cross-service equality deterministically. The neighbouring pipeline's HC-3A names
the default read as "the compatibility shim for its callers **outside this pipeline** (the
working-sections surface and the price-scenario typical block, both settled-basis and out
of scope)" — this pipeline brings price-scenario into scope for the same evidence, so the
shim's stated justification lapses for it and only for it. `ServiceContext.now` is always
present (`context.py:24`, `default_factory`), so the change is a one-line argument, no
payload key moves, and price-scenario becomes deterministic within a request.
`/working-sections/typical-times` is task-free, HC-2 does not bind it, and D24 requires it
byte-identical — it keeps the default. **Listed for owner ratification: this extends the
live-clock determinism contract to a fourth surface that pipeline deliberately excluded.**

**K2 — the result contract for K distinct specs.** §4.2 correctly refuses to contract the
*execution strategy*; the *result shape* must be contracted, because §6.2 makes "one
statement call for the batch" and `SectionTypicalEvidence` carries no spec identity.

```
len(specs) == 0  ->  columns (client_id, name, sample_count, typical_worker_seconds)
                     — today's shape, today's SQL (HC-4)

len(specs) == K >= 1  ->  columns
                     (client_id, name, spec_index,
                      section_sample_count,  section_typical_worker_seconds,
                      narrowed_sample_count, narrowed_typical_worker_seconds)
                     exactly one row per (live non-deleted working section x spec_index)
```

- `spec_index ∈ [0, K)` **positionally indexes the caller's own `specs` sequence.** It is
  not a hash, not a spec serialization, not a category id. The caller holds the sequence
  it passed, so the mapping needs no canonicalization contract and cannot drift (§3A C1).
- **Row cardinality is total**: every live section appears once per `spec_index`, sections
  with no qualifying history included (counts 0, seconds NULL). This preserves today's
  outer-join-from-`WorkingSection` behaviour per index.
- **The `section_*` columns are spec-independent and must be byte-equal across every
  `spec_index` for a given section.** This is the observable form of §4.2's
  "FILTER, never WHERE" rule and it is what makes §4.4's subset claim true (§4B).
- Domain mapping: `(client_id, spec_index) -> SectionTypicalEvidence`. Neither
  `spec_index` nor any column name appears in a domain object or on the wire.

**K3 — shape is a function of `K`, never of `is_narrowing`.** A caller that dedupes 50
tasks' specs and gets back a *different row shape* depending on whether every derived spec
happened to be empty would take a different parsing branch on a data-dependent condition —
a first-order silent failure. Therefore:

- `K == 0` ⇒ today's shape and today's SQL. This is the only condition HC-4 binds on.
- `K >= 1` ⇒ the keyed shape, **even if every spec is non-narrowing**; for a
  non-narrowing index the match is the constant TRUE, no item joins are emitted for it,
  and `narrowed_* == section_*` by construction.
- **Callers normalize before calling:** the sequence passed contains only *narrowing*
  specs. A task whose derived spec is non-narrowing maps to `spec_index = None` and takes
  `narrowed_* := section_*` (and, by §3B B1, a section-wide basis). If every task's spec
  is non-narrowing the caller passes `specs=()` and gets the K == 0 shape. This is what
  makes "empty spec ≡ no spec" (§3.1) true at the SQL boundary rather than only in prose.

**K4 — the two-population FILTER arithmetic, composed.**

```
qualifying   := grouped_steps.c.latest_closed_at >= cutoff
match_k      := coalesce(<spec k's item match>, FALSE)          -- 3A C3, group-level

section_sample_count   := count(task_id) FILTER (WHERE qualifying)
section_typical        := CASE WHEN section_sample_count  >= TYPICAL_MIN_SAMPLE_SIZE
                          THEN cast(round(percentile_cont(0.5) WITHIN GROUP (ORDER BY group_seconds)
                                          FILTER (WHERE qualifying)) AS INTEGER) END
narrowed_sample_count  := count(task_id) FILTER (WHERE qualifying AND match_k)
narrowed_typical       := CASE WHEN narrowed_sample_count >= TYPICAL_MIN_SAMPLE_SIZE
                          THEN cast(round(percentile_cont(0.5) WITHIN GROUP (ORDER BY group_seconds)
                                          FILTER (WHERE qualifying AND match_k)) AS INTEGER) END
```

- **The min-sample rule is applied per population, against that population's own count.**
  Today the module has one `sample_count` local reused by both the count column and the
  `CASE` threshold (`get_working_section_typical_times.py:47, :50`); the obvious
  copy-paste is to reuse it for the narrowed `CASE` too. Named mutation in §11A.
- **`match_k` must reach the outer aggregate as a non-aggregate column.** That is the
  real composition constraint behind §4.2's `bool_or` sketch: if the item joins are
  attached inside the `grouped_steps` subquery, the match must be selected there as
  `bool_or(match_k)`; if they are attached outside, to `grouped_steps.c.task_id`, the
  match is already per (section, task) and no `bool_or` exists. Both are permitted —
  §4.2's "internal strategy is not contract" stands — but each carries the same
  obligation, expressed as three behavioural criteria with their own mutations (§11A):
  section columns invariant to specs; per-group `SUM` invariant to specs; a primary-less
  task in `section_*` and not in `narrowed_*`. PostgreSQL permits `FILTER` on ordered-set
  aggregates and the current statement already relies on it, so no CTE is forced.

**K5 — HC-4, scoped precisely.** HC-4's byte-identity claim binds on **`len(specs) == 0`,
at both clock forms**. The cutoff enters as a bound parameter (`latest_closed_at >=
cutoff`, a Python `datetime`), so it does not appear in the compiled string and the string
is `now`-independent: `typical_times_statement(ws)` and `typical_times_statement(ws,
now=X)` must both compile to the string today's corresponding call compiles to. T11
therefore compiles **without `literal_binds`** (with it, the cutoff inlines and the
comparison becomes a clock race), runs at **both** clock forms, and compares against a
**frozen literal snapshot** of the pre-refactor string — see §11A, where T11's named
mutation is currently inert.

HC-4's second clause ("every consumer that passes no spec produces its current payload
unchanged") reaches, after V1, only `/working-sections/typical-times` (D24). The other
three pass `specs=()` exactly when every derived spec is non-narrowing — T3's case — and
there "unchanged" means **every pre-existing numeric field unchanged**, not byte-identical,
since §7.2/§7.3 add keys. §11.2's keys-only golden criterion is the same statement; T3's
wording is normative and must not be paraphrased.

### 4B. The reachability invariant, corrected (mechanism-inventory gate, 2026-08-22) (**⚠ strengthened by §4C / D25 — the deliberate `<= 0` reachability described below is closed for participating sections by the owner's ruling**)

**§4.4 as written is false, twice, and T10 asserts it.**

1. **The chain proves the wrong thing.** Under `item_narrowed_uniform` the selected value
   is the *narrowed* value. `has_narrowed ⇒ has_section` says nothing about whether the
   narrowed value can reach layer 2.
2. **`<= 0` is a real hole.** §4.5 fires layer 2 where the selected value is `None`
   **or `<= 0`**, deliberately (`test_c3_zero_typical_is_not_usable_and_uses_the_median`,
   `test_price_scenario_query.py:119`). `TaskStep.total_working_seconds` is
   `Integer, nullable=False, default=0` (§2B S-8), so a COMPLETED step can carry 0
   seconds and a group's `SUM` can be 0. Five or more qualifying same-category groups all
   summing to 0 give `narrowed_sample_count = 5` ⇒ `has_narrowed` ⇒
   `item_narrowed_uniform` ⇒ selected value `0` ⇒ **layer 2 fires on a participating
   section under `item_narrowed_uniform`.**

**The correct invariant:**

> Under `item_narrowed_uniform`, no participating section reaches layer 2 **through a
> NULL selected value**: `narrowed_sample_count >= TYPICAL_MIN_SAMPLE_SIZE ⇒
> narrowed_typical_worker_seconds IS NOT NULL`, because the statement's `CASE` returns
> non-NULL exactly when that population's own count meets the floor, and `percentile_cont`
> over one or more non-NULL `group_seconds` is non-NULL — every group's `SUM` is non-NULL
> because the column is `nullable=False` (§2B S-8).
> Layer 2 remains reachable under `item_narrowed_uniform` **only** through §4.5's `<= 0`
> clause, and that path is deliberate.

**And the subset claim's real reason.** Narrowed ⊆ section-wide holds because the
item match is applied **only inside the aggregate FILTER** and `qualifying AND match_k`
⊆ `qualifying` (§4A K4). §3.1's "unknown never matches" is what makes the subset *strict*
in the presence of unknowns; it is not what makes it a subset. A criterion built from
§4.4's stated reason tests the wrong mechanism.

T10 splits into two rows; see §11A.

### 4C. D25 — a usable narrowed median is required (owner answer to card C, folded by the coordinator, 2026-08-22)

**Owner ruling (card C → D25, 2026-08-22): "Require a real figure."** A narrowed
population whose median is zero is not "knowing the typical time for this item"; the task
falls back to section-wide figures throughout. Verbatim record in `owner_decisions.md`.

**Contract.**

- `SectionTypicalEvidence` gains one derived predicate:
  `has_usable_narrowed -> has_narrowed and narrowed_typical_worker_seconds is not None
  and narrowed_typical_worker_seconds > 0`.
  `has_narrowed` itself is unchanged — it remains §3.3's pure count predicate.
  *(Corrected at the plan-1 projection fold, 2026-08-22: the original text omitted the
  `is not None` conjunct, reasoning that §4B's SQL guarantee makes the median non-NULL
  wherever the floor is met. That guarantee holds for SQL-produced evidence, but the
  dataclass permits `(count ≥ floor, median None)`, where `None > 0` raises `TypeError` —
  the predicate must be total over every shape the dataclass permits, the same totality
  standard §3B applies. The conjunct is behavior-neutral on all SQL-reachable shapes.)*
- **§4.3's quantifier quantifies `has_usable_narrowed`, not `has_narrowed`:**
  `item_narrowed_uniform` requires the participating set non-empty AND every
  participating section `has_usable_narrowed`; otherwise `section_wide_uniform`.
- **§3.4's `BROADEN_TO_SECTION` first rung gains the same condition:** the narrowed
  value is selected only when the floor is met AND the narrowed median is `> 0`; a
  zero-median narrowed population steps to the section rung. This is the per-section
  form of the same ruling and governs excluded sections' independent resolution (§4.3).
  The section rung is unchanged: a zero **section-wide** median is still published
  verbatim (§3B B2) and still reaches layer 2 via §4.5.
- **`ANSWER_AS_ASKED` is deliberately NOT changed.** The analytics surface answers the
  narrowed question as asked, and a sufficient-count median of `0` IS the honest answer
  (HC-3, D17, D19). The asymmetry is the two policies' whole point: economics prefers
  usable values; analytics reports the asked statistic.
- **No SQL change.** Both populations are computed exactly as §4A specifies; D25 is a
  pure layer-1.5 rule — one predicate, one quantifier argument, one ladder rung.

**Consequences.**

- **§4B's residual reachability closes.** Under `item_narrowed_uniform` no participating
  section reaches layer 2 **at all**: a NULL selected value is impossible (§4B's
  corrected invariant) and a `<= 0` one is excluded by this ruling. Layer 2 on a
  participating section is reachable only under `section_wide_uniform` (a zero or
  insufficient section-wide median). §4.5's trigger, `apply_business_fallback`, T4 and
  T21 are untouched — zero remains unusable wherever it is selected.
- **On the wire, `typical_worker_seconds: 0` beside `typical_basis: "item_narrowed"` is
  unreachable on every task surface** (participating rows by the quantifier; excluded
  rows by the BROADEN rung). The reachable zero-statistic form is `section_wide` + `0`.
  On the deferred `ANSWER_AS_ASKED` statistics surface, `item_narrowed` + `0` remains
  reachable and honest. §3B B2's example reads accordingly.
- **§11A T10b is superseded as written** — its fixture (5 same-category groups summing
  0) now produces `section_wide_uniform`, which becomes the assertion, not the setup.
  Corrected row **T10b′**: section A: 5 same-category groups summing 0 (narrowed count
  5, median 0); section B: narrowed count ≥ 5, median 600 — contract:
  `task_typical_basis = "section_wide_uniform"` (A's zero median disqualifies the task)
  and both sections take section-wide values. Named mutation: in the reconciliation
  quantifier (`typical_filters`, definition), quantify `has_narrowed` instead of
  `has_usable_narrowed` — mutation yields `item_narrowed_uniform`, A's row
  `0 / item_narrowed` with layer 2 firing on a participating section. Both sides: the
  emitted `task_typical_basis` strings differ (`section_wide_uniform` vs
  `item_narrowed_uniform`); exact-literal assertion on that field is the bite.
- **§11A T16b's fixture moves to the reachable shape**; its assertion (a zero statistic
  is disclosed as a statistic, never as `insufficient_sample`) is unchanged. Corrected
  fixture: a `section_wide_uniform` task with a participating section whose
  **section-wide** median is 0 at count ≥ floor — contract row:
  `typical_worker_seconds: 0, typical_basis: "section_wide", sample_count: <n>`,
  `allowance_seconds` present. Named mutation unchanged (publish
  `null` / `insufficient_sample` for the zero-valued statistic).

Trace: card C (`owner_decisions.md` D25) · §3.3 · §3.4 · §4.3 · §4B · §3B B2 ·
§11A T10b/T16b · §4.5 and T21 (deliberately unchanged).
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

### 6.2 Per consumer (all four; no consumer issues more queries than today) (**⚠ the table below is six rows, and §6A A5 adds the worker face as a seventh surface — "all four" counts the consumers, not the table (§2B count check)**)

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

### 6.4 Layer-2 visibility (HC-2's third clause, per surface) (**⚠ the `is_estimated` definition below is SUPERSEDED by §6B — taken literally it reverses a shipped payload value; the disclosure clause reads "null OR ZERO selected", per §3B B2**)

- Division surfaces: a null-selected section publishes `typical_worker_seconds:
  null, typical_basis: "insufficient_sample"` **with its computed
  `allowance_seconds` beside it** — that adjacency is the disclosure. The neutral
  weight is a `Fraction` in ratio space with no duration meaning and is never
  serialized as seconds. Task level: `sections_by_basis.insufficient_sample ≥ 1`.
- Price-scenario: `is_estimated` means exactly **"layer 2 fired for ≥ 1
  participating section"** — and specifically does NOT become true merely because
  the task reconciled to `section_wide_uniform`. This is a semantic clarification
  to an approved contract and gets an explicit line in the handoff (§11.3).


### 6A. `TaskBudgetStatus` — the additive contract and its five construction surfaces (mechanism-inventory gate, 2026-08-22)

§6.2 row 1 mutates a dataclass consumed by a shipped endpoint from another pipeline
(`get_task_price_scenario.py:195`) and by a WORKER/SELLER face this document never names
(§2B S-3). The lineage has already paid one round for a `TaskBudgetStatus` claim.

**A1 — additive only.** Exactly one new field, appended last, with a default. No existing
field's name, type, order or value changes; `_empty_status`'s and
`_build_evaluated_status`'s existing outputs are untouched; the budget-status serializer
is untouched; `golden_budget_status.json` is unchanged. `TaskBudgetStatus` today carries
**14** fields including `result: ItemCostResult | None` (§2B S-1; "13" corrected to the
measured 14 at the planner fold, 2026-08-22) — the "carries only
`item_id`" grounding in F-A is stale and is not a basis for reasoning about the change.

**A2 — carry the derived spec, not the `Item`.** The new field is
`typical_filter_spec: TypicalFilterSpec | None = None`, computed once by
`derive_spec_from_primary_item` at the load site. Carrying the `Item` instead would put a
mutable ORM instance on a read-model dataclass that crosses three services, and would
leave each consumer to re-derive — the fork HC-1 exists to prevent, one layer up.

**A3 — which item derives it.** The **active PRIMARY `Item` loaded by
`_load_task_and_item`**, never `evaluation.item_id`. The spec describes "work comparable
to the task at hand" (§1); the evaluation's item is a historical binding, and
`item_binding == "mismatched"` already exists to flag when the two differ (§2B S-2).
Recorded consequence, so it is not later "fixed": on a `mismatched` task,
`typical_resolution.applied_filter` describes the current primary item while `item_id`
names the evaluated one. That combination is a criterion row.

**A4 — `None` is ambiguous, and the ambiguity has an expiry date.** `_empty_status`
receives no item and would default the field to `None`, which is indistinguishable from
"a primary item that has no `item_category_id`". In V1 both collapse to
`TypicalFilterSpec()` (§3.2) so the ambiguity is harmless. **It stops being harmless the
moment `COMPARABILITY_PROFILE` v2 adds a non-category axis** — the exact silent-policy
drift D11 exists to prevent. Either pass the item through at all **four** `_empty_status`
call sites (`get_task_budget_status.py:121, :132`;
`get_task_budget_status_worker.py:38, :48`), or record this expiry beside the field's
default. The v2 return path (§9) inherits the obligation.

**A5 — the worker face is a row of §6.2's table.** `get_task_budget_status_worker` calls
`_load_task_and_item`, both construction helpers, and returns `TaskBudgetStatus` to a
money-redacted serializer. It gains the field and **must not publish it**; its own comment
("must not inherit a future manager change") is the standing instruction. With it, §6.2's
table is **seven** rows, not the "all four" its header claims (§2B count check).

### 6B. `is_estimated` — the clarification reverses a payload value (mechanism-inventory gate, 2026-08-22)

Today (`get_task_price_scenario.py:175`):
`is_estimated = (sections_total == 0) or (sections_without_sample > 0)`, where
`sections_total = len(participating)`.

§6.4 redefines it as **"layer 2 fired for ≥ 1 participating section"**. Taken literally —
and it is written as an exact definition — a task with **zero participating sections** has
zero sections where layer 2 fired, so `is_estimated` becomes **False** where today it is
**True**, beside `total_seconds: 0`. A manager reading the price scenario of a task with
no live steps would see "measured, and it is zero" instead of "estimated". §6.4 calls
itself "a semantic clarification to an approved contract"; as written it is a behaviour
change to a shipped payload, in the direction of over-confidence.

**Contract:**

```
is_estimated := (participating_section_count == 0)
                OR (layer 2 fired for >= 1 participating section)
```

The `participating_section_count == 0` disjunct is **retained verbatim**. The
clarification replaces only the second disjunct's *definition*: "layer 2 fired" means the
**selected** typical was `None` or `<= 0` for that section — which is exactly the set
`sections_without_sample` counts today, so the value is unchanged in every case, and
§6.4's genuine content survives intact ("`section_wide_uniform` alone does not set it").

**The two existing fields §7.4 keeps, defined under the new regime** (the intention names
them in its CURRENT block and adds only `typical_resolution`, so both ship on):

- `sections_total` := `participating_section_count`. Meaning unchanged.
- `sections_without_sample` := the count of **participating** sections whose **selected**
  typical is `None` or `<= 0` — i.e. exactly where layer 2 fired. Under
  `section_wide_uniform`, a section with a usable section-wide value is **not** counted
  even though its narrowed sample was thin. This is §3.6's naming rule applied; the
  tempting misreading is "sections without a *narrowed* sample", which would silently
  re-scope a published field.

### 6C. Typicals stay settled-basis — restating the neighbouring pipeline's most expensive mistake (mechanism-inventory gate, 2026-08-22)

The archived `live_clock_for_working_time_economics` intention, §4.3A, closes with one
contract line: *"`divide_production_budget` receives live worked seconds and **nothing
else changes about its inputs** — `allowed_worker_minutes`, `typicals_by_section` and
`section_attributes` are settled-basis values."* Its path-3 paragraph calls a "make it
consistent" change here **"the most expensive mistake available in this feature"**, and
records that no guard against it existed anywhere in the repository until that pipeline's
phase 2 round 6.

**This pipeline is the first change to those inputs since**: §6.2 replaces
`typicals_by_section: Mapping[str, int | None]` with `Mapping[str, SelectedTypical]`. The
contract line must therefore be restated, not silently superseded:

> Every `typical_worker_seconds` inside every `SelectedTypical` handed to
> `divide_production_budget` originates from the statement's SQL aggregate over the
> **persisted** `TaskStep.total_working_seconds` column. No value produced by
> `load_live_worked_seconds` reaches a typical, a sample count, or the item-match
> predicate, on any path. Layer-2 terminals are `Fraction`s in weight space and are never
> seconds (§8, §6.4). `allowance_seconds` remains byte-identical to today at equal
> database state whenever the resolved weights are unchanged.

Why it is not self-evident: after this pipeline, production-time and budget-allocations
hand `divide_production_budget` `DivisionStep`s whose `total_working_seconds` **is** the
live figure, alongside typicals that must not be. The two live in the same call. The
named mutation is in §11A.

**And the D18 removal surface, corrected (§2B S-4).** Removing
`DivisionStep.typical_worker_seconds` edits **two production files** —
`get_task_production_time.py:50-62` and `get_task_budget_allocations.py:217-229` — not
only the test constructors §11.1 lists. Two further consequences:

- `_step_result`'s `typicals.get(section_id, _value(step, "typical_worker_seconds"))`
  (`budget_division.py:264`) uses the **two-argument** `.get`: its default fires only on a
  **missing key**, never on a `None` value. Removing the field turns it into a plain
  lookup whose miss must be contracted — that is §3B B4, which is what today's accidental
  default has been covering.
- `budget_division.py:324`'s fallback read sits inside `if typical is None`, so it does
  execute in production today and always yields `None`. It is deleted with the field; the
  surrounding branch is not.
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


### 11A. Test-matrix corrections — five inert named mutations, ten added rows (mechanism-inventory gate, 2026-08-22)

Every mutation below was checked by the standing rule: **state the value under the
contract and the value under the mutation, and confirm they differ.** All arithmetic here
is done on paper, from the code cited in §2B; nothing in this gate was executed.
§11.1's rows are otherwise unchanged and remain authoritative.

#### Inert as written — each reads perfectly well in prose

| Row | Why the mutation cannot redden it | Repair |
|---|---|---|
| **T5** | The mutation names "a fallback value" inside `reconcile_task_typicals`, which produces `SelectedTypical`s only — layer-2 fallbacks live in `apply_business_fallback` (§4.5, §8) and are **never serialized** (§6.4), so no mutation of one can change an emitted `typical_worker_seconds`. Under the contract and under the mutation the emitted value is the same SQL integer. | Mutate a **selected** value: in `reconcile_task_typicals` (definition), emit a participating section's value multiplied by the ratio of two others. Contract emits `600`; mutation emits `600 × (900/300) = 1800`. |
| **T7** | "Reintroduce a private predicate in one service" is inert when the copy is **faithful** — and a faithful copy is what an implementer writes. Contract: three services agree. Mutation: three services still agree. | Name the disagreeing form: reintroduce a private predicate in one service that **omits `FAILED`** from the excluded set. Contract: all three select `{A, B}`; mutation: one selects `{A, B, C}`. |
| **T11** | "Compiles to today's SQL string" is vacuous if the expected side is obtained by calling the same function: `f(x) == f(x)` survives any mutation of `f`. | The expected side is a **frozen literal snapshot** of the pre-refactor compiled string, captured once and committed. Compile **without `literal_binds`** (with it the bound cutoff inlines and the assertion becomes a clock race), and run the row at **both** clock forms (§4A K5). Contract: string equals the snapshot; mutation (unconditional item joins): the string gains `LEFT OUTER JOIN task_items … LEFT OUTER JOIN items …`. |
| **T14** | `apply_business_fallback` computes `filled = median(usable) if usable else terminal`, so a non-`Fraction` `terminal` is never touched when any usable value exists — annotations do not enforce. Contract and mutation both return the median; no `TypeError` is raised. | Bind the rule at the boundary (charter rule 11): `apply_business_fallback` validates `isinstance(terminal, Fraction)` on entry and fails closed. The mutation becomes "delete the entry guard", and the row bites on **any** fixture rather than only on the empty-`usable` one. Keep an empty-`usable` fixture as the second row. |
| **T19** | The bite depends on a strategy §4.2 deliberately leaves free. With the item joins **inside** the `grouped_steps` subquery, dropping `role == PRIMARY` fans the join to 3 rows and makes the group `SUM` `3S` — but the subquery still emits **one row per (section, task)**, so `count(task_id)` is `1` in both populations and T19's "counts once in both populations" stays green. It bites only under the outer-attachment strategy. | Assert the **value** as well as the count: the section's median is `S`, not `3S`. And enumerate the two fixtures rule 2 requires — secondaries of the **same** category as the primary (membership unchanged, only the value/count move) and one secondary of a **different** category (membership itself moves for a task whose primary does not match). |

#### Rows the contracts above add (ten: T10a replaces T10; nine are new)

| # | Case | Asserts | Named mutation (file · definition-vs-call-site) | Both sides |
|---|---|---|---|---|
| **T10a** | replaces T10 | under `item_narrowed_uniform`, no participating section's selected value is `NULL` | `typical_filters` (definition): define `has_narrowed` as `narrowed_sample_count >= 0` | narrowed count 3 (below floor), value `NULL` — contract: task is `section_wide_uniform`; mutation: `item_narrowed_uniform` with every participating selected `NULL` ⇒ layer 2 on a participating section |
| **T10b** (**⚠ superseded by §4C / D25 — use row T10b′ there**) | **new** — §4B | a participating section whose narrowed median is exactly `0` under `item_narrowed_uniform` **does** reach layer 2, in both consumers | treat `0` as usable in `apply_business_fallback` (definition) — **the same mutation T21 bites on; recorded per rule 12** | section A: 5 same-category groups summing 0; section B: median 600 — contract: A's weight/duration comes from `median({600}) = 600`, price-scenario total `1200`, `is_estimated` true; mutation: A resolves to `0`, total `600`, `is_estimated` false |
| **T18b** | **new** — §3A C5 | a join predicate moved from `ON` into the statement's `WHERE` is caught | `_typical_item_filter` / statement (definition): move `role == PRIMARY` (and, as a second row, `removed_at IS NULL`) out of the `ON` clause into `WHERE` | history with one primary-less task — contract: `section_sample_count = N`; mutation: `N − 1`. T18's own `outerjoin → join` mutation does not produce this form, which is the likelier slip |
| **T22** | **new** — §4A K4 | the narrowed `CASE` threshold reads the **narrowed** count | statement (definition): compare `section_sample_count >= TYPICAL_MIN_SAMPLE_SIZE` inside the narrowed `CASE` | section population 70, narrowed 2 — contract: `narrowed_typical = NULL`, and under `ANSWER_AS_ASKED` the analytics answer is `null`/`insufficient_sample`; mutation: a two-sample median is published, the exact HC-3 violation. SQL-layer sibling of T12, which mutates the policy branch |
| **T23** | **new** — §3B B1 | a non-narrowing spec never yields a narrowed basis | `typical_filters` (definition): consult `has_narrowed` before checking `spec.is_narrowing` | T3's fixture (primary item with no category) — contract: `task_typical_basis = "section_wide_uniform"`, per-section `section_wide`, `applied_filter: null`; mutation: `item_narrowed_uniform` / `item_narrowed` beside a null filter. **T3 does not constrain this**: it asserts numeric identity, and these are new string fields |
| **T24** | **new** — §6C | typicals handed to `divide_production_budget` are settled-basis | `get_task_production_time` (call site): pass `live_seconds[step]` into one section's typical | a task with an open WORKING record, served twice at two `ctx.now` values over identical database state — contract: every `allowance_seconds` identical across the two calls; mutation: the section's weight ticks, `total_weight` changes, `_largest_remainder` redistributes, and **every** section's allowance moves. Asserting this on price-scenario requires §4A K1's clock injection |
| **T25** | **new** — §4A K2 | the `section_*` columns are byte-equal across every `spec_index` and equal to the `K == 0` call's columns | statement (definition): apply the item match as a `WHERE` instead of inside the aggregate `FILTER` | narrowed population 6, section population 20 — contract: `section_sample_count = 20` at every index; mutation: `6`. The general form of T18, which today covers only the primary-less-task case |
| **T26** | **new** — §4A K4 | the per-group `SUM` entering the percentile is identical with and without specs | statement / `_typical_item_filter` (definition): drop `removed_at IS NULL` from the `TaskItem` `ON` clause | a task with one removed primary and one current one — contract: group sum `S`; mutation: `2S` under the inner-attachment strategy, and `count(task_id) = 2` under the outer one. **Bites under either strategy**, which is why it exists |
| **T16b** (**⚠ fixture amended by §4C / D25 — zero arises via a section-wide median on a `section_wide_uniform` task**) | **new** — §3B B2 | the **zero**-selected division row discloses correctly | `_step_result` / the serializer (definition): publish `null` + `insufficient_sample` for a zero-valued statistic | a section with 7 same-category groups all summing 0 — contract: `typical_worker_seconds: 0`, `typical_basis: "item_narrowed"`, `sample_count: 7`, `allowance_seconds` present; mutation: `null` / `insufficient_sample` / the section count. §6.4's disclosure clause reads "null **or zero** selected" |
| **T27** | **new** — §8 | `is_estimated` stays true for a task with no participating sections | `_typical_block` (definition): drop the `sections_total == 0` disjunct | a task whose every section is excluded — contract: `is_estimated: true`, `total_seconds: 0`; mutation: `is_estimated: false` beside `total_seconds: 0` (§6B) |

#### One correction to §8's stated reason

§8 says the division terminal `Fraction(1, 1)` is correct because "0 starves the section
of allowance". It does more than that: with `terminal = 0` and no usable typical anywhere
in the task, **every** resolved weight is `0`, `total_weight` is `0`, and
`budget_division.py:338-343`'s `… / total_weight` raises `ZeroDivisionError`. The terminal
is a division-by-zero guard stated in a parenthesis — the shape the corpus rule "every
`max(`, `min(` and `or 0` in a contract is a candidate criterion row" exists to catch. T4's
swap mutation therefore reddens by **raising**, not by asserting a different number; the
criterion says so, and D22's reason is stronger than it reads.
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

### 12A. D26 — the shapes are corrected and the gate is measurement, not a threshold (2026-08-22)

**Owner ruling (D26), answering the plan-2 projection's card 1.** There is **no
acceptance ceiling**. The ten measurements are taken and recorded in full, but no number
blocks a phase. Verbatim record in `owner_decisions.md`.

**Two corrections to §12 above, both consequences of the ruling:**

1. **The batch shape was wrong.** §12 measures "a batch of **50** tasks". 50 is the API
   cap (`get_task_budget_allocations._MAX_TASK_IDS`), not the operating point: **the
   frontend paginates task queries at 20**. The realistic row is therefore **20 tasks ×
   {5, 10, 20} categories**, with **one 50 × 20 row retained as the API-ceiling worst
   case**, labelled as such. Measuring only the ceiling would have described a load
   nobody generates.
2. **Five of the ten cells are constant by construction** (projection depth area 5): the
   *current* statement is spec-blind, so its cost is the same query at all five shapes,
   and the *new* no-spec row equals it by C1/HC-4. The doc **states this explicitly** —
   unrecorded, a reviewer cannot tell a measurement from a copy.

**Why no ceiling** (owner's grounds, recorded so a later reader does not read this as an
oversight): the realistic batch is 20 not 50; few item categories exist today, so the
K-spec fan-out is far below its modelled 20; and the chosen architectural fix is to
**freeze typicals into stored snapshots refreshed by a scheduler**, which removes the
per-request cost rather than tuning it. Optimising this query now would be work thrown
away.

**Standing scope note.** The freezing/scheduler direction is **recorded direction, not a
commitment**, and **no phase of this pipeline builds it**. §12's "no caching layer is the
remedy" continues to bind every phase here: within this pipeline a slow strategy is
swapped behind `typical_times_statement`, never papered over with a cache.

**What still binds.** Measurement is not optional and the numbers are not decoration —
the doc is the evidence the freezing decision will later be argued from. A result an
order of magnitude outside expectation is **surfaced to the owner as information**, not
gated and not silently filed.

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
- **Round 5 (2026-08-22) — mechanism-inventory gate.** Adversarial standalone session.
  Two deliverables, both written as lettered amendments so no existing citation moves.
  **(a) Re-grounding sweep (§2B)**, the sweep §13 step 1a owed after §2A's five-citation
  sample: every citation in §2.1, §2.2 and §§3–12 checked at source for address **and**
  substance; 14 addresses drifted, 8 substance changes found (F-A's `TaskBudgetStatus`
  grew a field and a fifth construction surface; F-F's "no production constructors" is
  false since `e7d65b9`; F-C's "identical step loads" no longer identical; §7.4's
  serializer citation points at the wrong block), and every counted sentence re-counted
  in both directions — six count defects, none touching D1–D24.
  **(b) Mechanism contracts (§3A, §3B, §4A, §4B, §6A, §6B, §6C, §11A)** for the
  spec's canonicalization and dedupe identity, the per-field predicate table with its
  NULL rows, the statement's clock × spec signature and its keyed result shape for K
  specs, the two-population FILTER arithmetic, basis/count totality, the
  `TaskBudgetStatus` additive contract, `is_estimated`, and the settled-basis guard the
  neighbouring pipeline calls the most expensive mistake available here.
  Three internal contradictions were resolved unilaterally by contract and are listed
  for ratification in the gate handoff: §4.4's reachability invariant is false and is
  corrected in §4B; §6.4's `is_estimated` definition reverses a shipped payload value
  and is corrected in §6B; price-scenario moves to the injected clock (§4A K1), which
  extends the live-clock determinism contract to a fourth surface that pipeline
  deliberately excluded.
  §11A records **five inert named mutations** (T5, T7, T11, T14, T19 — each computed on
  both sides) and adds **ten** rows the new contracts require.
  One question could not be settled without the owner and is opened as **card C → D25**
  (does a narrowed median of exactly zero count as a sufficient narrowed sample?).
  Ledger no longer empty; status is gate-run-with-one-card, not RESOLVED.
- **Round 6 (2026-08-22) — coordinator fold of the gate.** Card C answered by the owner
  ("the recommended option is the correct approach" → **Require a real figure**),
  recorded as **D25** and folded as **§4C**: the reconciliation quantifier and
  `BROADEN_TO_SECTION`'s first rung require a usable narrowed median (`> 0`);
  `ANSWER_AS_ASKED` deliberately still reports a zero median verbatim. Consequences:
  §4B's residual `<= 0` reachability closes for participating sections
  (`item_narrowed_uniform` now cannot reach layer 2 at all); `item_narrowed` + `0` is
  unreachable on task surfaces; §11A row T10b is superseded by T10b′ and T16b's fixture
  moves to the section-wide-zero shape (both recorded in §4C; the §11A rows carry
  pointers). Inline pointers added to §3.4, §4.3, §4B and §3B B2. The gate's three
  unilateral resolutions (§4B, §6B, §4A K1) were relayed to the owner for ratification
  at this fold. Ledger empty; status RESOLVED; next: **implementation-planner**.
- **Round 7 (2026-08-22) — planner fold, two count corrections.** The
  implementation-planner routed two documentation defects upstream (home-artifact rule;
  it did not patch them): §6A A1 and §2B S-1 said `TaskBudgetStatus` carries **13**
  fields — re-counted at source by planner and coordinator independently, it carries
  **14** (the fourteenth is `result: ItemCostResult | None`); both sites corrected in
  one edit. §6.2's header gains a pointer reconciling "all four" with its six-row table
  and §6A A5's seventh surface. No contract changes; §6A's additive rule is unaffected.
  Plan set exists: `master_plan.md` + `plans/plan_1..6.md`, six phases, strictly serial.
- **Round 8 (2026-08-22) — plan-1 projection fold, two intention amendments.** The
  phase-1 projection (AMENDMENTS_REQUIRED, 21 ledger rows, zero owner cards) routed one
  intention gap and one coordinator-owned correction upstream: **§3C** — the parser
  boundary raises `ValidationError` (repo convention: client-triggerable → 422), while
  `__post_init__` keeps `ValueError`; the parser's input is the router's already-typed
  dict, absent-key ≡ explicit-`None`. **§4C's predicate gains `is not None`** — the
  dataclass permits `(count ≥ floor, median None)` and the original text would raise
  `TypeError` there; behavior-neutral on SQL-reachable shapes. All other rows were plan-
  or master-plan-scoped and folded there. No owner decision reopened.
- **Round 9 (2026-08-22) — plan-2 projection fold, one owner card answered.** The
  projection returned AMENDMENTS_REQUIRED (33 rows, 9 blocking, 13 reality checks) with a
  single owner card on query cost. **D26:** no acceptance threshold — the owner overrode
  the projection's recommendation on stated grounds (the card reasoned from 50 tasks per
  call; the frontend paginates at **20**, few item categories exist, and the chosen fix is
  to freeze typicals into scheduler-refreshed snapshots, which removes the per-request cost
  rather than tuning it). Folded as **§12A**: corrected shapes (20-task rows plus one
  50×20 ceiling row), the five-of-ten-cells-are-copies disclosure, measurement still
  mandatory, and the frozen-snapshot direction recorded as direction — **no phase here
  builds it**, and §12's "no caching layer is the remedy" still binds within this pipeline.
  **§3D** records the `ItemCategory` join asymmetry (a soft-deleted category still matches
  `major_categories`) with its conversion trigger; §3A C5 is unchanged, and the field has
  no V1 producer. Every other row was plan-scoped and folded into `plans/plan_2.md` §6A.
