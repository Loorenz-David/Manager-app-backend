---
plan: 2
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-20
actor: Opus 5 (projection r0)
---

# Projection handoff — plan 2 (round 0), `live_clock_for_working_time_economics`

## Opening

Phase 2's plan is buildable and its design is right: I walked every task on paper
against the real code and found no case where the three surfaces would disagree with
each other, and no case where the goldens phase 1 captured would move. What the plan
does not yet do is make its own tests able to fail. Six of the eleven acceptance
criteria are written so that the specific defect each one exists to catch would leave
the test green — the same shape this project has now recorded seven times, and each
one is a paragraph to fix now versus a review round to find later. Nothing here needs
the owner personally, and nothing changes what the feature does or means. The
coordinator applies twenty-two ledger rows — fifteen plan amendments, one upstream
correction to the intention, six written delegations — and then compiles the
implementer prompt.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. No ledger row below changes product semantics, a shipped promise, or a D1–D9
decision; every row is a mechanism, a fixture, or a citation.

---

## Decision ledger

Twenty-two rows. Amendment and delegation text is verbatim-ready — the coordinator
applies these words.

| # | Decision point | Class | Proposed routing |
|---|---|---|---|
| P1 | C4 — where the loader-invocation counter is installed | plan gap | amend C4 (A1) |
| P2 | C4 — the fixture's evaluation precondition, both endpoints | plan gap | amend C4 (A2) |
| P3 | C4 — E-A's `today_utc()` mutation cannot bite on an arbitrary fixture | plan gap | amend C4 (A3) |
| P4 | C5 — assertion order (dirty-check before expire) | plan gap | amend C5 (A4) |
| P5 | C5 — "a fresh session" is not constructible on `db_session` | plan gap | amend C5 (A4, same block) |
| P6 | C3 — the population row's SKIPPED step sits at addition's identity element | plan gap | amend C3 (A5) |
| P7 | no criterion can observe a `DivisionStep` field-mapping omission | plan gap | amend C6 (A6) |
| P8 | E-A's `latest_state_record` — both obvious resolutions are defects | plan gap | amend §3 + C6 (A7) |
| P9 | C8 — no named mutation for the batch-keying guard | plan gap | amend C8 (A8) |
| P10 | C11 — the inertness row is not writable as worded and names no mutation | plan gap | amend C11 (A9) |
| P11 | C6 — the byte-identity comparison partner is undefined | plan gap | amend C6 (A10) |
| P12 | C10 — blast-radius perimeter and remedy set are both too narrow | plan gap | amend C10 (A11) |
| P13 | C7 — "the existing key-walk family" is not where the criterion implies | plan gap | amend C7 (A12) |
| P14 | §2 read-first omits plan 1 §5 **C5** and **C10**, the two shapes phase 2 actually reuses | plan gap | amend §2 (A13) |
| P15 | §2 attributes baseline `26 / 2459 / 1` to master plan §6, which carries `26 / 2436 / 1` | plan gap | amend master plan §6 (A14) |
| P16 | §6's "two loads in one E-P request" is false under N-2 as this plan specifies it | plan gap | amend §6 (A15) |
| U1 | a **fourth** wall-clock read on the E-B / E-P / price-scenario request path, named nowhere | intention gap | fold into intention §2.3A + §1A HC-3A (U1 below) |
| F1 | `now` positional vs keyword-only on `typical_times_statement` | free choice | delegation D4 |
| F2 | C11's clock-stub site and its recorded medium | free choice | delegation D5 |
| F3 | C8's counting medium (`count_queries` text filter vs patching the wrapper) | free choice | delegation D6 |
| F4 | what a substituted row carries when a step is absent from the live map | free choice | delegation D7 |
| F5 | E-P's call reordering (steps before `get_task_budget_status`) | free choice | delegation D8 |
| F6 | `live_seconds is None` vs falsy-empty branch in `_build_evaluated_status` | free choice | delegation D9 |

---

## Plan amendments, verbatim

### A1 — C4, the invocation counter's observation point (replaces C4's second sentence)

> Each consumer binds the loader by name at import
> (`from …live_worked_seconds import load_live_worked_seconds`), so a counter
> installed on one module's attribute observes only that module's calls. The
> criterion's counter is installed on **every** consumer binding —
> `get_task_production_time.load_live_worked_seconds`,
> `get_task_budget_status.load_live_worked_seconds`, and
> `get_task_budget_allocations.load_live_worked_seconds` — and the assertion is over
> the **total**. Contract: total == 1 per request for each of E-P, E-B manager face,
> E-B worker face, E-A. Under the named mutation (E-P passes `live_seconds=None`)
> the total is **2**, and a counter installed only at E-P's binding would read **1**
> under both sides, because E-P keeps its own loader call to build its division rows
> and only the second call moves — the row would be decoration.

**Why (derived, not asserted).** Under the mutation E-P still resolves its own map for
the `DivisionStep` substitution; the extra computation happens at
`get_task_budget_status.py:_build_evaluated_status`'s own binding. A single-site
counter is blind to exactly the call the criterion exists to see.

### A2 — C4, the fixture precondition (append to C4)

> **Fixture precondition, load-bearing:** the task carries a **committed,
> non-superseded, non-deleted `ItemCostEvaluation`**.
> `get_task_budget_status.py:get_task_budget_status` returns `_empty_status(…)`
> before `_build_evaluated_status` on every other branch, so without the evaluation
> the fold never runs, the mutation's second loader call never happens, and the total
> stays 1 under both sides. The same precondition makes E-B's contract total 1 rather
> than 0.

### A3 — C4, E-A's `today_utc()` mutation (replaces "E-A restoring `today_utc()` inside the loop ⇒ its determinism row red")

> **E-A restoring `today_utc()` inside the loop** (call site,
> `get_task_budget_allocations.py:get_task_budget_allocations`). This mutation only
> bites on a fixture where the two dates select different configuration rows:
> `today_utc()` and `ctx.now.date()` feed
> `configuration.py:resolve_economics_selection`'s `on_date`, which filters basis and
> cost-model versions through `configuration.py:is_applicable`. Fixture: a task in the
> batch with **an item and no committed evaluation** (the only branch that reaches this
> call), `ctx.now = 2020-01-01T00:00Z`, and a `ProductionCostBasisVersion` with
> `effective_from = 2020-06-01`. **Both sides:** contract `status ==
> "not_configured_no_basis_version"`; mutation (real today ≥ 2020-06-01) `status ==
> "ok"` or the valuation-derived status — differ ⇒ red. Without the straddle the
> mutation is inert and the row proves nothing.

### A4 — C5, assertion order and the session (replaces C5's assertion clause)

> **Assert in this order, per endpoint:** (1) `session.dirty` contains no `TaskStep`;
> then (2) `session.expire_all()`; then (3) re-read
> `task_steps.total_working_seconds` and assert it is unchanged. This is plan 1 §5
> C10's order, and the order is the criterion: `Session.expire_all()` **discards
> un-flushed attribute changes**, so an expire-then-re-read form passes under the very
> assignment this row exists to catch. In E-P and E-A the assignment would land after
> the request's last `session.execute()`, so no autoflush rescues the row.
>
> **Not "a fresh session".** `tests/conftest.py:db_session` is rollback-scoped and
> these fixtures are flush-only, so a genuinely new session sees none of the fixture
> rows and the contract-side assertion fails before any mutation is applied. The
> same-session form above is the constructible one. (If a committing fixture is used
> instead, it owns a `try/finally` teardown — charter 11½ — and the plan says which
> form ships; it is not the implementer's to pick, because one of the two silently
> disarms the row.)

### A5 — C3, the population row (replaces C3's last sentence)

> Plus the population row: a task carrying one `SKIPPED` step whose
> `total_working_seconds` is **non-zero** (use `240`) — headline still equals the fold
> over **all** non-deleted steps (§4.1A A), and `Σ sections[].worked_seconds` still
> includes it (`budget_division.py:group_steps_by_section` keeps excluded steps in
> `group["worked_seconds"]`). **Named mutation, call site in each of the three
> services:** filter `budget_division.EXCLUDED_STEP_STATES` out of the step set handed
> to the loader. **Both sides** for a task with one WORKING-open step at `600` live and
> one SKIPPED step at `240` settled: contract headline `840` == Σ rows `840`; mutation
> headline `600` vs Σ rows `840` — differ ⇒ red. At `total_working_seconds = 0` on the
> SKIPPED step the two sides coincide at addition's identity element and the row cannot
> fail (master plan §5, earned at plan 1 review r1 B1).

### A6 — C6, the substituted-row field mapping (append to C6)

> **Second row — the substituted row carries every field the allocator reads.** The
> goldens cannot guard this: both golden tasks hold exactly **one** step in **one**
> section (`test_live_clock_goldens.py`, `tsp_live_clock_golden_idle` /
> `tsp_live_clock_golden_frozen`), so `budget_division.py:_governing_step` has a single
> candidate and `_section_step_allowances`'s residual assignment is unique — every
> field that only affects **ordering** (`created_at`, `sequence_order`,
> `latest_state_record`) can be dropped from the substituted rows and the goldens stay
> byte-identical. Fixture: **two steps in one section**, with distinct
> `sequence_order`, distinct `created_at`, and distinct
> `latest_state_record.entered_at`, one of them holding an open working record. Assert
> the full E-P `sections[]` and E-A `steps[]` payloads equal those produced from the
> same fixture through the un-substituted (settled) path. **Named mutation,
> substitution site in `get_task_production_time.py`:** construct `DivisionStep`
> omitting `created_at` (leaving its `None` default). **Both sides:** contract —
> `_governing_step` orders the two candidates by `entered_at` desc and the payload's
> `state_entered_at` / `section_name_snapshot` follow the later-entered step; mutation
> — with `created_at` `None` on both rows the `created_at` sort becomes inert and the
> tie falls to `client_id`, moving `state_entered_at` on any fixture whose two steps'
> `client_id` order contradicts their `created_at` order (build it so it does) ⇒ red.
> The ten fields the allocator reads are enumerated in master plan §4, N-3.

### A7 — §3 and C6, E-A's `latest_state_record` (append to §3's E-A bullet, and one C6 row)

Append to `plans/plan_2.md` §3, `get_task_budget_allocations.py` bullet:

> **E-A's step-load options are unchanged — no `selectinload` is added.** The service
> selects steps with no eager load, and `budget_division.py:_loaded_latest_state_record`
> reads `step.__dict__` and yields `None` without emitting SQL, so `_governing_step`
> orders E-A's candidates by `created_at` / `client_id` alone. Both obvious
> resolutions are defects: building `DivisionStep(latest_state_record=step.latest_state_record)`
> triggers a lazy load on an async session (`MissingGreenlet` — loud), and "fixing"
> that by adding `selectinload(TaskStep.latest_state_record)` **silently moves E-A's
> `allowance_seconds` and `left_seconds`**, because a section whose steps are all
> COMPLETED takes `_section_step_allowances`'s `else` branch and hands the residual to
> whichever step `_governing_step` returns — an ordering that changes the moment the
> relationship is loaded. The substituted row therefore carries **exactly what the
> allocator would read today**: `budget_division._loaded_latest_state_record(step)`.
> Importing that private helper is the house precedent
> (`get_task_price_scenario.py` already imports `_median` and
> `_step_state_is_excluded` from the same module).

Append to C6:

> **Third row — E-A's all-completed section.** A task with one section whose steps are
> **all `COMPLETED`** (≥ 2 of them, distinct `created_at`), served through E-A: every
> `allowance_seconds` and `left_seconds` byte-identical to the pre-substitution
> payload. **Named mutation, `get_task_budget_allocations.py:get_task_budget_allocations`
> step-load site:** add `.options(selectinload(TaskStep.latest_state_record))` ⇒ the
> residual lands on a different step ⇒ red. Neither C1 nor C6's open-record rows can
> see this: the goldens' sections hold one step each, and a section with an open
> working record never reaches the `else` branch.

### A8 — C8, the named mutation (append to C8)

> **Named mutation, call site, `get_task_budget_allocations.py:get_task_budget_allocations`:**
> move the `load_live_worked_seconds` call **inside** the per-task loop, over that
> task's steps only. **Both sides**, one active worker holding one open working record
> in each of **3** batched tasks: contract — **1** open-record probe statement and
> **1** `compute_record_contributions` call; mutation — **3** probe statements and
> **3** wrapper calls, because the user's sweep is re-run once per task instead of once
> per request (§3.4A B's "a worker's sweep is shared across all their steps"). The
> two-worker row's contract side is 1 probe + **2** wrapper calls.

### A9 — C11, the inertness row (replaces C11's last sentence)

> Plus one behaviour-preservation row for the shim: `typical_times_statement(workspace_id)`
> called **without the `now` argument** — the form its three out-of-pipeline callers
> use (`get_working_section_typical_times.py:get_working_section_typical_times`,
> `get_task_price_scenario.py:_typical_block`) — executed against a fixture with
> exactly five qualifying completed section-totals, asserting the **exact** returned
> rows (`sample_count == 5`, `typical_worker_seconds ==` the fixture's median). "The
> same rows as before this phase" is not writable: the pre-phase function is not
> callable at test time, and `typical_times_statement()` with no argument at all is a
> `TypeError` (`workspace_id` is a required positional). **Named mutation, definition
> site, `get_working_section_typical_times.py:typical_times_statement`:** make the
> defaulted branch resolve to a fixed past instant (`datetime(2000, 1, 1,
> tzinfo=timezone.utc)`) instead of the clock ⇒ the cutoff falls before every fixture
> row's `latest_closed_at` … change it to a fixed **future** instant
> (`datetime(2099, 1, 1, tzinfo=timezone.utc)`) ⇒ `sample_count == 0` and
> `typical_worker_seconds is None` ⇒ red. Use the future form; the past form is inert
> because a wider window admits the same five rows.

### A10 — C6, the comparison partner (replaces C6's first clause)

> **C6 — T12 allowances:** serve the payload with an open working record; then close
> that record through the production transition path and run
> `_recompute_step_time_totals`; then serve again. Every `allowance_seconds` (sections
> and steps) in the first payload is byte-identical to the second's. The close recipe
> is plan 1 §5 C5's: `_step_transition_core.py:_apply_step_transition` with `now=t`
> (`transition_step_state.py:transition_step_state` stamps its own clock and cannot
> close at a pinned `t`).

### A11 — C10, the blast radius (replaces C10)

> **C10 — the `_build_evaluated_status` blast radius** (§2.6). N-2 changes that
> function from a scalar SQL aggregate into a step load plus a loader call, so its
> dependents can go red for **two** unrelated reasons, and the plan admits both
> remedies: (a) *time dependence* under the live basis — remedy is a frozen `ctx.now`
> in the affected fixtures, never a change to a shipped service file; (b) *statement
> shape* — a suite driving the service with a hand-rolled session
> (`test_price_scenario_query.py:_TypicalSession`,
> `test_phase9_committed_filter_structure.py:_CapturingSession` are the existing
> shapes) answers a `scalar()` for the aggregate and cannot answer a
> `select(TaskStep)`; remedy is the fixture's shape, again never the service.
> **Perimeter — every suite that reaches `_build_evaluated_status`,** enumerated at
> this phase's head and all four green:
> `tests/integration/services/queries/item_economics/test_price_scenario_query.py`,
> `tests/integration/services/queries/item_economics/test_live_clock_goldens.py`,
> `tests/integration/services/commands/item_economics/test_phase8_status_results.py`,
> `tests/integration/services/commands/item_economics/test_phase8_reviewer_r1_probe.py`.
> (Verified at projection r0: `test_phase9_committed_filter_structure.py` and the
> `_TypicalSession` rows early-return before `_build_evaluated_status` today, so the
> shape risk is latent, not present — which is why it must be named rather than
> discovered.) The Review log records which of the two outcomes happened, per file.

### A12 — C7, the worker-face row (replaces C7)

> **C7 — T7 worker face, one new integration row** in
> `app/tests/integration/services/queries/item_economics/`. Serve one fixture — a task
> with an open working record and a committed evaluation — through both faces on the
> production path, and assert: (1) walking every key of
> `serialize_task_budget_status(get_task_budget_status_worker(ctx),
> include_monetary=False)` yields no key containing `_minor`, `cost`, `price`,
> `currency`, `money` or `valuation` (the token walk at
> `test_production_time_query.py:test_c14_c16_flat_time_only_degradation_and_tenant_boundary`
> is the pattern); (2) the worker face's `actual_worker_seconds`,
> `actual_worker_minutes`, `remaining_worker_minutes`, `percent_consumed` and
> `variance_worker_minutes` equal the manager face's for that fixture, and are
> **greater than** the same task's settled-basis values (D5 — no split-brain, and the
> row is non-vacuous only because the live term is non-zero). **This is not an
> extension of `tests/unit/services/queries/item_economics/test_phase8_serializers.py`:**
> that family builds its status objects by hand, so it cannot carry a live field
> without breaching charter rule 3, and it sits outside this phase's declared test
> perimeter. **Named mutation, `get_task_budget_status_worker.py:get_task_budget_status_worker`:**
> replace the `_build_evaluated_status` delegation with the pre-phase settled aggregate
> ⇒ assertion (2) red (intention §4.1A D, row 2 — "worker face silently stays
> settled").

### A13 — §2 read-first (replaces item 1b)

> 1b. `plans/plan_1.md` §5 — **C5** (the `_apply_step_transition` close-at-`t` recipe
>    this phase's C6 and C9 both reuse; `transition_step_state` cannot be used),
>    **C10** (the dirty-check-before-expire assertion order this phase's C5 reuses),
>    and C9/C11/C12 as amended — §6's structural-facts note and its three written
>    delegations, and §7's Review log: six rounds of findings, every blocking one in a
>    plan or review artifact rather than in code.

### A14 — master plan §6, the baseline line

`plans/plan_2.md` §2 cites master plan §6 for the baseline `26 / 2459 / 1`; §6 carries
`26 / 2436 / 1` (the pre-phase-1 measurement at `2711b58`), and the `2459` figure lives
only in §3's phase-1 tracker row. The superseded-orientation banner added at `0151775`
now makes the same mis-citation. Amend master plan §6's baseline bullet:

> - **Start baseline, pre-phase-1, on a clean tree at `2711b58`: 26 failed / 2436
>   passed / 1 deselected.** **Current baseline, phase 1 approved, re-measured by
>   projection r0 at `0151775`: 26 failed / 2459 passed / 1 deselected** — the failure
>   ID set below is unchanged between the two measurements and is what every criterion
>   compares against.

### A15 — §6's E-P note (replaces the second bullet of `plans/plan_2.md` §6)

> Under N-2 as specified here, `_build_evaluated_status` loads steps **only** on the
> `live_seconds is None` path; on E-P's path it sums the passed map and issues no step
> query. E-P therefore ends this phase with **one** step load and no SQL aggregate,
> where it has one step load plus one aggregate today — a net reduction, not the "two
> loads in one request" this note previously anticipated. E-B standalone and the worker
> face trade their aggregate for a step load plus the loader's probe. No consolidation
> question remains; nothing is owed to the Review log here.

---

## U1 — upstream: a fourth wall-clock read on the E-B / E-P / price-scenario path

**Finding.** `services/commands/item_economics/_common.py:_load_preview_inputs` calls
`_common.py:today_utc` (`datetime.now(timezone.utc).date()`) and feeds it to
`configuration.py:resolve_economics_selection`. It is reached from
`get_task_budget_status.py:get_task_budget_status` and
`get_task_budget_status_worker.py:get_task_budget_status_worker` on the
no-committed-evaluation branch, and transitively from E-P and the price-scenario
endpoint. Intention §2.3A's corrected absence claim names **two** hits (E-A's
`today_utc()` and `get_economics_configuration_status.py`); round 4b's third
correction adds `typical_times_statement`. This one is named nowhere, and it is the
**same construct** as E-A's — `today_utc()` feeding `resolve_economics_selection` —
which plan 2 task 3 does bring under `ctx.now.date()`. Master plan §5: *sweep the
class, not the instance.* Fifth instance of the verification-scope rule in this family
(directory → term set → suite → call graph → **now the command package a query
service imports from**).

**Search run** (record it beside the claim):
`grep -rnE "datetime\.now|utcnow|func\.now|today_utc|date\.today|time\.time\(|datetime\.today"` over
`services/queries/item_economics/`, `services/queries/working_sections/`,
`services/queries/analytics/`, `domain/item_economics/`, `domain/analytics/`,
`domain/task_steps/`, **and** `services/commands/item_economics/_common.py`.

**Consequence if unrouted.** After phase 2, E-A resolves its economics selection from
`ctx.now.date()` while E-B/E-P resolve theirs from a fresh clock read. At a UTC date
rollover mid-request the two surfaces can select different basis/cost-model versions
and report a different `status` for the same task — a cross-surface disagreement on
the branch where `actual_worker_seconds` is `None`, so HC-5's own tests cannot see it.
It is also the one remaining counterexample to HC-3A's "within the three surfaces, one
request is one `now`".

**Proposed fold — intention §2.3A, appended as a fourth correction:**

> **Fourth correction (round 4e, projection r0 on plan 2 — the scope rule again, one
> package further out).** The corrected search of round 4b covered the query packages
> and the typicals callee. It did not enter
> `services/commands/item_economics/_common.py`, which
> `get_task_budget_status.py:get_task_budget_status` and
> `get_task_budget_status_worker.py:get_task_budget_status_worker` import from:
> `_common.py:_load_preview_inputs` calls `_common.py:today_utc` and hands the result
> to `configuration.py:resolve_economics_selection`. That is a wall-clock read on the
> E-B, E-P and price-scenario request paths, on the no-committed-evaluation branch. It
> is the **same construct** as E-A's `today_utc()` — the instance §2.3A named and the
> class it did not.

**Proposed fold — intention §1A HC-3A, scope bullet, appended:**

> **Round 4e — the second instance of E-A's construct.** `today_utc()` reaches
> `resolve_economics_selection` from **two** places on this pipeline's surfaces:
> `get_task_budget_allocations.py:get_task_budget_allocations` (E-A, brought under
> `ctx.now.date()` by plan 2) and `_common.py:_load_preview_inputs` (E-B both faces,
> and E-P and price scenario through composition). Both come under the injected `now`
> as `now.date()`, for the same reason and with the same behaviour-preserving
> character: `_load_preview_inputs` gains `now: datetime | None = None` whose default
> preserves the existing read for its command-side callers, and the two query services
> pass `ctx.now`. Leaving only one of the two converted is the split this pipeline
> exists to remove, reintroduced through the configuration date.

**Coordinator's call, not the owner's:** whether the `_load_preview_inputs` conversion
enters plan 2's perimeter (it is four lines and one added C11-shaped row) or is
recorded as a scoped-out known gap with the rollover consequence written down. Either
disposition is defensible; leaving it *unnamed* is not.

---

## Written delegations, verbatim

> **D4 — `typical_times_statement`'s `now` parameter form.** The implementer chooses
> between `def typical_times_statement(workspace_id: str, now: datetime | None = None)`
> and a keyword-only `*, now: datetime | None = None`. Both leave the three
> single-argument callers untouched. Record the choice **as a comment in
> `get_working_section_typical_times.py` beside the parameter**, naming the shim's
> purpose and its out-of-pipeline callers.
>
> **D5 — C11's clock-stub site.** The module binds `datetime` at import and reads it
> only inside `typical_times_statement`, so the stub is
> `monkeypatch.setattr(get_working_section_typical_times_module, "datetime", …)` — the
> same shape plan 1's C8 used at the loader. The counting class's construction (a
> `classmethod now(cls, tz=None)` appending to a list) is the implementer's. Record the
> choice **as a comment in the C11 test beside the stub**.
>
> **D6 — C8's counting medium.** Either (i) `tests/conftest.py:count_queries` filtered
> by compiled SQL text — the loader's probe is the only statement naming
> `step_state_records` without joining `task_steps`, and E-A issues no other
> `step_state_records` query (unlike E-P, whose
> `selectinload(TaskStep.latest_state_record)` does) — or (ii) monkeypatching
> `live_worked_seconds.compute_record_contributions` with a counting passthrough.
> Record the choice **as a comment in the C8 test**, including which of the two the
> "exactly one probe statement" half is asserted by.
>
> **D7 — a step absent from the live map.** The loader contracts that every input step
> is keyed in its output (plan 1 §4, task 3), so the case cannot arise under contract.
> Build the substituted rows with **strict indexing** (`live_map[step.client_id]`) so a
> population divergence introduced later raises rather than silently falling back to
> the settled column and masking C3's population row. Record **as a comment at the
> substitution site**.
>
> **D8 — E-P's call order.** `get_task_production_time.py:get_task_production_time`
> today calls `get_task_budget_status(ctx)` before loading its steps. It must load
> steps first, resolve the live map, then call the status service with it. The
> reordering is granted: both reads sit inside one transaction over rows this request
> does not write, so no observable value moves. No Review-log entry owed.
>
> **D9 — the `live_seconds` branch.** `_build_evaluated_status` branches on
> `live_seconds is None`, never on truthiness: a task whose non-deleted step set is
> empty yields `{}` from the loader, and a falsy test silently recomputes. No payload
> difference is observable (the loader short-circuits on an empty step set with zero
> SQL and returns `{}` again), so **no criterion is owed** — recorded so a reviewer
> does not file it and so the `is None` form the plan's own wording implies is the one
> that ships.

---

## Reality checks

Every path in `plans/plan_2.md` §3 exists; every symbol cited in §2, §3, §4, §5 and §6
resolves against the tree at `0151775`. Exceptions and corrections:

- **R1 — `plans/plan_2.md` §2 → master plan §6, baseline.** §2 attributes
  `26 / 2459 / 1` to §6; §6 carries `26 / 2436 / 1`. See A14. The
  `ORIENTATION_…20260820.md` banner added at `0151775` repeats the mis-citation.
- **R2 — `plans/plan_2.md` §2 item 1b → plan 1 §5.** It names C9 and C11/C12 as "the
  shapes this phase's criteria are modelled on". Plan 1's C9 is the naive-`now` guard
  row; plan 2's C9 is the settlement window, whose close recipe lives in plan 1's
  **C5**, and plan 2's C5 reuses plan 1's **C10** assertion order. See A13.
- **R3 — C7's "the existing key-walk family"** resolves to
  `tests/unit/services/queries/item_economics/test_phase8_serializers.py`, a unit
  family over hand-built status objects, outside §3's declared test perimeter and
  unable to carry a live field (charter rule 3). Intention §9 T7's "§11A.3 test
  family" and §9A T7's "`test_production_time_query.py`" point at two different
  places, neither of which is the E-B worker face. See A12.
- **R4 — `domain/item_economics/budget_division.py:DivisionStep.created_at`** is
  annotated `datetime | None` while the module imports no `datetime`. Inert today
  (`from __future__ import annotations` defers evaluation) but any
  `typing.get_type_hints()` / `dataclasses` type-resolution over `DivisionStep` raises
  `NameError`. Out of this phase's perimeter and no criterion is owed — recorded so an
  implementer building `DivisionStep` rows does not introduce such a call, and so a
  reviewer seeing it does not file it as this phase's.
- **R5 — phase 1's shipped output verified in the code, not from the plan's summary.**
  `live_worked_seconds.py:load_live_worked_seconds` has the signature, the
  `client_id` keying, the `settled + int(round(share))` arithmetic and the
  aware-`now` guard with its boundary-naming message that plan 2's head claims;
  `context.py:ServiceContext.now` is an aware-UTC `default_factory` field with the
  docstring rule amended; the three goldens and `test_live_clock_goldens.py` exist
  under `app/tests/integration/services/queries/item_economics/`. The loader takes its
  population **entirely from the caller** — it applies no step-state and no
  `is_deleted` filter of its own — which is what makes A5's population mutation
  meaningful and what the fold's correctness rests on.
- **R6 — the four-caller table (master plan §6) is accurate at `0151775`**, and
  `run_service.py:run_service` calls `fn(ctx)` with no signature introspection, so
  `get_task_budget_status(ctx, *, live_seconds=None)` is call-compatible with the
  router's `_run_budget_status` without a router change (HC-4 holds).
- **R7 — `typical_times_statement` has exactly four production callers**
  (`get_task_production_time.py`, `get_task_budget_allocations.py:_load_typicals`,
  `get_task_price_scenario.py:_typical_block`,
  `get_working_section_typical_times.py:get_working_section_typical_times`), matching
  intention §2.3A's third correction. The first two take `ctx.now`; the last two keep
  the default, which is exactly the shim's purpose.
- **R8 — the graph is where §6 says it is**, adjusted for phase 1's delta: 188 nodes /
  280 edges, 0 stale, 0 diagnostics, **3 pending** (the `ai_inferred` items awaiting
  the owner, tracked at `plans/plan_4.md` C6). Orientation only; nothing promoted,
  rejected or edited.

---

## Criteria decidability — C1 … C11

"Writable now" means: from the artifacts alone, one exact expected outcome per row,
no disjunction (charter rule 2).

| C | Writable now? | Finding |
|---|---|---|
| C1 | **yes** | The goldens survive the new code path: both fixture tasks hold open **PENDING** records, and the loader's probe filters `state == WORKING`, so the live term is `0` and the fold reproduces the aggregate exactly; E-A's `ctx.now.date()` equals `today_utc()` when the ctx is default-stamped (which the golden test's `_ctx` is); the typicals cutoff is time-invariant by fixture construction (no `COMPLETED` step, every `closed_at` NULL). **No field moves.** But C1 is *structurally insensitive* to the substituted-row field mapping — one step per section — which is why A6 exists. |
| C2 | **yes** | `_budget_seconds` gives `int((allowed_worker_minutes × 60).quantize(1, ROUND_HALF_EVEN))`, so `allowed_worker_minutes = 3.10` with one allocated section and no excluded steps yields `allowance_seconds = 186` exactly; a 1500 s live figure gives `share_state == "over_share"`, `worked_seconds == 1500`, `left_seconds == -1314` (`budget_division.py:divide_production_budget` does not clamp — `test_production_time_query.py:test_c13_negative_open_residual_is_not_clamped`). |
| C3 | **coherence half yes, population half no** | The coherence half holds by construction: `group_steps_by_section` sums the same per-step integers the headline sums, and every non-deleted step lands in exactly one group. The population half sits at addition's identity element as written — **A5**. |
| C4 | **no** | Three independent reasons the row cannot fail as written — the counter's site (**A1**), the missing evaluation precondition (**A2**), E-A's inert date mutation (**A3**). |
| C5 | **no** | Assertion order and the "fresh session" — **A4**. Both sides are otherwise computable: contract column `0`, mutation column `600`. |
| C6 | **partly** | The allowance half needs its comparison partner defined (**A10**); the honest-form rows (no excluded step holds an open working record; `charged_seconds` from settled values) are writable as stated and correctly reflect §4.3A path 2. Two rows added by **A6** and **A7**. |
| C7 | **no** | The named family is the wrong family and the equality clause is an identity with no mutation — **A12**. |
| C8 | **partly** | Counts are derivable and distinguishable (1 probe + 1 wrapper call for one worker; 1 + 2 for two), but no mutation is named — **A8** — and the counting medium is undelegated — **D6**. |
| C9 | **yes** | Constructible. `_step_transition_core.py:_apply_step_transition` closes `closing_record.exited_at` synchronously and only **emits the outbox task** (its own docstring); nothing in the test path runs the analytics worker, so "close without settling" is simply "call the core and do not run the worker". The step lands in `PAUSED` — not terminal, not excluded — so allowances do not move and the second read's `worked_seconds` is the stale settled column, i.e. the pre-work value. The recipe is plan 1 §5 C5's, which **A13** puts in the read-first list. The enqueued outbox row is committed state the fixture owns (charter 11½). |
| C10 | **no** | Perimeter and remedy set — **A11**. |
| C11 | **partly** | The stub-count rows and their per-call-site mutations are writable and both-sided (contract `0/0`; mutation ≥ 1 at the mutated site). The inertness row is not writable as worded and names no mutation — **A9**; stub site and parameter form delegated — **D4**, **D5**. |

**Deep-pass conclusions the prompt asked for, stated plainly.**

- **The fold's population.** The two populations **coincide on every path.**
  `_build_evaluated_status`'s aggregate spans `workspace_id`, `task_id`,
  `is_deleted.is_(False)` with no state filter; E-P's step load
  (`get_task_production_time.py`) spans the identical three predicates over the same
  task id; E-A's spans them over `visible_task_ids`; the worker face and the price
  scenario pass no map and make `_build_evaluated_status` load its own. Deleted steps
  are excluded on both sides; SKIPPED/CANCELLED/FAILED are **included** on both sides
  and their live term is `0` because every route into those states closes the open
  record first (§4.3A path 2, verified at `_step_transition_core.py` and
  `remove_task_step.py`). A task with **no** steps yields `{}` from the loader and `0`
  from the aggregate — equal, and an `int` either way. The one thing that can break the
  equality is a caller narrowing its own step set, which is why A5's mutation is owed.
- **Composition and the one-map contract.** Under the contract the loader runs exactly
  **once** per request on all five paths. It runs **twice** only if E-P omits
  `live_seconds` *and* the task has a committed evaluation. C4's assertion can observe
  that only with A1 and A2 applied; as written it cannot.
- **E-A's batch keying.** One loader call over all visible tasks' steps yields 1 probe
  statement plus one wrapper statement per distinct credited user holding an open
  working record, independent of task count — because the probe is a single
  `step_id IN (…)` over the flat step list and the user grouping happens in Python
  (`live_worked_seconds.py`). C8's assertion distinguishes one worker from two; it
  cannot distinguish batched from per-task without A8's mutation.
- **The typicals shim's inertness.** The two out-of-pipeline callers pass one
  positional argument and are behaviourally untouched under either parameter form.
  C11's inertness row, as worded, cannot fail; A9 gives it a mutation that can.
- **C1's golden invariance.** Reproduced byte-for-byte; no field moves. Insensitive to
  the substituted-row mapping — A6.
- **C9's constructibility.** Constructible, exactly as described, with plan 1 §5 C5's
  close recipe.

---

## Environment measurement

Full non-e2e suite, clean tree at `0151775`,
`PYTHONPATH=. pytest -m 'not e2e'` from `backend/app/`:

**26 failed / 2459 passed / 1 deselected** in 121 s. The 26 failing IDs are
**byte-identical** to master plan §6's enumerated set (`diff` over the sorted sets:
empty). The count matches the phase-1 approval record, so no repeat is owed; the
disagreement is with §6's *stated* "Start baseline" figure (2436), which is the
pre-phase-1 measurement — a documentation lag, not a suite anomaly. See A14.

---

## Write perimeter

`git status --short` and `git diff --name-only` were both **empty** at session start
(HEAD `4b426f9`, and `0151775` after two coordinator doc commits landed mid-session,
neither of them mine). This session's full write perimeter is exactly one file:

```
docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/
  handoffs/reviewer/2026-08-20_phase2_projection_r0_handoff.md
```

No code, no plan edit, no intention edit, no tracker row, no graph change (0 archgraph
write calls; `archgraph_status` only). Scratch files were written outside the
repository. The suite run mutates nothing (`db_session` is rollback-scoped) and left no
tracked change.

---

## Appendix — NON-AUTHORITATIVE skeleton (discard; never hand to the implementer)

The paper artifacts this projection derived, kept only so a reviewer can check the
findings above. **This is not guidance and must not reach the implementer session** —
if it does, this projection has become a second planner.

```
_build_evaluated_status(ctx, task, item, evaluation, binding, *, live_seconds=None)
    if live_seconds is None:
        steps = SELECT TaskStep WHERE workspace_id, task_id=task.client_id, is_deleted=False
        live_seconds = await load_live_worked_seconds(ctx.session, ctx.workspace_id, steps, ctx.now)
    actual_seconds = sum(live_seconds.values())        # replaces the func.sum aggregate
    ... unchanged from actual_minutes onward ...

get_task_budget_status(ctx, *, live_seconds=None)      # threads to _build_evaluated_status

get_task_production_time(ctx)
    steps  = <today's load, moved above the status call>
    live   = await load_live_worked_seconds(session, ws, steps, ctx.now)
    status = await get_task_budget_status(ctx, live_seconds=live)
    rows   = [DivisionStep(client_id, state, working_section_id,
                           total_working_seconds=live[client_id],
                           sequence_order, working_section_name_snapshot,
                           typical_worker_seconds, is_deleted,
                           created_at, latest_state_record) for step in steps]
    typicals: typical_times_statement(ws, now=ctx.now)
    divide_production_budget(allowed, rows, typicals_by_section, section_by_id)

get_task_budget_allocations(ctx)
    today = ctx.now.date()                             # hoisted above the loop
    steps = <today's batch load, options unchanged>
    live  = await load_live_worked_seconds(session, ws, steps, ctx.now)   # ONE call
    typicals: typical_times_statement(ws, now=ctx.now)
    per task: rows = DivisionStep(..., total_working_seconds=live[cid],
                                  latest_state_record=_loaded_latest_state_record(step))
              actual_seconds = sum(live[s.client_id] for s in task_steps)

typical_times_statement(workspace_id, now=None)
    cutoff = (now if now is not None else datetime.now(timezone.utc)) - timedelta(days=90)

get_task_budget_status_worker : unchanged (inherits the fold)
```
