# PLAN_process_step_transition_corrections_20260621

## Metadata

- Plan ID: `PLAN_process_step_transition_corrections_20260621`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-21T00:00:00Z`
- Last updated at (UTC): `2026-06-21T15:34:43Z`
- Related issue/ticket: —
- Intention plan: —
- Parent plan: `PLAN_task_step_aggregate_metrics_20260621` (post-implementation review)
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_process_step_transition_corrections_20260621.md`

## Goal and intent

- **Goal:** Correct two defects found during the post-implementation review of `PLAN_task_step_aggregate_metrics_20260621`:
  1. `TaskStep.updated_at` is never set by the analytics worker — the timestamp stays frozen at the last command write even after aggregate-metric columns are updated.
  2. `_get_or_create_user_section_daily` sets `section_name_snapshot` to the worker's display name instead of the working section name.
- **Business/user intent:** `TaskStep.updated_at` must reflect when metrics were last written so that cache-invalidation, auditing, and "recently updated" queries give correct results. `UserSectionDailyWorkStats.section_name_snapshot` must hold the section name, not the worker name, so section-level reporting is legible.
- **Non-goals:**
  - No change to any command, route, or serializer.
  - No change to the four analytics stats table models or their migration.
  - No fix for `resolved_count = total_count` in `_apply_issues_at_completion` — `ItemIssue` has no resolution-state field; that fix requires a separate schema migration and is out of scope.
  - No null-guard additions for `total_working_seconds` / `total_working_count` / etc. — confirmed `nullable=False, default=0` in `AggregateMetricsTimeMixin`, `AggregateMetricsCountsMixin`, and `AggregateMetricsTotalsMixin`; only `total_cost_minor` (`AggregateMetricsCostMixin`) is nullable and is already guarded.

## Scope

- **In scope:**
  - `app/beyo_manager/services/tasks/analytics/process_step_transition.py` — the only file that changes. Two targeted edits:
    1. Add `task_step.updated_at = datetime.now(timezone.utc)` immediately before `session.commit()` in `handle_process_step_transition`.
    2. Fix `_get_or_create_user_section_daily`: add a `section_name: str | None` parameter, use it for `section_name_snapshot`, and update the single call site in `_increment_user_section_daily` to pass `payload.working_section_name_snapshot`.

- **Out of scope:** everything else.

## Clarifications required

_(none — both fixes are fully determined by the review findings and the existing code)_

## Acceptance criteria

1. After the analytics worker processes a step transition event for a `TaskStep` that exists, `task_steps.updated_at` in the database reflects the time of the worker run, not the time of the originating command.
2. When `_get_or_create_user_section_daily` inserts a new `UserSectionDailyWorkStats` row, the `section_name_snapshot` column holds the value of `payload.working_section_name_snapshot` (or `""` if that is `None`), not the worker's display name.
3. `user_display_name_snapshot` on newly-created `UserSectionDailyWorkStats` rows continues to hold the worker's display name — unchanged.
4. When `task_step is None` (step soft-deleted), `TaskStep.updated_at` is not touched — the `if task_step is not None:` guard applies to the `updated_at` write exactly as it does to the metric increments.
5. `python3 -m compileall app/beyo_manager/services/tasks/analytics/process_step_transition.py` passes with no errors.
6. No regression: all four stats-table helpers (`_increment_user_daily`, `_increment_user_lifetime`, `_increment_user_section_daily`, `_increment_section_daily`) continue to produce the same increments as before.

## Contracts and skills

### Contracts loaded

- `backend/architecture/16_background_jobs.md`: worker handler pattern — `task_db_session()`, single commit at end, handler is non-raising for missing rows.

### File read intent — pattern vs. relational

Permitted reads before making changes:
- `app/beyo_manager/services/tasks/analytics/process_step_transition.py` — locate exact line numbers for both edit sites (relational: what exists).

Prohibited:
- Reading any other file. Both fixes are fully specified below.

### Skill selection

- Primary skill: N/A — targeted corrections to an existing worker; no new architectural concept.

## Cross-cutting rules (apply to every step)

**Rule 1 — One file, two edits:**
Both changes are in `process_step_transition.py`. Make them in order (Step 1 then Step 2). Do not touch any other file.

**Rule 2 — No other changes:**
Do not reformat, rename, or restructure any part of the file beyond the two specified edits.

---

## Implementation plan

---

### Step 1 — Set `TaskStep.updated_at` before commit

**File:** `app/beyo_manager/services/tasks/analytics/process_step_transition.py`

**Location:** `handle_process_step_transition`, immediately before the final `await session.commit()` line.

`datetime` and `timezone` are already imported at the top of the file — no new import needed.

**Add** the following block immediately before `await session.commit()`:

```python
        if task_step is not None:
            task_step.updated_at = datetime.now(timezone.utc)
        await session.commit()
```

The existing `await session.commit()` line is replaced by this two-line block (the guard + the commit). The `task_step` variable is in scope for the entire `async with task_db_session() as session:` block.

**Why this placement:** The commit persists all mutations in the session atomically. Setting `updated_at` here — once, right before the commit — is equivalent to what the stats-table helpers do individually but is cleaner for a single row mutation.

**No other lines change.**

---

### Step 2 — Fix `section_name_snapshot` in `_get_or_create_user_section_daily`

**File:** `app/beyo_manager/services/tasks/analytics/process_step_transition.py`

**Two sub-edits in this step:**

#### Sub-edit A — update helper signature and body

Current signature:
```python
async def _get_or_create_user_section_daily(
    session: AsyncSession, workspace_id: str, user_id: str, section_id: str, work_date: date, display_name: str
) -> UserSectionDailyWorkStats:
```

Replace with:
```python
async def _get_or_create_user_section_daily(
    session: AsyncSession, workspace_id: str, user_id: str, section_id: str, work_date: date,
    display_name: str, section_name: str | None = None,
) -> UserSectionDailyWorkStats:
```

Inside the helper body, find the `UserSectionDailyWorkStats(...)` constructor call. It currently sets:
```python
            section_name_snapshot=display_name,
            user_display_name_snapshot=display_name,
```

Replace with:
```python
            section_name_snapshot=section_name or "",
            user_display_name_snapshot=display_name,
```

No other lines in the helper change.

#### Sub-edit B — update the call site in `_increment_user_section_daily`

Current call inside `_increment_user_section_daily`:
```python
    row = await _get_or_create_user_section_daily(
        session, payload.workspace_id, payload.credited_user_id, payload.working_section_id,
        work_date, worker_display_name
    )
```

Replace with:
```python
    row = await _get_or_create_user_section_daily(
        session, payload.workspace_id, payload.credited_user_id, payload.working_section_id,
        work_date, worker_display_name, payload.working_section_name_snapshot,
    )
```

`payload.working_section_name_snapshot` is `str | None` on `StepTransitionPayload` — the `section_name or ""` guard in the helper handles the `None` case.

No other lines change.

---

## Risks and mitigations

- **Risk:** `task_step.updated_at` is `Mapped[datetime | None]` (nullable) — assigning a `datetime` value is unconditionally valid.
  **Mitigation:** N/A — assignment to a nullable column always succeeds.

- **Risk:** `_get_or_create_user_section_daily` has callers other than `_increment_user_section_daily`.
  **Mitigation:** The new `section_name` parameter has a default of `None` so all existing call sites remain valid without modification. Only the one call in `_increment_user_section_daily` is updated to pass the value.

- **Risk:** `payload.working_section_name_snapshot` could be `None` if the section was soft-deleted after the transition was recorded.
  **Mitigation:** The `section_name or ""` guard in the helper produces an empty string in that case, matching the pre-existing fallback in `_get_or_create_section_daily` (`section_name or ""`).

## Validation plan

- `python3 -m compileall app/beyo_manager/services/tasks/analytics/process_step_transition.py` — no errors.
- Manual: Trigger a step transition. After the analytics worker processes the event, verify `task_steps.updated_at` is newer than the originating command's `updated_at` on the same row.
- Manual: Inspect a newly-created `user_section_daily_work_stats` row — `section_name_snapshot` should match the working section name, not the worker's username.

## Review log

- Corrected `TaskStep.updated_at` persistence in the analytics worker.
- Corrected `UserSectionDailyWorkStats.section_name_snapshot` initialization to use the working section name snapshot.
- Validation completed with `python3 -m compileall app/beyo_manager/services/tasks/analytics/process_step_transition.py`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `David Loorenz`
