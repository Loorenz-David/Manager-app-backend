# Intention: Simple Production Budget Division (typical section times + per-step budget allocation)

```
status: phase 1 CLOSED/APPROVED (D1–D10) · phase 2 CLOSED/APPROVED 2026-08-17 (D11–D16);
        0 owner cards open. See §12.
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-16 (no raw_intention.md; the conversation
             followed the two frontend component mockups: production-time widget and
             worker task-step cards)
date: 2026-08-16 (phase 1) · 2026-08-17 (phase 2, §12)
round: 9 (phase-1 rounds 0–7; phase-2 rounds 8–9)
```

---

## 1. Objective & hard constraints

Two **read-only** query surfaces, no schema change, no write path:

1. **Typical section time** — per working section, the median settled working time of a
   completed step, derived from data the step system already stores. Answers: *"how long
   does Upholstery typically take per item?"*
2. **Per-step budget allocation** — divide one task's production time budget
   (`allowed_worker_minutes` from the committed item-cost evaluation) across the task's
   steps, **weighted by the sections' typicals**, so each step has its own allowance,
   its own "time left", and an on-track/over-share state. Answers: *"is this step eating
   other sections' time?"*

Consumers: the *Production time* widget on task details
(`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_component_20260816.md`,
§6 of which currently declares the typical line OMITTED in v1 — this pipeline is what
un-omits it) and the worker task-step cards (owner mockup 2026-08-16), plus any future
component that surfaces steps.

**Hard constraints:**

- **HC-1 — Independence.** New modules only. No change to `serialize_step`
  (`app/beyo_manager/domain/tasks/serializers.py:158`), to any existing endpoint's
  payload, to any published contract in `Application_contracts`, or to the
  item-cost-calculation v1 surfaces closed on 2026-08-15. Deleting this feature must
  leave zero residue. (Owner, 2026-08-16: "this implementation must remain independent
  and scalable independently.")
  **HC-1a — enumerated exception (D10, owner-authorized 2026-08-16):** mounting E2 on
  the item-economics router trips the v1 route-mirror tripwires by design; exactly
  FOUR v1 artifacts change, by addition only: the `_EXPECTED_ROUTES` hand-written
  literal (+1 row) and its count assertion (23 → 24) in
  `test_phase9_item_economics_route_mirror.py`; `routers/README.md` (one Quick
  Index row + one detail section); and — added round 6, coordinator consumption of
  implement r1 — the second mirror in
  `tests/unit/routers/api_v1/test_item_economics_router.py` (`_ROUTES` /
  `_ALL_ROLE_ROUTES` / the authoritative route-pair table), same route family, same
  D10 rationale, discovered red after E2 landed. Each is reverted by one edit if
  the feature is deleted. No other v1 artifact may change.
- **HC-2 — Read-only, derive-on-read.** No new tables, no migrations, no persisted
  derived values, no workers/events. Consequence: `CALCULATION_VERSION`
  (`app/beyo_manager/domain/item_economics/calculator.py:20`) is **not** bumped —
  its contract covers persisted formula outputs, and this feature persists nothing.
- **HC-3 — Time only, never money.** Both endpoints serve all four roles
  (ADMIN, MANAGER, WORKER, SELLER) and therefore may never carry a monetary field —
  same audience rule as the worker budget-status surface
  (`app/beyo_manager/domain/item_economics/serializers.py:197-207`, the deliberately
  enumerated worker contract).
- **HC-4 — One formula home.** The allocation arithmetic is a pure domain function
  (sibling of the item-economics calculator, same guard style), unit-tested directly;
  the endpoint's serializer computes nothing. Both frontend components read
  `share_state` from the server rather than re-deriving it — two apps re-implementing
  the threshold is how "on track" forks.
- **HC-5 — Swappability is contract-level.** Responses name their derivation
  (`method`, `window_days`, `allocation_method`) so future refinements (configured
  typicals, per-category medians, dynamic reallocation) change a labelled value, never
  the payload shape.

---

## 2. Grounding — what exists today (verified 2026-08-16, all paths read this session)

### 2.1 The step time source (authoritative for typicals)

`task_steps` (`app/beyo_manager/models/tables/tasks/task_step.py`) carries per step:
`working_section_id` (:65), `state` (:52, enum `pending / working / paused / blocked /
completed / skipped / failed / cancelled` —
`app/beyo_manager/domain/task_steps/enums.py:4-12`), `total_working_seconds`,
`recorded_time_marked_wrong` (:73), `closed_at` (:95), `is_deleted`. Existing index:
`ix_task_steps_workspace_task_state (workspace_id, task_id, state)` (:129).

`total_working_seconds` is recomputed from **settled (closed) state records only**,
concurrency-averaged per credited user
(`app/beyo_manager/services/tasks/analytics/process_step_transition.py:161`,
`_recompute_step_time_totals` docstring: "settled (closed) records only, matching the
daily totals"). Marked-wrong time is diverted to `inaccurate_working_seconds`, so
`total_working_seconds` on an accurate step is clean; a step whose record was flagged
carries `recorded_time_marked_wrong = true`.

### 2.2 The rejected source — `working_section_daily_work_stats`

(`app/beyo_manager/models/tables/analytics/working_section_daily_work_stats.py`,
columns via the `AggregateMetrics*` mixins,
`app/beyo_manager/models/base/aggregate_metrics.py`: `total_working_seconds`,
`total_completed_count`, …, one row per section per day, written by
`reconcile_user_time.py`.) The owner proposed it as the typicals source; rejected for
three measured reasons, recorded so the question is not reopened:

1. **Day-boundary mismatch** — a day's `total_working_seconds` credits the day worked;
   `total_completed_count` credits the day completed. A step worked Friday, completed
   Monday, splits numerator and denominator across rows.
2. **Polluted numerator** — seconds spent on steps that end `failed`/`cancelled`/
   `skipped` accumulate forever without ever incrementing a completion.
3. **Mean, not median** — repair time is long-tailed; "typically takes" is a median
   claim, and the daily aggregate cannot yield one.

The per-step rows (§2.1) contain the exact per-completed-step durations, so the median
is directly computable. PostgreSQL 18.4 provides `percentile_cont`.

### 2.3 The budget source

The committed-current evaluation row per task: `item_cost_evaluations` filtered
`kind = COMMITTED AND superseded_at IS NULL AND is_deleted = false`, giving
`allowed_worker_minutes` (Decimal, quantized 0.01) — same row budget-status reads
(`app/beyo_manager/services/queries/item_economics/get_task_budget_status.py:102-110`).
Task-level consumption is `SUM(task_steps.total_working_seconds)` over the task's live
steps (`:138-147`) — the identical column the per-step display itemizes, so per-step
figures and the task headline reconcile by construction.

Readiness statuses for tasks without a committed evaluation come from
`resolve_item_economics_status`
(`app/beyo_manager/domain/item_economics/configuration.py:129-169`), the twelve-value
vocabulary of the operational handoff §4.

### 2.4 The consuming surfaces

- Task details steps: `GET /api/v1/tasks/{task_id}/steps`
  (`app/beyo_manager/routers/api_v1/tasks.py:936`), roles ADMIN/MANAGER/WORKER/SELLER;
  every step payload already carries `working_section_id` — the client-side join key.
- Worker home feed: `list_working_section_steps` composing `step_light_bundle`
  (`app/beyo_manager/services/queries/tasks/step_light_bundle.py`) — lists steps of
  **many tasks** at once. This is why allocation must be batched server-side: computing
  an allowance needs the task's budget **and all sibling steps**, which for a feed of N
  cards done client-side means N budget-status + N step-list calls.
- Response envelope: `build_ok` → `{"data": …, "ok": true, "warnings": []}`
  (`app/beyo_manager/routers/http/response.py:6-11`).

### 2.5 The step-set mutation surfaces (verified 2026-08-16, owner-requested alignment)

The three flows that change a task's step set mid-flight, and what each does to the
rows M2 reads:

- **Add** — `POST /api/v1/tasks/{task_id}/steps` → `add_task_steps`
  (`app/beyo_manager/services/commands/task_steps/add_task_steps.py`): creates steps
  `state=PENDING` with `working_section_name_snapshot` copied from the live section
  (:125-140), may auto-assign a worker and reopen a READY task to WORKING; refused on
  terminal tasks (:93-94). → the new step is in M2's **allocated set** on the next
  read, exactly D8's re-assignment case.
- **Remove** — `DELETE /api/v1/tasks/{task_id}/steps` (batch) and
  `…/steps/{step_id}` → `remove_task_step(s)`
  (`app/beyo_manager/services/commands/task_steps/remove_task_step.py:131-138`):
  **soft-delete AND state flip in one write** — `state=SKIPPED, is_deleted=true,
  closed_at=now`, open state records closed (:140-148). A removed step is therefore
  NOT in M2's excluded set — it is out of M2's universe entirely (the non-deleted
  filter), see the M2 note below.
- **Force-ready** — `force_task_ready`
  (`app/beyo_manager/services/commands/tasks/force_task_ready.py:75-78,162`):
  transitions `pending/working/paused/blocked` steps to **SKIPPED without deleting
  them** → these ARE M2's excluded set, charged per D8. Normal worker transitions to
  `failed`/`cancelled` (`transition_step_state.py:58-68`) likewise excluded-not-
  deleted. (`PATCH …/steps/ready-by-at` → `update_task_step_ready_by_at` was also
  checked: it writes per-step `ready_by_at` deadlines only — no state, no time, no
  allocation impact.)

---

## 3. Mechanism contract M1 — typical section time

For workspace `W`, per working section `S` (every non-deleted section of `W` appears in
the output, including sections with zero samples). **The sample unit is a
(task, section) group, not a step** (owner-settled 2026-08-16, D9): a re-assigned
section gets a second step on the same task, and that rework is work the section
missed — it belongs inside that task's total for the section, not in the sample pool
as a fake short duration.

```
contributing steps (per group) =
              task_steps rows where
                workspace_id = W
              AND working_section_id = S
              AND state = 'completed'
              AND is_deleted = false
              AND recorded_time_marked_wrong = false
group (one per (task_id, S)) qualifies iff
                it has ≥ 1 contributing step
              AND MAX(closed_at) over its contributing steps
                    >= now() - interval '90 days'
              -- window admission is GROUP-level on the LATEST close; individual
              -- per-step closed_at admission is FORBIDDEN — it would degenerate an
              -- old-first-pass + recent-rework task into a rework-only sample,
              -- exactly the skew D9 exists to avoid
group value  = SUM(total_working_seconds) over its contributing steps
sample_count = COUNT(qualifying groups)
typical_worker_seconds =
    NULL                                          if sample_count < 5
    round_half_even(percentile_cont(0.5) WITHIN GROUP
                    (ORDER BY group value))            otherwise  → int seconds
    -- rounding locus (P2 pin, round 5): percentile_cont over integer input
    -- returns double precision, and PostgreSQL's round() on double IS half-even,
    -- as is Python's round(); a ::numeric cast switches to half-away-from-zero
    -- and silently moves .5 ties by one second. Round the double with SQL
    -- round() or Python round(); NEVER via ::numeric.
```

A `completed` step with `closed_at IS NULL` never contributes and can never admit a
group (`MAX(closed_at)` NULL fails the window) — deliberate (N5, round 5): a
completed step without a close timestamp is malformed data and silence is preferable
to guessing its date; 0 of 1703 completed rows are affected today.

Fixed parameters (owner-settled 2026-08-16, §10.1 D1): window **90 days**, minimum
sample **5** (groups), statistic **median**. They are constants in the query service,
echoed in every response row as `window_days` / `min_sample_size` / `method:
"median_completed_section_totals"` — the swappability hook (HC-5). Exclusions are
exact: only `completed` steps contribute (a `skipped` or `cancelled` step is not
evidence of how long the work takes), and a marked-wrong step is excluded entirely
rather than partially trusted. An in-flight rework step contributes nothing until it
completes; the group's value simply grows on a later read (computed-on-read, HC-2).

**Accepted MVP approximation (D9 note):** in M2, a task currently holding two live
steps of the same section weights that section twice with a typical that already
includes expected rework — a generous over-allocation, rare at allocation time
(rework usually appears after the first pass completes, and D8 re-divides then).
Tighter rework weighting is a future `method`/`allocation_method` refinement, not v1.

## 4. Mechanism contract M2 — per-step budget allocation

Inputs, per task `T`: budget `B_seconds` from the committed-current evaluation
(§2.3). **B2 contract (round 5):** `allowed_worker_minutes` is `Numeric(12,2)`, so
`× 60` is fractional whenever the cents are not a multiple of 5;
`B_seconds = int((Decimal(allowed_worker_minutes) × 60).quantize(Decimal("1"),
rounding=ROUND_HALF_EVEN))`, computed **before** `C` is subtracted — the house
rounding of `calculator.py`. (`195.01` → `11701`.) The task's non-deleted steps are
partitioned by state (owner-settled §10.1 D8):

- **allocated set** — states `pending, working, paused, blocked, completed`: these
  carry weights and receive allowances.
- **excluded set** — states `skipped, cancelled, failed`: they receive no allowance,
  but any worked time they consumed is charged against the budget first — a failed
  step that burned 40 minutes really did spend them, and pretending otherwise would
  let the remaining allowances promise time that no longer exists.

```
charged:      C = Σ total_working_seconds over the excluded set
distributable: D_seconds = max(0, B_seconds − C)
weights (allocated set only; B3/B4 contracts, round 5):
              w_i = t_i                        if t_i is not NULL AND t_i > 0
              w_i = median of the allocated    if the first rule fails for i and
                    set's t_j that pass it        ≥1 allocated sibling passes it
              w_i = 1 for all i                if no allocated step passes it
              -- t_i = 0 is treated as "no usable typical" (falls through the
              -- ladder), so Σw > 0 whenever the allocated set is non-empty
              -- even-count fallback median = interpolated mean of the two middles
empty allocated set:
              no allowances are produced; D remains undistributed (visible only
              as the task-level figures); every excluded step still reports
              share_state "excluded"
arithmetic:   weights, raw shares and fractional parts are computed in EXACT
              rational arithmetic (fractions.Fraction) — no float anywhere;
              weights are never rounded (only allowances are)
raw share:    r_i = D_seconds × w_i / Σ w_j
allowance_i:  largest-remainder rounding of r_i to int seconds such that
              Σ allowance_i = D_seconds exactly;
              remainder units assigned by largest fractional part,
              ties broken by (sequence_order ASC NULLS LAST, client_id ASC)
left_i:       allowance_i − total_working_seconds_i        (negative allowed)
share_state:  "no_budget"   if T has no committed-current evaluation
              "excluded"    if the step is in the excluded set
              "on_track"    if worked_i ≤ allowance_i      (allocated set)
              "over_share"  if worked_i >  allowance_i     (allocated set)
```

Excluded steps still appear in the E2 response (real rows, real `worked_seconds`) with
`allowance_seconds: null`, `left_seconds: null`, `share_state: "excluded"`.

**Deletion is a different door than exclusion (grounded §2.5).** A *removed* step
(`is_deleted=true`, which the remove services pair with `state=SKIPPED`) is not
excluded-and-charged — it leaves M2's universe entirely, exactly as it leaves
budget-status's task actual (`get_task_budget_status.py:138-147` sums non-deleted steps
only, approved v1 behavior). Its worked seconds are erased from the task's books on
both surfaces simultaneously, so E2 and budget-status cannot disagree. The charged set
`C` is precisely the **non-deleted** `skipped/cancelled/failed` steps — produced by
`force_task_ready` and by worker `failed`/`cancelled` transitions, never by the remove
endpoints. Consequence table:

| Manager action | Step afterwards | M2 treatment |
|---|---|---|
| add step | `pending`, non-deleted | allocated set, gets a slice (D8) |
| remove step | `skipped` + **deleted** | out of universe; its time erased from B's consumption too |
| force task ready | `skipped`, non-deleted | excluded; worked time charged into `C` |
| worker fails/cancels step | `failed`/`cancelled`, non-deleted | excluded; worked time charged into `C` |

Named properties (each a test):

- **P-SUM** — **when the allocated set is non-empty**, allowances sum to the
  distributable budget exactly (`Σ allowance = max(0, B − C)`); no step can be
  granted the task's whole remainder (the defect the owner named: "we can't use all
  the budget because there are working sections after this that also need time"),
  and no excluded step's consumption is double-promised. (Empty allocated set: no
  allowances exist, per the M2 empty-set rule above.)
- **P-PROP** — two allocated steps with typicals in ratio k have allowances in ratio k
  (before rounding); all-equal or all-missing typicals degrade to an equal split.
- **P-DET** — the function is deterministic: same inputs, same output, including the
  rounding-remainder assignment (rule-6 class: time division is silent-failure risk;
  the tie order is part of the contract, not an implementation detail).
- **P-FOLLOW (D8)** — the allocation follows the live step set on every read: a step
  the manager adds joins the allocated set and receives its slice; a step that ends
  skipped/cancelled/failed leaves it, its unconsumed share flowing to the survivors
  and its consumed seconds staying charged (C). This is deliberate motion — targets
  move when the *step set* changes.
- **P-STABLE (consumption)** — what does NOT move allowances is consumption inside an
  unchanged step set: a completed step keeps its full slice however far under or over
  it landed; savings and overruns surface in `left_i` and at task level, never as
  reflowed allowances (D6). Consumption-based reallocation remains a future
  `allocation_method` value.
- Recomputed on every read from the current step list; nothing is cached or
  persisted (HC-2).

`worked_i` is the settled `total_working_seconds` (§2.1). Live ticking of the open
working interval stays client-side, per the component handoff §5 — this contract
serves stored truth only.

## 5. API contracts

### E1 — `GET /api/v1/working-sections/typical-times`

(Mount corrected in round 3: a `working_sections` router already exists at prefix
`/api/v1/working-sections` — E1 belongs there, not under `/tasks`.)

Roles: ADMIN, MANAGER, WORKER, SELLER. Query: optional `working_section_ids`
(repeatable; omitted → all non-deleted sections of the workspace; unknown ids silently
absent from the result — owner-settled §10.1 D5: a worker fetching only their own
section must not pay for the rest).

```json
{ "typical_times": [
    { "working_section_id": "wsec…", "section_name": "Upholstery",
      "typical_worker_seconds": 3600, "sample_count": 23,
      "method": "median_completed_section_totals", "window_days": 90, "min_sample_size": 5 } ] }
```

`section_name` is the live working-section name (reference data for display), not a
snapshot. Rows with `sample_count < 5` appear with `typical_worker_seconds: null` —
absence-with-reason, so a young section renders "no typical yet" instead of vanishing.

### E2 — `GET /api/v1/item-economics/tasks/budget-allocations`

Roles: ADMIN, MANAGER, WORKER, SELLER. Query: required `task_ids` (repeatable,
1 ≤ n ≤ 50; over-limit → 422). Batched: one call per screen of worker cards, or one
task id from the production-time widget. Unknown/deleted task ids are **omitted** from
the response (batch-read semantics; the client notices absence by key). Tasks visible
to the caller by the same workspace scoping every task read uses.

Per returned task:

```json
{ "budget_allocations": [
    { "task_id": "tsk_…",
      "status": "ok",
      "allowed_worker_minutes": "195.00",
      "actual_worker_seconds": 9600,
      "remaining_worker_minutes": "35.00",
      "allocation_method": "static_proportional_v1",
      "steps": [
        { "step_id": "tsp…", "working_section_id": "wsec…",
          "section_name_snapshot": "Upholstery",   // string | null — nullable column
                                                   // (task_step.py:84), serialized as
                                                   // stored, no coalescing (N2 pin)
          "typical_worker_seconds": 3600,
          "allowance_seconds": 3600, "worked_seconds": 1500,
          "left_seconds": 2100, "share_state": "on_track" } ] } ] }
```

- `status` is the twelve-value economics vocabulary (§2.3). When it is not
  `ok`/`infeasible`: `allowed_worker_minutes`, `remaining_worker_minutes`,
  **`actual_worker_seconds`** (round 7, review N-h: mirrors budget-status's
  `_empty_status`, which T3 required E2 to follow), `allowance_seconds`,
  `left_seconds` are `null`, `share_state` is `"no_budget"`, and the steps still
  list with `typical_worker_seconds` + `worked_seconds` — the card degrades to
  typical-or-nothing exactly as the component handoff specifies; a client showing
  consumed time on an unevaluated task sums `steps[].worked_seconds`.
- **No monetary field, any role** (HC-3). This endpoint is time-only by contract, not
  by role-gating — there is nothing to gate.
- Decimal minutes serialize as strings (repo convention, `_decimal`); seconds are ints.

---

## 6. Degradation & consistency semantics (binding on consumers, documented in handoff)

- Section without a typical: E1 row present with `null`; E2 weights fall back per M2.
  Frontend renders worked time without an "of X" — never an even-split *typical*.
- Task without committed evaluation: E2 `share_state: "no_budget"`, steps still carry
  typicals — worker cards on unevaluated tasks show typical-based progress only.
- Skipped/cancelled/failed steps: listed with real `worked_seconds`,
  `share_state: "excluded"`, null allowance — the UI shows what they consumed without
  pretending they still hold a slice (D8).
- **On evaluated tasks (status `ok`/`infeasible`)**, E2's `actual_worker_seconds`
  equals the sum of its own `steps[].worked_seconds` by construction (same column,
  same instant, one query) — unlike the two-call pairing in the existing component
  handoff, this surface cannot skew against itself. (On unevaluated tasks the field
  is `null` per §5 as amended round 7.)
- Typicals move slowly (90-day median): frontend caches E1 per session/TTL; E2 is
  fetched per screen. Nothing here invalidates the existing two-call design of the
  production-time widget — E2 *supplements* budget-status, it does not replace it.

## 7. Non-goals (v1)

- Per-item-category typicals ("upholstery on a sofa vs on a chair") — future `method`.
- Manager-configured typicals — future `method`; the contract already carries the field.
- Dynamic remaining-budget reallocation — future `allocation_method` (§10.1 D6).
- Persistence, materialized stats, workers, events, alerts, notifications.
- Any change to how `total_working_seconds` is credited (averaging, accuracy flags).
- Embedding typicals in `serialize_step` or any existing payload (HC-1; owner-settled
  §10.1 D4 after explicit discussion of the alternative).

## 8. Relation to existing domains

Reads three domains, owns none of their writes: task-steps (step rows), working
sections (names), item-economics (committed evaluation + status resolution — reuse the
existing loaders/`resolve_item_economics_status` read-path where importable rather than
re-deriving status logic). Sits beside item-cost-calculation v1 (closed 2026-08-15) as
a separate pipeline with its own folder; it must not reopen any v1 artifact. After
approval, the coordinator folds the results into
`HANDOFF_TO_FRONTEND_production_time_component_20260816.md` (un-omitting §6.1 with the
real contract) and authors the worker-card component section — the frontend build
waits on this phase by owner decision ("before i ship this to the frontend i want to
tackle this 'typical' value").

## 9. Testing expectations (inherit charter standing rules)

- M2 properties P-SUM / P-PROP / P-DET / P-FOLLOW / P-STABLE as direct unit tests on
  the pure function (charter rule 3: production object shapes, not hand-built
  conveniences, where ORM rows are the input). P-FOLLOW's rows include: a failed step
  with nonzero worked seconds (its consumption charged, its weight gone), a skipped
  step with zero worked seconds (pure reflow), and the clamp case where excluded
  consumption exceeds the budget (`D = 0`, every allocated allowance 0).
- M1: fixture steps proving each exclusion independently bites (completed-only,
  marked-wrong, window edge, min-sample boundary at exactly 4 vs 5) — charter rule 2
  companion: each fixture's predicate is the only reason its expected outcome holds.
- E1/E2: role admission for all four roles; E2 batch limit; unknown-id omission;
  `no_budget` degradation shape; the money-absence assertion (HC-3) as an explicit
  key-set test on both role shapes.
- The §2.5 deletion-vs-exclusion boundary: a step removed via the remove endpoint
  (deleted+skipped, with nonzero worked seconds) appears in NO E2 row and is absent
  from E2's `actual_worker_seconds`, byte-agreeing with budget-status on the same
  fixture; a step skipped via `force_task_ready` (non-deleted, nonzero worked seconds)
  appears as `excluded` with its seconds charged into `C`. Same worked time, two
  doors, two different — both asserted — outcomes.
- Suite baseline: additive only; the item-cost v1 closure baseline
  (2249 passed / 23 failed / 1 deselected, master plan §10 of the v1 pipeline) grows by
  this phase's tests and its 23-failure list stays byte-identical.

---

## 10. Owner decisions

### 10.1 Settled (owner conversation, 2026-08-16 — recorded in owner_decisions.md)

- **D1** — Typical = median over completed steps, 90-day window, minimum 5 samples,
  null below minimum. ("sounds greate" to the recommendation triple.)
- **D2** — Per-section only in v1; no per-category split.
- **D3** — Both endpoints serve all four roles; time only, never money.
- **D4** — Standalone endpoints; NO embedding in `serialize_step` or any existing
  payload (decided after explicit discussion of the embedding alternative).
- **D5** — E1 takes an optional `working_section_ids` filter (owner request: a worker
  on Upholstery alone shouldn't fetch every section).
- **D6** — Allocation v1 is static whole-task proportional scaling of typicals to the
  budget (`allocation_method: "static_proportional_v1"`); dynamic reallocation
  deferred. ("perfect, i like it.")
- **D7** — `share_state` computed server-side so components cannot disagree on
  "on track".
- **D8** — (answers card 1, 2026-08-16, owner chose B generalized **against** the
  coordinator's A recommendation) the allocation follows the live step set: steps
  ending `skipped`/`cancelled`/`failed` leave the allocated set, and steps the manager
  **adds** mid-task join it and receive a slice — the owner's stated reason: "a
  manager not only can unassign but also assign, which should bring the allowed time
  for that re-assignment also." Consumed seconds of excluded steps stay charged
  against the budget (M2's `C`) so surviving allowances never promise spent time.
  Consumption-based reallocation inside an unchanged step set remains out (D6 stands).
- **D9** — (2026-08-16, owner-proposed) M1's sample unit is the **(task, section)
  group total**, not the individual step: all of a section's completed steps within
  one task sum into one sample. Owner's framing: "a re-assignment technically counts
  as work that was missed by the working section … a task with two task steps on the
  same working section will add both working times to obtain that 'total' working
  time." Replaces the coordinator's exclude-rework proposal (option B) — rework
  inflates the task's sample instead of polluting the pool with short durations.
  Coordinator-pinned corollaries: group-level window admission on MAX(closed_at)
  (per-step admission forbidden — see M1 comment), ≥1 contributing step qualifies a
  group, and the accepted MVP over-allocation note for same-section-twice live tasks.

None open. Card 1 (skipped-step allowance) was answered 2026-08-16 → D8.

---

## 11. Changelog

- **Round 0 (2026-08-16)** — shaped from the owner conversation following the two
  component mockups; D1–D7 recorded as settled; card 1 (skipped-step allowance)
  opened. Grounding verified against source this same session (all §2 citations).
- **Round 1 (2026-08-16)** — card 1 answered as D8 (owner chose live-step-set
  allocation, generalizing B to cover manager-added steps). M2 rewritten:
  allocated/excluded step partition, charged consumption `C`, distributable
  `D = max(0, B − C)`, `share_state: "excluded"` added; P-STABLE narrowed to
  consumption-stability and P-FOLLOW added; §9 gains the failed-with-consumption,
  skipped-pure-reflow, and clamp test rows.
- **Round 2 (2026-08-16)** — owner-requested alignment check against the step-set
  mutation surfaces (`add_task_steps`, `remove_task_step(s)`,
  `update_task_step_ready_by_at`, plus `force_task_ready` and
  `transition_step_state` found while verifying). Finding folded: the remove
  endpoints soft-delete AND set `state=SKIPPED` in one write, so "removed" ≠
  "excluded" — §2.5 added (grounding + consequence table), M2 gained the
  deletion-vs-exclusion note (deleted steps leave both E2 and budget-status's books
  together, mirroring approved v1 behavior), §9 gained the two-doors fixture pair.
  `ready-by-at` confirmed allocation-irrelevant (deadlines only).
- **Round 3 (2026-08-16)** — E1 mount corrected to the existing
  `/api/v1/working-sections` router prefix (coordinator, while compiling the master
  plan's naming registry). Also §1 consumer-list pointer: E1's earlier `/tasks/…`
  spelling anywhere downstream resolves to this path.
- **Round 4 (2026-08-16)** — D9 (owner-proposed, re-assignment skew): M1 sample unit
  changed from per-step to per-(task, section) group totals; method string →
  `median_completed_section_totals`; group-level window admission pinned; MVP
  double-weight note added to M1. Supersedes round 0's per-step sample wording
  everywhere.
- **Round 5 (2026-08-16)** — projection r0 ledger routed (handoff
  `handoffs/reviewer/2026-08-16_phase1_projection_r0_handoff.md`, verdict
  AMENDMENTS_REQUIRED). B1 → HC-1a enumerated v1-edit exception (owner card answer
  A → D10). B2 → `B_seconds` quantization contract in M2 (half-even, pre-`C`).
  B3 → weight rule requires `t_i > 0`; empty-allocated-set rule; P-SUM restated
  conditional. B4 → exact rational arithmetic (`fractions.Fraction`), unrounded
  weights, even-count fallback median = interpolated mean. P2 → M1 rounding-locus
  pin (never `::numeric`). N5 → NULL-`closed_at` sentence. N1/N2 → §5 example
  prefixes corrected (`tsp`/`wsec`), `section_name_snapshot` pinned `string | null`.
- **Round 6 (2026-08-16)** — HC-1a extended 3 → 4 artifacts: coordinator
  consumption of implement r1 verified that
  `test_item_economics_router.py::test_router_route_pairs_match_the_authoritative_route_table`
  is a second hand-written route mirror (tables at `:14`/`:48`) turned red by E2 —
  same designed tripwire family as B1, same D10 rationale, missed by projection B1
  and mislabeled "outside this phase surface" by the implementer.
- **Round 7 (2026-08-16)** — review r1 N-h folded: §5 E2's null list on
  non-`ok`/`infeasible` tasks gains `actual_worker_seconds` (implementation
  correctly mirrored budget-status's `_empty_status`, which T3 required — the
  intention's four-field enumeration was the artifact behind reality); §6's
  by-construction sum equality qualified to evaluated tasks. Carries to the
  frontend handoff fold at closeout.

---

## 12. Phase 2 — task-scoped production-time view (round 8, 2026-08-17)

```
status: shaping — 2 owner cards OPEN (C1 allocation unit, C2 section state)
round: 8
shaped_from: owner conversation of 2026-08-17 (frontend approach change, following
             the coordinator's four documentation gaps found while auditing the
             frontend handoff against shipped code)
```

### 12.1 Why this is phase 2 of THIS pipeline, not a new one

The new endpoint is a *composed read view* over M1 and M2 — the same two mechanisms
phase 1 shipped. Decisive reason: the recommended answer to card C1 changes the
allocation unit **inside `divide_production_budget`**, phase 1's core mechanism. Two
intentions both claiming authority over that function is exactly the duplication the
**one-copy rule** (master plan §6) was earned to prevent. So M2 evolves here, in one
place, and phase 1's naming registry, earned rules and closeout baseline carry forward.

### 12.2 Objective

**One** task-scoped endpoint that returns everything the *Production time* widget
renders, so the component makes a single call keyed by `task_client_id` instead of
today's four. The list's primary object is the **working section**, not the step —
because that is what the design renders as a row.

Motivation (owner, 2026-08-17): the current four calls return large payloads of which
the component uses a fraction, and the component must perform three client-side joins
to assemble a row. Consolidating also makes the surface *evolvable*: as the graph of
data behind "is this section on track" gains or loses inputs, the endpoint changes and
the component does not.

**Design 2 (worker task-step cards) needs no new backend work.** The owner confirmed
the card already renders with its existing step endpoints and its Start/transition
action; what phase 1 added — E1 filtered to the user's member sections at bootstrap,
E2 batched when the step feed loads — is precisely the progress-line data it was
missing. Phase 2 is E3 only. **But see C1:** if the allocation unit changes, E2's
per-step numbers change with it, and that card's "of 1h 0m" figure shifts meaning.

### 12.3 Additional hard constraints

- **HC-6 — One formula home, preserved and load-bearing.** `divide_production_budget`
  (`domain/item_economics/budget_division.py:78`) remains the ONLY allocation
  implementation. E3's service and serializer compute no allowance, no `left_seconds`
  and no `share_state`. If the allocation unit changes (C1), it changes *inside* that
  function, and E2 consumes the same change. A second allocator anywhere is a
  phase-2 failure regardless of test colour.
- **HC-7 — Time only, role-flat.** No monetary field, and — unlike budget-status —
  **no role-shaped payload**: all four roles receive a byte-identical body. The widget
  is time-only by contract (handoff §7), so there is nothing to redact and therefore no
  redaction branch to get wrong. Extends HC-3.
- **HC-8 — Read-only.** No tables, no migrations, nothing persisted, no worker, no
  event. `CALCULATION_VERSION` **not** bumped (HC-2's reasoning applies unchanged).
- **HC-9 — E1 and E2 survive.** E3 does not deprecate or wrap them. E1 serves worker
  bootstrap (reference data, cacheable, section-filtered); E2 serves the batched
  many-task card feed; E3 serves one task in full. Three surfaces, one formula.
- **HC-10 — No client-side join to render a row.** Every element of the design's
  section row must be present on that row's object. This is the whole point of the
  endpoint; a payload that still requires the client to zip two arrays has failed it.
- **HC-11 — Deterministic total order.** The `sections` array arrives in render order.
  The client must never need to sort it, and two calls against unchanged data must
  return the identical order (see the measured `order_list` ties in §12.4).

### 12.4 Grounding — measured 2026-08-17 on the configured database

Measured, not assumed. The `sequence_order` lesson from projection r0 (a contract
column that was NULL on 3032/3032 rows) is why each of these is a count.

**`working_sections.order_list`** — `Integer`, **nullable**
(`models/tables/working_sections/working_section.py:19`).

- Populated on **14 of 14** non-deleted sections. Unlike `sequence_order`, this column
  is real data, and it encodes the actual workshop pipeline: disassembly 1 → cleaning
  seat/wood 2 → structural repair 3 → upholstery removal 5 → padding 6 → upholstery
  installation/weaving 7 → assembly 8 → sewing 9 → wood fix 101 → ground oil 102 →
  hardwax oil 103 → photography 1000.
- **It is NOT unique: 12 distinct values over 14 rows.** Value `2` is shared by
  *cleaning seat* and *cleaning wood*; value `7` by *upholstery installation* and
  *weaving*. Ordering by `order_list` alone is therefore **non-deterministic today, on
  real data** — not in some future edge case. A tie-break is mandatory (M3.2).
- Nullable, so a newly created section can sort nowhere. NULLS LAST is mandatory.

**Steps per (task, section)** over 2833 non-deleted steps / 522 tasks:

| steps in one section | groups |
|---|---|
| 1 | 2732 |
| 2 | 49 |
| 3 | 1 |

So ~**1.8%** of section rows collapse more than one step. Multi-step sections are real
and rare — the exact profile that makes a bug ship unnoticed.

**Groups with 2+ *non-closed* steps: 0.** The section's live state is therefore
unambiguous in all current data, which means M3.4's multi-open tie-break is an
**unexercised branch** and must be pinned by fixture, never validated by production
reality.

**Four further counts, added round 10 (P3) because each is load-bearing.** §12.4's
headline "0 groups with 2+ non-closed steps" is true but describes the *rare* branch;
row 11 describes the common one.

| # | Measured | Drives |
|---|---|---|
| 11 | Of the 50 multi-step groups, **45 have NO open step** (44×{completed,completed}, 1×{c,c,c}); only **5** are {completed,pending} | M3.5b's no-open branch governs most rows in the database |
| 12 | **15** sections are referenced by live steps; **1 is soft-deleted** (`sanding`, `order_list=4`, 5 live pending steps) | M3.1's outer-join rule |
| 13 | `sequence_order` is **NULL on 2833 / 2833** live steps | the render-order authority moves to `order_list`; `min(sequence_order)` is useless as a grouped tie key |
| 14 | **0** committed-current evaluations and **0** `item_cost_results` in the whole database | the entire allocation surface is fixture-only; no production validation is possible |

Row 14's consequence is worth stating plainly: every task in this database resolves to a
non-`ok` status, so `budget.*` is null, every `share_state` is `no_budget`, and `final` is
always null on real data. "No data" is not "no coverage needed".

**Step states present:** completed 1764, pending 1039, paused 28, working 2.
**Zero `skipped`, `cancelled`, `failed`.** `EXCLUDED_STEP_STATES` has no production
instance at all today, so every excluded-path assertion must come from a fixture.
(Phase 1's projection measured 253 skipped on an earlier snapshot. **Resolved at
projection r0:** 255 skipped rows do exist — every one of them `is_deleted = true`, i.e.
produced by the *remove* door and therefore outside M2's universe per §4's consequence
table. `EXCLUDED_STEP_STATES` genuinely has **no** production instance. Independently
re-verified by the coordinator at consumption.)

### 12.5 Mechanism contract M3 — section-grouped production-time view

**M3.1 — Section set.** The distinct `working_section_id` over the task's
**non-deleted** steps. Not the workspace's section list: the component renders *this
task's* pipeline. A workspace section this task never touches does not appear.

**Including sections that have since been soft-deleted (B8, round 10).** Measured: 15
sections are referenced by live steps and **1 of them is soft-deleted** — `sanding`,
`order_list = 4`, carrying **5 live pending steps** across 5 tasks. Every source of a
section's name, order and typical filters `WorkingSection.is_deleted = false`
(`get_working_section_typical_times.py:58-61`), so that section yields no attribute row.
Section attributes are therefore resolved by an **OUTER** join: a section absent from the
live-section read renders `section_name: null`, `order_list: null`, and a `typical`
object with `typical_worker_seconds: null, sample_count: 0`. `section_name_snapshot`
(M3.9) is unaffected — it comes from the step — so the row always has a label. Such a
section sorts last under M3.2's NULLS-LAST rule; accepted, because it holds no future
work by definition. **An inner join would drop the row and violate P-COVER on 5
production tasks** — today those steps have worked 0 seconds, so the violation is
numerically invisible until someone works one of them.

**M3.2 — Order [P-ORDER].** `(order_list IS NULL, order_list ASC, name ASC,
working_section_id ASC)`. NULLS LAST because the column is nullable; `name` because the
measured ties above would otherwise be arbitrary; `working_section_id` as the absolute
determinism backstop. The frontend renders the array as given (HC-11).

**M3.3 — `worked_seconds`.** Σ `total_working_seconds` over **all** the section's
non-deleted steps, including any in `EXCLUDED_STEP_STATES` — that time was genuinely
spent by that section, and hiding it would make the rows stop summing to the headline.
Reassignments therefore sum into one row, consistent with **D9**.

**M3.4 — Section `state` and `state_entered_at`.** The state of the section's
**governing step**, defined as: its single non-closed step if one exists (measured: at
most one, always); otherwise its most recently closed step. `state_entered_at` comes
from that step's `latest_state_record.entered_at`, so §6.5's client-side live tick
works unchanged. Tie-break for the unexercised multi-open case: most recent
`latest_state_record.entered_at`, then `created_at` DESC, then `client_id` ASC.
**Enforcement note (round 11).** The backend must enforce this itself. Measured: 0
multi-step groups today disagree, and all 5 real `{completed, pending}` groups have the
pending step newest — but **that ordering is currently protected only by the frontend**
(owner, 2026-08-17: *"the reason why it hasen't happened is because so far it has been the
frontend defending this"*). An invariant enforced only by a client is not enforced. The
reachable breaking case: a manager adds a second step to a section that already holds a
pending one, and the newer step is completed first — newest-created is then closed while
older live work remains. Implementation therefore **partitions by liveness first**
(`state NOT IN TERMINAL_STEP_STATES`, imported per B7) and sorts second; sorting alone
agrees with D12 only by a coincidence nothing enforces.

**RESOLVED by D12 (round 9):** the live step governs. A section holding a completed
first pass and a pending reassignment renders `pending` — the section has work to do
again and its time keeps climbing. The furthest-state reading is the audit question and
is explicitly not what this widget answers.

**M3.5 — Allocation unit. RESOLVED by D11 (round 9): variant B — the working
section is the allocation unit.**
`divide_production_budget` allocates **per step**, weighting each step by *its
section's* typical (`budget_division.py:142-147`). A task with two Upholstery steps
therefore gives Upholstery two full Upholstery-sized weights — collectively about
twice its proportional share, squeezing every other section. Phase 1 accepted this
knowingly (the D9 MVP over-allocation note), because per-step rows made it invisible.
**A section-keyed row makes it visible**, as a single displayed number.

**Worked example that decided it** (180-minute budget; typicals Structural Repair 60,
Sanding 30, Upholstery 60; Upholstery holding two steps):

| | rejected variant A (per step) | **adopted variant B (per section)** |
|---|---|---|
| Structural Repair | 51.4 min | **72 min** |
| Sanding | 25.7 min | **36 min** |
| Upholstery (both steps) | 102.9 min | **72 min** |

Under A the second Upholstery step raises total weight 150 → 210, so the rework
**grants Upholstery 43 minutes and removes them from two sections that did nothing
wrong** — and Upholstery can rework indefinitely without ever reading late, because its
allowance grows with each pass. Under B its slice stays 72, both passes count against
it, and the overrun surfaces as `over_share`. A rework means a section is overrunning,
not that the item deserves more time: the budget is fixed by the item's price.

**Adopted rule.** Group the task's non-deleted steps by `working_section_id` (M3.1),
then pass **one unit per section** to `divide_production_budget`, weighted by that
section's typical exactly once. Allowances sum exactly to `distributable_seconds`
(P-SUM3). **No second allocator** — the existing function receives grouped units
(HC-6).

**D11 changes the WEIGHTING unit, not the CHARGING unit (B4, owner card 3, round 10).**
`C` remains Σ `total_working_seconds` over the non-deleted `skipped`/`cancelled`/`failed`
steps, exactly as M2 defines it — **§4's consequence table stands unchanged**, and D8's
stated purpose ("surviving allowances never promise time a failed step already spent")
is preserved. A section group carries a weight unless **all** its non-deleted steps are
excluded, in which case it is weightless and its row reports
`share_state: "excluded"`. The mixed case — one skipped step beside a live one — leaves
the section weighted, and the skipped step's seconds stay in the section's
`worked_seconds` (M3.3).

Because an excluded step's seconds are **already** charged against `B`, M3.5b's residual
subtracts only the section's **completed** steps' worked seconds — never an excluded
step's, which would charge them twice. (Round 9's wording moved `C` to the group unit;
that silently reversed D8 and falsified §4's table for any section still holding a live
step. It also rewrote five phase-1 assertions for no benefit. Superseded.)

**M3.5b — per-step split inside a section (D11a; rewritten round 10 from B2/B3/B5/B6/B7
and owner card 1).** E3 returns **no per-step data at all** — the owner's constraint:
*"this endpoint should not be returning the individual task steps. only what is need it
to read on the component."* The split exists solely so **E2's worker card** keeps one
number per step.

**"Live" is defined by state, never by timestamp (B7 — gate failure, contracted).** A
step is live iff `state NOT IN TERMINAL_STEP_STATES`
(`domain/task_steps/constants.py:4-9`), **imported, never re-listed** (one-copy rule).
Verified: `closed_at` is written exactly on entering terminality at all four writers, a
terminal step can never transition again, and no state is non-closed-yet-terminal — so
the two readings agree on **0 of 2833 disagreeing rows**. State is nonetheless the
faithful proxy: it is what the writers key off, it is total, and it cannot be defeated by
a missing timestamp — and §3 already contemplates the malformed `completed`-with-NULL-
`closed_at` row, which the timestamp reading would classify as the section's live step.

**The split:**

1. Each **closed** step is allowed exactly its own worked seconds.
2. The section's **open** steps share the remainder `slice − Σ closed worked seconds`,
   distributed with **equal weights** (B5 — all steps of one section share one typical,
   so nothing else is meaningful), by the same largest-remainder method, tie key
   `(sequence_order ASC NULLS LAST, client_id ASC)`.
3. If the section has **no open step** — measured: **45 of the 50 multi-step groups**,
   9× more common than the `{completed, pending}` case D11a was designed for, plus every
   single-step closed section — the remainder is allowed to its **governing step**
   (M3.4: its most recently closed step, same tie-break).

Σ of a section's step allowances therefore equals its slice **exactly, in every
branch** — which is what makes P-AGREE (§12.6) satisfiable. Verified consequences:
a one-step section's step is governing, so its allowance = worked + remainder = the
**whole slice**, byte-identical to today on the 98.2% case; `{completed, pending}` gives
the pending step `slice − first pass`, D11a's intent unchanged; `{completed, completed}`
has the later one absorb the remainder.

**Allowances and `left_seconds` may go negative (B3, owner card 2).** A section slice of
60 s whose closed pass burned 100 s leaves the open step **−40**. The owner's ruling:
*"the frontend gets the values and sees the overflow and will render the overflow, the
backend just presents the data, the frontend decides how to visualize it."* No clamping —
clamping would break P-AGREE's exact sum, which is the one guarantee this phase exists to
establish. The frontend handoff rewrite must carry the bar rule: a non-positive
`allowance_seconds` draws a full over-share bar, never a division.

**`share_state` on a step row is derived from its SECTION (owner card 1).** The owner:
*"if both working times additions overflow the allowed time it should not render on track
for independent steps … upholstery has worked a total of 2h regardless of how many task
steps was it re-assigned to."* So every step of a section whose **total** worked exceeds
its slice reports `over_share`, including an earlier pass that individually came in under
its own allowance. This is stricter than a per-step comparison, and it is what makes E2
and E3 report the **same state** for a section, not merely reconcilable numbers.
`allowance_seconds` and `left_seconds` stay per-step (they answer "how long do I have for
*this* pass?"); only the state is section-derived.

**The exact comparison (S1, ratified as D16, round 11).** `share_state` on a section row,
and on every step row that inherits it, compares **M3.3's `worked_seconds`** — the
section's total over all its non-deleted steps, **including excluded ones** — against
`allowance_seconds`: `over_share` iff `worked_seconds > allowance_seconds`, else
`on_track`. This is the same quantity the row displays, so `share_state`,
`worked_seconds` and `left_seconds` (= `allowance_seconds − worked_seconds`) can never
contradict each other on one card. **M3.5b's exclusion rule applies ONLY to the residual
that splits a slice across a section's steps, never to this comparison:** charging decides
how much is allocated, `share_state` reports what the section has spent. (Implement r1
built the two fields on different bases and produced `left_seconds: -100` beside
`share_state: "on_track"`.)

**Remainder tie key for grouped units: `working_section_id` ASC (B6 — gate failure,
contracted).** Section units have no `sequence_order`, and `client_id` is not a section's
identity. Both E2 and E3 must use `working_section_id` ASC, contracted in
`budget_division.py` for both callers. This is deliberately **not** M3.2's render order:
requiring the render order would force E2 to load `order_list` it has no other use for,
breaking its pinned 11-query budget. The two orders provably differ on live data
(`weaving` is 8th by M3.2, 11th by section id), so a mismatch would land the leftover
second on a **different section** in each surface and violate P-AGREE by exactly the
amount nobody looks at.

**The two `_governing_step` call sites can legitimately select different steps (N8,
round 12).** `group_steps_by_section` passes **all** the group's steps, so an all-terminal
mixed group's *displayed* governing step may be a `skipped` one; `_section_step_allowances`
passes **only** the completed steps, because an excluded step has no allowance row to
receive the residual. This divergence is intended: the first answers "what state is this
section in?", the second answers "who absorbs the leftover?". Verified at review r3 across
four all-terminal fallback cases, P-AGREE exact in each.

**Consequence for phase 1's shipped surface:** E2's per-step allowances change value, its
shape does not, and **its `allocation_method` label changes** — see M3.5c.

**M3.5c — `allocation_method` becomes `static_proportional_section_v1` (P2, ruling
delegated to the projectionist and made).** HC-5 makes this label the consumer's cache
key. Every per-step number on the worker card can move — measured 3200/1600 → 2800/2000
on the existing two-section fixture — while the label, the shape and the key set stay
identical, so a client holding a cached payload beside a fresh one has no way to tell
them apart. That is precisely the failure the label exists to prevent. The value names
*what* changed (the unit) rather than an opaque `_v2`, and it leaves `dynamic_*` free for
D6 so nothing is spent. Cost is one line: the literal lives at `budget_division.py:17`,
is echoed only in docs and in one **unasserted** test fixture dict, is published nowhere
in `Application_contracts`, and no frontend consumes it yet — the frontend build waits on
this pipeline by owner decision. Waiting until a consumer exists makes the same edit
breaking. **A new criterion must pin the literal string and assert E2 and E3 emit the
identical value**: today no test pins it at all, and a cache key no test pins can drift
silently.

**M3.8a — `final.percent_consumed` is the live figure (B12).** `ItemCostResult` has no
`percent_consumed` column. v1 already solved this by injecting the live percentage into
the frozen object (`serializers.py:193`, `:243-249`), so on the existing surface
`result.percent_consumed` is not frozen either. E3 follows that precedent: every `final`
field except `percent_consumed` is read from the frozen row; `percent_consumed` is the
live figure and equals `budget.percent_consumed`. Note `item_cost_results` is **empty in
the entire database**, so this branch is fixture-only.

**M3.6 — Typical nested per section, with its own labels.** Each section row carries a
`typical` object: `typical_worker_seconds`, `sample_count`, `method`, `window_days`,
`min_sample_size`. Deliberately **not** hoisted to the payload root, even though all
sections share the same values today. **D2** defers per-item-category refinement to a
future `method` value, and a manager-configured typical would be per-section — both
make these labels legitimately section-scoped. Hoisting now is a contract we would have
to break then. The cost of nesting is ~5 short fields × ≤14 rows.

**M3.7 — The headline computes nothing new.** `allowed_worker_minutes` from the
committed evaluation; `actual_worker_minutes` via `calculate_actual_worker_minutes`,
`remaining_worker_minutes` via `calculate_remaining_worker_minutes`,
`percent_consumed` via `calculate_percent_consumed` (`calculator.py:302/328/340`);
`status` and `item_binding` from the budget-status resolution path. E3 introduces no
arithmetic. This is the "shopping" the owner described, and HC-6 is what keeps it
shopping.

**M3.8 — Closed tasks.** The handoff instructs the component to prefer the frozen
`item_cost_result` figures once a task closes. If E3 omitted them the component would
still need budget-status for closed tasks, defeating §12.2. E3 therefore carries a
`final` object with the **time-only** fields of that row (`actual_worker_minutes`,
`variance_worker_minutes`, `percent_consumed`, `task_state_snapshot`, `computed_at`),
`null` while the task is open. Monetary fields are omitted under HC-7.

**M3.9 — Both names, one rule.** Each section row carries `section_name` (the live
`WorkingSection.name`, already joined for `order_list`) **and**
`section_name_snapshot` (from the governing step). They diverge only after a rename.
The contract states the rule so the frontend cannot pick by coin flip: **render the
snapshot** on the row — it is what the worker was assigned to — and reserve the live
name for section pickers and settings lists.

### 12.6 Properties

- **P-SUM3** — Σ section `allowance_seconds` over non-excluded rows ==
  `distributable_seconds`, exactly, for every budgeted task.
- **P-ORDER** — the `sections` array is a deterministic total order under M3.2; two
  calls on unchanged data are byte-identical.
- **P-COVER** — every non-deleted step of the task is counted in exactly one section
  row, and Σ section `worked_seconds` == the headline `actual_worker_seconds`.
- **P-AGREE** — E3 and E2 never disagree about a section. Under variant A, E3's
  section allowance == Σ of E2's step allowances for that section. Under variant B,
  E2's step allowances sum to E3's section allowance. **This property is D7's purpose
  generalized**: one formula, two surfaces, no contradiction.
- **P-FLAT** — the response body is identical for all four roles (HC-7).
- **P-PROP and P-STABLE hold at the SECTION unit and only there (P1, round 10).**
  Section slices are proportional to typicals and do not move with consumption. **Inside**
  a section, D11a deliberately reallocates by consumption: a closed pass's spend reduces
  what the open pass is allowed. That is the whole point of "12m left". It is the only
  place in the contract where consumption moves an allowance, and it is bounded by the
  section — **D6 still stands at the task level.** Consequence: phase 1's per-step ratio
  assertion of P-PROP is no longer a true invariant and must become a section-level
  assertion; it cannot be repaired by changing a literal.

### 12.7 API contract E3

`GET /api/v1/item-economics/tasks/{task_client_id}/production-time`

Roles: ADMIN, MANAGER, WORKER, SELLER. Mounts on the existing item-economics router,
**after** the fixed `/tasks/budget-allocations` path and beside
`/tasks/{task_client_id}/budget-status` (`routers/api_v1/item_economics.py:346-366`;
the ordering comment at `:345` explains why the fixed path precedes the parameterized
block). **HC-1a applies again**: the two hand-written route mirrors and
`routers/README.md` take one additive row each. That is the same designed tripwire
family D10 already authorized — recorded, no new card.

```json
{ "task_id": "tsk…", "status": "ok", "item_binding": "bound",
  "allocation_method": "static_proportional_v1",
  "budget": { "allowed_worker_minutes": "195.00", "actual_worker_seconds": 9600,
              "actual_worker_minutes": "160.00",
              "remaining_worker_minutes": "35.00", "percent_consumed": "82.05" },
  "final": null,
  "sections": [
    { "working_section_id": "wsec…", "section_name": "upholstery installation",
      "section_name_snapshot": "upholstery installation", "order_list": 7,
      "state": "working", "state_entered_at": "2026-08-17T09:12:00+00:00",
      "worked_seconds": 1500, "step_count": 2,
      "allowance_seconds": 3600, "left_seconds": 2100, "share_state": "on_track",
      "typical": { "typical_worker_seconds": 3600, "sample_count": 23,
                   "method": "median_completed_section_totals",
                   "window_days": 90, "min_sample_size": 5 } } ] }
```

**`step_ids` was removed from the wire in round 10** on the owner's constraint that E3
"should not be returning the individual task steps". `step_count` stays — it is a fact
*about the section* ("two passes"), not a step row. The domain function still returns
`step_ids` internally, because M3.5b's split needs them and E2 consumes them; P-COVER is
asserted in tests against the database rather than from E3's wire.

`allocation_method` is `static_proportional_section_v1` per M3.5c. There is no
`distributable_seconds` field on this payload (nor on E2's), so P-SUM3 is a property of
the pure allocator and is proven by a unit test on it, not from the wire.

404 when the task is absent, deleted, or belongs to another workspace — the tenant
boundary that earned the **tenant-boundary-row** rule in phase 1 gets its own
enumerated test row here (§12.10).

### 12.8 Degradation

Inherits §6 unchanged, restated at the section level. On any `status` other than `ok` /
`infeasible`: `budget.*` all `null` (including `actual_worker_seconds`, mirroring
`_empty_status` — the round-7 correction), every section's `allowance_seconds`,
`left_seconds` `null`, and `share_state: "no_budget"`.

**What still renders, and must:** `worked_seconds`, `state`, `state_entered_at`,
`order_list`, and the whole `typical` object stay populated on every section. An
unevaluated task therefore still shows its real pipeline with real times against real
typicals — "Sanding · 25m of typically 50m" — which is the intended degraded state, not
an error. Consumers sum `sections[].worked_seconds` for consumed time when
`budget.actual_worker_seconds` is null.

### 12.9 Non-goals (phase 2)

- No change to `serialize_step` or to the step-listing endpoint (HC-1 stands).
- No deprecation of Calls 1–4; the component stops calling them, the endpoints remain.
- No dynamic/consumption-based reallocation (**D6** stands; `allocation_method` is the
  label that will change when it arrives).
- No per-item-category typicals (**D2**).
- No persistence, no `order_list` backfill, no schema change — including no unique
  constraint on `order_list`. The measured ties are handled by M3.2's tie-break, not by
  a migration.

### 12.10 Testing expectations

Charter standing rules 1–11½ and phase 1's nine earned rules apply. Per the **MVP
calibration rule**, a full mutation ledger is required only for rule-6 mechanisms and
the tenant boundary; the first review is light-scoped.

Enumerated rows that must exist (each a *distinct* fixture, not a parametrization of
one):

1. **`order_list` tie** — two sections sharing one `order_list`, differing names;
   assert the exact resulting order, then assert it again after reversing insertion
   order. This is the measured production case.
2. **`order_list` NULL** — one section NULL, others populated; NULL sorts last.
3. **Multi-step section** — a task with two steps in one section (the measured 1.8%);
   assert one row, `step_count == 2`, `worked_seconds` == the sum, and — under the
   chosen C1 variant — the exact `allowance_seconds`, pinned as a literal.
4. **Governing step** — a section holding one `completed` step and one later `pending`
   step; assert the row's `state` per C2's answer. Delete the governing-step rule and
   this must go red.
5. **Multi-open tie-break** — two non-closed steps in one section (impossible in
   current data, hence a fixture): assert the deterministic winner.
6. **Excluded section** — all of a section's steps `skipped`; assert
   `share_state: "excluded"`, no allowance, and that its worked seconds are charged
   before division. Also the *mixed* case: one skipped + one completed in one section.
7. **P-SUM3** — Σ allowances == `distributable_seconds`, on a task whose typicals do
   not divide evenly (forces the largest-remainder path).
8. **P-COVER** — Σ section `worked_seconds` == headline `actual_worker_seconds`.
9. **P-AGREE** — same task through E2 and E3; assert the section-level agreement in
   C1's chosen direction. This is the cross-surface test phase 1 never had.
10. **P-FLAT** — the four roles receive byte-identical bodies (`sha256` of the
    serialized payload), and **no monetary key appears** at any depth.
11. **Tenant boundary** — a task in another workspace returns 404. Per the
    **tenant-boundary-row** rule, the fixture row must be *verified to exist* by
    deleting the workspace filter and watching this test go red.
12. **Degradation** — an unevaluated task: budget nulls, `share_state: "no_budget"`
    everywhere, typicals and worked seconds still populated.
13. **Closed task** — `final` populated from the frozen result; monetary fields absent.
14. **Route mirrors** — the two hand-written mirrors and README updated by addition
    only (HC-1a).

### 12.11 Owner decisions — phase 2

**Both cards answered 2026-08-17; 0 open.** C1 → **D11** (the working section is the
allocation unit) plus **D11a** (coordinator-specified per-step split, not carded, under
the MVP calibration rule). C2 → **D12** (the live step governs the displayed state).
Verbatim answers and the recorded coordinator correction to D11's reasoning are in
`planning/owner_decisions.md`. The gate to projection r0 is open.

---

## 13. Changelog (continued)

- **Round 8 (2026-08-17)** — phase 2 shaped from the owner's frontend approach change:
  one task-scoped, section-keyed endpoint (E3) replacing the component's four calls.
  Added HC-6…HC-11, §12.4 grounding measured this session (`order_list` populated
  14/14 but **non-unique — 12 distinct values, two real ties**; multi-step sections
  49+1 of 2782 groups; **zero** groups with 2+ open steps; **zero** excluded-state
  steps in the database), mechanism M3, properties P-SUM3/P-ORDER/P-COVER/P-AGREE/
  P-FLAT, contract E3, and the 14 enumerated test rows. Two owner cards opened: **C1**
  allocation unit (step vs section — recommended section, because a section-keyed row
  makes phase 1's accepted double-weighting *visible*, and because it is the only
  variant under which E2 and E3 cannot contradict each other) and **C2** section state
  semantics. Confirmed design 2 needs no new backend surface — E1 + E2 already serve
  the worker card's progress line — **subject to C1**, which would move E2's numbers.
- **Round 9 (2026-08-17)** — owner answers folded. **D11** resolves M3.5 to variant B
  (the working section is the allocation unit); the worked 180-minute example is now
  recorded inline as the rationale, because the owner's answer arrived with a different
  reason than the defect it fixes — they described the *consumed* sum (already D9/M3.3,
  true under both variants) rather than the *allowance* inflation. **D11a** adds M3.5b,
  the per-step split inside a section, specified rather than carded on the measured
  0-of-2782 multi-open figure. **D12** resolves M3.4 to the live-step-governs reading.
  New obligation routed to projection r0: rule on whether E2's `allocation_method` label
  must change now that its per-step values move, since HC-5 makes that label the
  consumer's cache key.
- **Round 10 (2026-08-17)** — projection r0 ledger routed (handoff
  `handoffs/reviewer/2026-08-17_phase2_projection_r0_handoff.md`, verdict
  AMENDMENTS_REQUIRED: 12 blocking, 10 amendments, 11 notes, 3 owner cards). §12.4 was
  confirmed **accurate on all seven claims** and extended with four load-bearing counts
  (P3). Owner cards answered: **card 1** → E3 returns no per-step data, and a step row's
  `share_state` is derived from its section, so no step of an overflowing section reads
  on-track; **card 2** → allowances and `left_seconds` may go negative, the frontend
  renders the overflow; **card 3** → charging stays at the task level, D8 and §4's
  consequence table intact. Intention changes: M3.1 gains the soft-deleted-section outer
  join (B8); the round-9 "exclusion at the allocated unit" clause is **superseded** (B4);
  M3.5b fully rewritten (B2 closed-step/governing-step rule, B3 negative allowances, B5
  equal weights, B6 `working_section_id` tie key, B7 state-not-timestamp liveness — B5/B6/
  B7 recorded as **gate failures** under the mechanism-inventory waiver's condition);
  M3.5c adds the `allocation_method` → `static_proportional_section_v1` ruling (P2); M3.8a
  the `final.percent_consumed` injection (B12); §12.6 scopes P-PROP/P-STABLE to the
  section unit (P1); §12.7 drops `step_ids` from the wire. Coordinator independently
  re-verified B8, B2's 45/5 split, B7's 0-of-2833, N9's zeroes and P5's partial unique
  index before routing — all five reproduce exactly.
- **Round 11 (2026-08-17)** — review r1 folded. **S1 → D16** (owner-ratified):
  `share_state` compares M3.3's total `worked_seconds` including excluded steps;
  `left_seconds` unchanged, so a card's three numbers cannot contradict. M3.5b's exclusion
  rule scoped explicitly to the residual only. **B1** (M3.4's governing step never
  consulted liveness) reclassified BLOCKING → should-fix after the coordinator corrected
  the reviewer's reachability claim — no multi-step group shares an identical `created_at`
  (49×2 distinct, 19×3 distinct) and `created_at` is NULL on 0 of 3049 rows, so two of its
  three fixtures are unreachable through the database. The owner's challenge was upheld on
  the reassignment flow and answered by the enforcement note above: the invariant is
  currently a frontend convention, not a backend guarantee.
- **Round 12 (2026-08-17)** — re-review r3 APPROVED. N8 folded into M3.5b (the two
  `_governing_step` call sites legitimately diverge). Phase 2 closed.
