# Intention: Live Clock for Working-Time Economics (live worked-seconds basis for the present-tense read surfaces)

```
status: RESOLVED and PLAN-READY (rounds 4a–4f, 2026-08-20; latest fold **round 4f**)
        — mechanism-inventory gate **PASSED**. 0 owner cards open: D8–D9 ratified
        2026-08-20 (§10.3), folded at the coordinator's round-4a pass. D5–D6 ratified
        §10.2; D7 recorded round 3. Coordinator review of 2026-08-19 folded (all six
        findings, owner-dispositioned). Rounds 4b–4e fold phase-1 and plan-2-projection
        findings upstream (see the changelog); **4d corrects 4c** on HC-3A's failure
        site — read 4d as the standing statement. Next: phase 2 implement prompt
        (planning DONE; phase 1 APPROVED; plan 2 projection folded at 4e).
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-19, following the frontend handoff
             HANDOFF_TO_BACKEND_production_time_live_budget_clock_20260819.md
             (frontend repo, docs/handoff/to_backend/). The owner's directive,
             verbatim: "my intention is for the system to use this live clock
             centralized so that any client ( the frontend, or a scheduler ) can
             make correct decisions."
date: 2026-08-19 (rounds 1–2) · 2026-08-20 (round 3)
round: 3
```

---

## 1. Objective & hard constraints

Every read surface that judges the **present** of a task's working time — the
production-time widget, the budget-status screen (both faces), the worker step cards —
currently serves numbers that freeze the moment a worker starts and unfreeze only when
they stop. The verdict (`share_state`), the headline (`actual_worker_seconds`,
`remaining_worker_minutes`, `percent_consumed`) and every per-step `left_seconds` are
computed from **settled work only**, so they are structurally blind during exactly the
window in which a manager could intervene. The motivating payload (frontend handoff,
"the problem in one card"): a section 25 minutes into a 3m 6s allowance reporting
`worked_seconds: 0 · share_state: "on_track"`.

This pipeline makes the worked-seconds basis **live**: settled work plus the
concurrency-averaged share of any currently-open `working` interval, evaluated at
request time, computed by **one** backend function and consumed by every
present-tense surface — so the manager's widget, the worker's card, and any future
alerting scheduler can never disagree.

**Hard constraints:**

- **HC-1 — Nothing live is ever persisted.** No new tables, no migration, no persisted
  derived value, no new worker, no schema change. The `task_steps.total_working_seconds`
  column keeps its exact meaning — settled, concurrency-averaged, recomputed at
  transitions — and every persisted consumer of it (`item_cost_results`, daily
  analytics rollups, `total_cost_minor`) is untouched. `CALCULATION_VERSION`
  (`calculator.py:CALCULATION_VERSION`) is **not** bumped: its contract covers persisted formula
  outputs, and this feature persists nothing. The dividing line, binding on every
  surface decision in this document: **"what is happening" is live; "what happened"
  is settled.**
- **HC-2 — One crediting rule, one home.** The live share of an open interval is
  computed by the **existing settlement sweep** —
  `averaged_seconds_by_record` (`domain/analytics/concurrency.py`) through its IO
  wrapper `compute_record_contributions`
  (`services/queries/analytics/averaged_time.py`) — with `now` as the open intervals'
  end. Implementing a second averaging rule, or the naive `now − entered_at` elapsed,
  anywhere in this feature is a defect by definition: the naive form over-credits
  batch work and produces numbers that **snap back** at settlement (§3.3), which is
  the frontend's original defect rebuilt server-side where an alerting service would
  amplify it.
- **HC-3 — `now` is injected, never read inside domain logic.** Query services obtain
  `now` once per request at the service boundary and thread it through; the pure sweep
  already takes `now` as a parameter. Determinism becomes a *tested convention*
  instead of a structural fact — with a fixed `now`, identical database state yields a
  byte-identical payload (§9, T1). This answers the frontend's fourth open question:
  yes, it wants a test, and gets one.
- **HC-4 — Response shapes are frozen.** No new field, no removed field, no
  `server_now` / `as_of` timestamp (the frontend explicitly declined one — their
  smoothing anchors to time-of-receipt precisely to avoid client-vs-server clock
  comparison). Error cases, role gates, pagination, ordering, and socket events all
  unchanged. This entire pipeline is a **behaviour** change behind existing contracts.
- **HC-5 — All dependent fields of one surface move together, from one number.** Per
  step, one live worked-seconds figure is computed once per request; every field
  derived from worked seconds on that response — section rows, verdicts, headline
  minutes, percent, variance, and (on manager faces) the money derived from seconds —
  is computed from that same figure. A payload in which the headline and its rows
  disagree about the same instant is the named defect of the frontend's D16 escalation
  and is a gate failure here.
- **HC-6 — Money audience unchanged.** Live seconds flow to all four roles exactly
  where settled seconds flow today; monetary fields remain ADMIN/MANAGER only
  (`decision-money-audience-admin-manager-only`). Making a number live never widens
  who sees it.

### 1A. Hard-constraint contracts (round 4, mechanism-inventory gate)

**HC-1A — "never persisted" is a statement about ORM instances, not only about
tables.** All three surfaces hand SQLAlchemy `TaskStep` instances, loaded from the
request session, into `budget_division.py:divide_production_budget`
(`get_task_production_time.py:get_task_production_time` passes the eager-loaded rows
directly; `get_task_budget_allocations.py:get_task_budget_allocations` passes
`task_steps`). Assigning the live figure onto `step.total_working_seconds` marks the
instance dirty, and the next autoflush or commit on that session writes the live value
into the settled column — silently, with no test failing and no error raised. It would
also leak onto an out-of-scope surface:
`tasks/serializers.py:serialize_task_step` ships `total_working_seconds` straight off
the ORM attribute.

The contract, binding on every phase:

1. **No code in this pipeline assigns to `TaskStep.total_working_seconds`, ever.** The
   live figure is carried on a **separate row shape** handed to the allocator —
   `budget_division.py:DivisionStep` already exists for exactly this and carries every
   field the allocator reads (`client_id`, `state`, `working_section_id`,
   `total_working_seconds`, `sequence_order`, `working_section_name_snapshot`,
   `typical_worker_seconds`, `is_deleted`, `created_at`, `latest_state_record`) — or on
   an equivalent shape the planner registers. `_value` (`budget_division.py:_value`)
   already accepts objects and mappings alike, so the allocator needs no change (§4.3).
2. **The invariant is proven on the production code path** (charter rule 3): after
   serving each of the three endpoints against a task with an open working record, the
   `task_steps.total_working_seconds` column re-read from the database is unchanged.
   See §9A, T9.

**HC-3A — the clock contract.** "One `now` per request" is undefined until three
things are pinned:

- **Type.** `entered_at` / `exited_at` are `DateTime(timezone=True)`
  (`step_state_record.py:StepStateRecord`) and arrive **timezone-aware** from the
  driver. `now` is therefore `datetime.now(timezone.utc)` — aware, UTC.
  **The loader fails closed at its own boundary** (round 4d — supersedes BOTH the
  round-4 claim that a naive `now` raises inside `concurrency.py:_sweep` AND the
  round-4c claim that the rows never reach the sweep. Each named a failure site
  without probing it in both directions; the second was written in the act of
  correcting the first).

  **What is measured.** A naive `window_end` bind is not "normalized" — the driver
  reinterprets it in the **client host's local UTC offset at that date**, shifting
  the overlap-fetch boundary by that offset. What follows depends on the shift and
  the fixture's timestamps, so the un-guarded loader has **two** failure modes and
  which one appears is an environment fact, not a mechanism fact:
  - the shift moves `window_end` before the open record's `entered_at` ⇒ 0 rows ⇒
    the sweep never runs ⇒ a **silently vanished live term**, no error;
  - the row is still fetched ⇒ `concurrency.py:_sweep` **does** raise `TypeError`
    at `(end - interval.entered_at)`.
  Measured both ways on one host by varying only `now` (review r4), and measured
  across hosts by varying only `TZ` (coordinator, same fixture: guard deleted, the
  loader's naive-`now` test fails on a `+02:00` host and **passes** under `TZ=UTC`).

  **The contract** is therefore an explicit guard at the top of
  `live_worked_seconds.py:load_live_worked_seconds` — rule-6 load-bearing, not
  defensive decoration, because one of its two un-guarded modes is silent. **The
  guard must be distinguishable from the failure it pre-empts**: it raises the same
  exception type at a lower frame, so a type-only assertion cannot tell them apart
  and the safety test is decoration on any host where the sweep raises (charter
  rule 11). The guard therefore carries a message naming its own boundary, and its
  named mutation (delete the guard, definition site) must redden the loader's
  naive-`now` test **on every host** — proven by running that mutation under at
  least two `TZ` settings, one of them `UTC`.
- **Injection site, given the router's fixed signature.** `run_service.py:run_service`
  calls every query service as `fn(ctx)`, and `context.py:ServiceContext` carries the
  standing instruction "Never add boolean flags or config values here". So `now` is
  either registered as a `ServiceContext` field by the planner (request data, not
  config — the planner records which reading it takes in the master plan §4) or read at
  the top of each of the three entry services and threaded down as an explicit
  parameter. Under the second reading `get_task_budget_status(ctx, ...)` must keep a
  call-compatible signature for its four callers (master plan §6), which means a
  default — and **a default that silently reads the clock is the defect T1 exists to
  catch** (§9A, T1).
- **Scope — what "one clock read" covers.** It is not true today that the
  item-economics query family reads no clock (§2.3A). Under HC-3 the residual read
  inside E-A (`get_task_budget_allocations.py:get_task_budget_allocations` calls
  `today_utc()` **inside the per-task loop**, so up to 50 independent clock reads per
  request) comes under the injected `now` as `now.date()`. This is behaviour-preserving
  except at a UTC date rollover mid-request, where it replaces an inconsistency with a
  consistent answer, and it is what makes T1 decidable for E-A at all.
  **Round 4b — a second residual read, found by projection r0 (§2.3A third
  correction):** `get_working_section_typical_times.py:typical_times_statement`
  derives its window cutoff from `datetime.now(timezone.utc)` on the E-P and E-A
  request paths. Resolution: the statement gains an **additive** `now` parameter
  whose default preserves the existing clock read — the compatibility shim for its
  callers outside this pipeline (the working-sections surface and the price-scenario
  typical block, both settled-basis and out of scope) — and **E-P and E-A pass
  `ctx.now`**, guarded per call site by a stub row (phase 2): with the module's clock
  stubbed, serving E-P/E-A performs zero clock reads there; dropping the `now`
  argument at either call site is the named mutation that reddens it. The defaulted
  clock read survives only where this pipeline's determinism contract does not reach;
  within the three surfaces, one request is one `now`, cutoff included.

  **Round 4e — the second instance of E-A's own construct, found by plan 2's projection
  r0 (§2.3A fourth correction).** `today_utc()` reaches `resolve_economics_selection`
  from **two** places on this pipeline's surfaces:
  `get_task_budget_allocations.py:get_task_budget_allocations` (E-A, brought under
  `ctx.now.date()` by plan 2) and
  `_common.py:_load_preview_inputs` (E-B both faces, and E-P and the price scenario
  through composition, on the no-committed-evaluation branch). Both come under the
  injected `now` as `now.date()`, for the same reason and with the same
  behaviour-preserving character: `_load_preview_inputs` gains `now: datetime | None =
  None` whose default preserves the existing read for its command-side callers, and the
  two query services pass `ctx.now`. Leaving only one of the two converted is the split
  this pipeline exists to remove, reintroduced through the configuration date — and it
  would be the one remaining counterexample to the sentence above. Guarded per call site
  by a stub row on the same shape as round 4b's (plan 2 C12).

---

## 2. Grounding — what exists today (verified 2026-08-19, all paths read this session)

### 2.1 The ledger: state records, and what "settled" means

`step_state_records` (`models/tables/tasks/step_state_record.py`): `state`,
`entered_at`, `exited_at` (**nullable — NULL means running now**),
`recorded_time_marked_wrong`, `credited_user_id` (attribution is
`COALESCE(credited_user_id, created_by_id)`), `is_deleted`. Exactly one open
record per step at a time — the transition core closes the previous record before
opening the next (`latest_state_record` is singular).

`task_steps.total_working_seconds` is recomputed at each transition by
`_recompute_step_time_totals`
(`process_step_transition.py:_recompute_step_time_totals`): it gathers the
step's records in `TIME_BEARING_STATES = {WORKING, PAUSED}`
(`task_steps/constants.py:TIME_BEARING_STATES`), runs each credited user's records through
the sweep, and **sums only closed contributions** (`c.is_open` rows are skipped by that function's
per-record filter). The column is therefore settled-only *by that filter*, per state:
`int(round(Σ closed working shares))`.

### 2.2 The crediting rule: the concurrency sweep

`averaged_seconds_by_record(intervals, now)`
(`analytics/concurrency.py:averaged_seconds_by_record`, sweep in `:_sweep`) — pure, deterministic:

- Intervals are grouped **per worker, per state**. Working intervals divide only
  among working intervals of the same worker.
- **Batchable** intervals (`TaskStep.allows_batch_working`) split each timeline
  segment by the number of that worker's concurrently-open batchable intervals;
  **non-batch** intervals earn full duration and never join a divisor.
- `marked_wrong` intervals earn nothing and reduce nothing.
- **Open intervals use `now` as their end and still count toward concurrency** — the
  function already does, verbatim from its docstring, exactly what this pipeline
  needs.
- The invariant the rule protects: one worker-minute is one credited minute, however
  many steps it is spread across; shares sum back to wall-clock time.

`compute_record_contributions(session, workspace_id, user_id, window_start,
window_end, now)` (`analytics/averaged_time.py:compute_record_contributions`) is the IO
wrapper: fetches one worker's time-bearing records overlapping a window, runs the
sweep, returns per-record `RecordContribution` rows carrying `seconds`, `is_open`,
`step_id`, bucketed `state`, and `marked_wrong`.

### 2.3 The precedent: live `now` already exists in a read path

`get_worker_daily_step_breakdown` (`worker_stats/get_worker_daily_step_breakdown.py:get_worker_daily_step_breakdown`) — a
query-layer read endpoint — already calls `compute_record_contributions` with
`now = datetime.now(timezone.utc)`. The "no clock in the read layer" property the
frontend worried about is a property of the **item-economics query family**, not of
the read layer as a whole. This pipeline extends an existing, shipped pattern; it does
not breach a covenant. (`list_workers_totals.py` is the second precedent.)

### 2.3A The absence claim, corrected and scoped (round 4)

The paragraph above is **false as stated**, and the correction strengthens its
conclusion rather than weakening it.

- **Search run:** `grep -rnE "datetime\.now|utcnow|func\.now|today_utc|date\.today|time\.time\(|timezone\.utc"` over
  `app/beyo_manager/services/queries/item_economics/` — the term set deliberately
  includes `today_utc`, the wrapper that defeated this project family's earlier grep
  (master plan §5).
- **Result:** two hits inside the family, one of them inside a surface this pipeline
  changes. `get_task_budget_allocations.py:get_task_budget_allocations` calls
  `today_utc()`; `get_economics_configuration_status.py` calls it too.
  `_common.py:today_utc` is `datetime.now(timezone.utc).date()`.
- **Therefore:** the item-economics query family **already reads the wall clock**,
  inside E-A itself. There is no covenant to breach and never was. The consequence
  that matters is HC-3A's third bullet, not the framing.

**Third correction (round 4b, projection r0 — the scope rule biting again, this time
on the corrected claim itself).** The search above ran over
`services/queries/item_economics/` and missed a clock read on a **callee** module
sitting on two of the three surfaces' request paths:
`get_working_section_typical_times.py:typical_times_statement` (in
`services/queries/working_sections/`) computes its qualifying cutoff as
`datetime.now(timezone.utc) − TYPICAL_WINDOW_DAYS` at statement build, and both
`sample_count` and `typical_worker_seconds` are filtered by
`latest_closed_at >= cutoff`. Its production callers: E-P, E-A, the price-scenario
typical block, and the working-sections surface itself. The term set was right; the
scope excluded a callee module — record the scope as the call graph, not the
directory. Resolution in HC-3A's scope bullet below; T1's byte-identity for E-P and
E-A rests on it.

**Fourth correction (round 4e, projection r0 on plan 2 — the scope rule again, one
package further out).** The corrected search of round 4b covered the query packages and
the typicals callee. It did not enter
`services/commands/item_economics/_common.py`, which
`get_task_budget_status.py:get_task_budget_status` and
`get_task_budget_status_worker.py:get_task_budget_status_worker` import from:
`_common.py:_load_preview_inputs` calls `_common.py:today_utc` and hands the result to
`configuration.py:resolve_economics_selection`. That is a wall-clock read on the E-B,
E-P and price-scenario request paths, on the no-committed-evaluation branch. It is the
**same construct** as E-A's `today_utc()` — the instance §2.3A named and the class it
did not. Verified at source by the coordinator before folding (the import at
`get_task_budget_status.py:29`, the call at `_common.py:203`). Consequence had it stayed
unnamed: after phase 2, E-A would resolve its economics selection from `ctx.now.date()`
while E-B/E-P resolved theirs from a fresh clock read, so a UTC date rollover mid-request
could select different basis/cost-model versions and report a different `status` for the
same task — on the branch where `actual_worker_seconds` is `None`, which HC-5's own
tests cannot see. **Fifth instance of the verification-scope rule in this family**
(directory → term set → suite → call graph → the command package a query service
imports from).

Second correction, same paragraph: the sweep's IO wrapper has **five** production
callers, not two — `get_worker_daily_step_breakdown.py`, `list_workers_totals.py`,
`estimation_sample.py:load_trusted_step_duration_sample`,
`reconcile_user_time.py`, and `process_step_transition.py:_recompute_step_time_totals`.
Three of the five are query-layer reads. `estimation_sample` is the closest existing
analogue to M1: it consumes `RecordContribution` rows and filters them by
`is_open` / `step_is_deleted` / `step_is_completed` / `marked_wrong`, which is the same
filtering shape M1 needs with the `is_open` polarity inverted.

### 2.4 The consuming surfaces (the freeze, per endpoint)

All three compute worked time from the settled column and only from it:

- **E-P** `GET /tasks/{id}/production-time`
  (`get_task_production_time.py:get_task_production_time`): composes `get_task_budget_status` with the
  task's steps and `divide_production_budget`; section `worked_seconds` is
  `Σ total_working_seconds` per section (`budget_division.py`,
  `group_steps_by_section`), verdict `share_state = "over_share" if worked > allowance`.
- **E-B** `GET /tasks/{id}/budget-status`: manager face and the independent
  worker/seller face (`get_task_budget_status_worker.py`, A7) both delegate the
  evaluated computation to the shared `_build_evaluated_status`
  (`get_task_budget_status.py:_build_evaluated_status`), whose
  `actual_seconds = SUM(total_working_seconds)` (in `_build_evaluated_status`) feeds Q4 minutes,
  remaining, percent, variance, and — manager only — `consumed_cost_minor` /
  `variance_cost_minor` through the pure calculator.
- **E-A** `GET /tasks/budget-allocations` (`get_task_budget_allocations.py:get_task_budget_allocations`):
  batch-loads steps (which carry the settled column) and calls
  `divide_production_budget` per task — the worker step cards' source.

The frontend's own handoff traced the six fields that must move together on E-P:
section `worked/left/share_state` and budget `actual_worker_seconds/minutes`,
`remaining_worker_minutes`, `percent_consumed`. §4 generalizes that list per surface.

### 2.5 The settled consumers that must NOT move

- `item_cost_results` — durable end-of-episode record, recomputed by the analytics
  worker at READY/terminal from settled data (`process_step_transition.py:handle_process_step_transition`).
- Daily analytics rollups (`reconcile_user_time.py` family) — settled at transitions.
- `task_steps.total_cost_minor` — salary-priced, persisted at settlement
  (`process_step_transition.py:_recompute_step_time_totals`); worker-compensation domain, out of scope.
- The `final` block of E-P (`division_serializers.py`,
  `_serialize_production_time_final`) — a frozen result record by definition. Its
  `percent_consumed` key is wired to the request's status percent today; that wiring
  is left untouched (§5.3).

This answers the frontend's third open question ("does anything else consume these on
a settled basis?"): yes — the four above — and none of them reads through the
endpoints this pipeline changes; they read persisted columns this pipeline never
writes.

### 2.5A The settled-consumer inventory, made total (round 4)

The list above is not total, and §2.5's answer to the frontend's third question is
therefore incomplete. **Search run:** `grep -rn "total_working_seconds"` over
`app/beyo_manager/`, excluding the model definitions; every hit classified. The
complete consumer set of `TaskStep.total_working_seconds`, with what each does under
M1:

| # | Site (`path:symbol`) | Reads via | Under M1 |
|---|---|---|---|
| 1 | `process_item_cost_result.py` — `SUM(total_working_seconds)` writing `item_cost_results` | SQL | settled, untouched (§2.5 row 1) |
| 2 | `reconcile_user_time.py` family — daily rollups | SQL over the daily tables, not the step column | settled, untouched (§2.5 row 2) |
| 3 | `process_step_transition.py:_recompute_step_time_totals` — writes the column and `total_cost_minor` | ORM write | settled, untouched (§2.5 row 3) |
| 4 | `division_serializers.py:_serialize_production_time_final` — the E-P `final` block | dict | **partly live** — see §4.1A |
| 5 | **`get_working_section_typical_times.py:typical_times_statement`** — `SUM(TaskStep.total_working_seconds)` feeding `typicals_by_section` | SQL | **must stay settled** — see §4.3A |
| 6 | **`get_worker_clock_out_analytics.py`** — `func.sum(TaskStep.total_working_seconds)` | SQL | settled, untouched; out of scope |
| 7 | **`tasks/serializers.py:serialize_task_step`** — ships the column on the task/step read surface | ORM attribute | settled, untouched **only if HC-1A holds** |
| 8 | `task_steps/aggregate_metrics.py:increment_step_time_metrics` | ORM write | **no callers** (stated in its own docstring); inert |

Rows 5–8 are new to this document. Rows 5 and 7 are load-bearing: row 5 is a third
worked-seconds→allowance path (§4.3A), row 7 is the blast radius of an ORM mutation
(HC-1A). The corrected list is what ships in the closeout handoff, not the list of
four.

### 2.6 In-flight neighbour

The `simple_valuation_editor` pipeline (intention resolved 2026-08-19) added
`get_task_price_scenario.py` / `price_scenario.py` in the same query family. Its
payload deliberately carries no progress block (its D5 ratified gross-of-progress),
so it does not consume the live figure in v1 — but as of its phase-2 implement round
(checkpoint `48705b3`, the same day this intention was shaped) the perimeters are
**not disjoint**: `get_task_price_scenario` resolves its task through
`get_task_budget_status` — imported and called inside
`get_task_price_scenario.py:get_task_price_scenario` — the
service whose `_build_evaluated_status` this pipeline makes live. Three consequences
the planner owns (coordinator review 2026-08-19, finding 1):

- changing `_build_evaluated_status` now changes a dependency of a **shipped**
  endpoint from another pipeline;
- any price-scenario test assertion that transitively depends on budget-status-derived
  numbers becomes time-dependent once the live basis lands — T1's fixed-`now`
  discipline extends to that suite;
- the coupling is structural, not semantic: the price-scenario payload consumes only
  `status`, `item_binding` and the committed evaluation, none of them worked-derived.

This pipeline adds **no route and no field** (HC-4), so it touches neither the router
nor the route-mirror tests. The round-1 claim of a router/mirror overlap between the
two pipelines was wrong and is withdrawn (round 3).

---

## 3. Mechanism contract M1 — the live worked-seconds figure

### 3.1 Definition

For a task's non-deleted step `s`, at request time `now`:

```
live_worked_seconds(s, now) =
    s.total_working_seconds                    -- the settled column, unchanged
  + open_working_share(s, now)                 -- 0 when the step has no open record

open_working_share(s, now) =
    0   if s has no state record with exited_at IS NULL
    0   if the open record's state is not WORKING       (a paused step accrues nothing)
    0   if the open record is marked wrong (record OR step flag — same disjunction
        the sweep applies) or is_deleted
    otherwise: the open record's concurrency-averaged share, i.e. the
        RecordContribution.seconds of that record from
        compute_record_contributions(session, workspace_id, u, W_start, now, now)
        where u       = credited_user_id or created_by_id of the open record
                        -- settlement's own attribution form (round 4c, review N2):
                        -- Python `or`, matching _recompute_step_time_totals; the
                        -- wrapper's SQL filter is COALESCE, and the two differ only
                        -- on "" — which no shipped writer produces. Matching
                        -- settlement is what the §3.3 parity requires.
              W_start = min(entered_at) over u's open working records − 1 day
                        -- ONE sweep per user serves all of u's open records (§3.4);
                        -- anchoring on any LATER open record would drop closed
                        -- records that overlapped an earlier one's first segments —
                        -- §3.2 case 4 reintroduced through the window instead of
                        -- the divisor (coordinator finding 3)
        filtered to is_open AND state == "working" AND record_id == the open record
```

rounded `int(round(·))` per step — the same rounding locus settlement applies to its
per-state sums.

### 3.1A M1 contract-grade definition (round 4)

§3.1 is a correct sketch. Everything below is what an implementer would otherwise
resolve silently in code. All of it verified at source at `a0aaacc`.

**A. Output type and rounding locus — pinned.**

```
live_worked_seconds(s, now) : int
  = s.total_working_seconds                       # int, already settled-rounded
  + int(round(open_working_share(s, now)))        # round the SHARE, then add
```

The rounding is applied to **the open share alone**, never to the sum. Two reasons,
both load-bearing:

- It is what makes §4.1's "two resolutions are arithmetically identical" **true**.
  Since `settled_s` and `int(round(open_s))` are both integers,
  `Σ_s (settled_s + round(open_s)) ≡ (Σ_s settled_s) + Σ_s round(open_s)` — the
  per-step fold and the SQL-sum-plus-live-term give the same task figure, exactly. Under
  the other locus (`int(round(settled_s + open_s))`) they do **not**: Python's `round`
  is banker's rounding, so `round(0 + 0.5) = 0` while `round(1 + 0.5) = 2`, and the two
  resolutions diverge on any share landing on an exact half-second — which a two-way
  batch split of an odd second count produces on demand. See §4.1A.
- `int(round(·))` means **Python's built-in `round`, half-to-even**, matching
  settlement's `int(round(totals[state][0]))`
  (`process_step_transition.py:_recompute_step_time_totals`). Not
  `Decimal.quantize(ROUND_HALF_UP)`, not `math.floor(x + 0.5)`. The difference is one
  second at exact halves, which is precisely the width of the §3.3 bound.

**B. The output is an `int`, and the two consumers punish a float differently.**
`budget_division.py:group_steps_by_section`, `:_step_result`, `:_section_step_allowances`
and `:divide_production_budget` all coerce with `int(_value(step, "total_working_seconds", 0) or 0)`
— **`int()` truncates**, so a float `1799.6` becomes `1799`, silently, in four places.
`calculator.py:_require_seconds` uses `_guard_type(..., exact=True)`, so the same float
raises a `ValidationError` on the money path. A loader returning floats therefore
produces a payload whose rows are truncated and whose headline is a 500. The loader
returns `int`.

**C. Input types, as the ORM actually delivers them.**

| value | type at the boundary | note |
|---|---|---|
| `entered_at`, `exited_at` | `datetime`, **tz-aware UTC** | `DateTime(timezone=True)`; `exited_at` NULL ⇒ open |
| `now` | `datetime`, tz-aware UTC | HC-3A |
| `state` on a `RecordContribution` | `str`, the **bucket key** | `averaged_time.py:_BUCKET_STATE`, not the raw column; `"working"`, `"paused"`, `"ended_shift"` |
| `credited_user_id`, `created_by_id` | `str | None` | both nullable |
| `RecordContribution.seconds` | `float` | `0.0` for any record absent from the sweep result — `averaged_time.py:compute_record_contributions` uses `.get(record_id, 0.0)`, so a missing key is never a `KeyError` |

The `state == "working"` filter in §3.1 is correct and cannot be replaced by the raw
column: the wrapper emits the derived bucket. It is also, for a WORKING record,
redundant — `_BUCKET_STATE`'s `ended_shift` branch requires `PAUSED` — and is kept as a
type-level assertion.

**D. The zero-case enumeration is total over the real state vocabulary, and the
ranking is inert.** `TaskStepStateEnum` (`task_steps/enums.py:TaskStepStateEnum`) has
eight members: `pending, working, paused, blocked, completed, skipped, failed,
cancelled`. §3.1's clause 2 ("state is not WORKING") covers the other seven in one
decidable predicate; every clause yields the same value (`0`), so no precedence between
the clauses can change an outcome and the "ranked rule" reading is unnecessary. Two
clauses are additionally **unreachable or redundant today**, recorded so no one reads
them as live paths:

- *record `is_deleted`* — `compute_record_contributions` already excludes deleted
  records in its `WHERE`, and **no shipped command ever sets
  `StepStateRecord.is_deleted = True`**. Verified: the only writer is
  `reset/phases/delete_step_state_records.py`, which issues a **hard** `DELETE` for a
  whole workspace. The clause is defense-in-depth (§6A).
- *record `marked_wrong`* — `averaged_seconds_by_record` drops flagged intervals before
  the sweep, so the record earns `0.0` through the wrapper anyway.

Three further zero-cases §3.1 does not enumerate, each decidable, each reachable:

- **`entered_at >= now`** (clock skew, or a record written with a future stamp): the
  sweep skips it (`duration <= 0: continue`) and it neither earns nor divides. Share
  `0`.
- **Both `credited_user_id` and `created_by_id` NULL**: `COALESCE(...) == u` matches no
  row, the sweep never sees the record, share `0`. Settlement skips the same record
  (`if uid is None: continue`), so the two agree.
- **`exited_at == entered_at`** (permitted by
  `ck_step_state_records_exited_after_entered`): duration `0`, share `0`. Not an open
  record, listed for completeness of the population.

**E. "The open record" is singular by database guarantee, not by convention.**
`step_state_record.py:StepStateRecord.__table_args__` carries
`uix_step_state_records_active` — `UNIQUE (workspace_id, step_id) WHERE exited_at IS
NULL`. It does **not** exclude soft-deleted rows, which is what makes the singularity
unconditional: at most one row per step has `exited_at IS NULL`, deleted or not. §2.1's
claim is therefore stronger than "the transition core closes the previous record
first". Caveat for the planner: the index is declared `postgresql_where`, so the
guarantee is Postgres-only; the suite runs against the configured Postgres
(`tests/conftest.py:initialize_database` → `init_db()`), so tests inherit it.

**F. A deleted *step*'s records still divide.** `compute_record_contributions` filters
`StepStateRecord.is_deleted` but **not** `TaskStep.is_deleted` — it returns
`step_is_deleted` for the caller to filter. So a deleted step's open batch record still
counts toward its worker's divisor and reduces a live step's share. This is what
settlement does too (`_recompute_step_time_totals` filters only by `step_id`), so M1
and settlement agree and the §3.3 bound is unaffected. It is recorded because it looks
like a bug and is not: "fixing" it would break parity in the direction the bound cannot
detect. See §9A, T10.

### 3.2 Why the share, not the elapsed — the four ways `now − entered_at` is wrong

Recorded in full so the naive form is never "simplified" back in:

1. **Two workers, one section.** Jonas and Marta each sand one chair, 9:00–9:30. Real
   work is 60 minutes. Dividing by open-record count per section yields 30; the
   correct rule divides per *worker* (divisor 1 each) and yields 60. Concurrency is a
   property of one person's attention, never of a section's open-record count.
2. **The divisor changes over time.** Jonas opens batch step A alone at 9:00, adds
   batch step B at 9:20; at 9:30 A has earned 20 + 10/2 = 25m and B 5m. A single
   division by the current count gives A 15m — his first 20 undivided minutes vanish.
   Only a segment-by-segment sweep represents a divisor that moves.
3. **The divisor can live on another task.** Jonas batch-works a chair (task 1) and a
   stool (task 2) simultaneously. Task 1's records alone show one open record; the
   truth is a divisor of 2. This is why the fetch is per **user** across the window,
   never per task — and why M1 delegates to `compute_record_contributions` instead of
   querying the task's own records.
4. **Closed records still shape the open one's past.** Jonas opens A and B at 9:00,
   closes B at 9:20, keeps A. At 9:30 A's correct share is 20/2 + 10 = 20m, not 30m.
   The open record's early segments were shared with a record that no longer appears
   in any "currently open" query — hence the window fetch back to `entered_at − 1 day`
   (the same buffer settlement uses, `process_step_transition.py:_recompute_step_time_totals` (the `timedelta(days=1)` buffer)).

Each case is an enumerated test row (§9, T3).

**Window note (round 3, owner context).** Operationally, an open working record today
cannot be older than the previous midnight UTC: every clock source — HTTP clock-out,
Connecteam, and the overnight sweep
(`services/tasks/users/auto_clock_out_open_shifts.py`) — closes open working records
through the same transition (`_clock_worker_shift.py`, the `SHIFT_ENDED` path), the
owner-built safeguard for forgotten steps; the company does not work nights, and
logout auto-closes as well. With the 1-day buffer, that makes the anchor choice
unreachable in practice. The `min(entered_at)` anchor is specified anyway: the
document must give one instruction, and correctness must not hang on a scheduler in
another domain (charter rule 11 — safety binds at the boundary). If the company ever
runs a night shift, or the sweep misses a night, nothing here needs revisiting.

### 3.2A The four cases, checked by hand; and the window rule, derived (round 4)

**Worked-example audit.** Every number in §3.2 was recomputed against
`concurrency.py:_sweep` as coded — segment boundaries from
`sorted({start, end})`, membership `start <= left and end >= right`, `share =
segment / k`. All four follow their own rule; none is decoration.

| case | contract arithmetic, re-derived | naive form | verdict |
|---|---|---|---|
| 1 two workers, one section | two `compute_record_contributions` calls (one per `user_id`), each a single interval, `k = 1` ⇒ 1800 s + 1800 s = **60 min** | divide by the section's open-record count ⇒ 900 + 900 = 30 min | follows |
| 2 divisor changes mid-interval | points `{9:00, 9:20, 9:30}`; `[9:00,9:20]` k=1 ⇒ A +1200; `[9:20,9:30]` k=2 ⇒ A +300, B +300 ⇒ A = **1500 s (25 m)**, B = 300 s (5 m) | one division by the current count ⇒ A = 900 s (15 m) | follows |
| 3 divisor on another task | wrapper filters by `user_id` with **no task predicate**, so both intervals enter one sweep ⇒ k=2 ⇒ each **half** | task-scoped fetch sees k=1 ⇒ full | follows |
| 4 closed record shapes the open one | points `{9:00, 9:20, 9:30}`; `[9:00,9:20]` k=2 ⇒ A +600, B +600; `[9:20,9:30]` k=1 ⇒ A +600 ⇒ A = **1200 s (20 m)** | `now − entered_at` ⇒ 1800 s (30 m) | follows |

In cases 2 and 4 the shares sum back to wall-clock (1500 + 300 = 1800; 1200 + 600 =
1800), which is the invariant §2.2 names.

**Missing precondition, now stated: cases 2, 3 and 4 require `allows_batch_working =
True` on every participating step.** `_sweep` divides only among **batchable**
intervals; a non-batch interval "earns full duration and is excluded from the divisor"
(`concurrency.py:averaged_seconds_by_record`). Case 4's prose is the one that never
says "batch" (cases 2 and 3 do), and a T3 fixture built from non-batch steps would
compute A = 1800 s and the row would fail — or worse, ship with the wrong expected
number. Case 1 is batchability-agnostic (`k = 1` either way) and stays correct.

**The window rule, derived rather than borrowed.** §3.1 anchors `W_start` at
`min(entered_at) − 1 day` over the user's open working records, and §3.2 justifies the
buffer by pointing at settlement's. That is a *borrowed* argument: settlement re-sweeps
a whole closed population and needs the day on both sides
(`_recompute_step_time_totals` uses `start − buffer, end + buffer`). M1 reads exactly
one record's share. The transferable argument is stronger and independent:

> The wrapper's overlap predicate is `entered_at < window_end AND (exited_at IS NULL OR
> exited_at > window_start)` (`averaged_time.py:compute_record_contributions`). Let
> `T₀ = min(entered_at)` over the user's open working records. Every record that can
> alter the open record's share must overlap `[T₀, now]`, hence has `exited_at > T₀` or
> is itself open. Open records are fetched unconditionally by the `IS NULL` branch. So
> **`W_start ≤ T₀` is sufficient**, and it is also **necessary**: any `W_start > T₀`
> drops records exiting in `(T₀, W_start]`, which understates the divisor over the open
> record's early segments and over-credits — §3.2 case 4 reintroduced through the
> window, exactly as coordinator finding 3 said.

Two consequences the document did not carry:

1. `W_start = T₀ − 1 day` is sufficient with a full day of slack. The buffer is not
   load-bearing for the live case; the **anchor** is. Records fetched but not
   overlapping `[T₀, now]` cannot change the open record's share — the sweep credits per
   segment, and a non-overlapping record shares no segment with it — so a generous
   window is harmless as well as unnecessary.
2. `window_end = now` with a **strict** `entered_at < window_end` means a record whose
   `entered_at` equals `now` to the microsecond is not fetched. Its duration would be
   `0` anyway (§3.1A D). No special case is needed; it is recorded so nobody adds one.

### 3.3 The no-snap invariant

Because M1 and settlement are the **same function** evaluated at two moments, closing
a record must not move the number — it moves the share from the live term into the
settled column:

```
| live_worked_seconds(s, t⁻)  −  total_working_seconds(s) after the transition
  that closes the record at t |   ≤   1 second per credited user
```

The ≤ 1s slack is rounding locus only: settlement rounds the sum of all closed shares
once (`int(round(Σ))`, where `_recompute_step_time_totals` writes the step fields), M1 rounds the settled column and the open share
separately. Nothing else may contribute drift — a violation beyond the slack means the
live computation and settlement have diverged, which is exactly the defect HC-2
exists to prevent. Tested as T2, the load-bearing test of this pipeline. (This is
also the operational meaning of the taxi rule: the meter and the receipt use one
tariff, so the receipt never surprises.)

### 3.3A The bound, derived; and the drift sources rounding does not cover (round 4)

§3.3 asserts a bound and asserts that rounding is its only source. The first is nearly
right and stated with the wrong denominator; the second is **false**.

**A. The derivation.** Let `P` be the exact float sum of step `s`'s closed working
shares before the close, and `s_R` the open record's exact share.

- Settlement writes `int(round(P + s_R))` — **one** rounding of one float sum, across
  **all** credited users' records for that step
  (`process_step_transition.py:_recompute_step_time_totals` accumulates
  `totals["working"][0]` over every contribution before rounding once).
- M1 serves `int(round(P)) + int(round(s_R))` — **two** roundings (§3.1A A).
- Each rounding error lies in `[−0.5, +0.5]`, so the real difference lies in
  `(−1.5, +1.5)`; both quantities are integers, so the difference is an integer with
  magnitude **≤ 1**. Attained: `P = 1.5, s_R = 1.5` ⇒ `2 + 2 = 4` vs `round(3.0) = 3`.

**B. The denominator is wrong.** "≤ 1 second **per credited user**" cannot be right:
a step has **at most one** open record (§3.1A E), hence at most one credited user
contributing an open share, while the settled column is rounded once no matter how many
users contributed closed records. Per step the bound is flatly **≤ 1 s**. The
denominator only appears on the aggregates, and it is not users:

> Per step: **≤ 1 s.** On any aggregate over steps (E-B's `actual_worker_seconds`,
> E-P's section and task figures, E-A's headline): **≤ 1 s per step holding an open
> working record**, since each per-step term contributes its own ≤ 1 s and the
> aggregate adds already-rounded integers (§3.1A A, §4.1A).

Concretely, the wrong denominator is falsifiable: one worker batch-working six steps of
one task holds six open records — six credited-user-1 steps — and the task figure can
sit 6 s from the post-settlement sum. "≤ 1 s per credited user" claims 1.

**C. Rounding is not the only drift source.** Three others, all verified at source. The
first is the significant one.

1. **Settlement is asynchronous, so there is a window in which the number falls and
   recovers.** The transition closes the record *synchronously*
   (`_step_transition_core.py:_apply_step_transition` sets `closing_record.exited_at =
   now`) and only **enqueues** the recompute — `create_instant_task(...,
   PROCESS_STEP_TRANSITION)`, routed to `queue:analytics`
   (`task_router.py`), executed later by
   `process_step_transition.py:handle_process_step_transition`. The core says so in its
   own comment: "Time totals recomputed async by the analytics worker."
   Between commit and worker, the open record is **closed** (so M1's live term is `0`)
   and the column is **stale** (so the settled term still excludes it). The live figure
   therefore **drops by the whole just-worked share and then jumps back**.
   Magnitude: the entire interval — 25 minutes for the motivating card, not 1 second.
   Duration: normally sub-second (the router is LISTEN/NOTIFY-driven), up to
   `FALLBACK_POLL_SECONDS = 30` (`task_router.py`) plus processing if a notify is
   dropped, and **unbounded** if the task exhausts `max_try = 3`
   (`task_factory.py:create_instant_task`) — in which case the column is only repaired
   by the next transition on that step, since the recompute is an absolute SET from
   records rather than an increment.
   This is a **new** behaviour: today the number is settled-only, so the same lag shows
   as a delayed *increase*. Under M1 it becomes a visible *decrease*. It is not one of
   §5.4's original two decrease modes. **D8 (owner, 2026-08-20) ships it as-is and
   discloses it**: §6A C carries the client rule, §5.4 carries the handoff obligation
   as the third decrease mode, and T11 pins the behaviour.
2. **`mark_step_time_inaccurate` never recomputes the column.**
   `mark_step_time_inaccurate.py:mark_step_time_inaccurate` sets the record flag and the
   **step** flag and dispatches `task:updated` — it enqueues no
   `PROCESS_STEP_TRANSITION`. So the live term drops to `0` immediately (the step flag
   makes `marked_wrong` true for every record of the step in
   `averaged_time.py:compute_record_contributions`, `row.marked_wrong or
   row.step_marked_wrong`) while the settled column keeps its now-disowned value until
   the next transition on that step. Live and settled diverge by the **whole settled
   column**, indefinitely. §6A.
3. **`remove_task_step` closes the open record without enqueuing a recompute**
   (`remove_task_step.py` sets `record.exited_at = now`, `step.state = SKIPPED`,
   `step.is_deleted = True`). No observable drift, because the step leaves every payload
   at the same instant — recorded so the absence of an outbox task there is not read as
   a bug to fix.

**D. What §3.3 may correctly claim.** The parity holds **between the live figure and
the column once settlement has run**, and the rounding-locus argument is the whole
story *for that comparison*. It does not hold at the instant of the transition, and it
does not survive a disowning event. The sentence "Nothing else may contribute drift"
is replaced by this enumeration; T2 tests the eventual parity (it runs
`_recompute_step_time_totals` itself), and a new row tests the transition-instant
behaviour so the gap is observed rather than assumed (§9A, T11).

### 3.4 Cost model

The settled term is a stored column — no history is ever re-swept on read. The live
term costs, per request: one query for open records across the task's (or, for E-A,
the batch's) steps; then one `compute_record_contributions` call per **distinct
credited user holding an open working record** — typically zero (idle task: zero
extra queries beyond the open-record probe) or one, each over a window of hours, not
history. Work is proportional to *current activity*, never to record accumulation.
E-A's 50-task bound adds only the same per-active-worker sweeps; a worker's sweep is
shared across all their steps in the batch, not repeated per task.

**The stated ceiling (round 3, coordinator finding 6):** sweeps per request ≤ distinct
active workers holding an open working record in the batch, itself bounded by the
endpoint's 50-task cap; each sweep's window is bounded to under ~2 days by the
overnight close (§3.2 window note) plus the 1-day buffer. The worst request is
therefore ≤ 50 small, bounded sweeps after one batched open-record probe. The plan
records one measured worst case at that ceiling (T8); if the measurement embarrasses
the design, the remedy is restructuring the fetch — never a cache (HC-1).

### 3.4A The cost contract, derived (round 4)

**A. What one sweep call actually costs.** `compute_record_contributions` issues **one**
SQL statement and then runs **two** in-memory sweeps —
`averaged_seconds_by_record` and `wasted_seconds_by_record`
(`averaged_time.py:compute_record_contributions`). M1 never reads `wasted_seconds`, but
HC-2 forbids forking the function to avoid the second sweep, so the second sweep is a
knowingly-paid cost, not an oversight. Query-count assertions (T8) count the one
statement; any wall-clock reasoning must count two sweeps.

**B. The stated ceiling's denominator is wrong.** §3.4 bounds the number of sweeps by
"the endpoint's 50-task cap". The 50-task cap
(`get_task_budget_allocations.py:_MAX_TASK_IDS`) bounds **tasks**, not workers. A task
carries an unbounded number of steps, each of which may hold one open working record
(§3.1A E) credited to a different user. The derivable bound is:

> sweeps per request  ≤  **min( number of open working records among the batch's
> non-deleted steps , number of distinct credited users in the workspace )**
>
> — the second term because one user's sweep serves every open record they hold, across
> every task in the batch (§3.4's own "a worker's sweep is shared across all their
> steps"). Operationally the binding term is **workspace headcount**, not 50.

For E-P and E-B the same bound applies over one task's steps.

**C. The window bound is conditional; correctness is not.** §3.4's "under ~2 days"
derives from the overnight close. Verified: `auto_clock_out_open_shifts.py:handle_auto_clock_out_open_shifts`
closes every shift whose latest `STARTED_SHIFT` is `< midnight` of the current UTC day
and stamps the close **at midnight**; `_clock_worker_shift.py:clock_out_shift_for_user`
closes the open step records through the `SHIFT_ENDED` transition. So a surviving open
working record entered at or after the previous midnight — at most ~24 h old — and
`W_start = entered_at − 1 day` puts the window under 48 h. The derivation holds.

But it holds **only while the sweep runs**. §3.2's window note deliberately refuses to
let *correctness* depend on that scheduler (charter rule 11), and it is right to. The
**cost ceiling** does depend on it: a missed night grows the window and the fetched
population without bound. The two must not be conflated — state the ceiling as
conditional, or a night the sweep misses reads as a mechanism failure rather than an
operational one.

---

## 4. Mechanism contract M2 — surface propagation (all fields, one number)

### 4.1 The propagation rule

Per response, the per-step live figures from M1 are computed **once**, then every
worked-seconds-derived field on that response is derived from them:

| surface | fields that go live |
|---|---|
| **E-P** production-time | `sections[].worked_seconds`, `left_seconds`, `share_state`; `budget.actual_worker_seconds`, `.actual_worker_minutes`, `.remaining_worker_minutes`, `.percent_consumed`; `status` OK↔INFEASIBLE unchanged (allowance-driven, not worked-driven) |
| **E-B** budget-status, manager face | `actual_worker_seconds`, `actual_worker_minutes`, `remaining_worker_minutes`, `percent_consumed`, `variance_worker_minutes`, and the seconds-derived money: `consumed_cost_minor`, `variance_cost_minor` (D6, owner-ratified: money ticks with its minutes — it is the same number times a frozen rate, and freezing it would rebuild the one-row-two-answers defect between a figure and its price tag) |
| **E-B** budget-status, worker/seller face | the same time fields through the shared `_build_evaluated_status`; the serializer still carries **no monetary keys** (HC-6) |
| **E-A** budget-allocations | `steps[].worked_seconds`, `left_seconds`, `share_state`; headline `actual_worker_seconds`, `remaining_worker_minutes` |

**The surface list above is owner-ratified in full (D5, 2026-08-19):** all four rows
ship live in the same release. The rejected branch — manager-only v1 — would have
shipped the manager/worker split-brain deliberately (the manager's widget red and
over, the worker's own card still "on track"), and would leave the future scheduler
unable to alert workers honestly, since the screen a worker checks would disagree
with the clock that fired the alert.

The natural seam — one shared loader that takes the step set, the session and `now`,
and returns `{step_id: live_worked_seconds}`, consumed by `_build_evaluated_status`
and by the two division-calling services before they hand rows to
`divide_production_budget` — is the planner's to finalize; the **contract** is only
that there is exactly one such computation per request and that no surface mixes
bases (HC-5). The future alerting scheduler consumes the same loader; it is this
pipeline's non-goal but this seam's first external customer (§7).

**One named structural consequence (round 3, coordinator finding 4).**
`_build_evaluated_status` currently produces `actual_seconds` as a **SQL aggregate**
(`func.coalesce(func.sum(TaskStep.total_working_seconds), 0)` over the task's
non-deleted steps, in `get_task_budget_status.py:_build_evaluated_status`).
Under M1 that aggregate can no longer be the sole producer of the task figure. Two
resolutions are arithmetically identical — replace it with a per-step fold over the
loader's output, or keep it for the settled term and add the loader's open shares on
top — and the planner picks **one** and records it before any implementer session.
What is contractual either way: the per-step figures and the task figure derive from
the same loader output (HC-5), never from two independent reads.

### 4.1A The field inventory, swept key by key; and the aggregate decision, resolved (round 4)

**A. The pre-registered decision (§4.1, coordinator finding 4) is answerable now, and
the gate answers it.** The two resolutions are arithmetically identical **if and only
if** the rounding locus is the one §3.1A A pins — round the open share per step, add to
the integer column. Given that locus:

- per-step fold: `Σ_s ( settled_s + round(open_s) )`
- keep-the-aggregate: `SUM(total_working_seconds) + Σ_s round(open_s)`
- both are sums of the same integers, so they are equal for every input.

Under the other locus they are not (§3.1A A). So the planner's choice is genuinely free
**only because the locus is pinned here**; without it, the "arithmetically identical"
sentence in §4.1 is false and the choice silently changes payloads. One practical note
for the planner: keeping the aggregate saves nothing, because the per-step figures are
needed anyway for the section rows and E-A's step rows — the aggregate would be a
second read of the same column while the loader already holds it (HC-5's "never from
two independent reads").

Population check, since the two resolutions must also agree on *which* steps:
`_build_evaluated_status`'s aggregate spans `TaskStep.workspace_id`, `task_id`,
`is_deleted.is_(False)` — **no state filter**, so SKIPPED/CANCELLED/FAILED steps are
included. `budget_division.py:group_steps_by_section` skips only `is_deleted` and keeps
excluded steps in `group["worked_seconds"]`. The two populations coincide today; the
loader's step set must be exactly "the task's non-deleted steps" or T6's headline-equals-rows
assertion breaks for a reason that has nothing to do with liveness.

**B. The §4.1 table is not total.** Every serializer key was walked. Two
worked-derived keys ship on live surfaces and appear in no row of that table — the
same construct, twice:

| surface | key | producer | in §4.1? |
|---|---|---|---|
| E-P | `final.percent_consumed` | `division_serializers.py:_serialize_production_time_final`, fed the **request-level** percent by `:serialize_task_production_time` | **no** — named only in §5.3 prose |
| E-B **worker/seller face** | `result.percent_consumed` | `serializers.py:_serialize_result`, `include_monetary=False` branch, fed `status.percent_consumed` by `:serialize_task_budget_status` | **no** — named nowhere |

The manager face's `result` block has no `percent_consumed` key at all (the
`include_monetary=True` branch), so it stays wholly frozen. This is the master plan's
standing rule arriving on schedule — *a comment asserting a property is a claim, and you
sweep the class, not the instance*: §5.3 pinned the E-P instance of this wiring in round
1 and the identical E-B instance went unmentioned for three rounds.

**D9 (owner, 2026-08-20) reverses §5.3's round-1 disposition for both keys: the frozen
blocks freeze whole.** `final.percent_consumed` (E-P) and the worker face's
`result.percent_consumed` (E-B) are decoupled from the request-level percent and derive
from the frozen result record's own settled figures — a frozen block never carries a
ticking field. The mechanism (what feeds the two serializer sites) is the planner's to
pick and register; the contract is that neither key moves with the live basis **nor
with post-freeze settled changes**. §5.3 is amended accordingly; T13 (§9A) guards both
sites. HC-4 is untouched: no key is added or removed.

**C. Everything else on the three payloads, confirmed non-worked-derived.**
E-P: `task_id`, `status`, `item_binding`, `allocation_method`,
`budget.allowed_worker_minutes`, `sections[].{working_section_id, section_name,
section_name_snapshot, order_list, state, state_entered_at, step_count,
allowance_seconds, typical{…}}`, `final.{actual_worker_minutes,
variance_worker_minutes, task_state_snapshot, computed_at}`.
E-B: `status`, `item_binding`, `production_budget_minor`, `allowed_worker_minutes`,
`evaluation_id`, `item_id`, and the manager `result` block in full.
E-A: `task_id`, `status`, `allowed_worker_minutes`, `allocation_method`,
`steps[].{step_id, working_section_id, section_name_snapshot, typical_worker_seconds,
allowance_seconds}`. With the two rows in **B** added, §4.1's table plus this list is
total over the three serializers.

**C.1 — the `allowance_seconds` claim carries a precondition (added round 4f, plan 2
review r3 S1).** Listing `allowance_seconds` above as non-worked-derived is true **only
while no *excluded* step holds an open working record.**
`budget_division.py:divide_production_budget` computes `charged_seconds` as the sum of
`total_working_seconds` over **excluded** steps, and from phase 2 onward those rows carry
the **live** figure. An excluded step with an open working record would therefore make
every `allowance_seconds` in its section tick downward second by second — the exact
property this list denies.

**It holds today, and the reason is structural, not incidental:**
`_step_transition_core.py:_apply_step_transition` sets `closing_record.exited_at = now`
unconditionally on every transition, so a step cannot enter an excluded state while its
working record is still open (verified at source twice — mechanism-inventory gate, and
again at plan 2 review r3). No live defect exists.

The precondition is written here rather than left implicit in a phase plan's prose
**because phases 3 and 4 cite §4.1A C, not plan 2's C6**. Any future path that moves a
step to SKIPPED / CANCELLED / FAILED without closing its record breaks this list, and the
breakage is silent: an allowance that drifts is indistinguishable from one that was always
that size. Plan 2 C6 row 1 carries the assertion that pins it.

**D. Composition — where HC-5's "one computation per request" is actually at risk.**
E-P calls `get_task_budget_status(ctx)` and then loads the task's steps again for the
division (`get_task_production_time.py:get_task_production_time`). If both sides run the
loader, the request holds two live computations and HC-5 fails silently — the two runs
differ only by microseconds, so the payload is *nearly* coherent and no assertion at
whole-second granularity catches it. The contract: **E-P resolves `now` and the live map
once and passes both into `get_task_budget_status`**, which passes them to
`_build_evaluated_status`. The four callers of that pair (master plan §6) each declare
what they pass:

| caller | passes `now` + live map | if it does not |
|---|---|---|
| E-B route selector (`item_economics.py:route_get_task_budget_status`) | resolves both itself | — |
| worker face (`get_task_budget_status_worker.py:get_task_budget_status_worker`, imports `_build_evaluated_status` directly) | resolves both itself | worker face silently stays settled — the D5 split-brain, shipped |
| E-P (`get_task_production_time.py:get_task_production_time`) | threads its own | two computations per request; HC-5 violated silently |
| price scenario (`get_task_price_scenario.py:get_task_price_scenario`) | resolves its own | a shipped endpoint from another pipeline reads a clock it never asked for |

The last row is the §2.6 coupling made concrete: `get_task_price_scenario` consumes no
worked-derived field, yet it will pay the loader's queries and acquire a wall-clock
read. That is a cost and time-dependence regression on a shipped endpoint, and it is
unavoidable while it composes `get_task_budget_status` — it is named so the price-scenario
suite's fixed-`now` retrofit is planned rather than discovered.

### 4.2 What stays settled on those same responses

`allowance_seconds`, `typical`, section membership and ordering, `allocation_method`,
`status` readiness values, the E-P `final` block **whole — `percent_consumed`
included** (round 4 excepted that key while §5.3's round-1 wiring stood; **D9,
round 4a, froze it and the E-B worker face's `result.percent_consumed` with their
blocks**, §4.1A B, §5.3), and every field not derived from
worked seconds: byte-identical to today at equal database state (T1/T5). The
frontend's acceptance criterion 2 — two calls seconds apart with no state change
differ **only** in time-dependent fields — follows from `divide_production_budget`
being pure and everything else in the inputs being equal.

### 4.3 The allocator is a consumer, not a participant

`divide_production_budget` (`budget_division.py`) is not modified (its HC-1
independence from the budget-division pipeline stands). It already computes
`worked_seconds` from whatever step rows it is handed via
`_value(step, "total_working_seconds")`; the services hand it rows whose worked
seconds are the M1 figures. Completed-step allowances inside
`_section_step_allowances` are unaffected: a completed step has no open record, so
its M1 figure equals its settled column identically.

### 4.3A Allowance independence: three paths, not one (round 4)

§4.3's claim — allowances cannot move — is **true**, but it is grounded on one of
**three** paths from worked seconds to `allowance_seconds`. The coordinator review
verified the first and stopped there; the other two are load-bearing and unnamed. All
three must hold, and each needs its own reason.

| # | Path | Site | Why it cannot move |
|---|---|---|---|
| 1 | completed steps' allowances are their worked seconds | `budget_division.py:_section_step_allowances` | a completed step has no open working record ⇒ M1 ≡ settled column (§4.3, verified) |
| 2 | `charged_seconds` → `distributable_seconds` → every section allowance | `budget_division.py:divide_production_budget` — `charged_seconds = sum(total_working_seconds for step in excluded)` | an *excluded* step (SKIPPED/CANCELLED/FAILED) has no open **working** record ⇒ M1 ≡ settled column |
| 3 | section **weights** — `typicals_by_section` → `resolved_weights` → `raw_shares` | `get_working_section_typical_times.py:typical_times_statement` — `SUM(TaskStep.total_working_seconds)` | it is a **SQL aggregate over the persisted column**, never fed the loader's output |

**Path 2, verified.** Every route into SKIPPED/CANCELLED/FAILED closes the open record
first: `_step_transition_core.py:_apply_step_transition` sets `closing_record.exited_at =
now` before opening a record whose `state` is the new terminal state, and
`remove_task_step.py` explicitly closes open records (`record.exited_at = now`) while
setting `state = SKIPPED`. So an excluded step's open record — if it has one — is in a
terminal state, not `working`, and M1 clause 2 returns `0`. The invariant this rests on
is the transition core's **close-then-open** discipline; if a future path ever assigns a
terminal `state` without closing the record, live seconds reach `charged_seconds` and
every section allowance on the payload moves. §9A, T12.

**Path 3, verified and fragile in the other direction.** The typicals statement is a
grouping subquery with no date predicate (master plan §6) that sums the settled column
across the workspace's history. It **must never** be handed live figures: a live typical
would make a section's weight tick while someone works, which moves
`section_allowances` for every section on the payload, which moves every
`left_seconds` and every `share_state` — the mixed-basis payload HC-5 exists to
prevent, arriving through the allowance rather than through the worked figure. Because
it reads through SQL rather than through the step rows, HC-1A's no-mutation rule is what
keeps it settled. A future "make it consistent" change here is the most expensive
mistake available in this feature.

**Restated as one contract line:** `divide_production_budget` receives live worked
seconds and **nothing else changes about its inputs** — `allowed_worker_minutes`,
`typicals_by_section` and `section_attributes` are settled-basis values, and
`allowance_seconds` is byte-identical to today at equal database state (§4.2, T5).

---

## 5. API contracts

### 5.1 The three endpoints

`GET /tasks/{task_client_id}/production-time`,
`GET /tasks/{task_client_id}/budget-status`,
`GET /tasks/budget-allocations` — **request shape, response shape, role gates, error
cases, ordering, and socket events all unchanged** (HC-4). The change is behavioural:
fields that were settled-only now reflect open work at request time.

### 5.2 The frontend's acceptance criteria, adopted verbatim as contract

1. A section whose governing step has been `working` past its allowance reports
   `share_state: "over_share"`, with `worked_seconds` and `left_seconds` consistent
   with that verdict **in the same payload**.
2. Two calls a few seconds apart with no state change differ only in time-dependent
   fields — never in `allowance_seconds`, `typical`, ordering, or section membership.
3. The item-level `budget` block agrees with its section rows on the same basis.
4. A task with no open working interval is **byte-for-byte identical** to today's
   response.

### 5.3 Two composition details pinned

- **`final` (E-P)** stays a frozen record — **whole, `percent_consumed` included
  (D9, owner, 2026-08-20; supersedes this bullet's round-1 disposition).** The key is
  today wired to the request-level percent, which under M1 would tick inside a frozen
  block; D9 freezes it with its neighbours: it derives from the frozen result record's
  own settled figures and moves on **no** event after the freeze — not the live basis,
  not post-freeze settled changes. The same contract governs the E-B worker face's
  `result.percent_consumed` (§4.1A B). The response *shape* is unchanged — no key
  added or removed (HC-4); only the value's source moves from the request-level figure
  to the frozen record. Guarded by T13 (§9A).
- **`status` OK↔INFEASIBLE** derives from the allowance sign, not from worked
  seconds — the live basis cannot flip it.

### 5.4 Closeout handoff obligation

Per the frontend's document convention (adopted): the answer ships as a **new dated
handoff**, never an edit of the 2026-08-18 file. It must carry, explicitly:
the go-live statement that deletes their interim verdict-suppression gate (their
stated deletion condition); the correction they are owed on the 2026-08-18 "Live
time" section (client ticking is superseded by server truth — smoothing from
time-of-receipt remains legitimate); the answers to their four open questions (§2.3,
§2.5, §4.1, HC-3/T1); and the note that `worked_seconds` decreases between polls in
exactly **three** ways (per-event client rules in §6A C, corrected round 4a): the
≤ 1 s rounding sense of §3.3; the D7 disowning events per §6A A — mark-inaccurate on
any record of the step, and step removal; record deletion is **not** a shipped
capability and is not named to the client — where it drops by the whole disowned
share at once, deliberately; and the D8 settlement window (§3.3A C.1), a
dip-and-recover at clock-out that the client renders as served. Client smoothing must
snap down to the served value, never
clamp — a clamp keeps displaying time the workspace has explicitly disowned.

---

## 6. Consistency semantics (binding on consumers)

- **Live figures are display and decision values, never records.** Nothing a client
  reads from these three endpoints while work is open may be stored, exported, or
  reconciled against payroll-adjacent data; the settled records remain the sole
  archival truth (HC-1).
- **Monotonicity within one open interval:** between two reads with no transitions,
  a step's live figure is non-decreasing (the sweep's divisor for future segments can
  change, but past segments are fixed) — **except on the disowning events, where it
  drops by design (D7).** Marking a running record's time inaccurate zeroes its live
  share immediately: `mark_step_time_inaccurate` selects any non-deleted record — no
  `exited_at` filter — and also sets the **step-level** flag, poisoning the step's
  surrounding timings exactly as settled inaccurate time is skipped today. Deleting
  the record or the step does the same. The drop is the feature working —
  acknowledged-wrong time is removed at once; recovery tooling is future work (§7).
  Across a transition, §3.3 bounds the move.
- **Client smoothing** (adding elapsed-since-receipt between polls) remains
  legitimate and skew-proof; clients must not re-derive verdicts — `share_state` is
  rendered as received. Unchanged from the standing rule (budget-division D7/HC-4);
  restated because the interim frontend gate is deleted at closeout.

### 6A The disowning-event family, verified at source; and what the client is told (round 4)

§6 names "mark-inaccurate, record/step deletion". Read against the commands, that family
is one event short, one event wide, and missing the two-sided effect of the step flag.

**A. The family, enumerated over the shipped commands.**

| event | command (`path:symbol`) | effect on the live figure | reachable? |
|---|---|---|---|
| E1 mark the **open** record inaccurate | `mark_step_time_inaccurate.py:mark_step_time_inaccurate` | the step's live term → `0` at once (record flag **and** step flag) | yes |
| E2 mark **any closed** record of the step inaccurate | same command | **also** → `0`, because the command sets `step.recorded_time_marked_wrong` and `averaged_time.py:compute_record_contributions` computes `marked_wrong = record OR step` | yes — **not named in §6** |
| E3 a sibling step's records leave the divisor | E1/E2 on another step of the same worker | other steps' live figures **rise**, retroactively over shared segments, because a flagged interval is dropped before the sweep ("earn nothing, reduce nothing", `concurrency.py:averaged_seconds_by_record`) | yes — **not named in §6** |
| E4 step removal | `remove_task_step.py` — sets `state = SKIPPED`, `is_deleted = True`, closes open records | the step's whole figure leaves every payload; its records **still divide** siblings (§3.1A F) | yes |
| E5 record deletion | — | — | **no shipped command soft-deletes a `StepStateRecord`**; the only writer is the workspace reset (`reset/phases/delete_step_state_records.py`), a hard `DELETE` |
| E6 task deletion | `delete_task.py` | all three endpoints 404 | yes, but not a decrease — a different contract |

E2 and E3 are consequences of the same step-level flag D7 ratified, so they are inside
D7's intent ("it has poisoned the surrounding timings") and are recorded rather than
re-opened. E5 is not a capability; naming it to the frontend as a decrease cause would
be telling another codebase to handle an event our API cannot emit.

**B. The immediate-zero contract, stated precisely.** On E1/E2 the live term becomes
`0` on the **next request**, with no state transition and no worker involvement — the
flag is read on every sweep. The **settled** portion does not move: the command
enqueues no `PROCESS_STEP_TRANSITION`, so `total_working_seconds` keeps its
now-disowned value until the next transition on that step recomputes it to `0` (§3.3A
C.2). So a step whose time is disowned mid-work serves `settled_old + 0`, then
`0` once any later transition settles it. Both drops are intended; they arrive at
different times, and the second is a **second** decrease from the same user action.

**C. §5.4's two-codebase contract, restated per event.** The closeout handoff tells the
frontend what to do, not what we believe. Per event, exactly:

- **Any decrease:** render the served value. Smoothing may add elapsed-since-receipt
  **on top of** the served value; it must **never** clamp the served value to a
  previously-displayed maximum. A clamp keeps displaying time the workspace has
  explicitly disowned.
- **On a drop of ≤ 1 s:** the rounding sense (§3.3A A). Smoothing may absorb it; no
  visible snap is required.
- **On a drop larger than 1 s:** treat the served value as authoritative immediately —
  reset the smoothing baseline to it and continue accruing from time-of-receipt. Do not
  animate the descent over time; the time is gone at once, not gradually.
- **On a drop followed within seconds by a return to the previous value:** this is the
  settlement window (§3.3A C.1), not a disowning event, and the client cannot tell them
  apart from the payload — by design, since HC-4 forbids an `as_of` field. The rule is
  the same in both cases: render what is served. (D8, owner-ratified 2026-08-20.)
- **`share_state` is rendered as received, never re-derived** — unchanged standing rule.

---

## 7. Non-goals (v1)

- **The alerting/scheduler machinery itself.** This pipeline ships the clock those
  services will read; the trigger rules, thresholds, delivery, and cadence are a
  separate intention. The seam (§4.1) is built so that machinery adds zero new
  time-computation code.
- **Push/socket updates of live figures.** Polling + client smoothing per the
  frontend's stated plan; `task:step-state-changed` invalidation unchanged.
- **Persisting any live value**, including caching layers (HC-1).
- **Changing the crediting rule** — batch averaging, marked-wrong exclusion, and
  attribution are consumed as-is from the analytics domain.
- **Paused-time display.** The open `paused` interval accrues nothing to working
  seconds (it never has); surfacing "paused for 40m so far" anywhere is future work.
- **`final`, `item_cost_results`, daily rollups, `total_cost_minor`** (§2.5).
- **The valuation editor's price-scenario payload** — stays gross-of-progress per its
  own ratified D5; it does not consume M1 in v1.

---

## 8. Relation to existing domains

- **Analytics** owns the crediting rule and keeps it: M1 adds *consumers* of
  `averaged_seconds_by_record` / `compute_record_contributions`, no forks. The
  architecture-graph delta records the new read dependency from the item-economics
  projections to the analytics sweep boundary.
- **Item economics** owns the three endpoints and the budget arithmetic; the pure
  calculator (`calculate_actual_worker_minutes` and downstream) is unchanged — it
  already takes seconds as input and does not care whether they are settled.
- **Tasks / task-steps** own the records and the settlement worker — untouched.
- **Graph delta at closeout:** update the four projection nodes'
  *(count corrected round 4a — this line read "three" above a list of four slugs from
  round 1 through the round-4 sweep, which added the fifth node below without catching
  it; coordinator finding at the fold)*
  descriptions (`projection-item-economics-task-budget-status`, `…-worker`,
  `…-task-budget-allocations`, `…-task-production-time`) whose current text asserts
  "live non-deleted task-step seconds" from the settled column, plus `reads_from`
  edges to the step-state-record table node as the graph vocabulary allows.
  **Round 4 — a fifth node belongs in the same batch:**
  `projection-item-economics-task-price-scenario`, which composes
  `get_task_budget_status` (§2.6, §4.1A D) and therefore acquires the same transitive
  read dependency without consuming a worked-derived field. Also verified this round:
  `projection-item-economics-task-budget-allocations` already records the invariant
  "the response's time-only fields reconcile with the same non-deleted step set used by
  budget status" — that is HC-5's cross-surface claim, already in the graph, and the
  closeout must keep it true rather than restate it. Graph state at the gate:
  187 nodes / 278 edges, 0 pending, 0 stale, 0 diagnostics.

---

## 9. Testing expectations

Charter standing rules apply in full. The named tests, because every one guards a
silent failure:

- **T1 — determinism under fixed `now`** (HC-3, frontend Q4). With `now` injected and
  frozen, two executions over identical database state produce byte-identical
  payloads for all three endpoints. Named mutation: introducing a second wall-clock
  read inside the computation (definition site: the shared loader) must turn this red.
- **T2 — the no-snap parity** (§3.3, the load-bearing test). Fixture: open working
  record; compute the E-P payload at `t`; close the record at `t` and run the real
  settlement recompute (`_recompute_step_time_totals`, production path, per charter
  rule 3); assert per-step figures agree within 1 second. Run once per §3.2 case
  shape. Named mutation: replacing the sweep call in the live loader with
  `now − entered_at` (call site, not the sweep's definition) must turn the batch
  rows red while leaving the single-open-record row green — recorded per-row.
- **T3 — the four naive-form failure rows, enumerated** (§3.2): two workers/one
  section (no division); divisor-changes-mid-interval (20 + 10/2); cross-task divisor
  (task 1's payload halves while task 2 is open elsewhere); closed-overlap
  (20/2 + 10). One row each, each fixture making its own predicate the only reason
  its expected number holds (charter rule 2 companion).
- **T4 — exclusions:** open `paused` record accrues 0; open record marked wrong
  (record flag and step flag, one row each) accrues 0; deleted record accrues 0;
  deleted step excluded entirely.
- **T5 — idle byte-identity** (criterion 4): golden-file comparison of all three
  payloads for a task with no open intervals. Sequencing is part of the criterion
  (coordinator finding 5): the goldens are **captured and committed at the
  pre-change checkpoint**, and the post-change suite asserts against those files. A
  golden captured after the change compares the new payload to itself and passes
  vacuously — writing one is a gate failure, not a test.
- **T6 — propagation coherence** (HC-5, criterion 3): with one open record, assert on
  one payload that `budget.actual_worker_seconds == Σ sections[].worked_seconds`
  basis-consistently, that `left_seconds = allowance − live worked` per row, and that
  `share_state` flips in the same payload as the figures that justify it
  (criterion 1).
- **T7 — worker-face redaction unchanged** (HC-6): the worker/seller budget-status
  serializer carries no monetary keys while its time fields are live — the existing
  §11A.3 test family extended by one live-state row.
- **T8 — E-A batch cost shape:** one active worker across N batched tasks triggers
  one sweep, asserted by query/call counting, not by wall-clock timing (rule 1). Plus
  the ceiling row (§3.4): a batch at the 50-task cap with distinct active workers
  performs exactly one batched open-record probe and ≤ one sweep per worker, and the
  plan records the measured worst case at that ceiling.

### 9A Test mechanisms: corrections, preconditions, and four added rows (round 4)

Every T-row was checked for **constructibility as stated**, **decidable assertions**,
and — where a mutation is named — **both sides computed for the named fixture**. The
environment supports all of it: the suite runs against the configured Postgres
(`tests/conftest.py:initialize_database`), integration tests already build real
`TaskStep`/`StepStateRecord` rows with `try/finally` teardown, `tests/conftest.py`
ships a `count_queries` fixture (SQL-statement capture) that makes T8 decidable, and
`test_production_time_query.py` already uses `json.dumps(sort_keys=True)` + `sha256`
for payload identity, which T1 and T5 reuse.

**T1 — the named mutation does not bite as stated.** "Two executions over identical
database state produce byte-identical payloads" run milliseconds apart. Introduce the
mutation (a second wall-clock read inside the loader) and the two runs differ by the
elapsed wall-clock between them — tens of milliseconds — which `int(round(·))` per step
collapses to the **same integer** in almost every run. The test would pass under its own
defect and fail rarely, i.e. it would read as flaky rather than as a guard. Rewrite so
the mutation is decidable:

> **T1′.** Patch the loader's clock source to a stub that advances by **+5 s** on each
> call, and assert the two payloads are still byte-identical. Under the contract the
> stub is never called (the injected `now` is used) and the payloads match; under the
> mutation the second call shifts every open share by 5 s and at least one
> `worked_seconds` differs. **Both sides, for a fixture with one open batchable record
> entered 600 s ago:** contract `600, 600`; mutation `600, 605`. Differ ⇒ red.
> **Site:** the loader's definition site — and a second row at the **call site**,
> asserting that each of E-P, E-B and E-A resolves `now` exactly once per request
> (call-count on the stub == 1), because the function-side and call-site mutations are
> different defects (charter rule 11) and the composition risk in §4.1A D is a
> call-site defect.

**T2 — writable as stated; mutation confirmed.** `_recompute_step_time_totals(session,
workspace_id, step_id, now)` is directly callable; it also writes `total_cost_minor`
via `_rate`, which returns `None` with no `UserWorkProfile` and costs `0` — harmless.
It mutates the step, so the fixture owns teardown (charter 11½).
**Named mutation, both sides computed** (replace the sweep call with `now − entered_at`
at the **call site** in the loader, not in `concurrency.py`):

| row | contract | mutation | verdict |
|---|---|---|---|
| batch row (§3.2 case 2 shape, `allows_batch_working=True`) | live `1500`, settled after close `1500`, \|Δ\| = 0 ≤ 1 | live `1800` vs settled `1500`, \|Δ\| = 300 | **red** ✓ |
| single-open-record row | live `1800`, settled `1800`, \|Δ\| = 0 | live `1800`, settled `1800`, \|Δ\| = 0 | **green** ✓ |

Precondition the row depends on: the single-open-record fixture's worker must hold **no
other open interval anywhere** (§3.2 case 3 — the divisor can live on another task), or
the "green" row goes red for an unrelated reason and the mutation's discrimination is
lost.

**T3 — writable, with one precondition added.** Rows 2, 3 and 4 require
`allows_batch_working = True` on every participating step (§3.2A); row 1 requires the
two records to be credited to **different** users, which is the only reason its expected
`3600` holds (charter rule 2 companion). Expected values are those re-derived in §3.2A.

**T4 — writable; two rows need their status stated and one row is missing.** The
`deleted record` row exercises a state **no shipped command produces** (§3.1A D) — the
fixture sets `is_deleted` directly, and the row is defense-in-depth, which the criterion
should say so a reviewer does not go looking for the writer. The marked-wrong rows must
be **two** rows (record flag alone; step flag alone), and the step-flag row must also
assert the E3 side-effect — that a sibling step's live figure **rises** — or the row
proves only half of what the flag does (§6A). Missing row, added:

> **T4.5** — a *deleted step* with an open batchable working record, sharing a segment
> with a live step of the same worker: the deleted step is absent from the payload
> **and** the live step's share is still halved (§3.1A F). Without this row, an
> implementer who "correctly" filters deleted steps out of the sweep population breaks
> parity with settlement in the direction §3.3's bound cannot see.

**T5 — writable, and the sequencing is right.** One fixture note: the strongest "no open
intervals" fixture is a task whose steps are `PENDING` and therefore hold an **open
PENDING record** — that proves the state filter rather than merely the absence of
records. Both fixtures belong in the row.

**T6 — decidable only because §3.1A A pins the locus.** `budget.actual_worker_seconds ==
Σ sections[].worked_seconds` holds because both sides sum the same per-step integers
(§4.1A A). Under the other locus the assertion is not guaranteed and would fail
intermittently on half-second shares.

**T7 — writable as stated.** The existing money-token walk over the payload keys
(`test_production_time_query.py`) is the pattern; extend it with a live-state row.

**T8 — writable; the ceiling row is not an automated criterion.** `count_queries` makes
"exactly one batched open-record probe and ≤ one sweep per worker" decidable
(`compute_record_contributions` issues one statement per call, §3.4A A). But "the plan
records the measured worst case" is a **measurement**, not an assertion — charter rule 1
puts it in the Review log, not in the criteria, and the criterion must be the
query-count shape alone. The ceiling asserted must be §3.4A B's, not §3.4's.

**Four rows this gate adds.**

> **T9 — nothing live is persisted** (HC-1A). Serve each of the three endpoints against
> a task with an open working record, then re-read `task_steps.total_working_seconds`
> from the database **in a fresh session** and assert it is unchanged. **Named
> mutation:** assign the live figure onto `step.total_working_seconds` before calling
> `divide_production_budget` (site: the loader's call site in each of the three
> services). Both sides for a step with settled `0` and an open share of `600`:
> contract column `0`; mutation column `600` after the request's session flushes.
> Differ ⇒ red. This is the only test standing between the pipeline and writing live
> values into the settled column.
>
> **T10 — the deleted-step divisor** — see T4.5 above; listed here as its own criterion
> because it guards a *parity* property, not an exclusion property.
>
> **T11 — the settlement window is observed, not assumed** (§3.3A C.1). Open a working
> record, read E-P, close the record through the production transition path **without
> running the analytics worker**, read E-P again. Assert the second payload's
> `worked_seconds` equals the pre-work settled value — i.e. **assert the drop exists**.
> Then run `_recompute_step_time_totals` and assert the value returns within the §3.3
> bound. The row's purpose is that the behaviour is pinned by a test rather than
> discovered by the frontend; if owner card 1 chooses to engineer the window away, this
> row inverts and becomes the guard for that.
>
> **T12 — allowances do not move** (§4.3A). One payload, one open working record, and
> assert `allowance_seconds` on every section and every step row is byte-identical to
> the same payload with the record closed and settled. **Named mutation:** feed the live
> figure into `charged_seconds` by including excluded steps in the loader's substitution
> (site: the loader's call site, where the live row set is built) **with** a fixture
> whose excluded step carries an open `working` record — which requires constructing a
> state the transition core cannot produce, so the row's honest form is: assert that no
> excluded step in the payload has an open working record, and assert `charged_seconds`
> is computed from settled values. Path 3 (`typical_times_statement`) is covered by
> T5's byte-identity on `typical`.
>
> **T13 — the frozen blocks are frozen (D9, added round 4a).** Fixture: a task with a
> persisted result whose step is re-opened into `working` with an open record. In one
> payload the live fields tick (T6's basis) while E-P's `final` block —
> `percent_consumed` included — and the E-B worker face's `result` block are
> byte-identical to the same task's pre-open payload. **Named mutation:** re-wire
> `final.percent_consumed` to the request-level percent (site:
> `division_serializers.py:serialize_task_production_time`, the call feeding
> `:_serialize_production_time_final`). Both sides: the fixture's live request percent
> differs from the frozen record's by construction (the open record adds share), so
> contract = frozen value, mutation = live value, differ ⇒ red. The worker-face key
> gets its **own** row at its own site (`serializers.py:serialize_task_budget_status`,
> the `percent_consumed=` argument) — two sites, two rows (sweep the class, master
> plan §5).

---

## 10. Owner decisions

### 10.1 Settled during shaping (owner conversation, 2026-08-19 — verbatim in `owner_decisions.md`)

**D1 — backend-owned, centralized.** One computation home consumed by every client.
Owner: "my intention is for the system to use this live clock centralized so that any
client ( the frontend, or a scheduler ) can make correct decisions"; and: "clearly
this is a backend implementation that needs to happen."

**D2 — the mechanism is settled-plus-open-interval.** Proposed by the owner ("take
the sum of all the work time of the close records and if there is an open working
record add the entered at until now"), refined in conversation to the sweep-averaged
share after the four failure cases of §3.2 were walked through; owner accepted the
correction and the reuse of the settlement rule ("sounds greate").

**D3 — the live/settled dividing line.** "What is happening" is live; "what happened"
is settled — surface list §4.1, untouched list §2.5. Accepted with the §Part-2
blast-radius explanation.

**D4 — honoured from the frontend handoff:** no new fields, no server-now timestamp,
shapes frozen (their explicit request; HC-4).

**D7 — the live figure drops on disowning events, by design (owner, 2026-08-20,
folded round 3).** Owner, verbatim: "the whole point of marked inaccurrate is exactly
that, to remove data that the user can acknowledge as incorrect, so that is something
that all users can account for, an open record that it is marked as inaccurate will
be removing that time passed as it has poisoned the surrounding timings like it
currently does today when skippiing inacurrate times ( later i will add ways to
recover that time )." Monotonicity (§6) and the closeout handoff (§5.4) are scoped
around these events; time-recovery tooling is future work, out of scope.

### 10.2 Ratified round 2 (owner, 2026-08-19)

Both round-1 cards answered, both recommendations accepted. Owner, verbatim: *"about
the two owner cards both recomendations are the correct answers."*

| D | decision | folded into |
|---|---|---|
| D5 | Worker-facing surfaces go live in the **same release** — all four §4.1 rows ship together | §4.1; T7 covers the live worker face; §5.4 handoff scope is all three endpoints |
| D6 | Seconds-derived **money ticks** with its minutes on the manager face (audience unchanged, HC-6) | §4.1 row 2 |

### 10.3 Ratified round 4a (owner, 2026-08-20)

Both mechanism-inventory cards answered in one pass, both recommendations accepted.
Owner, verbatim: *"about the owner cards the recommendations are the correct
approach."*

| D | decision | folded into |
|---|---|---|
| D8 | The **settlement window ships as-is and is disclosed**: closing a record may briefly drop the live figure by the just-worked share until the async recompute lands (normally sub-second; up to ~30 s on a dropped notify; until the next transition on that step if retries exhaust). No second computation path is built to mask it — D2's mechanism stands exactly as ratified. | §3.3A C.1, §5.4 (third decrease mode), §6A C, T11 |
| D9 | The **frozen blocks freeze whole**: `final.percent_consumed` (E-P) and the worker face's `result.percent_consumed` (E-B) stop tracking the request-level percent and derive from the frozen result record's own settled figures — moving on no event after the freeze. Shapes unchanged (HC-4). | §5.3, §4.1A B, §4.2, T13 |

**Ledger empty.** No decision in this intention is a guess; each rejected branch is
recorded with the failure it would have produced, in `owner_decisions.md`.

---

## 11. Changelog

**Round 1 — 2026-08-19.** Shaped from the frontend escalation handoff
(`HANDOFF_TO_BACKEND_production_time_live_budget_clock_20260819`) and the owner
conversation of the same day, in which the owner (a) chose a backend-owned live
clock over a permanent frontend display gate, (b) proposed the settled-plus-open-
interval mechanism and accepted its correction from raw elapsed to the settlement
sweep's averaged share, and (c) set the centralization directive that resolves the
frontend's second and third open questions (all fields together; one computation for
every client).

Resolutions made during shaping rather than deferred:

- **Elapsed vs averaged share** — resolved to the share (§3.2, four enumerated
  failure cases; the deciding one is the cross-task divisor, invisible from inside a
  task). The naive form is not a simplification; it is settlement's Story-2 defect
  relocated to the server.
- **New primitive vs reuse** — resolved to reuse: `averaged_seconds_by_record`
  already accepts `now` and already handles open intervals; worker-stats reads
  already call it live (§2.3), so the "no clock in the read layer" concern dissolves
  into "no clock in *this* family yet," and HC-3 turns the property into a tested
  convention.
- **Where liveness stops** — the live/settled line (§2.5, §4.2, §7): `final`,
  `item_cost_results`, rollups and `total_cost_minor` stay settled; `status`
  readiness cannot flip on the live basis; `final.percent_consumed`'s existing
  wiring is pinned rather than silently changed (§5.3).
- **The frontend's four open questions** — answered in-document: feasibility and
  cost (§3.4); all-six-together, generalized per surface (§4.1); the settled
  consumers audit (§2.5); the convention-wants-a-test question (HC-3, T1).

Two questions are genuinely the owner's and are cards (§10.2): whether workers see
their own numbers ticking in v1, and whether manager-face money ticks with its
minutes.

**Round 2 — 2026-08-19, owner ratification.** Both cards answered in one pass, both
recommendations accepted (D5–D6, §10.2). Folded into §4.1; each rejected branch kept
beside its decision in `owner_decisions.md`. Status draft → **resolved**; the
decisions ledger is empty.

What the answers settle downstream, so the planner does not rediscover it:

- **D5 fixes the release shape:** one phase family delivers the shared loader and all
  three endpoints together — there is no "manager-first" intermediate state to plan,
  test, or hand off. T5's idle byte-identity and T7's worker-face redaction rows run
  against the same release.
- **D6 removes the last mixed-basis payload:** every worked-seconds-derived field on
  every present-tense surface — time and money alike — now derives from the single
  M1 figure (HC-5 with no exceptions), which simplifies T6's coherence assertion to
  one rule with no carve-outs.

Next: **mechanism-inventory**. The claims most worth attacking there are the §3.3
no-snap ≤ 1s bound (is the rounding-locus argument the only drift source?), the
§3.1 window rule (`entered_at − 1 day` — is settlement's buffer provably sufficient
for the live case?), and T8's query-count bound on the 50-task batch.

**Round 3 — 2026-08-20, coordinator review folded.** Source:
`planning/coordinator_review_of_intention_20260819.md` (all six findings verified
against the code before folding; the review's two keystone verifications spare the
gate that re-work). Owner dispositions, conversation of 2026-08-20:

- **Finding 1** (accepted): §2.6 rewritten — the price-scenario endpoint calls
  `get_task_budget_status` since checkpoint `48705b3`, so the perimeters are not
  disjoint; the false router/mirror-overlap claim withdrawn.
- **Finding 2** (owner-ratified as intended behaviour → **D7**): the live figure
  drops immediately when a running record is marked inaccurate or deleted — that is
  the point of marking; §6 and §5.4 rewritten to name the event family instead of
  promising monotonicity the backend does not keep.
- **Finding 3** (accepted, with owner context): window anchor fixed to
  `min(entered_at)` of the user's open working records; the owner's operational
  safeguards (overnight auto-clock-out sweep, logout auto-close — both verified in
  code) make the distinction unreachable today and are recorded as the reason this is
  defense-in-depth rather than a live bug.
- **Finding 4** (accepted): the E-B SQL aggregate's fate is a named planner decision
  (§4.1) — per-step fold or settled-sum-plus-live-term, one chosen and recorded
  before implementation.
- **Finding 5** (accepted): T5 now carries its capture sequencing — goldens committed
  at the pre-change checkpoint, or the test is vacuous.
- **Finding 6** (accepted): §3.4 states the ceiling — ≤ 50 bounded sweeps worst-case,
  window bounded by the overnight close — and T8 records the measured worst case.

The review's process note is adopted for the gate: sweep §6 and §2.6 at equal depth
to the nominated claims; round 3 is itself evidence for that note — finding 2 sat in
§6, which round 2's self-assessment never flagged.

**Round 3a — 2026-08-20, citation form. No claim changed.** Every code reference in
this document was converted from `path:line` to `path:symbol`, the house convention
and the rule the `simple_valuation_editor` pipeline earned twice: **a cross-reference
must resolve from a clean checkout, and a line number does not.**

Two round-3 citations were wrong when written — `get_task_price_scenario.py:191` (the
call is at 192; 191 is a comment) and `get_task_budget_status.py:141-150` (the
`func.sum` is at 140, and the span ran three lines past the statement into unrelated
code). Both excluded the exact line they named.

The sweep then found **eleven more** from rounds 1–2, and four of those began *inside*
a signature or mid-statement — `concurrency.py:37-76` at the close of a signature,
`averaged_time.py:71` mid-parameter-list, `get_task_budget_status.py:135-176` five
lines into `_build_evaluated_status`, `get_task_budget_allocations.py:100-283`
forty-four lines into its function. The same defect shape found in six of eleven
architecture-graph anchors reviewed the same day: **someone records the line where the
interesting part is, not where the construct begins.**

Why the form, not just the numbers: the call cited as `:191` sat at line **152, 155,
169, 171, 185 and 192** across six commits on 2026-08-19–20, while **the code never
changed once** — every move was comments added above it. A citation correct in the
morning was wrong by the afternoon. All eleven symbols were verified to resolve
against the tree at `bf470d4`.

**One instance nearly survived the fix.** §4.1's aggregate citation was corrected
first; the identical reference appears again in §2.4 and was only caught by sweeping
for the *form* rather than re-reading the fix site — the failure this project has now
recorded four times, arriving inside the correction of its own class.

**Round 4 — 2026-08-20, mechanism-inventory gate.** Nine mechanisms inventoried,
ranked by silent-failure risk, and given contract-grade definitions in this document.
Verdict: **OWNER_DECISIONS_PENDING** — two cards, in
`handoffs/reviewer/2026-08-20_inventory_mechanism_inventory_handoff.md`. Sections
added, all lettered so no existing citation renumbers: §1A, §2.3A, §2.5A, §3.1A,
§3.2A, §3.3A, §3.4A, §4.1A, §4.3A, §6A, §9A. §4.2, §8 and this changelog amended in
place (no numbers moved).

What the gate changed, and why:

- **A new mechanism nobody had named: settlement is asynchronous** (§3.3A C.1). The
  transition closes the record synchronously and only *enqueues* the recompute, so
  between the two the live figure drops by the whole just-worked share and then
  recovers. Not one of §5.4's two decrease modes, not covered by §3.3's bound, and
  larger than every other effect in this document combined. **Owner card 1.**
- **Nothing stops the live figure being persisted** (§1A HC-1A). All three surfaces
  hand ORM `TaskStep` instances to the allocator; assigning the live value onto
  `total_working_seconds` marks the row dirty and the next flush writes it into the
  settled column — the direct negation of HC-1, silent, with no test failing. A new
  criterion (T9) is the only thing standing in front of it.
- **The parity bound's denominator was wrong** (§3.3A B). "≤ 1 s per credited user"
  cannot be right — a step has at most one open record by unique index, so at most one
  credited user, while the settled column is rounded once across all of them. The bound
  is ≤ 1 s per step, and on aggregates ≤ 1 s **per step holding an open working
  record**. One worker batch-working six steps falsifies the old wording by 6 s.
- **"Rounding is the only drift source" is false** (§3.3A C). Three non-rounding
  sources, all verified at the commands.
- **§4.1's "arithmetically identical" is conditional, and the condition is now
  pinned** (§3.1A A, §4.1A A). The two resolutions coincide **iff** the rounding is
  applied to the open share per step; under the other reading of §3.1's "rounded
  `int(round(·)) per step`" they diverge on any exact half-second. The pre-registered
  planner decision is therefore free — but only because the locus was pinned here.
- **The allocator has three worked-seconds→allowance paths, not one** (§4.3A). The
  keystone verification covered `_section_step_allowances`; `charged_seconds` and the
  typicals aggregate were unnamed. All three hold, each for a different reason, and the
  reasons are now written down — path 3 in particular, because "making it consistent"
  later is the most expensive available mistake.
- **Two live worked-derived keys shipped in no field table** (§4.1A B):
  `final.percent_consumed` on E-P (named only in §5.3 prose) and
  `result.percent_consumed` on the E-B **worker face** (named nowhere). Same construct,
  twice — §5.3 pinned the instance and missed the class. **Owner card 2.**
- **An absence claim was false** (§2.3A). The item-economics query family already reads
  the wall clock: `get_task_budget_allocations` calls `today_utc()` inside its per-task
  loop. Search terms recorded beside the claim. The conclusion survives; the framing
  does not, and HC-3's scope had to be defined around it (§1A HC-3A).
- **§2.5's settled-consumer list was not total** (§2.5A) — four named, eight exist.
  Rows 5 and 7 are load-bearing. The corrected list is what ships to the frontend.
- **The cost ceiling was bounded by the wrong quantity** (§3.4A B). The 50-task cap
  bounds tasks, not workers; the real bound is open-record count ∧ workspace headcount.
  Also: one sweep *call* runs two sweeps, and the window bound is conditional on a
  scheduler that correctness deliberately does not depend on.
- **The window argument was borrowed, not transferred** (§3.2A). It holds — for a
  stronger and simpler reason than settlement's buffer, now derived. `W_start ≤
  min(entered_at)` is necessary **and** sufficient; the day of buffer is slack.
- **T1's named mutation does not bite as written** (§9A). Two runs milliseconds apart
  round to the same integer, so the test passes under its own defect. Rewritten as T1′
  with both sides computed. T4 needs a missing row, T8's ceiling row is a measurement
  rather than a criterion, and four rows are added (T9–T12).
- **Four worked examples audited by hand** against `concurrency.py:_sweep`; all four
  follow their own rule (§3.2A). Cases 2–4 depend on an unstated precondition —
  `allows_batch_working = True` — without which a T3 fixture computes different numbers.

Nothing in D1–D7 was reopened. Every finding above is a mechanism, a totality, or a
derivation; no product semantics changed.

**Round 4b — 2026-08-20, plan 1 projection r0 folded (one upstream finding).** The
projection's L3: §2.3A's corrected absence claim was itself scope-limited — the
typicals statement's window cutoff is a `datetime.now(timezone.utc)` read on the E-P
and E-A request paths, in a callee module the directory-scoped grep never entered
(the verification-scope rule biting a fourth time in this family: directory, term
set, suite, now **call graph**). §2.3A carries the third correction; §1A HC-3A's
scope bullet carries the resolution (additive `now` parameter, E-P/E-A pass
`ctx.now`, defaulted clock read survives only outside this pipeline's surfaces;
guarded by plan 2 C11). Also fixed, class-swept: two citations of
`_step_transition_core.py:apply_step_transition` — the defined symbol is
`_apply_step_transition`. Plan-level amendments (golden composition, the
`_apply_step_transition` close path for T2's fixture, assertion-order and
stub-clock corrections) live in `plans/plan_1.md` and its Review log, not here. No
semantics changed; D1–D9 untouched.

**Round 4d — 2026-08-20, phase 1 re-review r4 folded (one upstream correction, and
it corrects round 4c's own correction).** HC-3A's Type bullet has now named a
failure site three times; the first two were never probed in both directions.
Round 4 said the sweep raises; round 4c said the sweep cannot fire; **both are
false as generalizations** — the naive bind is shifted by the *client host's* UTC
offset, so the un-guarded loader either loses the live term silently or raises from
the sweep, depending on the host and the fixture. Measured by varying `now` on one
host (r4) and by varying `TZ` on one fixture (coordinator: the guard's own mutation
bites at `+02:00` and **does not bite under `TZ=UTC`**). The bullet now records the
mechanism and obliges the guard to be distinguishable from the failure it pre-empts.
Sixth instance on this project of a defect class arriving inside the correction of
its own class — and the first where the correction was the coordinator's. No
semantics changed; D1–D9 untouched.

**Round 4c — 2026-08-20, phase 1 review r1 folded (two upstream corrections).**
(1) HC-3A's failure-site claim retired: on the configured driver a naive bind never
reaches `concurrency.py:_sweep` — it is accepted at the SQL boundary and silently
narrows the fetch, so the un-guarded loader loses its live term with no error. The
contract is now the loader's own boundary guard, fails-closed, with its named
mutation measured (review r1 S1, three probes; the implementer's unplanned guard is
absorbed as contract, not merely tolerated). Lesson, master plan §5: **a claim that
names where a failure surfaces is a mechanism claim and must be probed at that site
before it ships** — this one was written at the gate and survived it unprobed.
(2) §3.1's attribution formula restated in settlement's own form
(`credited_user_id or created_by_id`, review N1/N2): the loader must match
`_recompute_step_time_totals`, not the SQL `COALESCE`, and the two differ only on
`""`, which no shipped writer produces. No semantics changed; D1–D9 untouched.

**Round 4a — 2026-08-20, gate cards ratified; coordinator fold. Gate: PASS.** Owner,
verbatim: *"about the owner cards the recommendations are the correct approach."*
Card 1 → **D8** (ship the settlement window, disclose it as the third decrease mode);
card 2 → **D9** (the frozen blocks freeze whole — the one deliberate behaviour change
beyond liveness in this pipeline). Folded: §3.3A C.1, §6A C, §4.1A B, §5.3, §5.4, §4.2,
§10.3; **T13 added** to §9A (two rows, two serializer sites). One coordinator finding
at the fold, from the sealed calibration file (seal H3): §8 read "the three projection
nodes" above a list of four slugs from round 1 onward, and the round-4 sweep added a
fifth node to that list without catching the count — corrected to "four", with the
provenance note left inline. Status → **RESOLVED and PLAN-READY (round 4a)**.
Calibration outcome and the gate's tracker row live in `master_plan.md` §3/§7. Next:
**implementation planning**.

**Round 4e — 2026-08-20, plan 2 projection r0 folded (one upstream finding).** The
projection's U1: §2.3A's *corrected* absence claim was scope-limited again, one package
further out than round 4b's. `_common.py:_load_preview_inputs` — imported by
`get_task_budget_status.py:get_task_budget_status` and
`get_task_budget_status_worker.py:get_task_budget_status_worker` — calls
`_common.py:today_utc` and feeds it to `configuration.py:resolve_economics_selection`.
That is a wall-clock read on the E-B, E-P and price-scenario request paths, and it is
the **same construct** as E-A's `today_utc()`, the one instance §2.3A did name. Fifth
instance of the verification-scope rule in this family (directory → term set → suite →
call graph → the command package a query service imports from). §2.3A carries the
fourth correction; §1A HC-3A's scope bullet carries the resolution (additive `now`
parameter with a default that preserves the command-side callers' read; the two query
services pass `ctx.now`). Verified at source by the coordinator before folding.
**Disposition — coordinator's, no owner card:** the conversion enters **plan 2's**
perimeter (task 4b, criterion C12) rather than being recorded as a scoped-out gap,
because converting E-A's instance and not this one would leave a live counterexample to
HC-3A's "within the three surfaces, one request is one `now`" — a cross-surface `status`
disagreement at a UTC date rollover, on the branch where `actual_worker_seconds` is
`None` and HC-5's own tests cannot see it. This widens phase 2's file perimeter into
`services/commands/item_economics/`, named explicitly in `plans/plan_2.md` §3 and §7.
No product semantics, shipped promise, or D1–D9 decision moved.

**Round 4f — 2026-08-20, plan 2 review r3 folded (one upstream finding).** The review's S1:
§4.1A C lists `allowance_seconds` as non-worked-derived, which is true only while no
**excluded** step holds an open working record — `divide_production_budget` sums
`total_working_seconds` over excluded steps into `charged_seconds`, and from phase 2 those
rows carry the live figure. It holds today because
`_step_transition_core.py:_apply_step_transition` closes the open record unconditionally on
every transition, so **no live defect exists**; the precondition is recorded as **§4.1A C.1**
because §4.1A C is what phases 3–4 cite, and the failure mode is silent (a drifting
allowance looks exactly like a smaller one). Plan 2 C6 row 1 gains the assertion that pins
it. No product semantics changed; no D1–D9 decision reopened.
