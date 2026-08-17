> # ⛔ SUPERSEDED — do not build from this file
>
> Replaced in full on **2026-08-17** by
> **`HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260817.md`**.
>
> This document was written before the backend existed and patched twice afterwards. Its
> §4 row-ordering guidance (`sequence_order`) is **wrong in practice** — that column is
> NULL on every live step — and its four-call design for the production-time widget has
> been replaced by a single endpoint. Kept for provenance only. §9 of the new document
> lists every difference.

# Frontend handoff — "Production time" component (task details)

**Date:** 2026-08-16 · **Updated 2026-08-17** — the two gaps this document originally
declared are CLOSED. Typical section times and per-step allowances now ship as real
endpoints (§6), so the mockup renders completely, including the per-row "typical" line
and the per-row "On track" chip. §8 adds the worker task-step card component, which
uses the same two new calls.

**Scope:** the self-contained *Production time* widget shown on task details for the task's
PRIMARY item, plus (§8) the worker task-step cards. It fetches its own data on render;
this document is the complete list of endpoints it needs and the field-by-field mapping
to the mockup.

This document supplements — never replaces — the two v1 handoffs:

- `HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` (full budget-status contract, §4)
- `HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md` (setup surfaces)

If anything here disagrees with the operational handoff, the operational handoff wins.

---

## 1. The calls

The *Production time* widget needs these two GET requests keyed by the task's
`client_id`, plus the two in §6 (typicals and per-step allowances) for the per-row
"typical" line and on-track chip:

| # | Route | Roles | Gives you |
|---|---|---|---|
| 1 | `GET /api/v1/item-economics/tasks/{task_client_id}/budget-status` | ADMIN, MANAGER, WORKER, SELLER | the headline: allowed minutes, consumed minutes, remaining, percent, status, final result |
| 2 | `GET /api/v1/tasks/{task_id}/steps?limit=200` | ADMIN, MANAGER, WORKER, SELLER | the section rows: name, state, per-step worked seconds, live-interval start |

Both accept every role, so the component is portable across the manager and worker apps
with the same target URLs. The **server** shapes the payload by the caller's JWT role —
worker-role callers receive no monetary fields (deliberate, enumerated worker surface;
minutes and percentages only). The component must therefore treat every monetary field as
optional and never require it to render.

Every response uses the standard envelope:

```json
{ "ok": true, "warnings": [], "data": { … } }
```

---

## 2. Call 1 — budget status (the headline numbers)

`GET /api/v1/item-economics/tasks/{task_client_id}/budget-status`

Manager/admin shape (worker shape = the same minus the fields marked 💰):

```json
{
  "status": "ok",
  "item_binding": "bound",
  "actual_worker_seconds": 9600,
  "actual_worker_minutes": "160.00",
  "remaining_worker_minutes": "35.00",
  "percent_consumed": "82.05",
  "variance_worker_minutes": "35.00",
  "allowed_worker_minutes": "195.00",
  "production_budget_minor": 97500,        // 💰
  "consumed_cost_minor": 80000,            // 💰
  "variance_cost_minor": 17500,            // 💰
  "evaluation_id": "…",                    // 💰
  "item_id": "…",                          // 💰
  "result": null
}
```

Notes:

- Decimal fields arrive as **strings** (`"195.00"`), quantized server-side (minutes to
  0.01). Parse, don't `Number()`-truncate blindly if you re-format.
- `allowed_worker_minutes` **is present in the worker shape too** — the time budget is not
  monetary. Only the five 💰 fields disappear.
- `actual_worker_seconds` is the sum of `total_working_seconds` over the task's live steps
  — the same source Call 2 itemizes, so the rows genuinely add up to the headline
  (see §5 for the one skew caveat).
- `result` is non-null once the task has closed and analytics produced the final
  `item_cost_result` row (fields: `actual_worker_minutes`, `variance_worker_minutes`,
  `percent_consumed`, `task_state_snapshot`, `computed_at`, plus seconds/cost fields for
  monetary roles). When `result` is present, prefer it for the headline on
  closed tasks — it is the frozen, boundary-labelled outcome, while the live fields keep
  recomputing.

### When there is no budget — the empty state, fully specified

`status` is the twelve-value vocabulary from the operational handoff §4. The component
gets numbers **only** when `status` is `"ok"` (or `"infeasible"` — allowed ≤ 0, render an
over-budget-from-birth treatment). For every other status all time fields are `null`.

**Never hide the component and never show zeros.** Render the same card frame (header
"Production time") with an explanatory empty state, because absence-with-reason is
information the manager acts on — a blank space or a `0m of 0m` bar is not. Group the
statuses into three treatments:

| Statuses | Whose problem | Suggested treatment |
|---|---|---|
| `item_unvalued`, `item_missing_expected_price`, `item_missing_purchase_cost` | this item — fixable from the item/task screen | Reason line + (manager/admin only) a CTA to the item valuation form, e.g. "No production budget — this item has no purchase cost yet. **Add valuation →**" |
| `not_configured_no_cost_group`, `not_configured_ambiguous_cost_group`, `not_configured_no_basis_version`, `not_configured_no_cost_model_version`, `item_missing_major_category`, `currency_mismatch` | workspace configuration — fixable only in economics setup | Reason line pointing at setup, no per-item CTA: "Production budgets are not configured for this item's category." Workers/sellers see the line without the settings pointer. |
| `not_evaluated` | nothing missing — evaluation just hasn't been committed for this task | "Budget not calculated for this task yet." Manager/admin may get a "Calculate now" CTA → `POST /api/v1/item-economics/tasks/{task_client_id}/evaluations/commit` (returns the committed evaluation; refetch budget-status after). Typical for tasks created before the item was fully priced. |

Copy should name the *missing thing*, not the status code. Keep the raw status value in a
tooltip/dev attribute for support.

In the empty state, still render the step rows from Call 2 (names, states, worked time) —
time tracking exists independently of budgeting; only the budget frame (total / left /
percent) is absent.

Also handle:

- `item_binding: "detached" | "mismatched"` — the task lost or swapped its PRIMARY item;
  show the empty state ("no item is bound to this task"), not stale numbers.
- HTTP 404 — task not found / deleted; here the whole component hides, since its host
  screen is gone anyway.

---

## 3. Call 2 — the step rows (sections)

`GET /api/v1/tasks/{task_id}/steps?limit=200`

Returns `data.steps_pagination.items[]`, already ordered by `sequence_order` (nulls last),
each item carrying (fields irrelevant to this component omitted):

```json
{
  "client_id": "…",
  "state": "working",
  "readiness_status": "ready",
  "sequence_order": 3,
  "working_section_name_snapshot": "Upholstery",
  "assigned_worker_display_name_snapshot": "…",
  "total_working_seconds": 2400,
  "total_pause_seconds": 300,
  "recorded_time_marked_wrong": false,
  "closed_at": null,
  "latest_state_records": {
    "state": "working",
    "entered_at": "2026-08-16T09:12:00+00:00",
    "exited_at": null,
    "pause_reason": null
  }
}
```

- `state` vocabulary: `pending`, `working`, `paused`, `blocked`, `completed`, `skipped`,
  `failed`, `cancelled`.
- `limit` max is 200; one page covers any realistic task, but read
  `steps_pagination.has_more` and fetch again if true rather than assuming.
- Worker-role callers get the same rows minus `total_cost_minor` (which this component
  does not use anyway).

---

## 4. Mockup → field mapping

| Mockup element | Source |
|---|---|
| **"3h 15m"** (total production time) | Call 1 `allowed_worker_minutes` |
| **"2h 40m"** (consumed) | Call 1 `actual_worker_minutes` (+ live tick, §5) |
| **"35m left"** | Call 1 `remaining_worker_minutes` (negative ⇒ over budget) |
| Segmented progress bar | Call 1 `percent_consumed`; segment widths from each step's `total_working_seconds / actual_worker_seconds` |
| Row label ("Structural Repair", "Sanding", "Upholstery") | Call 2 `working_section_name_snapshot` |
| Row state chip ("completed", "in progress") | Call 2 `state` (`working` → "in progress") |
| Row time ("1h 10m", "50m", "40m") | Call 2 `total_working_seconds` (+ live tick for the `working` row, §5) |
| Row order | Call 2 `sequence_order` |
| **"typical 1h 0m"** | ✅ **now shipped** — Call 3 `typical_worker_seconds` (§6.1) |
| **"On track" / taking time from others** | ✅ **now shipped** — Call 4 `share_state` per step (§6.2) |
| Footer ("35m left for finishing and QC") | client-side copy over `remaining_worker_minutes` and the remaining `pending` rows |

Convert minutes⇄display client-side (`"195.00"` → `3h 15m`). Seconds fields are integers.

---

## 5. Live time — the one thing that will look frozen if you miss it

`total_working_seconds` (per step) and therefore `actual_worker_seconds` (task total) are
recomputed **from settled state records only** — a step currently in `working` state has
its open interval **excluded** until it transitions out. If the component only renders the
stored numbers, the "in progress" row and the headline sit still while the worker works.

To get the ticking display in the mockup:

1. Find rows where `latest_state_records.state == "working"` and `exited_at == null`.
2. Add `now − entered_at` to that row's seconds and to the headline total, ticking
   client-side.

Two honesty caveats on that client-side delta:

- The backend credits concurrent work **averaged**: a worker running two steps at once is
  credited 50/50 when the records settle. The naive live delta counts 100% per open step,
  so it can over-tick until the next transition reconciles it. Acceptable for display;
  don't persist or alert off it.
- Refetch both calls whenever a step transition happens (or poll at a modest interval,
  e.g. 30–60 s, when visible). After any transition the stored totals are authoritative
  again.

Minor skew: the two calls read the same columns but at two instants; if a transition lands
between them the rows may not sum exactly to the headline for one render cycle. Refetching
both together resolves it.

---

## 6. Typicals and per-step allowances — SHIPPED 2026-08-17

The two gaps this document originally declared are now closed by real endpoints.
Everything in the mockup, including the per-row "typical 1h 0m" line and the
per-row "On track" chip, renders from server data. Two more calls:

| # | Route | Roles | Gives you |
|---|---|---|---|
| 3 | `GET /api/v1/working-sections/typical-times` | all four | per-section typical duration (reference data — fetch once, cache) |
| 4 | `GET /api/v1/item-economics/tasks/budget-allocations?task_ids=…` | all four | per-step allowance, time left, and on-track state (batched, up to 50 tasks) |

### 6.1 Call 3 — typical section times

Optional repeatable filter `working_section_ids` (omit for all sections; a worker
who only ever sees Upholstery should pass just that id rather than fetching all).

```json
{ "typical_times": [
    { "working_section_id": "wsec…", "section_name": "Upholstery",
      "typical_worker_seconds": 3600, "sample_count": 23,
      "method": "median_completed_section_totals",
      "window_days": 90, "min_sample_size": 5 } ] }
```

What the number means, stated precisely because the UI must not overclaim it: the
**median**, over the last 90 days, of *how much total time this section spent per
item*. Re-assignments count toward the same item's total — if a sofa came back to
Upholstery for a second pass, that task contributes one sample equal to both
passes summed. So a section with frequent rework correctly reads as taking
*longer* per item, never shorter.

- `typical_worker_seconds` is **`null`** when the section has fewer than five
  qualifying samples (`sample_count` tells you how many it has). Render "no
  typical yet" — do not fall back to an average, an even split, or zero.
- This is slowly-changing reference data (a 90-day median barely moves day to
  day). **Fetch once per session and cache** (an hour TTL is plenty); join to
  steps client-side on `working_section_id`, which every step payload carries.
- `method` / `window_days` / `min_sample_size` are the swappability labels: when
  the backend later refines how typicals are derived (manager-configured, or
  per-item-category), those values change and the payload shape does not. **Key
  your display off these fields rather than hard-coding "90-day median".**

### 6.2 Call 4 — per-step allowances and on-track state

`task_ids` is a repeatable query param, 1–50 ids per call. One call serves a
whole screen: pass the single task for this component, or every visible task for
a list of worker cards.

```json
{ "budget_allocations": [
    { "task_id": "tsk…", "status": "ok",
      "allowed_worker_minutes": "195.00", "actual_worker_seconds": 9600,
      "remaining_worker_minutes": "35.00",
      "allocation_method": "static_proportional_v1",
      "steps": [
        { "step_id": "tsp…", "working_section_id": "wsec…",
          "section_name_snapshot": "Upholstery",
          "typical_worker_seconds": 3600,
          "allowance_seconds": 3600, "worked_seconds": 1500,
          "left_seconds": 2100, "share_state": "on_track" } ] } ] }
```

**How an allowance is computed** — worth understanding, because it answers the
question the mockup poses. The task's whole budget is divided across its steps
**in proportion to their sections' typicals**, so the allowances always sum to
exactly the budget. Consequences you can rely on:

- No single step can be shown the task's entire remaining time. "40m left" on the
  Upholstery card is *Upholstery's slice* minus what it has worked — never the
  task's whole remainder that later sections still need.
- Steps that ended `skipped`, `cancelled` or `failed` keep no slice, but the time
  they already burned is charged against the budget before it is divided, so the
  survivors are never promised time that is already spent.
- The division follows the **live** step set: a step a manager adds mid-task joins
  the division and receives a slice on the next fetch; one that is removed leaves
  it. Targets legitimately move when the *step set* changes — they do **not** move
  because someone finished early or ran over.
- A section with no typical yet is weighted by the median of its siblings' typicals
  (or equally, if none has one), so an unmeasured section still gets a fair slice.

**`share_state` is the on-track answer, computed server-side — render it, do not
re-derive it.** Both this component and the worker cards read the same field so
they can never disagree:

| `share_state` | Meaning | Suggested chip |
|---|---|---|
| `on_track` | `worked_seconds ≤ allowance_seconds` | "On track" |
| `over_share` | worked past its slice — it is now eating time the arithmetic gave to other sections | "Over its share" |
| `excluded` | step ended skipped/cancelled/failed; no slice (its consumed time is still charged) | muted / struck row |
| `no_budget` | the task has no committed evaluation, so no allowances exist | see below |

`allocation_method` is this call's swappability label (today
`static_proportional_v1`). A future dynamic reallocation changes that value, not
the shape.

### 6.3 Degradation — what to render when there is no budget

When `status` is anything other than `ok` / `infeasible`, the whole budget frame
is absent: `allowed_worker_minutes`, `remaining_worker_minutes`,
**`actual_worker_seconds`**, `allowance_seconds` and `left_seconds` are all
`null`, and every step reports `share_state: "no_budget"` — including steps that
are skipped or failed (`excluded` appears only when a budget exists).

Two things that still work, and should still render:

- **`typical_worker_seconds` and `worked_seconds` stay populated.** So a card on
  an unevaluated task can still show "Sanding · 25m of typically 50m" — typical
  progress without a budget. That is the intended degraded state, not an error.
- **To show consumed time on an unevaluated task, sum `steps[].worked_seconds`
  yourself** — `actual_worker_seconds` is null there. On evaluated tasks the
  field equals that sum by construction; the null on unevaluated tasks mirrors
  what the budget-status endpoint does, so the two surfaces agree.

Use §2's status→copy grouping for the reason line; the same twelve-value
vocabulary applies here.

### 6.4 Absence semantics (both calls)

Absence is meaningful and never an error:

- Call 4 **omits** task ids that are unknown, deleted, or belong to another
  workspace — you notice by key, not by an error. Ask for four ids, get two rows,
  that is a correct answer.
- Call 3 returns every non-deleted section of the workspace, including ones with
  zero samples (`typical_worker_seconds: null`, real `sample_count`) — a young
  section appears saying "no typical yet" rather than vanishing.
- Sending more than 50 ids to Call 4 → `422 BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`.
  An empty `?task_ids=` counts as one unknown id and comes back with no rows.

### 6.5 Live time still ticks client-side

§5 applies unchanged to both new calls: `worked_seconds` excludes the currently
open working interval, so tick it forward from `latest_state_records.entered_at`
for steps in `working` state. `left_seconds` should tick *down* correspondingly.
Everything the server returns is settled truth; the tick is presentation.

---

## 7. Self-containment checklist

- Inputs: `task_client_id` + the app's normal auth header. Nothing else.
- Works for all four roles; monetary fields are a manager/admin bonus the component never
  requires (this widget is time-only, so the worker shape is fully sufficient).
- Render decision tree: `404` → hidden/empty · `status != ok/infeasible` → empty state
  with reason chip · `result != null` → frozen final figures · else → live figures + tick.
- Steps call failing but budget call succeeding → headline without rows (degrade, don't
  blank).

---

## 8. The worker task-step cards (added 2026-08-17)

The second component from the owner's mockup: a list of cards, one per assigned
step, each reading *"Upholstery · 25m of 1h 0m … 35m left"* with a progress bar and
a "Start Task" action.

**It needs the same two new calls and nothing else.** Every number on the card comes
from Call 4, joined with Call 3 for the display typical:

| Card element | Source |
|---|---|
| Section name ("Upholstery", "Sanding") | Call 4 `steps[].section_name_snapshot` |
| Worked time ("25m", "47m") | Call 4 `steps[].worked_seconds` (+ live tick, §6.5) |
| "of 1h 0m" | Call 4 `steps[].allowance_seconds` — the step's slice of the task budget |
| "35m left" / "3m left" | Call 4 `steps[].left_seconds` (negative ⇒ over its share) |
| Progress bar fill | `worked_seconds / allowance_seconds` |
| Bar colour / status | Call 4 `steps[].share_state` (`over_share` ⇒ the amber/red treatment the second card shows) |
| Typical-only fallback label | Call 3 `typical_worker_seconds` when there is no budget (§6.3) |
| Task reference (`#CH6-090726`), type, date | the existing step/task listing the feed already uses |

**Efficiency, because this is a list:** Call 4 is batched — collect the `task_id`s of
the visible cards and make **one** request with up to 50 ids, not one per card. Call 3
is workspace-level reference data: fetch once per session, cache, and pass
`working_section_ids` if the worker only ever sees a couple of sections.

**Two distinctions the card must not blur.** The "of 1h 0m" figure is the step's
**allowance** (its share of this task's budget), not the section's typical. They often
look similar — the allowance is derived by weighting typicals — but they answer
different questions, and only the allowance respects the task's actual budget. Show
the typical alone (§6.3) when the task has no budget; otherwise show the allowance.

Everything in §6.2's `share_state` table and §6.3's degradation rules applies to these
cards identically — that is the point of computing `share_state` server-side: the task
detail widget and the worker card can never disagree about whether a step is on track.
