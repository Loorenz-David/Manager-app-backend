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
- Sequencing: **successor set** — decided 2026-07-31 by the session tracking
  `MASTER_PLAN_system_transition_reasons_20260731.md`. See "Sequencing assessment" for the ruling
  and its reasoning. This intention is no longer asking a question; it is awaiting its own plan.

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

> ### ⚠ The "sharpening" claim above is WRONG, and this is a blocking design question
>
> *Added 2026-07-31 by the transition-reasons tracking session, verified against
> `aggregate_metrics.py:17-25`.*
>
> An earlier revision of this section claimed the re-key *sharpens* semantics: "only the system
> clock-out force-close lands in the `ended_shift` bucket; a worker manually choosing a reason
> becomes an ordinary pause." That reasoning holds for a lunch break. It does **not** hold for a
> reason whose entire meaning is *"I am going home now"*, and as written it reintroduces the exact
> corruption this document says must be prevented.
>
> **Today:** a worker picks "Ended shift" → `pause-reason-transition.ts` maps it to
> `new_state: ended_shift` → the step closes into `ENDED_SHIFT` → the overnight gap lands in
> `total_ended_shift_seconds`. Quarantined, correctly.
>
> **Under this intention as written:** the same pick produces `state: paused` +
> `pause_reason_id`, and bucketing keys on `transition_reason == SHIFT_ENDED` — **null** for a
> worker's pick. Those ~15 hours land in `total_pause_seconds`. Clock-out does not rescue it:
> it force-closes `WORKING` steps, not `PAUSED` ones, so the step genuinely sits open overnight.
>
> That is verbatim the failure named four paragraphs above: *"if that lands in
> `total_pause_seconds`, every pause-ratio and productivity metric is corrupted."*
>
> **Two resolutions. This is a product decision and belongs to the operator.**
>
> 1. **Remove "Ended shift" from the worker's pause sheet** as part of this set, when
>    `pause-reason-transition.ts` is deleted. The worker clocks out instead; clock-out force-closes
>    the step with `SHIFT_ENDED`; one path, one bucket, no ambiguity. **Recommended** — it is
>    consistent with this document's own thesis, and it dissolves the duplicate-display problem
>    below at the same time.
> 2. **Keep it selectable and bucket on either signal** — `transition_reason == SHIFT_ENDED` *or*
>    `pause_reason_id` pointing at that row. Preserves the metric, but puts a catalog dependency
>    back inside a metric, which is the thing the parent feature set exists to remove.
>
> **Related, and resolved by option 1:** after phase 4 keeps `pause_ended_shift` selectable, a
> worker-picked and a system-written ended shift render with the **same name and the same icon**,
> distinguishable only by `client_id` (`par_…` versus `shift_ended`). Under option 2 they would
> also sit in different time buckets while looking identical — a reporting inconsistency a manager
> could see and not be able to explain.
>
> **Consequence for the parent set:** phase 4's amendment keeping `pause_ended_shift` selectable is
> correct **now** — removing it today would break the pause sheet, which has no other way to
> produce the state. But that justification is **interim**. Once this set deletes
> `pause-reason-transition.ts`, the row's reason for existing goes with it, and under option 1 the
> row should be retired here rather than in phase 4.

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
   **This criterion is currently unmeetable as the document is specified** — see the boxed warning
   in "Architectural direction". The characterization test must cover **both** an
   operator-initiated clock-out **and** a worker-picked ended-shift pause left open overnight; the
   second is the one that regresses.
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

### Interaction with the phase 4 retirement question — RESOLVED

This intention raised a live defect in the transition-reasons set: phase 4 soft-deleted
`pause_ended_shift`, but `list_pause_reasons.py:19` filters `is_deleted IS false`, so the row would
have vanished from the worker's picker and `pause-reason-transition.ts` could then never produce
`ended_shift`. T6's amendment kept the `slug` *column* but did not address the *row* disappearing.

**Fixed at source, 2026-07-31.** Phase 4 was amended: it now retires the *machinery* — the slug
lookup, `is_system_managed`, runtime resolution — and leaves `pause_ended_shift` as an ordinary
worker-selectable row. The reasoning is that feature set's own thesis applied consistently: a
catalog row is fine; a catalog row that system behaviour depends on is not.

**Consequence for this intention: the row survives**, which is the opposite of what this document
originally assumed. That is *better* for this work, not worse — the pause sheet keeps its "Ended
shift" entry throughout, so removing `TaskStepStateEnum.ENDED_SHIFT` changes only what state that
selection produces, not whether the selection exists. There is no window in which a worker loses the
ability to end a shift from the sheet.

A second consequence, recorded so this intention's implementer does not trip on it: **phase 3 no
longer backfills rows pointing at `pause_ended_shift`.** Historically a worker's pick and a
clock-out write are indistinguishable (same state, same `pause_reason_id`, `transition_reason` null
on both), so backfilling would have relabelled real worker choices as system transitions. Those rows
therefore still carry a catalog reference when this work begins.

## Sequencing assessment — DECIDED

**Ruling (2026-07-31, operator, via the session tracking the transition-reasons set): run this as a
successor set.** The analysing session recommended exactly this and argued honestly against its own
convenience; the ruling agrees with it.

**Decisive reason.** The transition-reasons set's stated delivery shape is a **single deploy**.
Folding this in would put a second irreversible enum-and-backfill migration over
`step_state_records` and `task_steps` into a deploy that already carries phase 3's. Two destructive
migrations reaching production together is how history is lost. Compounding it, this is the only
part of the combined work that is cross-repo — every phase of the current set is backend-only, so
folding it in would change the delivery model, not merely the scope.

**One correction to the analysis, which strengthened the ruling.** This document worried that
folding the work in *after* phase 4 ships might require revisiting phase 4's check constraints. It
would not: that constraint governs `transition_reason` versus `pause_reason_id`, which removing a
`state` enum member does not touch. The coupling between the two sets is weaker than assumed, so
there is correspondingly less reason to rush.

### Constraints on the successor set

- **Implementation starts after the transition-reasons set is deployed.** The hard dependency is
  phase 3's backfill: the bucketing rewrite reads `transition_reason` on historical rows, and run
  before it would silently zero every historical `ended_shift` bucket.
- **Planning may begin earlier.** Planning is parallel-safe, and doing it during phase 3 or 4 allows
  whatever those phases learn about the data to be folded in. There is no urgency; the trace below
  will keep.
- **Keep it small.** Three or four phases at most — this is one enum removal, one backfill, one
  frontend change. The transition-reasons set was drafted at eleven phases and restructured to four
  precisely because ceremony sized for a larger feature set is expensive and buys nothing. The one
  phase that genuinely earns an independent review is the timeline precedence rework at
  `linear_timeline.py:241-243`, which this document already identifies as the highest-risk item.
- **Its own deploy**, separate from the transition-reasons set, and coordinated with the frontend
  because of W2.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| *(none yet)* | — | — | awaiting the sequencing decision above |

## Open questions

- ~~**Sequencing** — successor set, or a phase 5?~~ **Resolved 2026-07-31: successor set.** See
  "Sequencing assessment".
- ~~**`pause_ended_shift` catalog row** — retire it, or keep it worker-selectable?~~ **Resolved
  2026-07-31: the row survives**, decided in the transition-reasons set rather than here. Phase 4
  retires the machinery and leaves the row selectable. This intention originally assumed the row
  would disappear and argued it did not matter either way; the outcome is the more convenient of
  the two.
- **Does the timeline keep emitting `"ended_shift"` as a derived state string?** Still open, and
  still the one that blocks specifying the timeline rework. This document assumes **yes**
  (contract-preserving), which the tracking session endorsed as correct: it is a *derived label*,
  not a step state, so preserving it costs nothing and changing it would be a published frontend
  contract change needing its own handoff. Confirm before planning.
- **Do historical `task_steps.state = 'ended_shift'` rows need `transition_reason` on the step
  itself?** Still open. The column lives on `step_state_records`, not `task_steps`. Assumed
  acceptable that the step's current state becomes `paused` with no reason attached — matching how a
  normally-paused step already behaves. Confirm; impact if unresolved is that the backfill's
  step-table half is underspecified.
- **BLOCKING — does "Ended shift" stay in the worker's pause sheet?** See the boxed warning in
  "Architectural direction". As specified, this set moves a worker-picked ended-shift pause from
  `total_ended_shift_seconds` into `total_pause_seconds`, corrupting the pause ratio the metric
  exists to protect. Option 1 (remove it from the sheet, worker clocks out instead) is recommended
  and also resolves the identical-rendering problem. **Impact if unresolved: the bucketing rework
  cannot be specified, and success criterion 3 — same values before and after — cannot be met.**
- **New — what happens to worker-chosen `pause_ended_shift` rows?** Because phase 3 deliberately
  leaves them carrying a catalog reference, this work will meet `step_state_records` rows that are
  `state = ended_shift` with a non-null `pause_reason_id`. Under the target semantics those become
  `PAUSED` with the catalog reference retained — an ordinary worker pause, which is the correct
  outcome. State it explicitly in the plan; do not let the backfill assume every `ended_shift` row
  is a system transition.

## Progress notes

- `2026-07-31`: **Bucketing regression found** by the transition-reasons tracking session, verified
  against `aggregate_metrics.py:17-25`. This document's "sharpening" claim was wrong: re-keying the
  `ended_shift` bucket onto `transition_reason` alone moves a worker-picked ended-shift pause into
  `total_pause_seconds`, which is the corruption the document itself says must be prevented.
  Recorded as a blocking design question with two resolutions; the recommended one removes "Ended
  shift" from the worker's pause sheet as part of this set. Found while assessing whether the phase
  2 round-3 fix prompt carried unstated assumptions — it did not; this did.
- `2026-07-31`: **Sequencing decided — successor set** (see above). The assessment was accepted as
  written, with one correction: phase 4's check constraints are not affected by removing a `state`
  member. Two changes were made to the transition-reasons set as a direct result of this document:
  phase 4 no longer retires `pause_ended_shift` (it would have broken the worker app's pause sheet),
  and phase 3 no longer backfills rows pointing at it (a worker's pick and a clock-out write are
  historically indistinguishable, so backfilling would have relabelled real worker choices). Both
  were live defects in that set, found by this trace.
- `2026-07-31`: Intention drafted from an operator decision taken while reviewing the worker-shift
  endpoints for the reassigned-steps frontend handoff. The chain that produced it: the phase 4
  retirement of `pause_ended_shift` was found to break the worker app's pause sheet → tracing why
  the sheet needs that row showed it exists only to select a *state* → which raised whether the
  state should exist at all. Full reference trace recorded above so the receiving session does not
  repeat it.

## Lifecycle transition

- Current status: `active` — sequencing decided, awaiting its own implementation plan
- Next status: `achieved`
- Transition trigger: all success criteria met. **Absorption into
  `MASTER_PLAN_system_transition_reasons_20260731.md` is no longer a possible outcome** — that was
  ruled out on 2026-07-31. This intention gets its own plan set, planned no earlier than convenient
  and implemented after the transition-reasons set is deployed.
