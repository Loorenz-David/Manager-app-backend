# Plan 2 — the three surfaces go live (one loader run, one `now`, per request)

```
state: CHANGES_REQUESTED — 2026-08-20 (implement r1 · coordinator consumption; fix r2 dispatched)
phase: 2
date: 2026-08-20
depends_on: plan 1 APPROVED 2026-08-20 (`d21fe9e`) — holds
```

**What phase 1 shipped, that this phase consumes** (facts, verified at approval):

- `live_worked_seconds.py:load_live_worked_seconds(session, workspace_id, steps, now)
  -> dict[str, int]` — keyed by step `client_id`, every input step present, values
  `settled + int(round(open_share))`. Raises `TypeError("load_live_worked_seconds
  requires an aware UTC now")` on a naive `now`: it **fails closed at its own
  boundary**, and that guard is load-bearing (intention §1A HC-3A round 4d).
- `context.py:ServiceContext.now` — aware UTC, stamped once per construction,
  overridable by `now=`. Every service in this phase reads `ctx.now`; no service
  reads a clock.
- Three golden files + `test_live_clock_goldens.py` under
  `app/tests/integration/services/queries/item_economics/` — captured **before** any
  live code existed. They are this phase's payload-freeze proof (C1).

## 1. Goal

Wire `load_live_worked_seconds` into E-P, E-B (both faces) and E-A so every
worked-seconds-derived field on the three payloads derives from one loader run and one
`ctx.now` per request (HC-5, §4.1A D), and delete the E-B SQL aggregate in favour of
the per-step fold (decision N-2). All four §4.1 surface rows ship together (D5).

**NOT in this phase:** no change to `budget_division.py`, `concurrency.py`,
`averaged_time.py`, the router, any serializer's key set, or the two frozen-percent
feed sites — `final.percent_consumed` and the worker face's `result.percent_consumed`
keep today's request-level wiring until phase 3 (D9). No handoff (phase 4).

## 2. Read first

1. `master_plan.md` §4 (N-1…N-4), §5 — **including the nine rules earned in phase 1**,
   which bind here — and §6 (the four-caller table fact; the **current** baseline
   **26 / 2459 / 1** with its enumerated ID set — §6 now carries both baselines, cite
   the phase-1-approved one; the third-flake and `TZ` environment facts).
1b. `plans/plan_1.md` §5 — **C5** (the `_apply_step_transition` close-at-`t` recipe
   this phase's C6 and C9 both reuse; `transition_step_state` cannot be used),
   **C10** (the dirty-check-before-expire assertion order this phase's C5 reuses),
   and C9/C11/C12 as amended — §6's structural-facts note and its three written
   delegations, and §7's Review log: six rounds of findings, every blocking one in a
   plan or review artifact rather than in code.
2. Intention §1A (HC-1A, HC-3A scope — E-A's `today_utc()`), §4.1 + §4.1A (the field
   table, the fold, the composition contract and per-caller declaration table), §4.2,
   §4.3 + §4.3A (the three allowance paths — path 3 is the expensive mistake), §2.6
   (the price-scenario coupling), §5.2 (the frontend's four criteria, adopted as
   contract), §9A (T1′ row b, T5–T9, T11, T12).
3. Source: the three services + `get_task_budget_status_worker.py`,
   `division_serializers.py`, `serializers.py:serialize_task_budget_status`,
   `get_task_price_scenario.py` (read — its call is in your blast radius),
   `budget_division.py:DivisionStep`, `_step_transition_core.py:_apply_step_transition`
   (T11's close path).

## 3. Files expected to change

- `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` — the
  fold (N-2): `_build_evaluated_status` loads the task's **non-deleted steps** (no
  state filter — §4.1A A population check), obtains the live map, and computes
  `actual_seconds = Σ live map`; the `func.sum` aggregate is **deleted**. Signature
  per §4.1A D: `get_task_budget_status(ctx, *, live_seconds: Mapping[str, int] | None
  = None)` — `None` means "compute the map yourself from `ctx.now`", never "skip";
  same optional threading through `_build_evaluated_status`.
- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` —
  resolves the live map **once** over its loaded steps, passes it into
  `get_task_budget_status(ctx, live_seconds=…)`, and hands the allocator
  `DivisionStep` rows carrying the live figures (HC-1A: built, never assigned onto
  ORM steps).
- `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` —
  one loader call **per batch** keyed over all visible tasks' steps (the per-user
  sweep is shared across tasks — §3.4A B); `DivisionStep` substitution per task;
  headline `actual_seconds` from the map; `today_utc()` → `ctx.now.date()` resolved
  **once before the loop** (HC-3A scope).

  **E-A's step-load options are unchanged — no `selectinload` is added** (projection
  r0, A7). The service selects steps with no eager load, and
  `budget_division.py:_loaded_latest_state_record` reads `step.__dict__` and yields
  `None` without emitting SQL, so `_governing_step` orders E-A's candidates by
  `created_at` / `client_id` alone. Both obvious resolutions are defects: building
  `DivisionStep(latest_state_record=step.latest_state_record)` triggers a lazy load on
  an async session (`MissingGreenlet` — loud), and "fixing" that by adding
  `selectinload(TaskStep.latest_state_record)` **silently moves E-A's
  `allowance_seconds` and `left_seconds`**, because a section whose steps are all
  COMPLETED takes `_section_step_allowances`'s `else` branch and hands the residual to
  whichever step `_governing_step` returns — an ordering that changes the moment the
  relationship is loaded. The substituted row therefore carries **exactly what the
  allocator would read today**: `budget_division._loaded_latest_state_record(step)`.
  Importing that private helper is the house precedent (`get_task_price_scenario.py`
  already imports `_median` and `_step_state_is_excluded` from the same module).
- `app/beyo_manager/services/commands/item_economics/_common.py` — **additive only,
  and this is a deliberate widening of the perimeter into the commands package**
  (coordinator's disposition of projection r0's U1; intention round 4e).
  `_load_preview_inputs` gains `now: datetime | None = None`; `None` preserves today's
  `today_utc()` read for its command-side callers, and it passes `now.date()` to
  `configuration.py:resolve_economics_selection` when given one. The two query
  services that import it — `get_task_budget_status.py:get_task_budget_status` and
  `get_task_budget_status_worker.py:get_task_budget_status_worker` — pass `ctx.now`.
  **Why it is in scope:** this is the *same construct* as E-A's `today_utc()`, which
  task 3 already converts, on the E-B / E-P / price-scenario request path; converting
  one instance and not the other leaves a live counterexample to HC-3A's "within the
  three surfaces, one request is one `now`" and a cross-surface `status` disagreement
  at a UTC date rollover. Nothing else in the commands package is touched, and no
  command-side caller changes behaviour. Covered by C12.
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py` —
  only if the `_build_evaluated_status` threading requires a call-site change; expected
  unchanged (it inherits the fold).
- `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
  — **additive only** (round 4b, projection r0 / intention HC-3A):
  `typical_times_statement` gains a `now: datetime | None = None` parameter; `None`
  preserves the existing `datetime.now(timezone.utc)` cutoff read (the compatibility
  shim for callers outside this pipeline — the working-sections surface and the
  price-scenario typical block, both settled-basis and out of scope, whose behaviour
  and suites must be untouched); E-P and E-A pass `ctx.now`. No other change to this
  file — its aggregates and grouping are path 3 of §4.3A and stay settled.
- New/extended test files under
  `app/tests/integration/services/queries/item_economics/` for C1–C11 below; the
  price-scenario suite (`test_price_scenario*.py`) **only if** C10 finds it red —
  fixed-`ctx.now` fixture additions and nothing else in it.

## 4. Ordered tasks

1. The fold in `_build_evaluated_status` (N-2), with the loader threading (§4.1A D
   caller table: E-B route resolves its own; worker face inherits; E-P passes its map;
   price scenario resolves its own **by not changing** — `ctx.now` exists for it).
2. E-P: one map, both consumers (status + division rows).
3. E-A: batch probe, per-user sweeps shared across tasks, headline from the map,
   `today_utc()` replacement.
4. The typicals cutoff under `ctx.now` (intention HC-3A round 4b): the additive
   parameter and the two call sites (E-P's `typical_times_statement(...)` call and
   E-A's `_load_typicals`).
4b. The configuration-date read under `ctx.now` (intention HC-3A round 4e): the
   additive `now` parameter on `_common.py:_load_preview_inputs` and the two query
   call sites (`get_task_budget_status`, `get_task_budget_status_worker`). Same shim
   shape as task 4 — a default that preserves the existing read for callers outside
   this pipeline.
5. Tests C1–C12, mutation ledger per master plan §5.

## 5. Acceptance criteria

- **C1 — T5 goldens stay green, untouched.** The three golden files from plan 1 are
  byte-identical assertions against the live code — **the golden files and their test
  are read-only in this phase's diff** (any edit to them is an automatic review
  finding). This is §5.2 criterion 4.
- **C2 — the motivating card** (§5.2 criterion 1, §1): a section 25 minutes into a
  3 m 6 s allowance with an open working record reports `share_state: "over_share"`
  with `worked_seconds` and `left_seconds` consistent in the same payload (exact
  expected integers in the test, derived from the fixture).
- **C3 — T6 coherence** (§5.2 criterion 3, HC-5): one open record;
  `budget.actual_worker_seconds == Σ sections[].worked_seconds`; per row
  `left_seconds == allowance_seconds − worked_seconds`; `share_state` consistent with
  the figures beside it.

  Plus the population row (projection r0 A5, **as amended by the coordinator** — see
  §7): a task carrying one `SKIPPED` step whose `total_working_seconds` is **non-zero**
  (use `240`) — headline still equals the fold over **all** non-deleted steps
  (§4.1A A), and `Σ sections[].worked_seconds` still includes it
  (`budget_division.py:group_steps_by_section` keeps excluded steps in
  `group["worked_seconds"]` — verified at source, measured `840`). At
  `total_working_seconds = 0` on the SKIPPED step the two sides coincide at addition's
  identity element and the row cannot fail (master plan §5, earned at plan 1 review r1
  B1).

  **Named mutation, definition site,
  `get_task_budget_status.py:_build_evaluated_status`:** filter
  `budget_division.EXCLUDED_STEP_STATES` out of the step set it hands the loader.
  **Both sides**, task with one WORKING-open step at `600` live and one SKIPPED step at
  `240` settled, **asserted on the E-B manager face** (headline only, no substituted
  rows): contract `actual_worker_seconds == 840`; mutation `== 600` ⇒ red.
  **Why E-B and not E-P for this row:** under delegation D7 the substituted rows index
  the live map strictly, so the same mutation applied at E-P's or E-A's loader-input
  site raises `KeyError` on the SKIPPED step's `client_id` instead of producing the
  divergence — still red, but not the observable the row names, and a criterion states
  what actually happens (charter rule 11: both sides for the *named* fixture). If the
  implementer also probes the E-P/E-A site, the ledger records the raise as the
  observed red, not a value comparison.
- **C4 — T1′ row b (call sites, one per endpoint):** with `ctx.now` frozen and the
  loader's clock-stub in place, serving each endpoint twice yields byte-identical
  payloads and **loader invocations == 1 per request** (E-P's composition included —
  this is the §4.1A D double-computation guard).

  Each consumer binds the loader by name at import
  (`from …live_worked_seconds import load_live_worked_seconds`), so a counter installed
  on one module's attribute observes only that module's calls. The criterion's counter
  is installed on **every** consumer binding —
  `get_task_production_time.load_live_worked_seconds`,
  `get_task_budget_status.load_live_worked_seconds`, and
  `get_task_budget_allocations.load_live_worked_seconds` — and the assertion is over the
  **total**. Contract: total == 1 per request for each of E-P, E-B manager face, E-B
  worker face, E-A. Under the named mutation (E-P passes `live_seconds=None`) the total
  is **2**, and a counter installed only at E-P's binding would read **1** under both
  sides, because E-P keeps its own loader call to build its division rows and only the
  second call moves — the row would be decoration.

  **Fixture precondition, load-bearing:** the task carries a **committed,
  non-superseded, non-deleted `ItemCostEvaluation`**.
  `get_task_budget_status.py:get_task_budget_status` returns `_empty_status(…)` before
  `_build_evaluated_status` on every other branch, so without the evaluation the fold
  never runs, the mutation's second loader call never happens, and the total stays 1
  under both sides. The same precondition makes E-B's contract total 1 rather than 0.

  **Named mutations, per endpoint at the call site:**
  - E-P passing `live_seconds=None` instead of its map ⇒ invocation total 2 ⇒ red.
  - **E-A restoring `today_utc()` inside the loop** (call site,
    `get_task_budget_allocations.py:get_task_budget_allocations`). This mutation only
    bites on a fixture where the two dates select different configuration rows:
    `today_utc()` and `ctx.now.date()` feed
    `configuration.py:resolve_economics_selection`'s `on_date`, which filters basis and
    cost-model versions through `configuration.py:is_applicable`. Fixture: a task in the
    batch with **an item and no committed evaluation** (the only branch that reaches
    this call — verified at source), `ctx.now = 2020-01-01T00:00Z`, and a
    `ProductionCostBasisVersion` with `effective_from = 2020-06-01`. **Both sides:**
    contract `status == "not_configured_no_basis_version"`; mutation (real today ≥
    2020-06-01) `status == "ok"` or the valuation-derived status — differ ⇒ red.
    Without the straddle the mutation is inert and the row proves nothing.
- **C5 — T9 (HC-1A), three rows:** serve each endpoint against a task with an open
  working record; `task_steps.total_working_seconds` unchanged.

  **Assert in this order, per endpoint:** (1) `session.dirty` contains no `TaskStep`;
  then (2) `session.expire_all()`; then (3) re-read
  `task_steps.total_working_seconds` and assert it is unchanged. This is plan 1 §5
  C10's order, and the order is the criterion: `Session.expire_all()` **discards
  un-flushed attribute changes**, so an expire-then-re-read form passes under the very
  assignment this row exists to catch. In E-P and E-A the assignment would land after
  the request's last `session.execute()`, so no autoflush rescues the row.

  **Not "a fresh session".** `tests/conftest.py:db_session` is rollback-scoped and
  these fixtures are flush-only, so a genuinely new session sees none of the fixture
  rows and the contract-side assertion fails before any mutation is applied. The
  same-session form above is the constructible one and is **the form that ships** — it
  is not the implementer's to pick, because one of the two silently disarms the row.
  (A committing fixture would owe a `try/finally` teardown — charter 11½.)

  **Named mutation (loader call site in each service):** assign the live figure onto
  `step.total_working_seconds` before division ⇒ column re-read `600` not `0` ⇒ red
  (§9A T9's both sides).
- **C6 — T12 allowances.** Serve the payload with an open working record; then close
  that record through the production transition path and run
  `_recompute_step_time_totals`; then serve again. Every `allowance_seconds` (sections
  and steps) in the first payload is byte-identical to the second's. The close recipe is
  plan 1 §5 C5's: `_step_transition_core.py:_apply_step_transition` with `now=t`
  (`transition_step_state.py:transition_step_state` stamps its own clock and cannot
  close at a pinned `t`). Honest-form rows per §9A T12 — no excluded step in the fixture
  has an open working record (assert), `charged_seconds` computed from settled values
  (assert on the division input). `typical` blocks byte-identical (path 3, §4.3A).

  **Second and third rows — the substituted row carries every field the allocator
  reads.** The goldens cannot guard this: both golden tasks hold exactly **one** step in
  **one** section (`test_live_clock_goldens.py`, `tsp_live_clock_golden_idle` /
  `tsp_live_clock_golden_frozen` — verified), so
  `budget_division.py:_governing_step` has a single candidate and every field that only
  affects **ordering** can be dropped from the substituted rows with the goldens still
  byte-identical. `_governing_step` applies three stable sorts — `client_id` asc, then
  `created_at` desc, then `latest_state_record.entered_at` desc — so **the last one
  applied is the primary key**, and a field is only observable on a fixture that ties
  every key above it. Each row therefore gets its own fixture (charter rule 2's
  companion), both with **two steps in one section**, one holding an open working
  record, asserting the full E-P `sections[]` and E-A `steps[]` payloads against those
  produced from the same fixture through the un-substituted (settled) path.

  Coordinator-measured against the real `_governing_step` (see §7):

  - **Row 2 — `created_at`.** Fixture: the two steps' `latest_state_record.entered_at`
    are **equal**; `created_at` distinct; `client_id` order contradicts `created_at`
    order (the later-created step sorts *higher* by `client_id`). **Named mutation,
    substitution site in `get_task_production_time.py`:** construct `DivisionStep`
    omitting `created_at` (leaving its `None` default). **Both sides:** contract —
    governing step is the later-created one, and `state_entered_at` /
    `section_name_snapshot` follow it; mutation — the `created_at` sort goes inert and
    the tie falls to the `client_id` order, moving the governing step to the other one
    ⇒ red. Measured: `stp_b` → `stp_a`.
  - **Row 3 — `latest_state_record`.** Fixture: `entered_at` **distinct** and ordered
    *against* `created_at` (the later-entered step is the earlier-created one). **Named
    mutation, same site:** construct `DivisionStep` omitting `latest_state_record`.
    **Both sides:** contract — governing is the later-**entered** step; mutation — the
    `entered_at` key ties at `None` for both, `created_at` takes over, governing moves
    ⇒ red. Measured: `stp_b` → `stp_a`.
  - **Do not merge these two fixtures.** On row 3's fixture the `created_at` mutation is
    **inert** (measured: `stp_b` → `stp_b`) — distinct `entered_at` decides the order by
    itself and nothing below it is ever consulted. A single fixture with distinct
    `entered_at` carrying both mutations is the row-that-cannot-fail shape this project
    has now recorded eight times.

  The ten fields the allocator reads are enumerated in master plan §4, N-3.

  **Fourth row — E-A's all-completed section.** A task with one section whose steps are
  **all `COMPLETED`** (≥ 2 of them, distinct `created_at`), served through E-A: every
  `allowance_seconds` and `left_seconds` byte-identical to the pre-substitution payload.
  **Named mutation, `get_task_budget_allocations.py:get_task_budget_allocations`
  step-load site:** add `.options(selectinload(TaskStep.latest_state_record))` ⇒ the
  residual lands on a different step ⇒ red. Neither C1 nor C6's open-record rows can see
  this: the goldens' sections hold one step each, and a section with an open working
  record never reaches `_section_step_allowances`'s `else` branch.
- **C7 — T7 worker face, one new integration row** in
  `app/tests/integration/services/queries/item_economics/`. Serve one fixture — a task
  with an open working record and a committed evaluation — through both faces on the
  production path, and assert: (1) walking every key of
  `serialize_task_budget_status(get_task_budget_status_worker(ctx),
  include_monetary=False)` yields no key containing `_minor`, `cost`, `price`,
  `currency`, `money` or `valuation` (the token walk at
  `test_production_time_query.py:test_c14_c16_flat_time_only_degradation_and_tenant_boundary`
  is the pattern); (2) the worker face's `actual_worker_seconds`,
  `actual_worker_minutes`, `remaining_worker_minutes`, `percent_consumed` and
  `variance_worker_minutes` equal the manager face's for that fixture, and are
  **greater than** the same task's settled-basis values (D5 — no split-brain, and the
  row is non-vacuous only because the live term is non-zero). **This is not an
  extension of `tests/unit/services/queries/item_economics/test_phase8_serializers.py`:**
  that family builds its status objects by hand, so it cannot carry a live field
  without breaching charter rule 3, and it sits outside this phase's declared test
  perimeter. **Named mutation,
  `get_task_budget_status_worker.py:get_task_budget_status_worker`:** replace the
  `_build_evaluated_status` delegation with the pre-phase settled aggregate ⇒ assertion
  (2) red (intention §4.1A D, row 2 — "worker face silently stays settled").
- **C8 — T8 cost shape:** one active worker across N batched tasks ⇒ exactly one
  open-record probe statement and one `compute_record_contributions` call
  (`count_queries` / call counting, never wall-clock); two workers ⇒ two calls. The
  50-task ceiling **measurement** is a Review-log obligation, not a criterion
  (charter rule 1; §9A T8) — record it there with the fixture shape.

  **Named mutation, call site,
  `get_task_budget_allocations.py:get_task_budget_allocations`:** move the
  `load_live_worked_seconds` call **inside** the per-task loop, over that task's steps
  only. **Both sides**, one active worker holding one open working record in each of
  **3** batched tasks: contract — **1** open-record probe statement and **1**
  `compute_record_contributions` call; mutation — **3** probe statements and **3**
  wrapper calls, because the user's sweep is re-run once per task instead of once per
  request (§3.4A B's "a worker's sweep is shared across all their steps"). The
  two-worker row's contract side is 1 probe + **2** wrapper calls.
- **C9 — T11 settlement window observed** (D8): open record → read E-P → close through
  the production transition **without** running the analytics worker → read E-P again
  ⇒ `worked_seconds` equals the pre-work settled value (the drop exists); then run
  `_recompute_step_time_totals` ⇒ value returns within ≤ 1 s per step (§3.3A).
- **C10 — the `_build_evaluated_status` blast radius** (§2.6). N-2 changes that
  function from a scalar SQL aggregate into a step load plus a loader call, so its
  dependents can go red for **two** unrelated reasons, and the plan admits both
  remedies: (a) *time dependence* under the live basis — remedy is a frozen `ctx.now`
  in the affected fixtures, never a change to a shipped service file; (b) *statement
  shape* — a suite driving the service with a hand-rolled session
  (`test_price_scenario_query.py:_TypicalSession`,
  `test_phase9_committed_filter_structure.py:_CapturingSession` are the existing
  shapes) answers a `scalar()` for the aggregate and cannot answer a
  `select(TaskStep)`; remedy is the fixture's shape, again never the service.

  **Perimeter — every suite that reaches `get_task_budget_status` /
  `_build_evaluated_status`,** enumerated at this phase's head and all green (this list
  is the coordinator's, measured by `grep -rln` over `tests/`; projection r0's A11
  named four of the seven — see §7):

  1. `tests/integration/services/queries/item_economics/test_price_scenario_query.py`
  2. `tests/integration/services/queries/item_economics/test_live_clock_goldens.py`
  3. `tests/integration/services/commands/item_economics/test_phase8_status_results.py`
  4. `tests/integration/services/commands/item_economics/test_phase8_reviewer_r1_probe.py`
  5. `tests/integration/services/queries/item_economics/test_budget_allocations_query.py`
     — **calls `get_task_budget_status` directly on a real session** (line ~148). E-A's
     own suite, and the one this phase rewrites hardest; it was absent from A11.
  6. `tests/unit/services/queries/item_economics/test_phase9_committed_filter_structure.py`
     — drives both faces through `_CapturingSession` with `(_task(), None, None)`,
     which takes the no-PRIMARY-item branch and **early-returns before**
     `_build_evaluated_status`. The shape risk is therefore latent, not present —
     named rather than discovered, because the moment a row of it grows an evaluation
     it becomes case (b). Its `_SITES` ids embed source line numbers
     (`"get_task_budget_status.py:106-108"`) that this phase's edits will make stale:
     they are **test ids, not assertions**, so nothing reddens — do not "fix" them and
     do not file them.
  7. `tests/unit/routers/api_v1/test_item_economics_router.py` — references the two
     service functions **by identity** (`assert calls[0][0] is
     item_economics.get_task_budget_status`), never executing their bodies. Immune to
     a keyword-only signature addition (R6: `run_service` calls `fn(ctx)` with no
     signature introspection), but listed so its greenness is checked rather than
     assumed.

  The Review log records, **per file**, which of the two outcomes happened.
- **C11 — the typicals cutoff reads no clock on E-P/E-A** (intention HC-3A round 4b):
  with `beyo_manager.services.queries.working_sections.get_working_section_typical_times`'s
  module clock stubbed, serving E-P and E-A performs **zero** clock reads in that
  module (stub call-count == 0). **Named mutation, one per call site:** drop the
  `now` argument at E-P's call ⇒ the statement falls back to the defaulted clock read
  ⇒ stub intercepted ⇒ that row red; same for E-A's `_load_typicals` call. Both sides:
  contract stub-count 0/0, mutation ≥ 1 at the mutated site.

  Plus one behaviour-preservation row for the shim:
  `typical_times_statement(workspace_id)` called **without the `now` argument** — the
  form its two out-of-pipeline callers use
  (`get_working_section_typical_times.py:get_working_section_typical_times`,
  `get_task_price_scenario.py:_typical_block`) — executed against a fixture with
  exactly five qualifying completed section-totals, asserting the **exact** returned
  rows (`sample_count == 5`, `typical_worker_seconds ==` the fixture's median). "The
  same rows as before this phase" is not writable: the pre-phase function is not
  callable at test time, and `typical_times_statement()` with no argument at all is a
  `TypeError` (`workspace_id` is a required positional). **Named mutation, definition
  site, `get_working_section_typical_times.py:typical_times_statement`:** make the
  defaulted branch resolve to a fixed **future** instant (`datetime(2099, 1, 1,
  tzinfo=timezone.utc)`) instead of the clock ⇒ the cutoff moves past every fixture
  row's `latest_closed_at` (the filter is `latest_closed_at >= cutoff` — verified at
  source) ⇒ `sample_count == 0` and `typical_worker_seconds is None` ⇒ red. Use the
  future form; a fixed **past** instant is inert, because a wider window admits the
  same five rows.
- **C12 — the configuration date reads no clock on the three surfaces** (intention
  HC-3A round 4e; this criterion is the coordinator's, added with U1's disposition —
  see §7). Same shape as C11, one package further out: with
  `beyo_manager.services.commands.item_economics._common`'s module clock stubbed,
  serving **E-B (both faces), E-P and E-A** performs **zero** clock reads in that module
  (stub call-count == 0), on a fixture that takes the **no-committed-evaluation**
  branch — the only branch that reaches `_load_preview_inputs`. **Named mutation, one
  per call site** (`get_task_budget_status.py:get_task_budget_status`,
  `get_task_budget_status_worker.py:get_task_budget_status_worker`): drop the `now`
  argument ⇒ the callee falls back to its defaulted `today_utc()` ⇒ stub intercepted ⇒
  that row red. **Both sides:** contract stub-count 0 per surface; mutation ≥ 1 at the
  mutated site. Plus one behaviour-preservation row: `_load_preview_inputs(ctx, item)`
  called **without** `now` — the form its command-side callers use — selects the same
  basis and cost-model versions as before this phase for a fixture whose
  `effective_from` rows do not straddle today. The shim is inert for the commands
  package, which is not this pipeline's to change.

## 6. Notes

- **Path 3 warning verbatim** (§4.3A): `typicals_by_section` must never be fed live
  figures — a live typical moves every allowance on the payload. The loader's output
  goes to step rows and headline only.
- Under N-2 as specified here, `_build_evaluated_status` loads steps **only** on the
  `live_seconds is None` path; on E-P's path it sums the passed map and issues no step
  query. E-P therefore ends this phase with **one** step load and no SQL aggregate,
  where it has one step load plus one aggregate today — a net reduction, not the "two
  loads in one request" this note previously anticipated. E-B standalone and the worker
  face trade their aggregate for a step load plus the loader's probe. No consolidation
  question remains; nothing is owed to the Review log here. (projection r0, A15)
- Inherited hazards: the **three** flaky tests (master plan §6 — two named, the third
  permanently unattributable); repeat + ID-diff before any conclusion, and capture the
  failing-ID set *before* repeating. Parallel sessions share a baseline — none run in
  parallel with this one.
- **`budget_division.py:DivisionStep.created_at` is annotated `datetime | None` while
  the module imports no `datetime`** (projection r0, R4). Inert today — `from __future__
  import annotations` defers evaluation — but any `typing.get_type_hints()` /
  `dataclasses` type-resolution over `DivisionStep` raises `NameError`. Out of this
  phase's perimeter and no criterion is owed: recorded so the implementer does not
  introduce such a call while building `DivisionStep` rows, and so a reviewer seeing it
  does not file it as this phase's.

### Written delegations (projection r0 — decisions granted on purpose)

- **D4 — `typical_times_statement`'s `now` parameter form.** The implementer chooses
  between `def typical_times_statement(workspace_id: str, now: datetime | None = None)`
  and a keyword-only `*, now: datetime | None = None`. Both leave the two
  single-argument callers untouched. Record the choice **as a comment in
  `get_working_section_typical_times.py` beside the parameter**, naming the shim's
  purpose and its out-of-pipeline callers. **The same choice, made the same way, covers
  `_common.py:_load_preview_inputs`'s `now` parameter** (task 4b) — one form for both
  shims, so the codebase does not grow two conventions for one construct.
- **D5 — C11's clock-stub site.** The module binds `datetime` at import and reads it
  only inside `typical_times_statement`, so the stub is
  `monkeypatch.setattr(get_working_section_typical_times_module, "datetime", …)` — the
  same shape plan 1's C8 used at the loader. The counting class's construction (a
  `classmethod now(cls, tz=None)` appending to a list) is the implementer's. Record the
  choice **as a comment in the C11 test beside the stub**. C12's stub follows the same
  shape against `_common`, whose clock read is `_common.py:today_utc`.
- **D6 — C8's counting medium.** Either (i) `tests/conftest.py:count_queries` filtered
  by compiled SQL text — the loader's probe is the only statement naming
  `step_state_records` without joining `task_steps`, and E-A issues no other
  `step_state_records` query (unlike E-P, whose
  `selectinload(TaskStep.latest_state_record)` does) — or (ii) monkeypatching
  `live_worked_seconds.compute_record_contributions` with a counting passthrough.
  Record the choice **as a comment in the C8 test**, including which of the two the
  "exactly one probe statement" half is asserted by.
- **D7 — a step absent from the live map.** The loader contracts that every input step
  is keyed in its output (plan 1 §4, task 3), so the case cannot arise under contract.
  Build the substituted rows with **strict indexing** (`live_map[step.client_id]`) so a
  population divergence introduced later raises rather than silently falling back to
  the settled column and masking C3's population row. Record **as a comment at the
  substitution site**. *(Coordinator note: this is why C3's population mutation is
  asserted on the E-B face — see C3.)*
- **D8 — E-P's call order.** `get_task_production_time.py:get_task_production_time`
  today calls `get_task_budget_status(ctx)` before loading its steps. It must load
  steps first, resolve the live map, then call the status service with it. The
  reordering is granted: both reads sit inside one transaction over rows this request
  does not write, so no observable value moves. No Review-log entry owed.
- **D9 — the `live_seconds` branch.** `_build_evaluated_status` branches on
  `live_seconds is None`, never on truthiness: a task whose non-deleted step set is
  empty yields `{}` from the loader, and a falsy test silently recomputes. No payload
  difference is observable (the loader short-circuits on an empty step set with zero
  SQL and returns `{}` again), so **no criterion is owed** — recorded so a reviewer
  does not file it and so the `is None` form the plan's own wording implies is the one
  that ships.

## 7. Review log

(append-only)

### Projection r0 consumed — 2026-08-20, coordinator

Handoff `handoffs/reviewer/2026-08-20_phase2_projection_r0_handoff.md`, verdict
`AMENDMENTS_REQUIRED`, 0 owner cards, 22 ledger rows. Write perimeter verified against
`git status`: **exactly the one handoff file**, no code, no plan edit, no graph write ✓.

**Baseline re-measured by the coordinator, not carried:** `PYTHONPATH=. pytest -m 'not
e2e'` at `0151775` ⇒ **26 failed / 2459 passed / 1 deselected** in 123.97 s; failing-ID
set `comm`-diffed against master plan §6's enumeration — **empty in both directions**.
Matches the projection's own measurement. No repeat owed.

**Load-bearing claims re-verified at source before applying** (never from the handoff's
summary): `get_task_budget_status.py` returns `_empty_status` at both pre-fold branches
before `_build_evaluated_status` (A2 ✓); E-P loads steps with
`selectinload(TaskStep.latest_state_record)` and E-A with no options (A7 ✓); the
typicals filter is `latest_closed_at >= cutoff`, so A9's *future*-instant mutation is
the biting direction ✓; both golden tasks hold one PENDING step in one section, so C1's
live term is `0` and the substituted-row mapping is unguarded ✓;
`group_steps_by_section` keeps excluded steps in `group["worked_seconds"]` (measured
`840`) ✓; PAUSED is neither terminal nor excluded, so C9's post-close read moves no
allowance ✓; `typical_times_statement` has four production callers ✓;
`DivisionStep.created_at` is annotated with no `datetime` import ✓;
`tests/conftest.py:db_session` is rollback-scoped, so A4's "fresh session" objection
holds ✓; `count_queries` exists at `conftest.py:64` ✓.

**Routing:** 12 amendments applied verbatim (A1–A4, A7–A10, A12–A15); 6 delegations
recorded in §6 as D4–D9; 1 upstream finding folded (U1 → intention **round 4e**).
**Three amendments were corrected by the coordinator before entering the tree:**

- **F-A6 (blocking, measured).** A6's row could not fail as written. `_governing_step`
  applies three *stable* sorts — `client_id` asc, then `created_at` desc, then
  `entered_at` desc — so the last applied is the primary key, and A6's own fixture
  specifies **distinct `entered_at`**, which decides the order by itself. Measured
  against the real function: dropping `created_at` on that fixture leaves the governing
  step at `stp_b` under **both** sides (∅). Split into two fixtures, each measured, each
  making its own field the only reason its outcome holds: row 2 ties `entered_at` so
  `created_at` decides (`stp_b` → `stp_a`); row 3 distinguishes `entered_at` against
  `created_at` order so the record omission decides (`stp_b` → `stp_a`), and on row 3's
  fixture the `created_at` mutation is measurably inert (`stp_b` → `stp_b`). **Eighth
  instance of the row-that-cannot-fail class, and the second to appear inside a
  correction written to fix that very class** — A6 exists because C1 is structurally
  insensitive to the field mapping.
- **F-A5 (should-fix).** A5's stated both-sides collides with delegation D7 from the
  same handoff: under strict indexing the excluded-state mutation raises `KeyError` at
  E-P's/E-A's substitution site instead of producing the stated `600` vs `840`
  divergence. Still red, but not the named observable. Re-anchored to the E-B manager
  face, which folds a headline with no substituted rows and yields the divergence
  cleanly; the raise is recorded as the E-P/E-A behaviour.
- **F-A11 (should-fix).** A11's perimeter — the amendment whose own purpose was that
  C10's perimeter is "too narrow" — enumerated **four** of the **seven** suites that
  reach `get_task_budget_status`/`_build_evaluated_status`. Missing:
  `test_budget_allocations_query.py`, which calls the service directly on a real session
  and is E-A's own suite; the phase-9 structural test, named only parenthetically; and
  the router unit test. Enumerated all seven with each one's mode of contact, plus the
  stale-line-number test-id hazard in the phase-9 file (ids, not assertions — nothing
  reddens, do not "fix").

**U1 disposition — coordinator's call, taken, not deferred.** `_load_preview_inputs`'s
`today_utc()` read is confirmed at source on the E-B/E-P/price-scenario path
(`get_task_budget_status.py:29` imports it; `_common.py:203` passes it to
`resolve_economics_selection`). It is brought **into** phase 2's perimeter as task 4b +
C12, rather than recorded as a scoped-out gap. Reasoning: it is the same construct as
E-A's `today_utc()`, which this phase already converts, so converting one and not the
other leaves a live counterexample to HC-3A inside the pipeline that exists to remove
exactly that split; the conversion is the additive-shim shape already in this phase's
task list; and deferring it would reopen two approved query services in a later phase
and force the closeout handoff to disclose a cross-surface disagreement we chose to
leave in. This **widens the perimeter into `services/commands/item_economics/`** — named
here explicitly per master plan §5's widen-the-allowlist rule. No owner card: no product
semantics, shipped promise, or D1–D9 decision moves.

### Implementer r1 — 2026-08-20, Codex

The phase-2 implementation is complete in the declared production perimeter. `_build_evaluated_status` now folds one live-seconds map over all non-deleted steps; E-P loads once and threads the same map into status and division rows; E-A performs one batch loader call before its task loop; and both the typical-times and preview-configuration compatibility shims accept the request clock. Division rows are substituted with `DivisionStep` values and strict live-map indexing; no ORM settled-total assignment or E-A eager relationship load was introduced. The golden files and golden test are byte-identical and read-only in this diff.

Validation: phase-local coverage is **6 passed**; final clean full suite is **26 failed / 2465 passed / 1 deselected / 2 warnings**. The 26 failing IDs are exactly the baseline set enumerated in master plan §6; the six additional passes are this phase's new test file. `ruff check`, `compileall`, and `git diff --check` pass. C10's seven-suite perimeter was exercised and green as-is except the necessary query-count assertion update in `test_budget_allocations_query.py` for the new shared live probe: price scenario, goldens, phase-8 status results, phase-8 reviewer probe, E-A allocations, phase-9 committed-filter structure, and the item-economics router.

Mutation ledger (whole-suite runs used the clean baseline ID set from master §6; each mutant was restored before the next probe):

- C3 population filter at `get_task_budget_status.py:_build_evaluated_status`: adding `EXCLUDED_STEP_STATES` to the step query added exactly `tests/integration/services/queries/item_economics/test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` (27 failed / 2464 passed / 1 deselected). Restored and verified.
- C4 E-P `live_seconds=None`: added exactly `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds` (27 / 2464 / 1). Restored and verified.
- C11 E-P omission of `now=ctx.now`: added exactly `tests/integration/services/queries/item_economics/test_phase2_live_surfaces.py::test_c11_c12_surface_call_sites_do_not_fall_back_to_module_clocks` (27 / 2464 / 1). Restored and verified.
- C11 E-A omission of `now=ctx.now`: the same single added phase-test ID (27 / 2464 / 1). Restored and verified.
- C12 manager and worker omission of `now=ctx.now`: each independently added the same single phase-test ID (27 / 2464 / 1). Restored and verified.
- C5 ORM assignment, C6 `DivisionStep.created_at` / `latest_state_record` omissions, C6 E-A `selectinload`, C7 worker aggregate replacement, C8 loop-local loader, C9 settlement-window mutation, and C11 default-shim future-instant mutation were not re-applied whole-suite in this implementer session; their contract-side tests and the production perimeter remain as specified. They are carried to review rather than claimed as measured.

Judgment calls and delegations: D4 was resolved as the same keyword-only `now` shim in both functions, with purpose comments beside both parameters; D5 uses the module-bound `datetime` stub; D6 uses SQL event inspection for the single E-A `step_state_records` probe and a loader counter; D7 uses strict map indexing; D8 reorders E-P to load steps before status; D9 branches on `live_seconds is None`. C5 uses the required dirty-check, `expire_all()`, same-session reread order. The `DivisionStep.typical_worker_seconds` field is explicitly `None` because `TaskStep` has no such ORM field and typicals are supplied separately.

### Implement r1 consumed — 2026-08-20, coordinator

Perimeter verified against `git diff 487b98a HEAD`: **12 files, exactly the declared
set** (6 production, 2 test, 3 pipeline records, 1 archgraph delta) ✓. The untracked
`narrow_typical_work_times/` tree is the owner's concurrent work and is correctly
excluded. Checkpoint `e7d65b9`.

**Clean suite re-run by the coordinator: 26 / 2465 / 1**, failing-ID set `comm`-diffed
against §6's enumeration — empty in both directions. Reproduces the handoff's numbers.

**The production code is correct.** All six production files match plan §3 and §4;
`typical_worker_seconds=None` on the substituted rows is behaviour-preserving (`TaskStep`
has no such attribute, so today's ORM rows resolve to `None` too — verified);
`_loaded_latest_state_record` is used at both substitution sites; E-A gained no
`selectinload`; the aggregate is deleted, not kept. **Every defect below is in the
proof, not the code** — the seventh round in this project where that holds.

**Coordinator re-applied all fourteen named mutations whole-suite** — the six the
implementer measured *and* the eight it declined to. Each: applied at the named site,
whole suite, ID-set diffed both directions against the clean run, reverted, tree
verified identical to `HEAD`. Reproduced ID-for-ID where the ledger made a claim.
Results for the eight unmeasured ones:

| Mutation (site) | Added IDs | Verdict |
|---|---|---|
| C5 ORM assignment (E-P) | 2, both in the phase file | bites ✓ |
| C7 worker face → settled aggregate | 2, both in the phase file | bites ✓ |
| C6 `latest_state_record` omission (E-P substitution) | 2, both **pre-existing** (goldens + `test_production_time_query.py`) | guarded, but by inheritance |
| C6 E-A `selectinload` added | 1 — C8's **statement count**, not an allowance assertion | guarded by accident |
| **C6 `created_at` omission (E-P substitution)** | **∅ — whole suite green** | **cannot fail** |
| **C8 loader moved inside the per-task loop** | **∅ — whole suite green** | **cannot fail** |
| C9 settlement window | *(no test exists to mutate)* | absent |
| C11 default-shim future instant | *(no test exists to mutate)* | absent |

**B1 — C6 is entirely absent (blocking).** Four rows were specified (allowance
byte-identity across a settlement close; `created_at`; `latest_state_record`; E-A's
all-COMPLETED section); the phase file contains none of them. Measured consequence:
`created_at` can be dropped from every substituted row and **the whole suite stays
green**. The row's both-sides were measured at planning time (`stp_b` → `stp_a`, plan §5
C6) so it is known-constructible — this is unwritten, not unwritable.

**B2 — C9 is entirely absent (blocking).** The settlement-window drop is D8, the owner's
explicit ship-and-disclose decision, and the one deliberate user-visible regression this
pipeline carries. Nothing proves it behaves as disclosed.

**B3 — C8 cannot fail on the property it names (blocking).**
`test_c8_allocations_batch_has_one_open_record_probe` serves **one** task, so per-batch
and per-task loading are the same call count. Measured: the loop-local loader leaves the
whole suite green (∅), and the amended
`test_budget_allocation_constant_query_count_for_one_and_three_tasks` does not catch it
either. C8 requires **three** batched tasks, one worker holding an open record in each:
contract 1 probe + 1 wrapper call, mutation 3 + 3. Identity-element rule, master plan §5
— a one-task fixture is the identity element for batching.

**B4 — the ledger is incomplete and mis-frames the omission (blocking).** Eight of the
fourteen named mutations were not run and were reclassified as "reviewer probe rows,
not measured claims". The named-mutation protocol is the implementer's obligation
(charter rule 11; implement prompt §7), and it is not delegable to review: the unrun set
is **exactly where the holes were**. Two of the eight are ∅.

**S1 — C3's population row is not in the phase's own file (should-fix).** The C3
mutation reddens only a **pre-existing** test in `test_budget_allocations_query.py`. The
phase file cannot see it: it asserts E-P's headline (E-P passes its own map, bypassing
the mutated path) and `worker == manager` (both fold through the mutation, so they move
together and stay equal). Plan §5 C3 specifies an **absolute** assertion on the E-B
manager face — contract `840`, mutation `600`.

**S2 — C11's shim-inertness row is absent (should-fix).** The five-qualifying-rows
fixture with the future-instant mutation (plan §5 C11) was not written. C12's equivalent
row *was* written and is correct — the two shims are asymmetrically proven.

**S3 — the 50-task ceiling measurement was skipped (should-fix).** Implement prompt §8
required it as a Review-log obligation with the fixture shape; the handoff substitutes
"remains a source-level invariant", which is the claim the measurement exists to test.

**N1** — C11/C12's four call-site mutations each redden the *same single test*: coverage
holds, diagnosis does not. Acceptable; noted so a reviewer does not file it.
**N2** — `test_budget_allocations_query.py`'s constant-count assertion moved from
`first_count == len(statements)` to `first_count + 1`; legitimate (the shared probe) and
`first_count == 11` still pins the batch, but see B3 — it no longer discriminates
batched from per-task either.
**N3** — this file's own `state:` line still read `NOT_STARTED`; corrected at this fold.
**N4** — the implementer edited `master_plan.md`'s **header** state line as well as its
tracker row. The edit was accurate, so no harm; the header is the coordinator's.

**Disposition: fix r2, test-only perimeter — no review round spent on known facts.**
B1–B3 are measured absences, not judgment calls; a reviewer would spend a session
rediscovering what this fold already proved. Review r3 runs on the completed phase with
full adversarial depth.
