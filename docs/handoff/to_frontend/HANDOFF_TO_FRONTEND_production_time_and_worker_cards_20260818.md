# HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818`
- Created at (UTC): `2026-08-18T00:00:00Z`
- Owner agent: pipeline-coordinator (Claude Opus 5)
- Source plan: `backend/docs/architecture/under_construction/implementation/simple_production_budget_division/planning/intention.md`
- Related contracts: `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` (budget-status
  semantics and the twelve-value `status` vocabulary), `HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md` (setup surfaces)

## Backend delivery context

**What backend implemented.** Two self-contained read surfaces that answer "how is this
item's production time being spent, and is each working section on track?"

- A **task-scoped production-time projection**: one call returns a task's whole pipeline as
  working-section rows, with the time budget, what each section is allowed, what it has
  worked, and a server-computed on-track verdict.
- A **batched per-step allocation** and a **typical-times reference read**, for surfaces
  that show one card per assigned step across many tasks.

The production budget comes from the item's committed cost evaluation
(`allowed_worker_minutes`). It is divided across the task's working sections in proportion
to how long each section typically takes, so the allowances always sum to exactly the
budget. All arithmetic is server-side and exact.

**API changes.** Three GET endpoints, all additive. No existing payload changed.

**Feature flags.** None. Read-only; nothing is persisted by these calls.

## Frontend action required

1. Build the **Production time** widget (task details) against `production-time` — one
   request, no client-side joins, no client-side division.
2. Add the progress line to the **worker task-step cards** using `budget-allocations`
   (batched when the feed loads) and `typical-times` (once at bootstrap, cached). The
   cards' existing data and their Start action are unchanged.
3. Render `share_state` as given; never re-derive an on-track verdict client-side.
4. Implement the live tick (§ *Live time*) — without it the active row sits still while
   someone is working.
5. Implement the no-budget states (§ *When there is no budget*) — never hide the component
   and never show zeros.

## Interface details

### Endpoints, by component

**Production time widget — one endpoint, and only this one.**

| Route | Roles |
|---|---|
| `GET /api/v1/item-economics/tasks/{task_client_id}/production-time` | ADMIN, MANAGER, WORKER, SELLER |

It returns the headline figures, the section rows, each section's typical, and each
section's on-track state in a single response. Nothing else is needed to render the widget.

**Worker task-step cards — two endpoints.**

| Route | Roles | When |
|---|---|---|
| `GET /api/v1/working-sections/typical-times` | all four | once at bootstrap, cached |
| `GET /api/v1/item-economics/tasks/budget-allocations?task_ids=…` | all four | when the step feed loads; batched, 1–50 ids |

These two serve the cards rather than the widget for two structural reasons: the feed spans
many tasks at once, and `budget-allocations` answers for up to 50 task ids in one request;
and the cards need **per-step** allowances, while the widget's endpoint returns
**per-section** rows by design.

Both components read the same server-computed `share_state`, so the two screens cannot
disagree about whether a section is on track.

All three responses use the standard envelope:

```json
{ "ok": true, "warnings": [], "data": { … } }
```

All three are **time-only**. The production-time response is **byte-identical for all four
roles** — there is no monetary field at any depth, so there is nothing to branch on.

---

### Response shape — `production-time`

```json
{ "task_id": "tsk…",
  "status": "ok",
  "item_binding": "bound",
  "allocation_method": "static_proportional_section_v1",
  "budget": {
    "allowed_worker_minutes": "195.00",
    "actual_worker_seconds": 9600,
    "actual_worker_minutes": "160.00",
    "remaining_worker_minutes": "35.00",
    "percent_consumed": "82.05" },
  "final": null,
  "sections": [
    { "working_section_id": "wsec…",
      "section_name": "upholstery installation",
      "section_name_snapshot": "upholstery installation",
      "order_list": 7,
      "state": "working",
      "state_entered_at": "2026-08-17T09:12:00+00:00",
      "worked_seconds": 1500,
      "step_count": 2,
      "allowance_seconds": 3600,
      "left_seconds": 2100,
      "share_state": "on_track",
      "typical": { "typical_worker_seconds": 3600, "sample_count": 23,
                   "method": "median_completed_section_totals",
                   "window_days": 90, "min_sample_size": 5 } } ] }
```

Decimal fields arrive as **strings**, quantized server-side to 0.01. Seconds fields are
integers.

#### The rules that matter

**The `sections` array is already in render order — never sort it.** It follows the
workshop pipeline (`order_list`), with deterministic tie-breaks behind it, because sections
legitimately share an `order_list` value. Two calls on unchanged data return the identical
order.

**One row per working section, not per step.** A section the task visited twice — a
reassignment — is **one** row whose `worked_seconds` sums both passes and whose `step_count`
is 2. "Upholstery has taken 2h", regardless of how the work was split.

**Draw the segments from `allowance_seconds`.** The backend has already divided the budget;
do not compute your own ratios from the typicals. Four things happen between a typical and
an allowance: a failed step's time is subtracted from the budget first, a fully
skipped section receives no slice, a section with no typical yet falls back to the median of
its siblings, and rounding leftovers are assigned so the slices sum to the budget exactly.

**`share_state` is the on-track answer. Render it; never re-derive it.**

| value | meaning | suggested treatment |
|---|---|---|
| `on_track` | `worked_seconds ≤ allowance_seconds` | neutral / green |
| `over_share` | worked past its slice — now eating time the arithmetic gave to later sections | amber / red |
| `excluded` | every step of this section ended skipped, cancelled or failed | muted / struck row |
| `no_budget` | the task has no committed evaluation | reason line, no bar |

It is a **section** verdict. Every step belonging to a section reports that section's state,
so if two passes together overran, both read `over_share` even if one individually came in
under its own number.

**`left_seconds` and `allowance_seconds` may be negative.** A section whose failed pass
already consumed more than its whole slice is legitimately below zero. **Guard every
division by `allowance_seconds`** — a non-positive value should draw a full over-share bar,
not a division. The three numbers on a row are always mutually consistent:
`left_seconds = allowance_seconds − worked_seconds`, and `share_state` is `over_share`
exactly when that is negative.

**Two names, one rule.** `section_name_snapshot` is the section's name as of the work;
`section_name` is its name today. They differ only after a rename. **Render the snapshot on
the row** — it is what the worker was assigned to — and use `section_name` in pickers and
settings lists. Either may be `null` if the section was later deleted; the snapshot is the
fallback label.

**`final`** is `null` while the task is open. Once the task closes and analytics produce the
result, it carries the frozen outcome and should be preferred for the headline:

```json
"final": { "actual_worker_minutes": "160.00", "variance_worker_minutes": "35.00",
           "percent_consumed": "82.05", "task_state_snapshot": "completed",
           "computed_at": "2026-08-17T18:03:00+00:00" }
```

**`allocation_method`** (`static_proportional_section_v1`) and the typical's `method` /
`window_days` / `min_sample_size` are derivation labels. When the backend later refines how
budgets are divided or how typicals are derived, those values change and the payload shape
does not. **Key any explanatory copy off these fields rather than hard-coding "90-day
median".**

---

### Response shape — `budget-allocations`

`task_ids` is a repeatable query parameter, 1–50 ids per call.

```json
{ "budget_allocations": [
    { "task_id": "tsk…", "status": "ok",
      "allowed_worker_minutes": "195.00", "actual_worker_seconds": 9600,
      "remaining_worker_minutes": "35.00",
      "allocation_method": "static_proportional_section_v1",
      "steps": [
        { "step_id": "tsp…", "working_section_id": "wsec…",
          "section_name_snapshot": "upholstery installation",
          "typical_worker_seconds": 3600,
          "allowance_seconds": 3600, "worked_seconds": 1500,
          "left_seconds": 2100, "share_state": "on_track" } ] } ] }
```

Card mapping:

| card element | field |
|---|---|
| section name | `steps[].section_name_snapshot` |
| worked time | `steps[].worked_seconds` (+ live tick) |
| "of 1h 0m" | `steps[].allowance_seconds` — this step's share of the task budget |
| "35m left" | `steps[].left_seconds` (may be negative) |
| bar fill | `worked_seconds / allowance_seconds` — **guard the denominator** |
| bar colour | `steps[].share_state` |
| fallback when no budget | the section's typical (see below) |

**A step's allowance is not its section's typical.** "of 1h 0m" is this step's share of this
task's budget. Allowances are *derived* by weighting typicals, but only the allowance
respects the actual budget. Show the typical alone when the task has no budget; otherwise
show the allowance.

**Batch it.** Collect the visible cards' `task_id`s and make one request. If your visible
list is empty, **skip the call** — `task_ids` is required and an omitted parameter returns a
generic 422.

---

### Response shape — `typical-times`

Optional repeatable filter `working_section_ids` — pass just the sections a worker belongs
to rather than fetching all.

```json
{ "typical_times": [
    { "working_section_id": "wsec…", "section_name": "upholstery installation",
      "typical_worker_seconds": 3600, "sample_count": 23,
      "method": "median_completed_section_totals",
      "window_days": 90, "min_sample_size": 5 } ] }
```

The **median**, over the last 90 days, of how much total time a section spends per item.
Re-assignments count toward the same item's total, so a section with frequent rework
correctly reads as taking **longer** per item, never shorter.

- `typical_worker_seconds` is **`null`** below five qualifying samples; `sample_count` tells
  you how many exist. Render "no typical yet" — never substitute an average, an even split,
  or zero. Live sections with zero samples exist today.
- Not cached server-side; every call recomputes, so there is no staleness to invalidate.
  Cache it client-side for the cards (an hour is plenty) and join on `working_section_id`.
- Do **not** cache typicals separately for the production-time widget — they arrive inline
  per section there, and a cached typical beside a fresh allowance would disagree for no
  reason.

---

### Live time

`worked_seconds` counts **settled** work only. A step currently in `working` state has its
open interval excluded until it transitions out. Render the stored numbers alone and the
active row sits still while someone works.

To tick: find sections (or steps) whose `state` is `working`, add `now − state_entered_at`
to the worked figure and to the headline, and subtract it from the time left.
`state == "working"` is the correct and sufficient predicate.

Two caveats. The backend credits concurrent work **averaged** across steps, while a naive
client tick counts 100% per open row — so it can over-tick until the next transition
reconciles. Acceptable for display; never persist or alert on it. And refetch after any
step transition, or poll at 30–60 s while the component is visible.

### When there is no budget

`status` is the twelve-value vocabulary from the operational handoff. You get figures only
when it is `"ok"` — or `"infeasible"`, meaning allowed ≤ 0, which deserves an
over-budget-from-birth treatment. For every other value the whole budget frame is absent:
each `budget.*` field is `null` **including `actual_worker_seconds`**, every
`allowance_seconds` and `left_seconds` is `null`, and every `share_state` is `"no_budget"`.

**Never hide the component and never show zeros.** Absence with a reason is information a
manager acts on; a blank space or `0m of 0m` is not. Render the same card frame with:

| statuses | whose problem | treatment |
|---|---|---|
| `item_unvalued`, `item_missing_expected_price`, `item_missing_purchase_cost` | this item | reason line + (manager/admin) a CTA to the item valuation form |
| `not_configured_no_cost_group`, `not_configured_ambiguous_cost_group`, `not_configured_no_basis_version`, `not_configured_no_cost_model_version`, `item_missing_major_category`, `currency_mismatch` | workspace configuration | reason line pointing at economics setup; no per-item CTA |
| `not_evaluated` | nothing missing — just not calculated yet | "Budget not calculated yet"; manager/admin may get a "Calculate now" CTA → `POST /api/v1/item-economics/tasks/{task_client_id}/evaluations/commit`, then refetch |

Name the *missing thing*, not the status code; keep the raw value in a tooltip for support.

**What still renders, and must.** `worked_seconds`, `state`, `state_entered_at`,
`order_list` and the whole `typical` object stay populated. An unevaluated task therefore
still shows its real pipeline against real typicals — **"Sanding · 25m of typically 50m"**.
That is the intended degraded state, not an error, and it is the one case where the display
is driven by the typical. For consumed time here, sum `sections[].worked_seconds` yourself,
since `budget.actual_worker_seconds` is `null`.

### Error cases

| case | behaviour |
|---|---|
| task unknown, deleted, or in another workspace | **404** — hide the component; its host screen is gone |
| `item_binding: "detached"` / `"mismatched"` | the task lost or swapped its primary item → empty state, never stale numbers |
| more than 50 `task_ids` | **422** `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS` |
| `task_ids` omitted entirely | generic **422** — skip the call when the visible list is empty |
| `?task_ids=` present but empty | treated as one unknown id; returns no rows |
| unknown / deleted / foreign task ids in a batch | **silently omitted** — ask for four, get two rows; notice by key, not by error |
| a section deleted after the work happened | still returned, with `section_name: null`, `order_list: null` and a null typical; `section_name_snapshot` is your label |

## Validation notes

**Backend validation run.** Full suite 2313 passed / 26 failed / 1 deselected, the 26
failures being a pre-existing inherited set unrelated to this work, verified byte-identical
before and after. The mechanism carries 26 acceptance criteria, each with a named mutation
proven to turn its test red. Exercised against production data: sections return in true
pipeline order, all four roles receive byte-identical bodies, no monetary key appears at
any depth, and the degraded state renders correctly on unevaluated tasks.

**Suggested frontend validation.**

- A task whose section list includes a reassignment: assert **one** row with `step_count: 2`.
- A task with `status` other than `ok`: assert rows still render with typicals and worked
  time, and that no bar is drawn.
- A section with `allowance_seconds ≤ 0`: assert the bar does not divide.
- Render the array as returned and confirm the order matches the workshop pipeline.
- Point the widget and a worker card at the same section and confirm both show the same
  `share_state`.

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/simple_production_budget_division/planning/intention.md` (§12 for the section-keyed view)
- Decisions register: `…/simple_production_budget_division/planning/owner_decisions.md`
- Master plan: `…/simple_production_budget_division/master_plan.md`
