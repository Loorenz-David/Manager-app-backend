# Intention: Live Clock for Working-Time Economics (live worked-seconds basis for the present-tense read surfaces)

```
status: RESOLVED (round 3, 2026-08-20) — 0 owner cards open (D5–D6 ratified §10.2;
        D7 recorded round 3). Coordinator review of 2026-08-19 folded (all six
        findings, owner-dispositioned). NOT plan-ready until the mechanism-inventory
        gate passes.
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
  (`calculator.py:20`) is **not** bumped: its contract covers persisted formula
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

---

## 2. Grounding — what exists today (verified 2026-08-19, all paths read this session)

### 2.1 The ledger: state records, and what "settled" means

`step_state_records` (`models/tables/tasks/step_state_record.py`): `state` (:39),
`entered_at` (:76), `exited_at` (:77, **nullable — NULL means running now**),
`recorded_time_marked_wrong` (:75), `credited_user_id` (:91, attribution is
`COALESCE(credited_user_id, created_by_id)`), `is_deleted` (:92). Exactly one open
record per step at a time — the transition core closes the previous record before
opening the next (`latest_state_record` is singular).

`task_steps.total_working_seconds` is recomputed at each transition by
`_recompute_step_time_totals`
(`services/tasks/analytics/process_step_transition.py:185-258`): it gathers the
step's records in `TIME_BEARING_STATES = {WORKING, PAUSED}`
(`domain/task_steps/constants.py:11-14`), runs each credited user's records through
the sweep, and **sums only closed contributions** (`c.is_open` rows are skipped at
`:236`). The column is therefore settled-only *by that filter*, per state:
`int(round(Σ closed working shares))`.

### 2.2 The crediting rule: the concurrency sweep

`averaged_seconds_by_record(intervals, now)`
(`domain/analytics/concurrency.py:79-93`, sweep at `:37-76`) — pure, deterministic:

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
window_end, now)` (`services/queries/analytics/averaged_time.py:71-…`) is the IO
wrapper: fetches one worker's time-bearing records overlapping a window, runs the
sweep, returns per-record `RecordContribution` rows carrying `seconds`, `is_open`,
`step_id`, bucketed `state`, and `marked_wrong`.

### 2.3 The precedent: live `now` already exists in a read path

`get_worker_daily_step_breakdown` (`services/queries/worker_stats/…:211-214`) — a
query-layer read endpoint — already calls `compute_record_contributions` with
`now = datetime.now(timezone.utc)`. The "no clock in the read layer" property the
frontend worried about is a property of the **item-economics query family**, not of
the read layer as a whole. This pipeline extends an existing, shipped pattern; it does
not breach a covenant. (`list_workers_totals.py` is the second precedent.)

### 2.4 The consuming surfaces (the freeze, per endpoint)

All three compute worked time from the settled column and only from it:

- **E-P** `GET /tasks/{id}/production-time`
  (`get_task_production_time.py:23-95`): composes `get_task_budget_status` with the
  task's steps and `divide_production_budget`; section `worked_seconds` is
  `Σ total_working_seconds` per section (`budget_division.py`,
  `group_steps_by_section`), verdict `share_state = "over_share" if worked > allowance`.
- **E-B** `GET /tasks/{id}/budget-status`: manager face and the independent
  worker/seller face (`get_task_budget_status_worker.py`, A7) both delegate the
  evaluated computation to the shared `_build_evaluated_status`
  (`get_task_budget_status.py:135-176`), whose
  `actual_seconds = SUM(total_working_seconds)` (`:141-150`) feeds Q4 minutes,
  remaining, percent, variance, and — manager only — `consumed_cost_minor` /
  `variance_cost_minor` through the pure calculator.
- **E-A** `GET /tasks/budget-allocations` (`get_task_budget_allocations.py:100-283`):
  batch-loads steps (which carry the settled column) and calls
  `divide_production_budget` per task — the worker step cards' source.

The frontend's own handoff traced the six fields that must move together on E-P:
section `worked/left/share_state` and budget `actual_worker_seconds/minutes`,
`remaining_worker_minutes`, `percent_consumed`. §4 generalizes that list per surface.

### 2.5 The settled consumers that must NOT move

- `item_cost_results` — durable end-of-episode record, recomputed by the analytics
  worker at READY/terminal from settled data (`process_step_transition.py:87-97`).
- Daily analytics rollups (`reconcile_user_time.py` family) — settled at transitions.
- `task_steps.total_cost_minor` — salary-priced, persisted at settlement
  (`process_step_transition.py:249-256`); worker-compensation domain, out of scope.
- The `final` block of E-P (`division_serializers.py`,
  `_serialize_production_time_final`) — a frozen result record by definition. Its
  `percent_consumed` key is wired to the request's status percent today; that wiring
  is left untouched (§5.3).

This answers the frontend's third open question ("does anything else consume these on
a settled basis?"): yes — the four above — and none of them reads through the
endpoints this pipeline changes; they read persisted columns this pipeline never
writes.

### 2.6 In-flight neighbour

The `simple_valuation_editor` pipeline (intention resolved 2026-08-19) added
`get_task_price_scenario.py` / `price_scenario.py` in the same query family. Its
payload deliberately carries no progress block (its D5 ratified gross-of-progress),
so it does not consume the live figure in v1 — but as of its phase-2 implement round
(checkpoint `48705b3`, the same day this intention was shaped) the perimeters are
**not disjoint**: `get_task_price_scenario` resolves its task through
`get_task_budget_status` (`get_task_price_scenario.py:43-45`, called at `:191`) — the
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
        where u       = COALESCE(credited_user_id, created_by_id) of the open record
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
   (the same buffer settlement uses, `process_step_transition.py:230`).

Each case is an enumerated test row (§9, T3).

**Window note (round 3, owner context).** Operationally, an open working record today
cannot be older than the previous midnight UTC: every clock source — HTTP clock-out,
Connecteam, and the overnight sweep
(`services/tasks/users/auto_clock_out_open_shifts.py`) — closes open working records
through the same transition (`_clock_worker_shift.py:200-224`, `SHIFT_ENDED`), the
owner-built safeguard for forgotten steps; the company does not work nights, and
logout auto-closes as well. With the 1-day buffer, that makes the anchor choice
unreachable in practice. The `min(entered_at)` anchor is specified anyway: the
document must give one instruction, and correctness must not hang on a scheduler in
another domain (charter rule 11 — safety binds at the boundary). If the company ever
runs a night shift, or the sweep misses a night, nothing here needs revisiting.

### 3.3 The no-snap invariant

Because M1 and settlement are the **same function** evaluated at two moments, closing
a record must not move the number — it moves the share from the live term into the
settled column:

```
| live_worked_seconds(s, t⁻)  −  total_working_seconds(s) after the transition
  that closes the record at t |   ≤   1 second per credited user
```

The ≤ 1s slack is rounding locus only: settlement rounds the sum of all closed shares
once (`int(round(Σ))`, `:245-246`), M1 rounds the settled column and the open share
separately. Nothing else may contribute drift — a violation beyond the slack means the
live computation and settlement have diverged, which is exactly the defect HC-2
exists to prevent. Tested as T2, the load-bearing test of this pipeline. (This is
also the operational meaning of the taxi rule: the meter and the receipt use one
tariff, so the receipt never surprises.)

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
(`func.sum(TaskStep.total_working_seconds)`, `get_task_budget_status.py:141-150`).
Under M1 that aggregate can no longer be the sole producer of the task figure. Two
resolutions are arithmetically identical — replace it with a per-step fold over the
loader's output, or keep it for the settled term and add the loader's open shares on
top — and the planner picks **one** and records it before any implementer session.
What is contractual either way: the per-step figures and the task figure derive from
the same loader output (HC-5), never from two independent reads.

### 4.2 What stays settled on those same responses

`allowance_seconds`, `typical`, section membership and ordering, `allocation_method`,
`status` readiness values, the E-P `final` block, and every field not derived from
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

- **`final` (E-P)** stays a frozen record. Its `percent_consumed` key is today wired
  to the request-level percent; that wiring is deliberately untouched. Consequence,
  named rather than hidden: in the rare state where a result exists *and* a step is
  open in `working` again, `final.percent_consumed` ticks while the other `final`
  fields stay frozen — exactly what that wiring already does for settled changes
  after the result froze. Changing `final`'s composition is out of scope (HC-4).
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
exactly two ways: the ≤ 1s rounding sense of §3.3, and the D7 disowning events
(mark-inaccurate, record/step deletion), where it drops by the whole disowned share
at once, deliberately. Client smoothing must snap down to the served value, never
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
- **Graph delta at closeout:** update the three projection nodes'
  descriptions (`projection-item-economics-task-budget-status`, `…-worker`,
  `…-task-budget-allocations`, `…-task-production-time`) whose current text asserts
  "live non-deleted task-step seconds" from the settled column, plus `reads_from`
  edges to the step-state-record table node as the graph vocabulary allows.

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
