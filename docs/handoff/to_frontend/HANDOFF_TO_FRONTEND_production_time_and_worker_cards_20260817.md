# Frontend handoff — Production time widget + worker task-step cards

**Date:** 2026-08-17 · **Status:** all endpoints shipped and approved.

**This document replaces `HANDOFF_TO_FRONTEND_production_time_component_20260816.md`
entirely.** That file was written before the backend existed and was then patched twice;
it now contains stale guidance (see §9). Treat it as superseded — do not read both.

Covers two components:

- **A — Production time** (task details, one task's full pipeline)
- **B — Worker task-step cards** (a worker's feed, one card per assigned step)

If anything here disagrees with
`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`, that one wins on
budget-status semantics; this one wins on everything below.

---

## 1. The calls

| # | Route | Roles | Used by |
|---|---|---|---|
| 1 | `GET /api/v1/item-economics/tasks/{task_client_id}/production-time` | all four | **A** — the whole widget, one call |
| 2 | `GET /api/v1/working-sections/typical-times` | all four | **B** — fetch once at bootstrap, cache |
| 3 | `GET /api/v1/item-economics/tasks/budget-allocations?task_ids=…` | all four | **B** — batched, ≤50 task ids |

Standard envelope on all three: `{ "ok": true, "warnings": [], "data": { … } }`.

**Component A needs call 1 and nothing else.** It carries the headline, the section rows,
the typicals and the on-track states in one response. Do not also call budget-status, the
step list, or typical-times for this widget — they were the old four-call design.

**All three are role-flat for time data.** Call 1 in particular returns a **byte-identical
body to all four roles** — there is no monetary field at any depth, so there is nothing to
branch on. This is enforced by a test that walks every key recursively.

---

## 2. Call 1 — production time (component A)

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

### 2.1 The rules that matter

**The array is already in render order. Never sort it.** Ordering is the workshop
pipeline (`order_list`), with deterministic tie-breaks behind it — two sections legitimately
share an `order_list` value today. Two calls on unchanged data return the identical order.

**One row per working section, not per step.** A section the task visited twice — a
reassignment — is **one** row whose `worked_seconds` is the sum of both passes and whose
`step_count` is 2. This is the whole point: "Upholstery has taken 2h" regardless of how the
work was split.

**Draw segments from `allowance_seconds`, never from the typicals.** The backend already
divided the budget. Deriving your own ratios from `typical_worker_seconds` will drift from
the server, because four things happen between the ratio and the answer: a failed step's
time comes off the top first; a fully skipped section gets no slice; a section with no
typical yet falls back to the median of its siblings; and rounding leftovers are assigned
so the slices sum to the budget **exactly**.

**`share_state` is the on-track answer — render it, never re-derive it.**

| value | meaning | suggested |
|---|---|---|
| `on_track` | `worked_seconds ≤ allowance_seconds` | neutral/green |
| `over_share` | worked past its slice; eating time the arithmetic gave to later sections | amber/red |
| `excluded` | every step of this section ended skipped/cancelled/failed | muted / struck |
| `no_budget` | the task has no committed evaluation — see §4 | reason line, no bar |

**`left_seconds` can be negative, and `allowance_seconds` can be too.** A section whose
failed pass already ate more than its whole slice is legitimately below zero. **Do not
divide by `allowance_seconds` without guarding** — a non-positive value draws a full
over-share bar, not a division. The three numbers on a row are always consistent:
`left_seconds = allowance_seconds − worked_seconds`, and `share_state` is `over_share`
exactly when that is negative.

**Two names, one rule.** `section_name_snapshot` is the name as of the work; `section_name`
is the section's name today. They differ only after a rename. **Render the snapshot on the
row** — it is what the worker was assigned to. Use `section_name` in pickers and settings
lists. Either may be `null` if the section was deleted; the snapshot is your fallback label.

**`final`** is `null` while the task is open. Once closed it carries the frozen outcome —
`actual_worker_minutes`, `variance_worker_minutes`, `percent_consumed`,
`task_state_snapshot`, `computed_at`. Prefer it for the headline on closed tasks.
(`percent_consumed` inside it is the live figure and equals `budget.percent_consumed`;
every other field is frozen.)

---

## 3. Live time — the thing that will look frozen if you miss it

`worked_seconds` counts **settled** work only. A step currently in `working` state has its
open interval excluded until it transitions out. Render the stored numbers alone and the
active row sits still while someone works.

To tick:

1. Find sections where `state == "working"`.
2. Add `now − state_entered_at` to that row's `worked_seconds` and to the headline, and
   subtract it from `left_seconds`.

`state == "working"` is the correct and sufficient predicate — verified against all 2,833
live steps. Two honesty caveats, unchanged from the old handoff: the backend credits
concurrent work **averaged** across steps while the naive client tick counts 100% per open
row, so it can over-tick until the next transition reconciles; and refetch after any
transition, or poll at 30–60 s while visible. Everything the server returns is settled
truth — the tick is presentation, never persisted or alerted on.

---

## 4. When there is no budget

`status` is the twelve-value vocabulary from the operational handoff §4. You get numbers
only when it is `"ok"` (or `"infeasible"` — allowed ≤ 0, render an over-budget-from-birth
treatment). Otherwise the whole budget frame is absent: every `budget.*` field is `null`
**including `actual_worker_seconds`**, every `allowance_seconds` and `left_seconds` is
`null`, and every `share_state` is `"no_budget"` — including sections whose steps were
skipped (`excluded` appears only when a budget exists).

**Never hide the component and never show zeros.** Absence-with-reason is information a
manager acts on; a blank space or `0m of 0m` is not. Render the same card frame with:

| statuses | whose problem | treatment |
|---|---|---|
| `item_unvalued`, `item_missing_expected_price`, `item_missing_purchase_cost` | this item | reason line + (manager/admin) CTA to the item valuation form |
| `not_configured_*`, `item_missing_major_category`, `currency_mismatch` | workspace configuration | reason line pointing at economics setup; no per-item CTA |
| `not_evaluated` | nothing missing, just not calculated | "Budget not calculated yet"; manager/admin may get a "Calculate now" CTA → `POST /api/v1/item-economics/tasks/{task_client_id}/evaluations/commit`, then refetch |

Name the *missing thing*, not the status code; keep the raw value in a tooltip for support.

**What still renders, and must.** `worked_seconds`, `state`, `state_entered_at`,
`order_list` and the whole `typical` object stay populated. So an unevaluated task still
shows its real pipeline against real typicals — **"Sanding · 25m of typically 50m"**. That
is the intended degraded state, not an error, and it is the one case where you *do* drive
the display from the typical. For consumed time here, sum `sections[].worked_seconds`
yourself, since `budget.actual_worker_seconds` is null.

Also handle `item_binding: "detached" | "mismatched"` (task lost or swapped its item →
empty state, not stale numbers) and **404** (task missing, deleted, or another workspace →
hide; the host screen is gone anyway).

---

## 5. Component B — worker task-step cards

Cards read *"Upholstery · 25m of 1h 0m … 35m left"* with a progress line and your existing
Start action. **The Start action and the card's own data are unchanged** — you already have
those endpoints. What this pipeline adds is the progress line.

| card element | source |
|---|---|
| section name | call 3 `steps[].section_name_snapshot` |
| worked time | call 3 `steps[].worked_seconds` (+ live tick, §3) |
| "of 1h 0m" | call 3 `steps[].allowance_seconds` — this step's share |
| "35m left" | call 3 `steps[].left_seconds` (may be negative) |
| bar fill | `worked_seconds / allowance_seconds` — **guard the denominator** |
| bar colour | call 3 `steps[].share_state` |
| typical-only fallback | call 2 `typical_worker_seconds` when there is no budget |

**Efficiency.** Call 3 is batched: collect the visible cards' `task_id`s and make **one**
request with up to 50 ids, not one per card. Sending more → `422
BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`. **If your visible list is empty, skip the call** —
`task_ids` is required, and an omitted parameter returns a generic 422. Call 2 is
workspace-level reference data: fetch once per session, cache (an hour TTL is plenty), and
pass `working_section_ids` for just the sections this worker belongs to.

**Two distinctions the card must not blur.**

*Allowance is not typical.* "of 1h 0m" is this step's **share of this task's budget**, not
the section's typical duration. They look similar because allowances are derived by
weighting typicals, but only the allowance respects the actual budget. Show the typical
alone when there is no budget (§4); otherwise show the allowance.

*`share_state` is a section verdict, not a step verdict.* Every step of a section reports
its **section's** state. If Upholstery's two passes together overran, **both** cards read
`over_share`, including a pass that individually came in under its own number. This is
deliberate — it is the owner's ruling, and it is why this widget and these cards can never
disagree about whether a section is on track.

---

## 6. Call 2 — typical times (reference data)

```json
{ "typical_times": [
    { "working_section_id": "wsec…", "section_name": "upholstery installation",
      "typical_worker_seconds": 3600, "sample_count": 23,
      "method": "median_completed_section_totals",
      "window_days": 90, "min_sample_size": 5 } ] }
```

The **median**, over the last 90 days, of *how much total time this section spent per
item*. Re-assignments count toward the same item's total, so a section with frequent rework
correctly reads as taking **longer** per item, never shorter.

- `typical_worker_seconds` is **`null`** below five qualifying samples (`sample_count`
  tells you how many). Render "no typical yet" — never fall back to an average, an even
  split, or zero. At least one live section has zero samples today.
- **Not cached server-side.** Every call recomputes; there is no staleness to invalidate.
  The caching advice above is for your client.
- `method` / `window_days` / `min_sample_size` are swappability labels — when the backend
  refines how typicals are derived, those values change and the shape does not. **Key your
  display off them rather than hard-coding "90-day median".**

`allocation_method` on call 1 and call 3 plays the same role. It is
`static_proportional_section_v1` today. **It changed from `static_proportional_v1` in this
release, and the per-step numbers moved with it** — if you cached anything from a preview
build, that label is how you tell the generations apart.

---

## 7. Absence semantics

Absence is meaningful, never an error.

- Call 3 **omits** task ids that are unknown, deleted, or in another workspace. Ask for
  four, get two rows — that is a correct answer. Notice by key, not by error.
- Call 2 returns every live section of the workspace including zero-sample ones.
- Call 1 returns only sections **this task actually touched** — not the workspace list.
- A section deleted after the work happened still appears, with `section_name: null`,
  `order_list: null` and a null typical. Its `section_name_snapshot` is your label.

---

## 8. Self-containment checklist (component A)

- Inputs: `task_client_id` + the normal auth header. Nothing else.
- One call. Four roles, identical body. No monetary field to hide.
- Decision tree: `404` → hidden · `status` not `ok`/`infeasible` → empty state with reason,
  rows still rendered · `final != null` → frozen figures · else → live figures + tick.
- Guard every division by `allowance_seconds`.
- Render `sections` in the order given.

---

## 9. What changed from the superseded document

Read this if you already started against the old file.

1. **Four calls became one** for component A. Budget-status, the step list, typical-times
   and budget-allocations are no longer needed there.
2. **Rows are sections, not steps.** A reassigned section is one row, not two.
3. **Ordering authority changed.** The old file said rows are ordered by
   `sequence_order` — that column is **NULL on all 2,833 live steps**, so that guidance
   produced an effectively arbitrary order. Order now comes from `order_list` and is
   server-decided.
4. **`share_state` is section-derived**, so two cards for one section always agree.
5. **`allocation_method` changed value** and the per-step numbers moved with it.
6. **Negative allowances are possible**, not just negative `left_seconds`. Guard your
   divisions.
7. **The old §6.1 advice to cache typicals client-side does not apply to component A** —
   they arrive inline per section and caching them separately would show a stale typical
   beside a fresh allowance. It still applies to component B.
