# PLAN_task_post_handling_corrections_20260703

## Metadata

- Plan ID: `PLAN_task_post_handling_corrections_20260703`
- Status: `archived`
- Owner agent: `Claude`
- Created at (UTC): `2026-07-03T00:00:00Z`
- Last updated at (UTC): `2026-07-03T07:03:28Z`
- Related issue/ticket: `—`
- Source plan (corrects): `backend/docs/architecture/archives/implementation/PLAN_task_post_handling_system_20260701.md`

## Goal and intent

- Goal: Fix two issues found in the post-review of `PLAN_task_post_handling_system_20260701`:
  1. **Logic bug** — the PRE_ORDER evaluator uses OR between `fulfillment_method` and the schedule date check; it must use AND.
  2. **Security gap** — when `complete_task_post_handling` is called with an explicit `post_handling_id`, the query does not verify the instance belongs to the `task_id` in the route, allowing cross-task completion within the same workspace.
- Business/user intent: Ensure post-handling state only reaches FILLED when all required PRE_ORDER fields are set, and ensure completion requests are scoped to the correct task.
- Non-goals: No schema changes, no new routes, no changes to RETURN evaluator logic, no changes to any other service.

## Scope

- In scope:
  - Fix `evaluate_post_handling_state` in `_post_handling_state_evaluator.py`: PRE_ORDER FILLED requires `fulfillment_method` set **AND** at least one of `scheduled_start_at`/`scheduled_end_at` set.
  - Fix `complete_task_post_handling` in `complete_task_post_handling.py`: when finding by `post_handling_id`, also filter by `task_id` when it is available in the request.
- Out of scope:
  - RETURN evaluator logic (unchanged and correct).
  - Any other service, router, migration, or serializer.

## Clarifications required

- None. Confirmed by user: PRE_ORDER requires `fulfillment_method` AND at least one schedule date (AND logic).

## Acceptance criteria

1. `evaluate_post_handling_state` returns `PENDING` for a PRE_ORDER task in READY state when `fulfillment_method` is set but no schedule date is set.
2. `evaluate_post_handling_state` returns `PENDING` for a PRE_ORDER task in READY state when a schedule date is set but `fulfillment_method` is null.
3. `evaluate_post_handling_state` returns `FILLED` for a PRE_ORDER task in READY state when both `fulfillment_method` is set AND at least one schedule date is set.
4. `complete_task_post_handling` returns `404` when `post_handling_id` is provided but it does not belong to the `task_id` supplied in the route.
5. `py_compile` passes for both changed modules.

## Contracts and skills

### Contracts loaded

- `backend/task_system/architecture/05_errors.md`: `NotFound` usage in the complete service.
- `backend/task_system/architecture/08_domain.md`: pure domain logic must have no I/O — the evaluator fix must remain a pure function.

### File read intent

Permitted relational reads:
- Reading `_post_handling_state_evaluator.py` to apply the precise change.
- Reading `complete_task_post_handling.py` to apply the precise change.

## Implementation plan

### Step 1 — Fix PRE_ORDER evaluator: OR → AND

File: `app/beyo_manager/domain/tasks/_post_handling_state_evaluator.py`

Replace the PRE_ORDER block (currently lines 15-18):

**Before:**
```python
    if task.task_type == TaskTypeEnum.PRE_ORDER:
        filled = bool(task.fulfillment_method) or bool(
            task.scheduled_start_at is not None or task.scheduled_end_at is not None
        )
```

**After:**
```python
    if task.task_type == TaskTypeEnum.PRE_ORDER:
        has_fulfillment_method = bool(task.fulfillment_method)
        has_schedule = task.scheduled_start_at is not None or task.scheduled_end_at is not None
        filled = has_fulfillment_method and has_schedule
```

No other changes to this file.

---

### Step 2 — Fix `complete_task_post_handling`: scope `post_handling_id` lookup by `task_id`

File: `app/beyo_manager/services/commands/task_post_handling/complete_task_post_handling.py`

Replace the `post_handling_id` lookup block (currently lines 41-48):

**Before:**
```python
        if request.post_handling_id is not None:
            result = await ctx.session.execute(
                select(TaskPostHandling).where(
                    TaskPostHandling.workspace_id == ctx.workspace_id,
                    TaskPostHandling.client_id == request.post_handling_id,
                )
            )
            instance = result.scalar_one_or_none()
```

**After:**
```python
        if request.post_handling_id is not None:
            filters = [
                TaskPostHandling.workspace_id == ctx.workspace_id,
                TaskPostHandling.client_id == request.post_handling_id,
            ]
            if request.task_id:
                filters.append(TaskPostHandling.task_id == request.task_id)
            result = await ctx.session.execute(
                select(TaskPostHandling).where(*filters)
            )
            instance = result.scalar_one_or_none()
```

No other changes to this file. The existing `if instance is None: raise NotFound(...)` guard on the next line already handles the 404 response when the instance is not found under that task.

---

### Step 3 — Validate

```bash
.venv/bin/python -m py_compile app/beyo_manager/domain/tasks/_post_handling_state_evaluator.py
.venv/bin/python -m py_compile app/beyo_manager/services/commands/task_post_handling/complete_task_post_handling.py
```

Both must exit 0 with no output.

## Risks and mitigations

- Risk: The AND change makes the FILLED state harder to reach for PRE_ORDER tasks. Any existing post-handling records that were in FILLED state due to the OR condition (e.g., only `fulfillment_method` was set, no schedule date) will not be automatically re-evaluated. They remain FILLED in the DB.
  Mitigation: This is acceptable — existing records are grandfathered. The sync helper (`_sync_post_handling_state_in_session`) will re-evaluate and correct the state the next time `update_task` or `update_task_post_handling` is called for that task.

- Risk: Adding `task_id` as an optional filter (only when `request.task_id` is present) means direct invocations of `complete_task_post_handling` without a `task_id` remain unscoped. The route always injects `task_id`, so in practice all calls through the API are scoped. Direct service invocations are internal and trusted.
  Mitigation: Acceptable. If future callers need stricter enforcement, require `task_id` in the request model.

## Validation plan

- `py_compile` for both changed files: must pass.

## Review log

- `2026-07-03` Claude: Correction plan created from post-implementation review findings.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `user`
