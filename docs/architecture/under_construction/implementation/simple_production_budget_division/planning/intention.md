# Intention: Simple Production Budget Division (typical section times + per-step budget allocation)

```
status: resolved — 0 owner cards open; D1–D10 settled (projection r0 routed, round 5)
role: intention (pipeline root artifact)
shaped_from: owner conversation of 2026-08-16 (no raw_intention.md; the conversation
             followed the two frontend component mockups: production-time widget and
             worker task-step cards)
date: 2026-08-16
round: 0 (initial shaping)
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
