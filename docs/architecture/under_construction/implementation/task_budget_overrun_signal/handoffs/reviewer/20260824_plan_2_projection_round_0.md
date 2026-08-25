---
plan: plan_2
role: projection
round: 0
date: 2026-08-24
verdict: AMENDMENTS_REQUIRED
actor: Claude Opus 5
---

Phase 2 is not ready to hand to an implementer. The rule it consumes is settled and the
service's shape is fully specified, but the phase's *fixtures* are not: the plan tells the
implementer to copy a ready-made seed helper from the neighbouring test file, and that helper
quietly attaches an extra step carrying twenty minutes of work to the very task most of the
phase's expected numbers are computed for. Six of the phase's number-bearing rows would come
out different from what the plan says, and the two most likely repairs — silently recomputing
the expected numbers, or silently trimming the fixture — both end with a test that agrees with
whatever the code does. Fifteen points are recorded below; fourteen are plan-local and the
coordinator can fold them without changing product meaning. One needs the owner: a standing
project rule says any pre-existing file beyond four is an automatic finding, and this phase's
own file list contains a fifth. Re-projection after folding. No code, tests, plans or graph
records were touched, and no tests were run.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — The "four files, no more" rule forbids the file this phase must edit

**Question.** May the "exactly four pre-existing files" wording be corrected so that adding
two functions to the existing serializer module is not counted as a breach?

**Story.** The plan for this phase says: create the new service, and add two small functions
to the file where the neighbouring endpoint's serializers already live. That is what you
approved — one new serializer, living beside its sibling. But a standing rule written to stop
"small refactors into shared code" says any pre-existing file touched beyond a named set of
four is automatically a defect, and the serializer file is not one of the four. So the
implementer will do exactly what the plan asks and the reviewer will be obliged to file it as
a defect, costing a full round on a non-problem. Left alone, the likelier outcome is worse:
the implementer avoids the rule by inventing a second serializer module, and the endpoint
family that has kept its serializers in one place since it shipped quietly grows a duplicate.

**Branches.**
- *Correct the wording* — the four-file count keeps meaning what it was written to mean (the
  route-mirror files), and the additive serializer pair is allowed where the plan already puts it.
- *Leave it* — the phase ships either a filed non-defect or a duplicate serializer module.
- *Move the serializer* — a new module for two functions; contradicts the local serialization
  rule this project already resolved in its favour.

**Recommendation.** Correct the wording. It is a precision fix, not a change of intent: the
four-file promise was always about the route-mirror files, and the new serializer function was
named in the additive-only constraint from the start.

**On silence.** The gate holds. The implementer prompt is not compiled while the phase's own
file list contradicts the rule the reviewer will apply to it.

**Trace.** intention §1A M6, §1 HC-2/HC-2a; master plan §6.1 file table, §9 rule 6.

## Decision ledger

| ID | Decision point | Classification | Proposed routing |
|---|---|---|---|
| PROJ-01 | The copied `_seed` attaches a `FAILED` step worth 1200 s and a `PENDING` step to the same task every arithmetic criterion names with an exact step set. The plan never says how a row's named steps relate to those three. | plan gap | State, in §6's conventions, that each arithmetic row's task carries **only** the steps its Fixture cell names — and how (a fresh task per row, or a `_seed` variant that omits `failed`/`live`/`deleted`). Name the choice; do not leave it to the implementer. |
| PROJ-02 | `_seed` creates exactly one evaluation (`allowed 100.00`, snapshot `0.0001`, SEK) but C2(b) needs `-12.50`, C3(c) needs EURO, C8(c) needs a basis at `9.9999`, and the unique current-evaluation index permits one per task. | plan gap | Say in §6's conventions that the seed's evaluation is parameterised (allowed / snapshot / currency / basis rate) and that each divergent row gets its own task+item+evaluation. |
| PROJ-03 | C1(a): whether the fixture's `completed` step carries `closed_at` decides section A's typical (3600 vs 3000) and therefore the row's expected value (`0, within_budget` vs `150, projected_over`). | plan gap | Pin it in the C1(a) fixture cell: the task's own completed step carries **no** `closed_at` (or, if it does, restate the expected pair). |
| PROJ-04 | `ctx.now` is required to be "a fixed aware datetime" but is unconstrained against the wall-clock `closed_at` the copied historical loop stamps; the typical-time window is `ctx.now − 90 days`. | plan gap | Either stamp the historical `closed_at` relative to `ctx.now`, or state the constraint (`ctx.now` no later than the seeded `closed_at` + 90 days) in §6's conventions. |
| PROJ-05 | The copied `_cleanup` issues no `StepStateRecord` delete; `StepStateRecord.step_id` is `ondelete="RESTRICT"`, so C7(b)/C7(c)'s teardown raises on its `delete(TaskStep)`. | plan gap | Add to §5 task 1: the copied `_cleanup` gains a `StepStateRecord` delete **before** the `TaskStep` delete, and any test seeding an open record uses it. |
| PROJ-06 | C8(c) says "on the **ORM-read** value", but the test's `evaluation` object still holds the `Decimal` the test constructed unless it is expired/refreshed — the hand-built value §4A.2 forbids, and the row cannot observe a column-scale change. | plan gap | Require an explicit `await db_session.refresh(evaluation)` (or a re-select) before the assertion, in the C8(c) fixture cell. |
| PROJ-07 | MUT-17 says "`cost_per_worker_minute_minor_snapshot=basis.cost_per_worker_minute_minor` at the call site", but no `basis` is bound on the budget-bearing branch — the sibling's `selection` there is the typicals reconciliation, not the economics selection. | plan gap | Respell the mutant against a binding that exists on that branch (the copied `basis_versions` list), or state how the basis is resolved for the mutation. |
| PROJ-08 | MUT-16 (and the `Decimal(over_seconds)` probe) name no file. Their expression lives in phase 1's `budget_signal.py`, outside this phase's write perimeter. Charter rule 11 requires file plus definition-vs-call-site. | plan gap | Add the file and the site to both rows, and record in §6.1 that these two probes are applied to a phase-1 file and reverted (declared, not a perimeter breach). |
| PROJ-09 | MUT-06 deletes the `no_budget` short-circuit and runs the general path, but on that branch there is no evaluation and therefore no rate to hand `compute_budget_signal`. | free choice | Delegate explicitly: the mutant may pass any `Decimal` rate; record which, since it does not change the observed red on `actual_worked_seconds`. |
| PROJ-10 | §7A.1's cap contract has two halves — "on the raw list" and "**before any query**". MUT-11/MUT-12 witness the first; nothing witnesses the second, so C5(d)'s `statement count == 0` is an absence row with no planted-presence probe (charter rule 15). | plan gap | Add MUT-18: move the cap check to **after** the visibility query; C5(d)'s statement-count assertion must redden. Update the closed count to 18. |
| PROJ-11 | Master plan §9 rule 6 ("Four pre-existing files, no more … any other pre-existing file in a diff is an automatic finding") and intention §1A M6's wording both contradict master plan §6.1's file table, which lists **five** pre-existing files. `division_serializers.py` — this phase's only pre-existing edit — is the one outside the four. | intention gap (+ master-plan gap) | See **owner card 1**. On approval: amend M6's wording in the intention (lettered section, never renumbered) to scope "the four HC-2a artifacts" to the route-mirror set, and restate master plan §9 rule 6 as "the §6.1 table is the perimeter; anything outside it is an automatic finding". |
| PROJ-12 | The service's returned top-level key set is not pinned by any criterion, and §6.3's "Envelope: `{"budget_signals": [...]}`; `warnings` stays `[]`" reads as if the service emits `warnings` (it is `build_ok`'s field, added by phase 3's route). | plan gap | Extend C4 with a row asserting `set(result.keys()) == {"budget_signals"}`, and reword §6.3's bullet to attribute `warnings` to the route. |
| PROJ-13 | §6's `ctx` convention omits `incoming_data`, a `ServiceContext` field with no default, and writes `identity` as a set literal containing one mapping entry. An implementer transcribing it writes code that does not construct. | plan gap | Replace the sketch with the sibling's `_ctx` shape plus `now=`, or write the full keyword list. |
| PROJ-14 | The phase needs at least eight tasks in one seeded workspace; `uq_tasks_workspace_scalar_id` and the one-current-evaluation-per-task index constrain how they are numbered. | free choice | Delegate explicitly: scalar ids and client-id tokens are the implementer's, provided they do not collide with `_seed` (1, 2) or `_seed_two_section_allocation` (100+). |
| PROJ-15 | §2's Read-first cites `test_budget_allocations_query.py:31-131` as containing `_seed`, `_ctx`, `_seed_two_section_allocation` **and** `_cleanup`; `_cleanup` is at `:229-244`. | plan gap | Correct the citation to `:31-131` plus `:229-244`. |

## Reality checks and decidability

### Gate and artifact reality

- `planning/intention.md:1-10` carries `status: **RATIFIED**` (round 10, 2026-08-24). Gate passes.
- `master_plan.md:103-105`: phase 1 `APPROVED`, phase 2 `NOT_STARTED`, phase 3 `NOT_STARTED`.
  `plans/plan_2.md:7` declares `projection_gate: MANDATORY`. All three gate conditions hold.
- `plans/plan_2.md:198` Review log is empty — no upstream handoff for this phase is in
  `OWNER_DECISIONS_PENDING`.
- **Files expected to change** (`plans/plan_2.md:56-58`): `get_task_budget_signals.py` and
  `test_budget_signals_query.py` are absent and correctly marked `NEW`;
  `division_serializers.py` exists (220 lines) and is correctly marked `MOD` — see PROJ-11 for
  the rule that forbids it.
- **Phase-1 dependency verified in the tree, not assumed.**
  `app/beyo_manager/domain/item_economics/budget_signal.py` exists and its shipped surface is
  byte-faithful to master plan §6.2: the eight-field frozen `BudgetSignal`, `NO_BUDGET_SIGNAL`
  as a constructed constant, `PROJECTED_OVER_FLOOR_SECONDS = 60`, `CURRENCY_VOCABULARY`
  derived from `ItemCurrencyEnum`, `_TERMINAL_STATE_VALUES` derived from
  `TERMINAL_STEP_STATES`, and the keyword-only `compute_budget_signal` with exactly the four
  parameters §6.3 will call it with. No signature drift; §7's "amend §6.2 here first" clause is
  not triggered.
- **Cited source anchors resolve.** `get_task_budget_allocations.py` `:51-56` (cap), `:58-67`
  (visibility, three clauses at `:61-63`), `:69-200` (loads), `:203-229` (status), `:231-249`
  (`DivisionStep` rows, strict index at `:241`), `:292` (actual seconds), `:314` (inline
  serialization); `live_worked_seconds.py:18-30`; `services/context.py:24` (`now` default);
  `division_serializers.py:22-23`, `:57-71`, `:210-220`;
  `item_cost_evaluation.py:30`/`:37`/`:38`/`:39`/`:56`;
  `test_budget_allocations_query.py:178-208` (statement counting);
  `test_live_worked_seconds.py` (present, same directory). One miss: `:31-131` — PROJ-15.
  Minor drift, not filed: `:284-291` is cited as "reconciliation" but `:290-291` are the
  `allowed` binding and the allocator call.
- **Architecture graph**, read-only: valid, revision
  `344f99e481463b7753ebc56356222ed6c6fab2c6636e77fb66870b547b384db0`, 204 nodes / 308 edges,
  6 stale, 3 pending, mode `review`, no diagnostics. `archgraph_build_context` was **not**
  called. The `budget` search returned 13 nodes; the three prescribed anchors resolved. The
  four `reads_from` targets master plan §8 prescribes for the phase-2 node all exist on the
  sibling projection (`table-task-step`, `table-item-cost-evaluation`,
  `projection-live-worked-seconds`, `table-step-state-record`), and the `implements` edge runs
  from `source-file-item-economics-budget-division` **to** the projection, which is the
  direction §8 states. No graph write, promotion, rejection or edit was made.

### Findings

#### PROJ-01 — the copied seed carries steps the criteria do not account for (highest severity)

`plans/plan_2.md:43` sends the implementer to `test_budget_allocations_query.py:31-131` for
"the fixture kit to copy", and `:103` names `_seed`'s `unevaluated_task` directly, so `_seed`
is intended, not optional. `_seed` (`:61-63`) attaches three steps to its evaluated task:
`failed` (state `FAILED`, `total_working_seconds=1200`), `live` (`PENDING`, 0) and `deleted`
(`SKIPPED`, `is_deleted=True`, 1200) — all in the same section.

Every arithmetic row in §6 states its task's steps exhaustively ("one `completed` step settled
3736", "one `pending` step, no work"). Carried on `_seed`'s task, the `FAILED` step is charged
(`budget_division.py:327-328`: `charged_seconds` sums excluded steps, `distributable_seconds =
max(0, budget_seconds - charged_seconds)`) **and** its 1200 s enter `actual_worked_seconds`
(`get_task_budget_allocations.py:292` sums every non-deleted step). Worked through:

| Row | Plan's expected | On `_seed`'s task |
|---|---|---|
| C1(a) | `0, within_budget` | `800, projected_over` (charged 1200 → distributable 2400 → A 1600 / B 800; actual 3600; pot 0) |
| C2(b) | `projected_over, 750, 0, 0, 37500` | `over`, `over_seconds 1200` — the untouched-infeasible row becomes a worked one, which is inventory trap 4 exactly |
| C7(c) | `over_seconds 100` | `1300` |
| C8(a) | `136, 9, 136, 9, over` | `1336, …` |
| C8(b) | `over_seconds 2` | `1202` |
| C8(d) | `8, 0, over` | `1208, …` |

C2(a) survives by coincidence (the projection still lands at 0), which is worse than failing:
it makes the fixture look sound.

The two repairs an implementer reaches for are both defects. Recomputing the expected numbers
to match the fixture is the "adjust the test" move §5 task 0 and master plan §9 rule 3
explicitly forbid — and for C2(b) it destroys the row's purpose. Silently trimming `_seed` is
the right code with an undeclared decision behind it. The plan must choose.

#### PROJ-02 — one seeded evaluation, four required shapes

`_seed` (`:51-60`) commits one `ItemCostEvaluation` with `allowed_worker_minutes=Decimal("100.00")`,
`cost_per_worker_minute_minor_snapshot=Decimal("0.0001")`, `currency=SWEDISH_KRONA`, and its
basis at `cost_per_worker_minute_minor=Decimal("0.0001")`. §6's conventions require `60.00`
and `3.7500`; C2(b) requires `-12.50`; C3(c) requires `EURO`; C8(c) requires the basis at
`9.9999` while the snapshot stays `3.7500`. `uix_item_cost_evaluations_current`
(`item_cost_evaluation.py:56`) permits one current committed evaluation per task, so these are
different tasks, not different evaluations on one. Verified seedable: nothing constrains
`allowed_worker_minutes` to be positive, and `ck_pcbv_cost_per_worker_minute_minor_positive`
admits `9.9999`.

#### PROJ-03 — C1(a)'s typical depends on a field the fixture cell does not mention

`_seed_two_section_allocation` (`:84-131`) seeds five completed historical steps per section —
`[1000, 2000, 3600, 5000, 6000]` and `[600, 1200, 1800, 2400, 3000]` — whose medians are the
3600 / 1800 the plan names. The typical statement
(`get_working_section_typical_times.py:145-186`) groups **every** completed, non-deleted,
not-marked-wrong step in the workspace by `(section, task)` and filters on
`latest_closed_at >= cutoff`; a group whose `closed_at` is NULL is excluded from both the
count and the percentile.

C1(a) adds a **completed** step worth 2400 s in section A to the measured task. If that step
carries a `closed_at` inside the window it becomes a sixth sample: `percentile_cont(0.5)` over
`[1000, 2000, 2400, 3600, 5000, 6000]` is `3000`, weights become 3000:1800, allowances
2250/1350, and the row yields `150, projected_over` — not `0, within_budget`. If it carries no
`closed_at`, the plan's figures hold exactly.

The second-order cost is the one that matters: under MUT-01 the same fixture gives
`600, projected_over`, so with `closed_at` set the criterion and its mutant agree on
`budget_state` and differ only in the seconds — the discriminating half of the assertion is
gone, which is inventory trap 1 (equal typicals under §3A.1) reached through a different door.

#### PROJ-04 — a fixed `ctx.now` against a wall-clock `closed_at`

`_seed_two_section_allocation` stamps `closed_at=datetime.now(timezone.utc) - timedelta(days=1)`
(`:116`) — the real clock — while §6's conventions require `now=<fixed aware datetime>` and the
typical cutoff is `ctx.now - 90 days` (`get_working_section_typical_times.py:147`). A `ctx.now`
in the past is safe; a `ctx.now` more than ~89 days ahead of the run date silently empties both
sections' samples below `TYPICAL_MIN_SAMPLE_SIZE`, `apply_business_fallback` weights every
section `Fraction(1,1)`, and C1(a) becomes its own mutant with nothing red. The plan leaves the
choice open and the neighbouring file the plan cites for C7's seeding pattern
(`test_live_worked_seconds.py:151`) uses `datetime(2026, 1, 10, 9, 0)` — safe today, but by
accident rather than by contract.

#### PROJ-05 — the copied teardown cannot tear down C7's fixture

`_cleanup` (`:229-244`) deletes `TaskStep`, evaluations, task items, valuations, tasks, items,
basis, model, group, sections, user and workspaces — and no `StepStateRecord`.
`StepStateRecord.step_id` is `ForeignKey("task_steps.client_id", ondelete="RESTRICT")`
(`step_state_record.py:36-37`). C7(b) and C7(c) require an open `StepStateRecord`, so the
`finally` block's first statement raises `IntegrityError` and the round loses two criteria to a
teardown fault that reads like a product failure. §5 task 1 already invokes charter rule 11½;
it needs the concrete clause.

#### PROJ-06 — C8(c)'s ORM-read half is not reachable as written

`plans/plan_2.md:155` requires the equality "on the **ORM-read** value", which is §4A.2's whole
point: `int(rate.scaleb(4))` is exact only because the column scale is 4, and the row exists to
observe a scale change. A test that flushes an `ItemCostEvaluation` it built and then reads
`evaluation.cost_per_worker_minute_minor_snapshot` gets back the identical `Decimal("3.7500")`
object it wrote — the hand-built value §4A.2 names as the thing not to assert on. Without an
explicit `refresh` or re-select the row measures a property of the test, and a column-scale
change would leave it green. This is the row plan 1's projection deliberately moved here
(`plans/plan_1.md:304`), so it should land carrying its own instrument.

#### PROJ-07 — MUT-17 names a binding that does not exist on the branch it mutates

The mutation reads `cost_per_worker_minute_minor_snapshot=basis.cost_per_worker_minute_minor`
"at the call site". On the budget-bearing branch there is no `basis`: the sibling computes
`resolve_economics_selection(...)` only inside `if evaluation is None`
(`get_task_budget_allocations.py:207-227`), and the `selection` name live at the allocator call
is `reconcile_task_typicals(...)` (`:284-289`), which carries typicals, not a rate. What *is*
in scope is the `basis_versions` list loaded once per request (`:163-170`). As written the
mutation cannot be transcribed; it has to be invented, which is how plan 1's MUT-07 produced a
false green (`plans/plan_1.md:308`).

#### PROJ-08 — two probes are sited in a phase-1 file and say so nowhere

MUT-16 replaces `over_seconds` with a minute-domain derivation and the first exception-shape
probe passes `Decimal(over_seconds)` into the money call. Both expressions live in
`budget_signal.py` (`compute_budget_signal`, the arithmetic block and the two
`calculate_consumed_cost_minor` calls) — phase 1's approved module, outside
`plans/plan_2.md:56-58`. Reverted probes are legitimate, but master plan §9 rule 6 makes any
undeclared pre-existing file in a diff an automatic finding, and charter rule 11 requires each
named mutation to state its file and whether it lands on the definition or the call site.
Declaring both up front costs one sentence and prevents a perimeter dispute at review.

#### PROJ-10 — the cap's "before any query" half has no witness

§7A.1 fixes two properties: the cap counts the **raw** list, and it fires **before any query**.
MUT-11 (`len(set(task_ids))`) and MUT-12 (`_MAX_TASK_IDS = 51`) witness the first. C5(d)'s
`statement count == 0` asserts the second and is an absence claim; charter rule 15 requires an
absence row to be shown able to observe the presence, and no declared mutation plants it. The
mutation is one line — move the `if len(task_ids) > _MAX_TASK_IDS` block below the visibility
`select` — and C5(d) then reddens on the count while still raising.

#### PROJ-12 — the top-level shape is unpinned, and §6.3 mis-attributes `warnings`

`build_ok` (`routers/http/response.py:6-11`) owns `warnings`; it is an envelope field the route
supplies in phase 3, not a key the service returns. §6.4 fixes
`serialize_budget_signals(rows) -> {"budget_signals": [...]}`, so the artifacts do determine the
answer — but §6.3's bullet reads the other way, and C4(c)'s recursive walk is scoped to *rows*,
so an implementer who adds `"warnings": []` to the service's return ships an unpinned wire
change with nothing red. One row closes it.

### Criteria decidability — the rest

Every remaining row is writable now from the artifacts alone, with one exact expected outcome
per case. Confirmed by re-derivation rather than by reading the plan's arithmetic back:

- **C1(a)/MUT-01.** `apply_business_fallback([3600, 1800], terminal=Fraction(1,1))` returns the
  values themselves; `typicals_by_section=None` makes `typicals` an empty dict, every section
  resolves to the terminal `Fraction(1,1)`, and the split is equal. On a two-step task the
  criterion's `0, within_budget` and the mutant's `600, projected_over` both re-derive exactly.
- **C1(b).** The statement count is 12 with steps present and 11 without: the loader's probe is
  skipped when `settled` is empty (`live_worked_seconds.py:38-39`) and it adds exactly one
  further statement per distinct user holding an open record
  (`compute_record_contributions` issues one). With every requested task carrying steps and no
  open records, one-task and three-task requests both cost 12, and MUT-02 makes the three-task
  request cost 14. The sibling's own `first_count == 11` is **not** a counter-example — it
  measures a task with no steps.
- **C2(b).** `divide_production_budget` returns `budget_seconds = _budget_seconds(allowed)`
  **unclamped** (`budget_division.py:323`) while only `distributable_seconds` is floored
  (`:328`), so `allowed_seconds_raw = -750` reaches the rule as D1 requires. With one `pending`
  section and no work: commitment 0, pot `-750`, projection 750, `over` 0, served pot 0, rate
  37500 — the plan's tuple, re-derived.
- **C7(b) delta 60.** A single user's single open interval earns its full duration
  (`averaged_seconds_by_record`, verified by the sibling test's `1800` over 30 minutes), so
  `T` → 600 s and `T + 60` → 660 s. MUT-15 collapses the delta to ~0 under both `TZ` settings.
- **C8(a)/(b)/(d).** On a single completed step the section is terminal, commitment is 0, and
  `projected = max(0, 0 - (3600 - actual))` equals `over` exactly: 3736 → `136, 9, 136, 9,
  over`; 3602 → 2 against the minute-domain mutant's 1; 3608 → `8, 0, over`.
- **C6 / MUT-14.** Inserting in descending `client_id` order means an unordered sequential scan
  returns `c, b, a`, so deleting `.order_by(Task.client_id.asc())` reddens C6(a) on the first
  run rather than by luck; the plan's miss-and-grow protocol covers the residual case.
- **C4(c) / MUT-09.** The absence row has its planted-presence probe, correctly.

### Trace verification, both directions

Forward: all eight criteria carry trace cells and each resolves to a section that says what the
row asserts — C1→§3.1/§3A.1/§7A.6→M1,M6; C2→§6A.1/D2→M4; C3→§5A.2/§5A.3/D3→M4;
C4→§5/§5A.1/HC-4→M4; C5→§7A.1/§7.3/D7→M4; C6→§7A.2→M5; C7→§6A.4→M5;
C8→§4A.1/§4A.2/§4.1/§3A.5→M2. No void-symbol trace found.

Reverse: the tracker's phase-2 claim (§§3A.1, 5A.1/5A.2, 6A.1, 6A.4, 7A.1/7A.2, M2 on the
production path) is served row-for-row — §3A.1 by C1, §5A.1 by C4, §5A.2 by C3, §6A.1 by C2,
§6A.4 by C7, §7A.1 by C5, §7A.2 by C6, M2 by C8. Nothing claimed is unserved.

Two boundary notes, neither a finding: §5A.3's enum-untouched absence claim and §6A.2's rows 3
and 6 are discharged by plan 1 (C7(b), C6(c), C6(e)) at the pure level, so plan 2's C3(b)/C8(a)
are production-path echoes and correctly carry no duplicate mutation. Counts check: §6.1
declares 17 and lists MUT-01…MUT-17; PROJ-10 would make it 18.

## Write perimeter

Documents written: exactly one —
`docs/architecture/under_construction/implementation/task_budget_overrun_signal/handoffs/reviewer/20260824_plan_2_projection_round_0.md`.

Code, tests, plans, master plan, intention: **unchanged**. Architecture graph: three reads
(`archgraph_status`, `archgraph_search_nodes`, two `archgraph_get_node`) and **no** write, no
review decision, no maintenance change; `archgraph_build_context` was not called and
`.archgraph/contexts/current-task.md` was neither read nor edited.

Tree identity at session close: `bd83950`, working tree carrying only the pre-existing
modifications this session inherited —

```text
 M .archgraph/architecture.yml
 M docs/archgraph-anchor-observations.md
?? .archgraph/backfill/
?? docs/architecture/under_construction/implementation/task_budget_overrun_signal/prompts/reviewer/
?? docs/handoff/from_frontend/HANDOFF_TO_BACKEND_worker_time_pressure_20260824.md
```

L4 runs: 0 (budget: exactly 0). Tests executed: 0. Probes run: 0 — every figure above was
derived by source inspection.

**Perimeter conflict declared, per master plan §9 rule 1.** One standing brief external to this
prompt would have this session append to a document outside the perimeter above. It was **not**
written. Recording it here and letting the coordinator rule is what rule 1 prescribes.

## Owner layer

**What I did.** I did the implementer's first hour on paper for the second phase — the piece
that reads tasks from the database, works out each one's budget verdict, and hands back one
flat row per task. I checked every number the plan promises by re-deriving it from the real
code, and checked that each test the plan asks for could actually fail if the code were wrong.

**What I found and what it means for you.** The rule itself is settled and the service's shape
is fully described. The problem is the test setup. The plan tells the builder to reuse a
ready-made helper from the neighbouring test file, and that helper quietly attaches an extra
step carrying twenty minutes of work to the exact task most of the phase's numbers are computed
for. Six of the phase's number-bearing checks would come out different from what the plan
says. The dangerous part is not the mismatch — it is the two natural ways out: rewrite the
expected numbers to match, or trim the fixture without saying so. Both end with a test that
agrees with whatever the code happens to do, which is the failure this project has paid for
repeatedly. Three smaller gaps have the same shape: a date field nobody mentioned changes one
task's expected verdict; the clean-up step cannot remove the one kind of record the "live
clock" checks create, so those two checks would die in tear-down; and the check meant to prove
the money rate comes from the database would actually be reading the value the test itself
wrote, so it could never catch the thing it exists to catch. All fourteen are fixable in the
phase plan without changing what the feature does.

**What happens next.** The coordinator folds these into the phase plan and projects it once
more before anyone writes code. Nothing is implemented and nothing was changed.

**What needs you.** One decision — owner card 1 above, verbatim: a standing rule in this
project says touching any pre-existing file beyond a set of four is automatically a defect, and
this phase's own file list contains a fifth (the serializer file the plan asks the builder to
add two functions to). Left as it is, the builder does what the plan says and the reviewer is
obliged to call it a defect — or the builder avoids the rule by creating a duplicate serializer
module. My recommendation is to correct the wording, because the four-file promise was always
about the route files. Unanswered, the gate holds and the phase is not dispatched.

Technical detail: this file.
