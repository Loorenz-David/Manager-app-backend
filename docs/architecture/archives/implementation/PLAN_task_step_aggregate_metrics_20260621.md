# PLAN_task_step_aggregate_metrics_20260621

## Metadata

- Plan ID: `PLAN_task_step_aggregate_metrics_20260621`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-21T00:00:00Z`
- Last updated at (UTC): `2026-06-21T15:17:00Z`
- Related issue/ticket: `—`
- Intention plan: `—`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_task_step_aggregate_metrics_20260621.md`

## Goal and intent

- Goal: Extend the existing analytics worker (`WORKER-1 / handle_process_step_transition`) to also write the time, count, totals, and cost increments directly onto the `TaskStep` row, so that its inherited `AggregateMetricsTimeMixin`, `AggregateMetricsCountsMixin`, `AggregateMetricsTotalsMixin`, and `AggregateMetricsCostMixin` columns are populated.
- Business/user intent: `TaskStep` already carries `total_working_seconds`, `total_pause_seconds`, `total_ended_shift_seconds`, `total_working_count`, `total_pause_count`, `total_ended_shift_count`, `total_issues_count`, `total_issues_resolved_count`, and `total_cost_minor` columns — but they are never written. Populating them makes per-step metrics available directly on the step row without aggregating across the four analytics tables, enabling efficient step-level reporting and future UI display.
- Non-goals: No new worker, no new task type, no new command, no new route. No change to the four analytics stats tables. No change to `transition_step_state.py` or any other command. No new migration (columns already exist).

## Scope

- In scope:
  - `app/beyo_manager/services/tasks/analytics/process_step_transition.py` — the only file that changes.
    - Add `TaskStep` import.
    - Add `_fetch_task_step` private helper.
    - Fetch `TaskStep` in `handle_process_step_transition` immediately after `closing_record` is fetched.
    - Pass `step` into `_apply_working_close`, `_apply_paused_close`, `_apply_ended_shift_close`, and `_apply_issues_at_completion`.
    - Increment the correct mixin columns in each handler (same exclusion rule applies: skip if `recorded_time_marked_wrong`).
- Out of scope:
  - Any change to `transition_step_state.py` or any other command.
  - Any change to the four analytics stats tables or their handler logic.
  - Any new Alembic migration (mixin columns already exist on `task_steps`).
  - Any new API route or serializer.
  - `AggregateMetricsCostMixin` on the task row itself — `total_cost_minor` on `TaskStep` follows the same computation already done for the stats tables; include it in this plan (see handler detail below).

## Clarifications required

_(none — all constraints are derivable from existing code)_

## Acceptance criteria

1. After a `WORKING → PAUSED` transition, `TaskStep.total_working_seconds` increments by the duration of the WORKING interval and `TaskStep.total_working_count` increments by 1.
2. After a `PAUSED → WORKING` transition, `TaskStep.total_pause_seconds` increments by the duration of the PAUSED interval and `TaskStep.total_pause_count` increments by 1.
3. After a `WORKING → ENDED_SHIFT` transition, `TaskStep.total_ended_shift_seconds` increments by the WORKING duration and `TaskStep.total_ended_shift_count` increments by 1. (Note: ENDED_SHIFT is the state of the record being closed, same as the existing pattern.)
4. After a step reaches `COMPLETED`, `TaskStep.total_issues_count` and `TaskStep.total_issues_resolved_count` reflect the issues linked to that step.
5. `TaskStep.total_cost_minor` accumulates the same cost computed for the analytics stats tables on each WORKING or PAUSED close.
6. If `closing_record.recorded_time_marked_wrong` is `True`, none of the time/count/cost columns on `TaskStep` are incremented (mirrors the exclusion rule already applied to the stats tables).
7. If `TaskStep` is not found (e.g. soft-deleted between transition and worker execution), the worker logs a warning and continues — it does not raise; the stats-table updates are still applied.
8. No regression: the four analytics stats tables continue to receive the same increments they received before this change.
9. `python3 -m compileall` on `process_step_transition.py` passes with no errors.

## Contracts and skills

### Contracts loaded

- `backend/architecture/16_background_jobs.md`: worker and handler patterns — handler receives `(raw: dict, task_id: str)`, uses `task_db_session()`, commits once at end.
- `backend/architecture/06_commands.md`: N/A — this is a worker handler, not a command.

### File read intent — pattern vs. relational

Permitted reads before making changes:
- `app/beyo_manager/services/tasks/analytics/process_step_transition.py` — exact function signatures and import block (relational: what exists).
- `app/beyo_manager/models/tables/tasks/task_step.py` — exact column names from the mixins (relational: field names).
- `app/beyo_manager/models/base/aggregate_metrics.py` — mixin column names (relational: field names).

Prohibited:
- Reading another handler to understand `task_db_session()` usage → existing code in this file already demonstrates it.
- Reading any analytics stats model to understand increment pattern → existing `_increment_*` helpers in this file already demonstrate it.

### Skill selection

- Primary skill: N/A — pure extension of existing analytics worker; no new architectural concept.

## Implementation plan

### Step 1 — Add `TaskStep` import

In `process_step_transition.py`, add to the existing model imports block:

```python
from beyo_manager.models.tables.tasks.task_step import TaskStep
```

---

### Step 2 — Add `_fetch_task_step` helper

Add immediately after `_fetch_user`:

```python
async def _fetch_task_step(session: AsyncSession, step_id: str, workspace_id: str) -> TaskStep | None:
    result = await session.execute(
        select(TaskStep).where(
            TaskStep.client_id == step_id,
            TaskStep.workspace_id == workspace_id,
            TaskStep.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()
```

---

### Step 3 — Fetch `TaskStep` in `handle_process_step_transition`

After the existing `closing_record` fetch (and its early-return guard), add:

```python
task_step = await _fetch_task_step(session, payload.step_id, payload.workspace_id)
if task_step is None:
    logger.warning("step_not_found | step_id=%s task_id=%s", payload.step_id, task_id)
```

`task_step` being `None` is non-fatal — the worker continues and the stats-table updates still apply. The `None` value is forwarded to the handlers, which guard against it.

---

### Step 4 — Update `_apply_working_close` signature and body

Add `task_step: TaskStep | None` parameter. After the existing stats-table increment calls, add:

```python
    if task_step is not None:
        task_step.total_working_seconds += interval_seconds
        task_step.total_working_count += 1
        if cost_minor:
            task_step.total_cost_minor = (task_step.total_cost_minor or 0) + cost_minor
```

---

### Step 5 — Update `_apply_paused_close` signature and body

Add `task_step: TaskStep | None` parameter. After the existing stats-table increment calls, add:

```python
    if task_step is not None:
        task_step.total_pause_seconds += interval_seconds
        task_step.total_pause_count += 1
        if cost_minor:
            task_step.total_cost_minor = (task_step.total_cost_minor or 0) + cost_minor
```

---

### Step 6 — Update `_apply_ended_shift_close` signature and body

Add `task_step: TaskStep | None` parameter. After the existing stats-table increment calls, add:

```python
    if task_step is not None:
        task_step.total_ended_shift_seconds += interval_seconds
        task_step.total_ended_shift_count += 1
```

(No cost increment for ENDED_SHIFT — mirrors the stats-table rule.)

---

### Step 7 — Update `_apply_issues_at_completion` signature and body

Add `task_step: TaskStep | None` parameter. After the existing stats-table increment calls, add:

```python
    if task_step is not None:
        task_step.total_issues_count += total_count
        task_step.total_issues_resolved_count += resolved_count
```

---

### Step 8 — Forward `task_step` at each call site in `handle_process_step_transition`

Update the three dispatch calls inside the `if not closing_record.recorded_time_marked_wrong:` block:

```python
if closing_state == TaskStepStateEnum.WORKING:
    await _apply_working_close(session, payload, interval_seconds, credited_user_display_name, task_step)
elif closing_state == TaskStepStateEnum.PAUSED:
    await _apply_paused_close(session, payload, interval_seconds, credited_user_display_name, task_step)
elif closing_state == TaskStepStateEnum.ENDED_SHIFT:
    await _apply_ended_shift_close(session, payload, interval_seconds, credited_user_display_name, task_step)
```

And the completion call:

```python
if new_state == TaskStepStateEnum.COMPLETED:
    await _apply_issues_at_completion(session, payload, credited_user_display_name, task_step)
```

The `session.commit()` at the end of `handle_process_step_transition` already persists everything — the `TaskStep` mutations are included because SQLAlchemy tracks them in the same session.

---

## Risks and mitigations

- Risk: Worker is idempotent by design but not deduplicated — duplicate event delivery causes double-increment on `TaskStep` columns, same as on the stats tables.
  Mitigation: Accepted as-is, matching the existing design decision from Plan 6. Duplicates are rare (outbox + `max_try=3`). This plan does not change idempotency guarantees.

- Risk: `TaskStep` fetch adds one extra SELECT per analytics event.
  Mitigation: The row is primary-key indexed. The cost is negligible compared to the four stats-table upserts already executed per event.

- Risk: `task_step.is_deleted.is_(False)` filter means a soft-deleted step's metrics are never updated.
  Mitigation: A soft-deleted step is no longer active — it is correct to skip metrics updates. The warning log ensures visibility.

- Risk: `total_cost_minor` is `Mapped[int | None]` (nullable), requiring the `(col or 0) + value` null-merge.
  Mitigation: The pattern is already established in `_increment_user_daily` and siblings — replicate exactly.

## Validation plan

- `python3 -m compileall app/beyo_manager/services/tasks/analytics/process_step_transition.py` — no errors.
- Manual: Trigger a `PENDING → WORKING → PAUSED` step cycle. After the analytics worker processes both events, verify `task_steps.total_working_seconds` > 0, `total_working_count == 1`, `total_pause_seconds` == 0 (PAUSED record not yet closed), `total_pause_count == 0`.
- Manual: Trigger `PAUSED → WORKING`. Verify `total_pause_seconds` > 0, `total_pause_count == 1`.
- Manual: Trigger `WORKING → COMPLETED`. Verify `total_working_count == 2` (two WORKING intervals), and issue counts match linked issues.
- Manual: Mark one `StepStateRecord` as `recorded_time_marked_wrong = True`, then re-trigger processing. Verify `TaskStep` columns are not incremented for that record.
- Regression: Verify all four stats-table rows (`UserDailyWorkStats`, `UserLifetimeStats`, `UserSectionDailyWorkStats`, `WorkingSectionDailyWorkStats`) are still updated as before.

## Review log

- Implemented in `app/beyo_manager/services/tasks/analytics/process_step_transition.py`.
- Validation completed with `python3 -m compileall app/beyo_manager/services/tasks/analytics/process_step_transition.py`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
