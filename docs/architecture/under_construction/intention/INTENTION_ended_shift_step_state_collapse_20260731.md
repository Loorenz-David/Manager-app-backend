# INTENTION_ended_shift_step_state_collapse_20260731

## Metadata

- Intention ID: `INTENTION_ended_shift_step_state_collapse_20260731`
- Status: `active`
- Owner: David (operator)
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T00:00:00Z`
- Related intention: `INTENTION_system_transition_reasons_20260730` — **this intention depends on
  that one's `transition_reason` column existing and being backfilled.** It is the natural
  continuation of the same argument, applied one layer up.
- Addressed to: the session tracking
  `MASTER_PLAN_system_transition_reasons_20260731.md`, to assess whether this belongs in that
  phase set or as a successor set. See "Sequencing assessment" — that is the decision being asked
  for.

## Goal

Remove `TaskStepStateEnum.ENDED_SHIFT` as a task-step state. A step that stops because a shift
ended is simply **`PAUSED`**, and *why* it paused is carried by `transition_reason` (system) or
`pause_reason_id` (worker's choice) — never by the state itself.

## Why this matters

`ENDED_SHIFT` is a **state that encodes a reason**. That is the same category error
`INTENTION_system_transition_reasons_20260730` exists to remove — there, a state transition
depended on a catalog row's *slug*; here, the reason for a pause is smuggled into the *state
enum*. Both conflate "what is this thing" with "why did it happen".

Two concrete consequences visible today:

1. **The step state and the shift state disagree about what they model.** "The worker ended their
   shift" is a fact about the **worker**, and `UserShiftStateRecord` already records it
   (`UserShiftStateEnum.ENDED_SHIFT`). Duplicating it onto the step means the same event is stored
   in two vocabularies that can drift.

2. **It forces a fake choice into the worker's pause picker.** Today the worker app renders the
   pause-reason sheet and translates one specific row into a *different state*:

   | Location | Behaviour |
   |---|---|
   | `frontend/apps/workers-app/.../features/task_steps/lib/pause-reason-transition.ts:12` | `reason.slug === "pause_ended_shift" ? "ended_shift" : "paused"` |
   | `frontend/apps/workers-app/.../pages/task_steps/PauseReasonSheetPage.tsx:108-113` | sends `new_state: transition.newState` **and** `pause_reason_id: reason.client_id` together |

   So a *pause reason* selection silently changes the *state machine target*. Under this
   intention, every pause reason means `paused`, the reason travels in `pause_reason_id`, and
   `pause-reason-transition.ts` is deleted outright.

**Operator's framing (2026-07-31), which is the intent to preserve:** if a worker picks "ended
shift" from the pause sheet, that is *precisely* a pause with a reason the worker chose. The real
"ended shift" concept belongs to the worker's shift record, which the declared-worker-states and
system-transition-reasons work already owns. The step record should record only that *a pause
happened, for a stated reason*.

## Architectural direction

Target semantics for a step that stops because the shift ended:

| Case | step `state` | `transition_reason` | `pause_reason_id` |
|---|---|---|---|
| Clock-out force-closing an open working step | `PAUSED` | `SHIFT_ENDED` | `NULL` |
| Worker chose "ended shift" (or any reason) in the sheet | `PAUSED` | *(worker-paused)* | the chosen catalog row |
| Auto-pause on task switch *(unchanged)* | `PAUSED` | `OTHER_TASK_PRIORITY` | `NULL` |

`TaskStepStateEnum` reduces to `PENDING · WORKING · PAUSED · BLOCKED · COMPLETED · SKIPPED ·
FAILED · CANCELLED`.

### The one thing that must not be lost

`total_ended_shift_seconds` exists to **quarantine off-shift time from pause time**. A step left
open at 17:00 and resumed at 08:00 accrues ~15 hours; if that lands in `total_pause_seconds`,
every pause-ratio and productivity metric is corrupted.

The metric survives by changing the *bucketing key*, not by dropping the column:

```python
# app/beyo_manager/domain/task_steps/aggregate_metrics.py:23-25 — today
elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
    step.total_ended_shift_seconds += interval_seconds
    step.total_ended_shift_count += 1

# proposed
elif closing_record.transition_reason == TransitionReasonEnum.SHIFT_ENDED.value:
    step.total_ended_shift_seconds += interval_seconds
    step.total_ended_shift_count += 1
```

Every published field keeps its name **and its meaning** ("time a step sat idle because the shift
ended"). This is what makes the change contract-neutral — see "Published surface" below.

Note this *sharpens* the semantics rather than blurring them: only the system clock-out
force-close lands in the `ended_shift` bucket. A worker manually choosing a reason becomes an
ordinary pause, bucketed by `pause_by_reason` like any other. That matches the operator's framing.

## Traced evidence (2026-07-31 — verify, do not re-derive)

Traced outward from `TaskStepStateEnum.ENDED_SHIFT`. Every reference in `app/` is listed; an
unlisted site is one the implementing phase can miss.

### Writers (2)

| # | Site | Note |
|---|---|---|
| W1 | `services/commands/users/_clock_worker_shift.py:203` | `new_state=TaskStepStateEnum.ENDED_SHIFT` on clock-out. **The primary writer** — every clock source (HTTP, Connecteam, overnight safeguard) reaches it. Already carries `transition_reason=SHIFT_ENDED` after phase 2, so only the state changes. |
| W2 | frontend `PauseReasonSheetPage.tsx:108-113` | sends `new_state: "ended_shift"` when the picked slug is `pause_ended_shift`. Cross-repo. |

### Time bucketing (4) — all key on state, all move to the reason

| # | Site |
|---|---|
| B1 | `domain/task_steps/aggregate_metrics.py:23-25` — the step-level totals |
| B2 | `services/tasks/analytics/process_step_transition.py:102` (`_STEP_TIME_FIELDS`) and `:108` (inaccurate-seconds map) |
| B3 | `services/queries/worker_stats/get_worker_daily_step_breakdown.py:62` (`_TIME_STATES`), plus the `{"working","paused","ended_shift"}` dicts at `:224,232,321-323,330,427,432` and the field map at `:297` |
| B4 | `services/queries/analytics/averaged_time.py:27` (`_TIME_STATES`) |

### Timeline composition (1) — **the highest-risk item**

`domain/analytics/linear_timeline.py:241-243` implements a slice precedence:

```
active pause  >  ended_shift  >  idle
```

It distinguishes "worker is present but this step is paused" from "worker went home with the step
open". With one state, that has to come from the reason instead. Phase 1 of the transition-reasons
set already taught these composers to read `transition_reason` (audit rows R8–R12), so the
plumbing exists — but this is where defects are most likely.

Related: `linear_timeline.py:58,107` type comments, `:276,292` the seconds dict,
`concurrency.py:28`.

### "Non-terminal / still active" membership (4)

`ENDED_SHIFT` is **not** in `TERMINAL_STEP_STATES` (`domain/task_steps/constants.py`), so the step
stays alive and resumable. It appears in:

| # | Site | Effect of removal |
|---|---|---|
| M1 | `domain/task_steps/constants.py:14` — `TIME_BEARING_STATES` | drop the member |
| M2 | `services/queries/worker_stats/_roster.py:25` | drop the member |
| M3 | `services/queries/working_sections/get_worker_working_sections.py:19` | drop the member |
| M4 | `services/queries/working_sections/get_user_last_active_step_record.py:16` | drop the member |

All four already contain `PAUSED`, so removing `ENDED_SHIFT` is subtractive — **no behaviour
changes**, because the steps in question will now be `PAUSED` and already match.

### State machine (1)

`services/commands/task_steps/transition_step_state.py:54-70`. Today:

```
WORKING      → {PAUSED, ENDED_SHIFT, COMPLETED, FAILED, CANCELLED}
PAUSED       → {WORKING, ENDED_SHIFT, FAILED, CANCELLED}
ENDED_SHIFT  → {WORKING, FAILED, CANCELLED}
```

Removing the member is a pure simplification: the `ENDED_SHIFT` row disappears and it drops out of
the other two sets. Nothing gains a transition it did not have.

### Published surface (contract-relevant)

| Field | Where | Impact |
|---|---|---|
| `total_ended_shift_seconds`, `total_ended_shift_count` | `domain/tasks/serializers.py::serialize_step` | **None**, if bucketing moves to the reason (above). Note this ships in every step payload, including the new reassigned-steps endpoint — see `HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md` §5.1. |
| `ended_shift_seconds`, `ended_shift_open_count` | `domain/analytics/serializers.py:29,32,57,60` | None, same reason |
| `"ended_shift"` as a **timeline state string** | `linear_timeline.py`, breakdown responses | **Preserved deliberately.** It is a *derived* label, not a step state. The frontend keeps rendering the same value; only its derivation changes. |
| step `state: "ended_shift"` | any step payload | **Disappears.** After migration no step carries it. Frontend must not switch on it. |

### Migration cost — the real risk

`TaskStepStateEnum` is a **native Postgres enum** (`task_step_state_enum`), declared with
`create_type=True` on `models/tables/tasks/task_step.py:52-53` and reused with `create_type=False`
on `models/tables/tasks/step_state_record.py:39-40`. **Two tables share the type.**

Removing a value therefore requires recreating the type and rewriting both columns, plus a
backfill of every historical row:

```
step_state_records: state='ended_shift'  →  state='paused', transition_reason='shift_ended'
task_steps:         state='ended_shift'  →  state='paused'
```

Irreversible. Volumes must be measured **workspace-scoped and with the suite quiescent**, per the
standing instruction in the transition-reasons master plan's "Phase 1 inventory".

### Behavioural guard to verify explicitly

Clock-out will now leave steps **open in `PAUSED`**. On the next clock-in,
`reconcile_worker_shift_state` loads open steps in `states=(WORKING, PAUSED)`
(`reconcile_worker_shift_state.py:171`) — so yesterday's still-open pause could derive the worker
into `in_pause` instead of `idle`.

The protection already exists: `:172` passes `entered_at_or_after=shift_started_at` (the F6
guard), which excludes a record entered at 17:00 yesterday from a shift started at 08:00 today.
**But today that guard is redundant for this case**, because `ENDED_SHIFT` is not queried at all.
Under this change it becomes **load-bearing**. It needs a direct test, not an inherited one.

## Success criteria

1. No code path writes `TaskStepStateEnum.ENDED_SHIFT`; the enum member is gone from
   `task_step_state_enum` in the database.
2. Clock-out with an open working step produces `state = paused`, `transition_reason =
   shift_ended`, `pause_reason_id = NULL`.
3. `total_ended_shift_seconds` / `total_ended_shift_count` hold the **same values** for an
   equivalent scenario before and after — proven by a characterization test written first.
4. A worker selecting any pause reason (including one named "ended shift") produces `state =
   paused` with that `pause_reason_id`, and the frontend sends no `new_state` other than `paused`.
5. The linear timeline still distinguishes "paused while present" from "off shift" for both new
   and historical rows.
6. Clocking in the morning after leaving a step open derives the worker to `idle`, not `in_pause`.
7. Historical rows resolve to the same human-visible labels and the same time buckets as before.
8. `frontend/.../lib/pause-reason-transition.ts` is deleted and its two call sites simplified.

## Scope boundary

- **In scope:** removing the step state; re-keying time bucketing onto `transition_reason`; the
  timeline precedence rework; the enum migration and historical backfill; the state-machine
  simplification; the frontend simplification.
- **Out of scope:** `UserShiftStateEnum.ENDED_SHIFT` — that is the *worker's* shift state and is
  the correct home for this concept. Untouched.
- **Out of scope:** the `pause_ended_shift` catalog row's fate. That is a live open question in
  the transition-reasons set (phase 4 retirement vs. keeping it selectable). **This intention makes
  that question easier but does not answer it** — see below.
- **Non-goal:** changing what `total_ended_shift_seconds` *means*. It keeps its definition; only
  its derivation changes.

### Interaction with the phase 4 retirement question

The transition-reasons set has an unresolved issue: phase 4 soft-deletes `pause_ended_shift`, but
`list_pause_reasons` filters `is_deleted IS false`, so the row vanishes from the worker's picker —
and `pause-reason-transition.ts` can then never produce `ended_shift`. T6's amendment kept the
`slug` *column* (fixing the Zod break) but did not address the *row* disappearing.

**This intention dissolves that problem** rather than solving it: once no pause reason maps to a
different state, it does not matter whether `pause_ended_shift` survives as a catalog row. If the
operator wants a worker-visible "Ended shift" reason, it becomes an ordinary workspace-editable
personal reason like any other.

That is an argument for doing this work **close to** phase 4 — not necessarily inside it.

## Sequencing assessment (the decision being requested)

**Recommendation from the analysing session: run this as a successor set, not as a phase of
`system_transition_reasons`.** Presented with the reasoning so the tracking session can overrule
it on evidence this session does not have.

**Against folding it in:**

- It adds a **second irreversible enum-and-backfill migration** over `step_state_records` and
  `task_steps`, in a set that already has one (phase 3). Two destructive migrations reaching
  production in a single deploy — which is this set's stated delivery shape — is how history is
  lost.
- It is the only part of the combined work that requires a **cross-repo frontend change**. Every
  current phase is backend-only.
- The current set's phases 2–4 are `under_construction` with an active implement→review cycle.
  Widening scope mid-cycle costs the review discipline the restructure was designed to buy.

**For folding it in:**

- It reads `transition_reason` — the exact column phases 1–3 create and backfill. The dependency
  is real and one-directional.
- It resolves the phase 4 retirement question by dissolving it (above), and phase 4 currently has
  no answer to that question.
- The timeline composers are touched by both. Doing them twice risks conflicting rewrites.

**If the tracking session decides to fold it in**, the ordering constraint is hard: it must come
**after phase 3's backfill**, because the bucketing rewrite reads `transition_reason` on
historical rows. Sequenced before phase 3 it would read an empty column and silently zero every
historical `ended_shift` bucket. It should also be the **last** phase, so phase 4's constraint work
lands on the final shape of the enum rather than being redone.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| *(none yet)* | — | — | awaiting the sequencing decision above |

## Open questions

- **Sequencing** — successor set, or a phase 5 of `system_transition_reasons`? Impact if
  unresolved: the work cannot be planned; and if it is eventually folded in *after* phase 4 ships,
  phase 4's check constraints may need revisiting.
- **Does the timeline keep emitting `"ended_shift"` as a derived state string?** This intention
  assumes yes (contract-preserving). If the operator would rather the timeline show it as a pause
  with a typed reason, that is a **published frontend contract change** and needs its own handoff.
  Impact if unresolved: the timeline rework cannot be specified.
- **`pause_ended_shift` catalog row** — retire it (phase 4 as planned) or keep it as an ordinary
  worker-selectable personal reason? This intention works either way; the operator picks. Impact
  if unresolved: none for planning, but the worker's picker content differs.
- **Do historical `task_steps.state = 'ended_shift'` rows need `transition_reason` on the step
  itself?** The column lives on `step_state_records`, not `task_steps`. The step's *current* state
  becomes `paused` with no reason attached — which matches how a normally-paused step already
  behaves. Assumed acceptable; confirm. Impact if unresolved: the backfill's step-table half is
  underspecified.

## Progress notes

- `2026-07-31`: Intention drafted from an operator decision taken while reviewing the worker-shift
  endpoints for the reassigned-steps frontend handoff. The chain that produced it: the phase 4
  retirement of `pause_ended_shift` was found to break the worker app's pause sheet → tracing why
  the sheet needs that row showed it exists only to select a *state* → which raised whether the
  state should exist at all. Full reference trace recorded above so the receiving session does not
  repeat it.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved | superseded`
- Transition trigger: all success criteria met, **or** absorbed into
  `MASTER_PLAN_system_transition_reasons_20260731.md` as a phase (in which case this intention is
  marked `superseded` and points at that plan)
