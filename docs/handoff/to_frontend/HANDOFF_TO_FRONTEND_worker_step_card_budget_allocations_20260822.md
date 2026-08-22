# Handoff to frontend — worker step cards: the budget-allocations endpoint, today and after item-aware typicals

```
date: 2026-08-22
audience: frontend (worker task-step cards with per-section budget display)
status of the endpoint described: SHIPPED and stable; every claim verified at source 2026-08-22
relation to other handoffs:
  - HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818 — the card recipe.
    ⚠ This document SUPERSEDES exactly one instruction of it: the bootstrap-cached
    typical-times join (§2 below). Everything else there stands.
  - HANDOFF_TO_FRONTEND_live_working_time_clock_20260822 — the live clock. Its §5
    (worked_seconds can decrease: three modes and the client rule) applies verbatim to
    every worked_seconds field in this document and is NOT restated here.
  - A future dated handoff will accompany the item-aware-typicals release (§6). It, not
    this document, will be the authority for the fields that release adds.
```

## 1. The one endpoint the cards call

```
GET /api/v1/item-economics/tasks/budget-allocations?task_ids=<id>&task_ids=<id>&...
```

- **Roles:** ADMIN, MANAGER, WORKER, SELLER — workers can call it directly.
- **Batching:** `task_ids` is repeatable, **at most 50 per call**. One batched call per
  feed page is the intended shape. More than 50 → the standard error envelope with
  identity `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`.
- **Unknown, deleted, or other-workspace task ids are silently omitted** from the
  response — not an error. Do not treat a missing task entry as a failure.
- Standard response envelope (`build_ok` / `build_err`), like every item-economics route.
- This is the cards' **single economics source**. Do not combine it with any other
  endpoint to compose the card's figures (§2).

## 2. ⚠ Superseded instruction — do not build the typical-times join

The 2026-08-18 handoff's worker-card section instructs the cards to fetch and cache
`GET /working-sections/typical-times` at bootstrap and join it in as the no-budget
fallback figure. **That instruction is superseded. Do not build it.**

Reason: after the item-aware-typicals release, that cached response would pair a
*generic* section typical with *item-aware* card figures for the same task and section —
a client-side cache surviving as the last source of cross-surface disagreement. The
fallback figure the cards need is already in this endpoint's own payload
(`steps[].typical_worker_seconds`, §4), in the `no_budget` state where it is needed, and
it will become item-aware automatically when the backend release lands — no frontend
change required.

`/working-sections/typical-times` remains a task-free benchmark surface for other
screens; it is simply not part of the card path.

## 3. Response shape today (verified at source)

```jsonc
{
  "budget_allocations": [
    {
      "task_id": "task_…",
      "status": "ok",                        // §5 — twelve exact values
      "allowed_worker_minutes": "120.00",    // string decimal | null
      "actual_worker_seconds": 4509,         // int, live basis
      "remaining_worker_minutes": "44.85",   // string decimal | null
      "allocation_method": "static_proportional_section_v1",
      "steps": [
        {
          "step_id": "tstp_…",
          "working_section_id": "wsec_…",
          "section_name_snapshot": "Cutting",
          "typical_worker_seconds": 2400,    // int | null — see §4 and §5
          "allowance_seconds": 7200,         // int | null — the card's "budget"
          "worked_seconds": 4509,            // int, LIVE — live-clock handoff §5 applies
          "left_seconds": 2691,              // int | null — negative = over budget
          "share_state": "on_track"          // §5 — four exact values
        }
      ]
    }
  ]
}
```

One row per **non-deleted step** of the task; each row is tagged with its working
section. Steps of the same task in the same section each carry their own slice of that
section's allowance, so a card-per-step UI maps one-to-one onto `steps[]`.

## 4. Mapping the payload onto the card design

| Card element | Field | Notes |
|---|---|---|
| "2h 00m budget" / "of 2h 00m" | `allowance_seconds` | Already fully derived server-side: task budget → split across participating sections weighted by their typicals → split across the section's steps. The frontend computes nothing. |
| The running timer | `worked_seconds` | Live at request time (settled seconds + the open working share). Tick it locally between fetches per the live-clock handoff §5, including its decrease rule. |
| "44m left" / "9m left" | `left_seconds` | `allowance_seconds − worked_seconds`, server-computed. |
| "Over budget by 26m 28s" | `left_seconds < 0` | Render the absolute value. Key the banner on the step's own `left_seconds`, not on `share_state` (see the nuance in §5). |
| No-budget reference figure | `typical_worker_seconds`, only when `share_state == "no_budget"` | Label it as history, never as a limit: "usually takes ~40m". There is no budget to be over in this state. May itself be `null` (young section, §5) — then show no figure. |
| Warning/normal coloring thresholds | frontend's choice | The backend ships no threshold; "44m left" teal vs "9m left" amber is a client decision. |

**The two states must be visually distinct:** "budget: 44m left" is a *limit*;
"usually takes ~40m" is *history talking*. A worker should never mistake one for the
other — this distinction is a backend contract requirement (the same figure family must
not be presentable as two different kinds of truth).

## 5. Exact value sets and nullability (each null names the state that produces it)

**`share_state`** — exactly four values, no others:

| Value | Meaning | `allowance_seconds` / `left_seconds` |
|---|---|---|
| `"on_track"` | allocated; the step's **section** is within its share | int / int (may still be negative per step — see nuance below) |
| `"over_share"` | allocated; the step's **section** has consumed more than its share | int / int (typically negative somewhere in the section) |
| `"excluded"` | the step is SKIPPED / CANCELLED / FAILED — it gets no allowance; its already-worked time was charged against the task pot before the split | `null` / `null` |
| `"no_budget"` | the task has no usable committed evaluation — there is no pot at all | `null` / `null` |

Nuance: `on_track` / `over_share` describe the step's **section**, mirrored onto every
step row of that section. The step's own position is `left_seconds`. So: over-budget
banner ← `left_seconds < 0`; section-level tinting (if you want it) ← `share_state`.

**`status`** — exactly twelve values: `ok`, `infeasible`, `item_missing_major_category`,
`not_configured_no_cost_group`, `not_configured_ambiguous_cost_group`,
`not_configured_no_basis_version`, `not_configured_no_cost_model_version`,
`item_unvalued`, `item_missing_expected_price`, `item_missing_purchase_cost`,
`currency_mismatch`, `not_evaluated`. Only `ok` and `infeasible` produce a real
division; **every other status yields `no_budget` step rows** and null task-level
minutes. The card does not need to branch on the individual failure statuses —
`share_state` already tells it what to render.

**Nullability table:**

| Field | Null exactly when |
|---|---|
| `allowed_worker_minutes`, `remaining_worker_minutes` | status is anything other than `ok` / `infeasible` (no usable evaluation) |
| `steps[].allowance_seconds`, `steps[].left_seconds` | `share_state` is `"excluded"` or `"no_budget"` |
| `steps[].typical_worker_seconds` | the section has fewer than 5 qualifying completed tasks in the 90-day window — the backend answers `null` rather than inventing a number |
| `steps[].worked_seconds`, `actual_worker_seconds` | never null |

`left_seconds`, when present, **can be negative** — that is the over-budget state, not
an error.

## 6. What changes with the item-aware-typicals release — build for this now

A backend pipeline currently in implementation makes the typicals **item-aware**: a
chair task's sections are weighted by *chair* history where enough exists, instead of
generic section history. Complexity gets rewarded through the weights. Consequences for
this endpoint, in order of what you must do about them:

1. **Numeric values may shift; shapes will not.** The owner-ratified contract wording:
   *"every task is evaluated under the new rule; allowances are eligible to change
   wherever item-category narrowing changes the relative section weights; many tasks
   remain numerically identical. The contract changes even where an individual numeric
   result does not."* → **Do not hard-code expected minutes in frontend tests or
   fixtures.** Render what arrives.
2. **New keys arrive, additively.** Planned (final authority = the release handoff):
   `steps[].typical_basis` (`"item_narrowed"` | `"section_wide"` |
   `"insufficient_sample"`), `steps[].sample_count` (int ≥ 0), and one
   `typical_resolution` object per task entry (the reconciliation provenance). Every new
   field will be always-present and non-nullable with an explicit default — the standing
   contract style you already rely on. → **Tolerate unknown keys today; build no UI
   against these until the release handoff ships.** They will enable a provenance badge
   or tooltip ("chair-specific figure, 14 samples") later.
3. **`allocation_method` flips** from `static_proportional_section_v1` to
   `static_proportional_section_v2`. → Treat it as data. If any test pins the string,
   expect the flip.
4. **`typical_worker_seconds` becomes item-aware** — same field, same nullability rule,
   smarter number. Your `no_budget` fallback display needs no change to benefit.
5. **No key is renamed or removed, no existing field changes type or nullability.**
   The card you build against §3's shape today keeps working unmodified.

## 7. Provenance appendix (for the backend record; frontend may ignore)

Claims in this document were verified at source on 2026-08-22, tree `2d83f40`:
route and roles `routers/api_v1/item_economics.py:route_get_task_budget_allocations`;
batch cap and omission of invisible tasks
`services/queries/item_economics/get_task_budget_allocations.py:get_task_budget_allocations`;
wire keys `domain/item_economics/division_serializers.py:serialize_budget_step` /
`serialize_budget_allocation` / `serialize_budget_allocations`; share states and
null production `domain/item_economics/budget_division.py:divide_production_budget` /
`_step_result`; status values `domain/item_economics/enums.py:EconomicsStatusEnum`;
live worked basis `services/queries/item_economics/live_worked_seconds.py:load_live_worked_seconds`.
The §6 forward-looking section derives from the `narrow_typical_work_times` intention
(RESOLVED round 7, D1–D25) and binds nobody until its release handoff ships.
