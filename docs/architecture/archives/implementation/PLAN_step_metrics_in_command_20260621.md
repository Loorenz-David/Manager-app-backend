# PLAN_step_metrics_in_command_20260621

## Metadata

- Plan ID: `PLAN_step_metrics_in_command_20260621`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-21T00:00:00Z`
- Last updated at (UTC): `2026-06-21T15:45:01Z`
- Related issue/ticket: —
- Intention plan: —
- Parent plan: `PLAN_task_step_aggregate_metrics_20260621` (post-implementation review)
- Supersedes: Fix 1 of `PLAN_process_step_transition_corrections_20260621` (`TaskStep.updated_at` in worker). Fix 2 of that plan (`section_name_snapshot`) remains independent and unaffected.
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_step_metrics_in_command_20260621.md`

## Goal and intent

- **Goal:** Move `TaskStep` time/count aggregate-metric writes (`total_working_seconds`, `total_working_count`, `total_pause_seconds`, `total_pause_count`, `total_ended_shift_seconds`, `total_ended_shift_count`) from the analytics worker into the `transition_step_state` command transaction. Remove those writes from the analytics worker to prevent double-counting.
- **Business/user intent:** After the original `PLAN_task_step_aggregate_metrics_20260621`, these columns are written asynchronously by the analytics worker. The frontend refetches the step immediately after a state transition and sees stale zeros until the worker runs. Moving the writes into the command transaction makes the step row immediately consistent on commit — the same response or the first refetch shows correct time/count values.
- **Architecture:** Time and count require no extra queries — all needed data (`closing_record.entered_at`, `now`, `closing_record.recorded_time_marked_wrong`, `step`) is already in scope at the point of record closure. Cost (`total_cost_minor`) requires a `UserWorkProfile` salary lookup and stays in the analytics worker. Issue counts (`total_issues_count`, `total_issues_resolved_count`) require a separate `ItemIssue` query at COMPLETED and also stay in the analytics worker.
- **Non-goals:**
  - No change to `total_cost_minor` writes — analytics worker continues to handle cost.
  - No change to `total_issues_count` / `total_issues_resolved_count` writes — analytics worker continues to handle issues.
  - No change to the four analytics stats tables or their handler logic.
  - No change to any route, serializer, or model.
  - No fix for `resolved_count = total_count` in `_apply_issues_at_completion` — out of scope (requires schema migration).

## Scope

- **In scope:**
  - **New file**: `app/beyo_manager/domain/task_steps/aggregate_metrics.py` — pure synchronous helper `increment_step_time_metrics(step, closing_state, interval_seconds)`.
  - **Modify**: `app/beyo_manager/services/commands/task_steps/transition_step_state.py` — two call sites: primary step and auto-paused conflicting step.
  - **Modify**: `app/beyo_manager/services/tasks/analytics/process_step_transition.py` — remove TaskStep time/count writes from `_apply_working_close`, `_apply_paused_close`, `_apply_ended_shift_close`; remove `task_step` parameter from `_apply_ended_shift_close`; add `task_step.updated_at` before `session.commit()` (covers Fix 1 of `PLAN_process_step_transition_corrections_20260621`).

- **Out of scope:** All other files.

## Clarifications required

_(none — all design decisions resolved below)_

## Acceptance criteria

1. After `transition_step_state` commits, `TaskStep.total_working_seconds` reflects the closed WORKING interval immediately (no worker delay).
2. After `transition_step_state` commits, `TaskStep.total_pause_seconds` and `total_ended_shift_seconds` behave equivalently for their respective closing states.
3. When a step transition auto-pauses a conflicting step, the conflicting `TaskStep.total_working_seconds` is also incremented within the same transaction.
4. If `closing_record.recorded_time_marked_wrong` is `True`, no time/count columns are incremented on `TaskStep` — matches the existing exclusion rule applied in the analytics worker.
5. The analytics worker no longer increments `TaskStep.total_working_seconds`, `total_working_count`, `total_pause_seconds`, `total_pause_count`, `total_ended_shift_seconds`, or `total_ended_shift_count` — double-counting is eliminated.
6. The analytics worker still increments `TaskStep.total_cost_minor` (WORKING and PAUSED closes) and `TaskStep.total_issues_count` / `TaskStep.total_issues_resolved_count` (at COMPLETED) — those writes are unchanged.
7. `_apply_ended_shift_close` no longer receives or touches `task_step` — it has no remaining TaskStep write (no cost, time/count moved to command).
8. After the analytics worker processes any step event that results in a `TaskStep` write (cost or issues), `task_step.updated_at` is set to the worker's `datetime.now(timezone.utc)` before commit.
9. `python3 -m compileall` on all three modified/created files passes with no errors.
10. No regression: all four stats-table rows (`UserDailyWorkStats`, `UserLifetimeStats`, `UserSectionDailyWorkStats`, `WorkingSectionDailyWorkStats`) continue to receive the same increments as before.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: all new reads and mutations inside `maybe_begin`; no manual commit or rollback.
- `backend/architecture/16_background_jobs.md`: worker handler pattern — single commit at end; non-raising for missing rows.

### File read intent — pattern vs. relational

Permitted reads before making changes:
- `app/beyo_manager/services/commands/task_steps/transition_step_state.py` — locate exact insertion points for Steps 1 and 2 (relational: line numbers).
- `app/beyo_manager/services/tasks/analytics/process_step_transition.py` — locate exact removal points for Step 3 (relational: what exists).

Prohibited:
- Reading any other file. The helper specification in Step 0 and all removal targets in Step 3 are fully specified below.

### Skill selection

- Primary skill: `backend/architecture/06_commands.md` (command mutation pattern, placement of writes inside `maybe_begin`).

## Cross-cutting rules

**Rule 1 — Exclusion rule is mandatory:**
Every call to `increment_step_time_metrics` must be guarded by `if not closing_record.recorded_time_marked_wrong:` (or `if not conflicting_record.recorded_time_marked_wrong:` for the auto-pause). Never call the helper unconditionally.

**Rule 2 — Interval computation:**
Use `max(0, int((now - closing_entered_at).total_seconds()))` inline — `now` and `closing_entered_at` are already in scope at both call sites. No shared helper needed.

**Rule 3 — No other command changes:**
Only `transition_step_state.py` is modified on the command side. No other command imports or calls `increment_step_time_metrics` in this plan.

**Rule 4 — Worker: only remove, never reorder:**
In `process_step_transition.py`, make surgical removals only. Do not reorder, rename, or reformat any surrounding code.

---

## Implementation plan

---

### Step 0 — Create `domain/task_steps/aggregate_metrics.py`

**Create** `app/beyo_manager/domain/task_steps/aggregate_metrics.py`:

```python
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.models.tables.tasks.task_step import TaskStep


def increment_step_time_metrics(
    step: TaskStep,
    closing_state: TaskStepStateEnum,
    interval_seconds: int,
) -> None:
    """Increment TaskStep time/count aggregate columns for a closed state record.

    Called synchronously inside the command transaction so the step row reflects
    correct values immediately on commit. Cost (total_cost_minor) and issue counts
    are still written by the analytics worker.
    Only call this when closing_record.recorded_time_marked_wrong is False.
    """
    if closing_state == TaskStepStateEnum.WORKING:
        step.total_working_seconds += interval_seconds
        step.total_working_count += 1
    elif closing_state == TaskStepStateEnum.PAUSED:
        step.total_pause_seconds += interval_seconds
        step.total_pause_count += 1
    elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
        step.total_ended_shift_seconds += interval_seconds
        step.total_ended_shift_count += 1
```

This is a pure synchronous function — no session, no `await`. It mutates the ORM object in-place; SQLAlchemy tracks the changes automatically and flushes them with the surrounding transaction. Any future command that closes a `StepStateRecord` calls this same helper.

---

### Step 1 — Primary step increment in `transition_step_state.py`

**File:** `app/beyo_manager/services/commands/task_steps/transition_step_state.py`

**Add import** (after the existing `beyo_manager.domain.task_steps.*` imports):
```python
from beyo_manager.domain.task_steps.aggregate_metrics import increment_step_time_metrics
```

**Location:** Inside `async with maybe_begin(ctx.session):`, immediately after the block that sets `step.updated_at = now` and `step.updated_by_id = ctx.user_id` (step-state update section, after `step.latest_state_record_id = new_record.client_id`).

`closing_entered_at` and `closing_state` are already captured earlier in the same block (`closing_state = closing_record.state`, `closing_entered_at = closing_record.entered_at`). `now` is defined at the top of the `async with` block.

**Add** the following block immediately after `step.updated_by_id = ctx.user_id`:

```python
        if not closing_record.recorded_time_marked_wrong:
            interval_seconds = max(0, int((now - closing_entered_at).total_seconds()))
            increment_step_time_metrics(step, closing_state, interval_seconds)
```

No other lines change in this section.

---

### Step 2 — Auto-paused step increment in `transition_step_state.py`

**File:** `app/beyo_manager/services/commands/task_steps/transition_step_state.py`

**Location:** Inside the auto-pause block (`if request.new_state == TaskStepStateEnum.WORKING:`, after `conflicting_step.updated_by_id = ctx.user_id` and `auto_paused_step = conflicting_step`), immediately before `await create_instant_task(...)` that enqueues the `PROCESS_STEP_TRANSITION` for the conflicting step.

`conflicting_closing_entered_at` is already captured in the auto-pause block (`conflicting_closing_entered_at = conflicting_record.entered_at`). The auto-pause always closes a `WORKING` record — the closing state is always `TaskStepStateEnum.WORKING`.

**Add** the following block immediately before the `await create_instant_task(...)` call in the auto-pause section:

```python
                if not conflicting_record.recorded_time_marked_wrong:
                    auto_pause_interval = max(0, int((now - conflicting_closing_entered_at).total_seconds()))
                    increment_step_time_metrics(conflicting_step, TaskStepStateEnum.WORKING, auto_pause_interval)
```

`TaskStepStateEnum` is already imported in this file. No new import needed beyond the one added in Step 1.

No other lines change in the auto-pause block.

---

### Step 3 — Remove TaskStep time/count writes from analytics worker

**File:** `app/beyo_manager/services/tasks/analytics/process_step_transition.py`

Three sub-edits:

#### Sub-edit A — `_apply_working_close`

In `_apply_working_close`, find the `if task_step is not None:` block at the end of the function:

Current:
```python
    if task_step is not None:
        task_step.total_working_seconds += interval_seconds
        task_step.total_working_count += 1
        if cost_minor:
            task_step.total_cost_minor = (task_step.total_cost_minor or 0) + cost_minor
```

Replace with (keep only the cost write):
```python
    if task_step is not None:
        if cost_minor:
            task_step.total_cost_minor = (task_step.total_cost_minor or 0) + cost_minor
```

#### Sub-edit B — `_apply_paused_close`

In `_apply_paused_close`, find the `if task_step is not None:` block at the end:

Current:
```python
    if task_step is not None:
        task_step.total_pause_seconds += interval_seconds
        task_step.total_pause_count += 1
        if cost_minor:
            task_step.total_cost_minor = (task_step.total_cost_minor or 0) + cost_minor
```

Replace with (keep only the cost write):
```python
    if task_step is not None:
        if cost_minor:
            task_step.total_cost_minor = (task_step.total_cost_minor or 0) + cost_minor
```

#### Sub-edit C — `_apply_ended_shift_close` (remove TaskStep block and parameter)

`_apply_ended_shift_close` has no cost write and its time/count writes are being removed. The `task_step` parameter is no longer needed.

Current signature:
```python
async def _apply_ended_shift_close(
    session: AsyncSession,
    payload: StepTransitionPayload,
    interval_seconds: int,
    worker_display_name: str,
    task_step: TaskStep | None,
) -> None:
```

Replace with:
```python
async def _apply_ended_shift_close(
    session: AsyncSession,
    payload: StepTransitionPayload,
    interval_seconds: int,
    worker_display_name: str,
) -> None:
```

Remove the `if task_step is not None:` block at the end of the function body:

Current (lines to remove):
```python
    if task_step is not None:
        task_step.total_ended_shift_seconds += interval_seconds
        task_step.total_ended_shift_count += 1
```

Remove these three lines entirely. The rest of the function body (stats-table increments) is unchanged.

Update the call site in `handle_process_step_transition`:

Current:
```python
            elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
                await _apply_ended_shift_close(session, payload, interval_seconds, credited_user_display_name, task_step)
```

Replace with:
```python
            elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
                await _apply_ended_shift_close(session, payload, interval_seconds, credited_user_display_name)
```

#### Sub-edit D — Add `task_step.updated_at` before commit

In `handle_process_step_transition`, immediately before `await session.commit()`:

```python
        if task_step is not None:
            task_step.updated_at = datetime.now(timezone.utc)
        await session.commit()
```

`datetime` and `timezone` are already imported at the top of the file. `task_step` is in scope. This ensures that when the analytics worker writes `total_cost_minor` or issue counts, `updated_at` reflects that write. (The command's `step.updated_at = now` handles the time/count case since those are now written in the command.)

---

## Risks and mitigations

- **Risk:** `closing_record.entered_at` is `datetime(timezone=True)` and `now = datetime.now(timezone.utc)` — subtraction produces a `timedelta`. Both are timezone-aware; subtraction is safe.
  **Mitigation:** `max(0, int(...total_seconds()))` clamps any negative delta (clock skew or extremely fast transitions) to zero, matching the worker's existing `_compute_interval_seconds` behavior.

- **Risk:** The auto-pause block increments `conflicting_step` metrics before `create_instant_task(PROCESS_STEP_TRANSITION)` is enqueued. When the analytics worker later processes that event, Sub-edit A above removes the time/count write from `_apply_working_close` for `task_step`, so there is no double-count on `total_working_seconds` / `total_working_count`.
  **Mitigation:** Sub-edits A and B are required before this plan is marked complete. Implementing only the command side without the worker side would cause double-counting.

- **Risk:** `_apply_ended_shift_close` signature change — if any other caller passes `task_step` positionally, removing the parameter breaks that caller.
  **Mitigation:** There is exactly one call site: in `handle_process_step_transition`. Sub-edit C updates it. No other file calls this private function.

- **Risk:** `task_step` is still fetched in the analytics worker even though it is no longer needed for ENDED_SHIFT. The fetch cost is negligible (PK lookup) and is still needed for WORKING/PAUSED cost and COMPLETED issues. No change to the fetch is needed.

- **Risk:** `recorded_time_marked_wrong` defaults to `False` (`nullable=False, default=False`). The guard `if not closing_record.recorded_time_marked_wrong:` is therefore safe to call on any freshly-loaded `StepStateRecord` including auto-pause records.

## Validation plan

- `python3 -m compileall app/beyo_manager/domain/task_steps/aggregate_metrics.py app/beyo_manager/services/commands/task_steps/transition_step_state.py app/beyo_manager/services/tasks/analytics/process_step_transition.py` — no errors.
- Manual: trigger `PENDING → WORKING` on a step. Query `task_steps` immediately — `total_working_count` is still 0 (PENDING close is not a metered state; no increment expected). Confirm `total_working_seconds == 0`.
- Manual: trigger `WORKING → PAUSED`. Query `task_steps` immediately (before analytics worker runs) — `total_working_seconds > 0`, `total_working_count == 1`, `total_pause_seconds == 0`.
- Manual: trigger `PAUSED → WORKING`. Query immediately — `total_pause_seconds > 0`, `total_pause_count == 1`.
- Manual: trigger a second step start that auto-pauses an in-progress step. Query the auto-paused step immediately — `total_working_seconds` incremented for the conflicting step.
- Manual: verify analytics worker still writes `total_cost_minor` after a WORKING close (non-zero salary profile required).
- Manual: verify `UserSectionDailyWorkStats` still receives the same increments — no regression on stats tables.

## Review log

- Added synchronous step time/count aggregation in `transition_step_state`.
- Removed overlapping step time/count writes from the analytics worker while preserving cost and issue writes there.
- Validation completed with `python3 -m compileall app/beyo_manager/domain/task_steps/aggregate_metrics.py app/beyo_manager/services/commands/task_steps/transition_step_state.py app/beyo_manager/services/tasks/analytics/process_step_transition.py`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `David Loorenz`
