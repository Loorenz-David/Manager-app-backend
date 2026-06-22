# PLAN_transition_step_mark_inaccurate_20260622

## Metadata

- Plan ID: `PLAN_transition_step_mark_inaccurate_20260622`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-22T00:00:00Z`
- Last updated at (UTC): `2026-06-22T12:21:21Z`
- Related issue/ticket: n/a
- Intention plan: n/a

## Goal and intent

- Goal: Allow `route_transition_step_state` to optionally mark the closing `StepStateRecord` as time-inaccurate in the same request, using the shared logic already owned by CMD-13 (`mark_step_time_inaccurate`).
- Business/user intent: Managers and workers often know at the moment they transition a step that the recorded interval was inaccurate (e.g. they forgot to pause, or paused very late). Today they must make a separate API call after the transition. This reduces that to one atomic operation.
- Non-goals: Does not change how `route_mark_step_time_inaccurate` (CMD-13) works; does not affect auto-pause logic; does not alter how `increment_step_time_metrics` is invoked — the existing guard already handles the skip.

## Scope

- In scope:
  - Add `mark_closing_record_inaccurate: bool = False` to `_TransitionStepBody` (router)
  - Add same field to `TransitionStepStateRequest` (request parser)
  - Extract shared helper `apply_inaccurate_time_flag(record, step, now)` from CMD-13
  - Call that helper inside `transition_step_state` before the metrics guard when the flag is set
- Out of scope:
  - Changing CMD-13 (`mark_step_time_inaccurate`) public API or route
  - Marking the **new** record inaccurate (only the closing/previous record)
  - Adding the flag to auto-pause logic
- Assumptions:
  - The existing guard in `transition_step_state.py` line 291 (`if not closing_record.recorded_time_marked_wrong`) already skips `increment_step_time_metrics` — no additional change needed there
  - `step.updated_at = now` is already set by the transition flow; the shared helper setting it again is harmless

## Clarifications required

None — requirements are clear.

## Acceptance criteria

1. `POST /{task_id}/steps/{step_id}/transition` with `mark_closing_record_inaccurate: true` sets `closing_record.recorded_time_marked_wrong = True` and `step.taken_from_average = True` atomically within the same transaction
2. When the flag is set, `increment_step_time_metrics` is NOT called for the closing record's interval (same behavior as if CMD-13 were called after the transition)
3. When the flag is absent or `false`, behavior is identical to the current implementation
4. CMD-13 (`mark_step_time_inaccurate`) continues to work correctly — now internally delegating to the shared helper

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md`: command shape, session.add/flush/error-raising pattern
- `backend/architecture/09_routers.md`: router handler wiring, Pydantic body, run_service, build_ok/err
- `backend/architecture/46_serialization.md`: serialization layer — not modified here

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: local delta for command patterns

### File read intent — pattern vs. relational

Permitted reads performed:
- `transition_step_state.py` — to understand the exact position to insert the inaccurate flag logic (after closing record, before metrics guard)
- `mark_step_time_inaccurate.py` — to understand the exact mutations to centralize
- `requests/__init__.py` — for exact field names in `TransitionStepStateRequest`
- `StepStateRecord` model — for `recorded_time_marked_wrong` and `taken_from_average` fields
- `TaskStep` model — for `taken_from_average` field

### Skill selection

- Primary skill: `architecture/06_commands.md` (write command pattern)
- Router trigger terms: `transition`, `mark-inaccurate`
- Excluded alternatives: none

## Implementation plan

### Step 1 — Extract shared helper into `mark_step_time_inaccurate.py`

**File:** `app/beyo_manager/services/commands/task_steps/mark_step_time_inaccurate.py`

Add a module-level function above `mark_step_time_inaccurate`:

```python
def apply_inaccurate_time_flag(
    record: StepStateRecord, step: TaskStep, now: datetime
) -> None:
    record.recorded_time_marked_wrong = True
    step.taken_from_average = True
    record.updated_at = now
    step.updated_at = now
```

Then update `mark_step_time_inaccurate` (lines 46-49) to call it:

```python
# before (inline mutations):
record.recorded_time_marked_wrong = True
step.taken_from_average = True
record.updated_at = datetime.now(timezone.utc)
step.updated_at = datetime.now(timezone.utc)

# after:
now = datetime.now(timezone.utc)
apply_inaccurate_time_flag(record, step, now)
```

---

### Step 2 — Add field to `TransitionStepStateRequest`

**File:** `app/beyo_manager/services/commands/task_steps/requests/__init__.py`

In `TransitionStepStateRequest` (line 96), add:

```python
mark_closing_record_inaccurate: bool = False
```

---

### Step 3 — Add field to `_TransitionStepBody`

**File:** `app/beyo_manager/routers/api_v1/tasks.py`

In `_TransitionStepBody` (line 166), add:

```python
mark_closing_record_inaccurate: bool = False
```

The body is already passed as `**body.model_dump()` into `ServiceContext.incoming_data` at line 607 — no change to the router handler needed.

---

### Step 4 — Apply the flag inside `transition_step_state`

**File:** `app/beyo_manager/services/commands/task_steps/transition_step_state.py`

1. Add import at the top:
   ```python
   from beyo_manager.services.commands.task_steps.mark_step_time_inaccurate import apply_inaccurate_time_flag
   ```

2. After step 5 (closing record is fetched and `closing_record.exited_at = now` is set, line 267), insert a new block labeled **5b** immediately before line 271 (where `new_record` is created):

   ```python
   # 5b. Optionally mark closing record as inaccurate (same logic as CMD-13)
   if request.mark_closing_record_inaccurate:
       apply_inaccurate_time_flag(closing_record, step, now)
   ```

   Because this runs before the guard at line 291:
   ```python
   if not closing_record.recorded_time_marked_wrong:
       ...
       increment_step_time_metrics(step, closing_state, interval_seconds)
   ```
   …the metrics increment is automatically skipped when the flag is set. No additional changes to the guard are needed.

---

## Risks and mitigations

- Risk: `step.updated_at` is set twice (once by `apply_inaccurate_time_flag`, once at line 289 in the transition flow)
  Mitigation: Both assign the same `now` value; SQLAlchemy deduplicates the write — harmless

- Risk: Forgetting to flush before the metrics guard
  Mitigation: No flush is required between step 5b and the guard — both mutate in-memory objects in the same transaction; the flush at line 283 (`await session.flush()`) follows after the new record is created, which is after the guard

- Risk: Event duplication — CMD-13 dispatches `task:updated`; should `transition_step_state` also dispatch it when flag is set?
  Mitigation: `transition_step_state` already dispatches `task:step-state-changed` (and `task:state-changed` if task state changed), which are higher-fidelity events. No extra `task:updated` event needed.

## Validation plan

- Call `POST /{task_id}/steps/{step_id}/transition` with `{"new_state": "paused", "mark_closing_record_inaccurate": true}` and verify `StepStateRecord.recorded_time_marked_wrong = True` and `TaskStep.taken_from_average = True` in the DB
- Call the same route with `mark_closing_record_inaccurate: false` (or absent) and verify neither flag is set
- Call CMD-13 directly and verify it still works, now via the shared helper
- Verify that `increment_step_time_metrics` is NOT called when flag is set (check aggregate seconds don't increment)

## Review log

- `2026-06-22` `claude-haiku-4-5`: Initial plan created and approved
- `2026-06-22` `codex`: Implemented the shared inaccurate-time helper, threaded the transition flag from router to command, validated the touched modules with compile/import checks, and prepared the archival summary.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation summary

- Added `mark_closing_record_inaccurate: bool = False` to the task step transition request body and parser.
- Extracted `apply_inaccurate_time_flag(record, step, now)` from CMD-13 and reused it inside `transition_step_state`.
- Applied the inaccurate flag to the closing record before the existing metrics guard, so inaccurate intervals are skipped without changing aggregate metric logic.
- Wrote the implementation summary at `docs/architecture/implemented_summaries/SUMMARY_PLAN_transition_step_mark_inaccurate_20260622.md`.
