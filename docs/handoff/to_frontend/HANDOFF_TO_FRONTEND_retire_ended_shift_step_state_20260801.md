# Handoff — retire `ended_shift` from step-state handling (workers app)

**Type:** contract cleanup. The backend already shipped a compatibility shim, so this is **not**
blocking, but it is the "separate handoff" promised at the end of
`HANDOFF_TO_FRONTEND_remove_pause_reason_transition_20260801`.
**Blocking anything?** No — but the shim is temporary and this is what lets it be deleted.
**Repos:** `frontend/apps/workers-app/ManagerBeyo-app-workers` (primary),
`frontend/apps/managers-app/ManagerBeyo-app-managers` (read-only check).

---

## What happened

Migration `2645b4327b17` removed `ended_shift` from `task_step_state_enum`. **No step or state
record carries that state any more.** A step the shift ended under is `paused`; *why* it stopped
lives in `transition_reason` (system) or `pause_reason_id` (the worker's pick).

The previous handoff said to delete the *write*-side mapping and leave *read*-side `ended_shift`
handling alone "until the backend is ready". The backend is now ready — and past ready: the shipped
workers app sends `ended_shift` in the steps-list state filter, which after the migration made every
working-section steps list fail:

```
GET /api/v1/working-sections/{id}/steps?record_step_state=pending,working,paused,ended_shift
→ 500  invalid input value for enum task_step_state_enum: "ended_shift"
```

**That is fixed backend-side already** (see "What the backend does now"), so nothing is broken while
this handoff sits in a queue.

---

## What the backend does now

`record_step_state` and `task_step_states` are parsed before they reach SQL
(`beyo_manager/domain/task_steps/state_filters.py`):

| Sent value | Result |
|---|---|
| any current member (`pending`, `working`, `paused`, `blocked`, `completed`, `skipped`, `failed`, `cancelled`) | filters on it |
| `ended_shift` | **resolves to `paused`** — the state those steps are now in, so the filter still selects the population you meant |
| anything else | `422` naming the bad value and listing the allowed set (previously a `500`) |

Sending `paused` *and* `ended_shift` together is de-duplicated, so the workers app's current
`DEFAULT_STATE_FILTERS` behaves exactly as intended today.

**The alias is a shim, not the contract.** It exists so a shipped client keeps working; it will be
deleted once this handoff lands, after which `ended_shift` becomes a `422` like any other unknown
value.

---

## Frontend action required

### 1. Stop sending `ended_shift` as a filter value

- `src/features/task_steps/controllers/use-working-section-steps.controller.ts:110-115` —
  `DEFAULT_STATE_FILTERS` should be `["pending", "working", "paused"]`.
- `src/pages/task_steps/StepStateFilterSheetPage.tsx:34` — drop the `ended_shift` option. Its rows
  are already inside the `paused` option; keeping both shows the same steps under two chips.

Nothing else needs to change for the list to keep showing the same steps — a step that was
`ended_shift` yesterday is `paused` today.

### 2. Stop switching on `state === "ended_shift"` on the read side

No payload can contain it, so each of these is now dead:

- `src/features/task_steps/components/TaskStepActionButton.tsx:78`
- `src/features/task_steps/components/detail/TaskStepCircularActionButton.tsx:86`
- `src/features/task_steps/components/LastActiveStepCard.tsx:398`
- `src/features/task_steps/actions/use-transition-step-state.ts:59,129,275`
- `src/features/task_steps/types.ts:352`

They all read `state === "paused" || state === "ended_shift"`, so deleting the second half is
behaviour-preserving. Do **not** delete the surrounding branch.

### 3. Leave these alone — they are not the step state

- **Timeline state strings.** `linear_timeline` and the worker-stats breakdowns still emit
  `"ended_shift"` as a *derived* label. That is deliberate and unchanged; keep rendering it.
- **`total_ended_shift_seconds` / `total_ended_shift_count` on step payloads**, and
  `ended_shift_seconds` / `ended_shift_open_count` on analytics payloads. Still shipped, still
  populated. Note their meaning narrowed: a *worker-chosen* "Ended shift" pause now counts as
  ordinary pause time, so these buckets read lower than before for the same history.
- **`task_steps_counts.ended_shift`** (`types.ts:238,256`, `features/working_sections/types.ts:16`,
  `NotificationDeepLinkMount.tsx:40,44`). Keep the `.default(0)` — it is already written for this.
  Confirm with the backend before removing the key; it is a different contract from the step state.
- **`pause_ended_shift`** stays in the pause-reason picker. It is an ordinary catalog row and a
  worker can still pick "Ended shift".

---

## How to know it worked

- Open a working section as a worker with the state filter at its default → the list loads, and a
  step that was force-closed by a clock-out appears under **Paused**.
- Filter explicitly to Paused → the same step is there, listed once.
- Grep the workers app for `"ended_shift"` → only timeline labels, `total_ended_shift_*`, and
  `task_steps_counts.ended_shift` should remain.

---

## Trace links

- Intention: `backend/docs/architecture/under_construction/intention/INTENTION_ended_shift_step_state_collapse_20260731.md`
- Plan: `backend/docs/architecture/archives/implementation/PLAN_ended_shift_step_state_collapse_20260801.md`
- Migration: `backend/app/migrations/versions/2645b4327b17_collapse_ended_shift_step_state.py`
- Predecessor handoff (the one that deferred this): `HANDOFF_TO_FRONTEND_remove_pause_reason_transition_20260801.md`
- Deploy runbook: `backend/docs/deploy/RUNBOOK_20260801_three_feature_sets.md`
