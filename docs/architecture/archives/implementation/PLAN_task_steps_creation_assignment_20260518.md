# PLAN_task_steps_creation_assignment_20260518

## Metadata

- Plan ID: `PLAN_task_steps_creation_assignment_20260518`
- Status: `under_construction`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T00:00:00Z`
- Related issue/ticket: `task-system-plan-3`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

---

## Goal and intent

- **Goal:** Implement task step creation (CMD-9 `add_task_step`) and worker assignment to steps (CMD-11 `assign_worker_to_step`). After this plan, a manager can add working-section steps to a task and assign workers to those steps.
- **Business/user intent:** A task becomes actionable only when it has at least one step assigned to a working section. Workers can then be assigned to those steps.
- **Non-goals:** Step state transitions (CMD-12 — Plan 5), dependency management (CMD-14, CMD-15 — Plan 4), step removal (CMD-10 — Plan 4), analytics (Plan 6).

---

## Prerequisite

**Plans 1 and 2 must be completed before this plan.** CMD-9 changes task state (`pending → assigned`) and requires the `Task` model and commands to exist. The tasks router must exist for route additions.

---

## Scope

- **In scope:**
  - Request models in `services/commands/task_steps/requests/__init__.py`
  - New command: `services/commands/task_steps/add_task_step.py` — CMD-9
  - New command: `services/commands/task_steps/assign_worker_to_step.py` — CMD-11
  - Route additions to existing `routers/api_v1/tasks.py`
- **Out of scope:** `_recalculate_readiness` (Plan 4), `StepStateRecord` state machine (Plan 5), analytics worker (Plan 6). No new migrations.
- **Assumptions:** `task_steps`, `step_state_records`, `task_step_assignment_records`, `working_sections`, `users` tables all exist. `TaskStepStateEnum` and `TaskStepReadinessStatusEnum` exist in `domain/task_steps/enums.py`.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. `POST /api/v1/tasks/{task_id}/steps` creates a `TaskStep` with `state = pending`, `readiness_status = ready` (no dependencies yet), and an initial `StepStateRecord` with `state = pending`, `entered_at = now()`, `exited_at = null`. Returns `{step_id}`.
2. The step's `working_section_name_snapshot` is populated from `WorkingSection.name` at creation time.
3. Adding the first step to a `pending` task transitions the task to `assigned` atomically in the same transaction.
4. Adding additional steps to an `assigned`, `working`, or other non-terminal task does NOT change the task state.
5. `POST /api/v1/tasks/{task_id}/steps/{step_id}/assign-worker` closes the current active `task_step_assignment_records` row (`removed_at = now()`), inserts a new row, and sets `step.assigned_worker_id` + `step.assigned_worker_display_name_snapshot` on the `TaskStep`. Returns `{assignment_id}`.
6. If no active assignment exists for the step, CMD-11 simply inserts a new row (no close step needed).
7. `latest_state_record_id` on the new `TaskStep` is set to the initial `StepStateRecord.client_id` after both are flushed. This update is transactionally coupled with the insert (same `maybe_begin` block).
8. Adding a step to a terminal task (RESOLVED, FAILED, CANCELLED) raises `ConflictError`.
9. Adding a step with a `working_section_id` that does not exist or is deleted raises `NotFound`.
10. `sequence_order` is optional — if not provided, it defaults to `None`. It can be set to an integer by the caller.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: structure
- `backend/architecture/04_context.md`: `ServiceContext`
- `backend/architecture/05_errors.md`: `ValidationError`, `NotFound`, `ConflictError`
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin`, circular FK pointer update rule (transactionally coupled), subordinate-command event rule
- `backend/architecture/09_routers.md`: router handler wiring
- `backend/architecture/21_naming_conventions.md`: naming

### Permitted relational reads

| File | What to extract |
|---|---|
| `models/tables/tasks/task_step.py` | All column names, `latest_state_record_id` circular FK pattern |
| `models/tables/tasks/step_state_record.py` | All columns: `step_id`, `state`, `entered_at`, `exited_at`, `created_by_id`, `workspace_id` |
| `models/tables/tasks/task_step_assignment_record.py` | All columns: `step_id`, `assigned_worker_id`, `assigned_at`, `assigned_by_id`, `removed_at`, `removed_by_id`, partial unique index name |
| `models/tables/tasks/task.py` | `state` column, `TaskStateEnum` import path |
| `models/tables/tasks/README.md` | Circular FK rules, `latest_state_record_id` transactional coupling, assignment record pattern |
| `domain/task_steps/enums.py` | `TaskStepStateEnum.PENDING`, `TaskStepReadinessStatusEnum.READY` |
| `domain/tasks/enums.py` | `TaskStateEnum.PENDING`, `TaskStateEnum.ASSIGNED` |
| `models/tables/working_sections/working_section.py` (if exists, for name) | Column name for `name` |

---

## Implementation plan

### Step 1 — Request models: `services/commands/task_steps/requests/__init__.py`

```
AddTaskStepRequest:
  task_id: str
  working_section_id: str
  sequence_order: int | None = None

AssignWorkerToStepRequest:
  step_id: str
  task_id: str   (used to verify scope)
  worker_id: str
```

Parse functions: `parse_add_task_step_request`, `parse_assign_worker_to_step_request`. Standard pattern.

### Step 2 — CMD-9: `services/commands/task_steps/add_task_step.py`

**Full flow:**

```python
async def add_task_step(ctx: ServiceContext) -> dict:
    request = parse_add_task_step_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        # 1. Fetch task
        task = ...  # select Task by client_id + workspace_id + is_deleted=False → 404 if not found

        # 2. Guard: terminal task cannot receive new steps
        if task.state in _TERMINAL_STATES:
            raise ConflictError("Cannot add a step to a terminal task.")

        # 3. Fetch working section
        section = ...  # select WorkingSection by client_id + workspace_id → 404 if not found
        # Guard: section must not be deleted (check is_deleted or deleted_at on section model)

        # 4. Create TaskStep
        now = datetime.now(timezone.utc)
        step = TaskStep(
            workspace_id=ctx.workspace_id,
            task_id=request.task_id,
            working_section_id=request.working_section_id,
            working_section_name_snapshot=section.name,
            state=TaskStepStateEnum.PENDING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            sequence_order=request.sequence_order,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(step)
        await ctx.session.flush()  # assign step.client_id

        # 5. Create initial StepStateRecord (PENDING, open — exited_at=None)
        record = StepStateRecord(
            workspace_id=ctx.workspace_id,
            step_id=step.client_id,
            state=TaskStepStateEnum.PENDING,
            entered_at=now,
            exited_at=None,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(record)
        await ctx.session.flush()  # assign record.client_id

        # 6. Update circular FK: latest_state_record_id → must be in same transaction
        step.latest_state_record_id = record.client_id

        # 7. Task state side effect: PENDING → ASSIGNED on first step
        if task.state == TaskStateEnum.PENDING:
            task.state = TaskStateEnum.ASSIGNED
            task.updated_at = now
            task.updated_by_id = ctx.user_id

    return {"step_id": step.client_id}
```

**Critical — circular FK update (Step 6):** `TaskStep.latest_state_record_id` points to `StepStateRecord`. This is a `use_alter=True` FK. The pointer update must happen in the SAME transaction as the record insert — do not let the `async with` block close without updating the pointer. The order is: `step.flush()` → `record.flush()` → `step.latest_state_record_id = record.client_id`. SQLAlchemy will issue the UPDATE to `task_steps` as part of the commit.

**`_TERMINAL_STATES`:**
```python
_TERMINAL_STATES = frozenset({
    TaskStateEnum.RESOLVED,
    TaskStateEnum.FAILED,
    TaskStateEnum.CANCELLED,
})
```
Define at module level. Do NOT import from Plan 1's command files to avoid coupling. Each command module that needs this frozenset defines it locally.

**First-step check:** The task state transitions to `ASSIGNED` only if `task.state == PENDING`. Other states (ASSIGNED, WORKING, STALLED, READY) are valid states for receiving additional steps — do NOT transition them.

### Step 3 — CMD-11: `services/commands/task_steps/assign_worker_to_step.py`

**Full flow:**

```python
async def assign_worker_to_step(ctx: ServiceContext) -> dict:
    request = parse_assign_worker_to_step_request(ctx.incoming_data)
    async with maybe_begin(ctx.session):
        # 1. Fetch step (scope by task_id for security)
        step = ...  # select TaskStep by client_id + task_id + workspace_id + is_deleted=False → 404

        # 2. Fetch worker (user) to get display_name
        worker = ...  # select User by client_id + workspace_id → 404 if not found

        now = datetime.now(timezone.utc)

        # 3. Close current active assignment (if any)
        active_assignment_result = await ctx.session.execute(
            select(TaskStepAssignmentRecord).where(
                TaskStepAssignmentRecord.workspace_id == ctx.workspace_id,
                TaskStepAssignmentRecord.step_id == step.client_id,
                TaskStepAssignmentRecord.removed_at.is_(None),
            )
        )
        active_assignment = active_assignment_result.scalar_one_or_none()
        if active_assignment is not None:
            active_assignment.removed_at = now
            active_assignment.removed_by_id = ctx.user_id

        # 4. Insert new assignment record
        new_assignment = TaskStepAssignmentRecord(
            workspace_id=ctx.workspace_id,
            step_id=step.client_id,
            assigned_worker_id=request.worker_id,
            assigned_at=now,
            assigned_by_id=ctx.user_id,
        )
        ctx.session.add(new_assignment)
        await ctx.session.flush()

        # 5. Update step snapshot fields
        step.assigned_worker_id = request.worker_id
        step.assigned_worker_display_name_snapshot = worker.display_name
        step.updated_at = now
        step.updated_by_id = ctx.user_id

    return {"assignment_id": new_assignment.client_id}
```

**Worker display_name:** Check the `User` model for the correct column name. It is likely `display_name` — verify by reading `models/tables/users/user.py`.

**No task state change:** Worker assignment does not affect task state.

### Step 4 — Routes in `routers/api_v1/tasks.py`

Add these imports:
```python
from beyo_manager.services.commands.task_steps.add_task_step import add_task_step
from beyo_manager.services.commands.task_steps.assign_worker_to_step import assign_worker_to_step
```

Body models:
```python
class _AddTaskStepBody(BaseModel):
    working_section_id: str
    sequence_order: int | None = None

class _AssignWorkerBody(BaseModel):
    worker_id: str
```

Routes:
```
POST "/{task_id}/steps"                            → route_add_task_step       (ADMIN, MANAGER)
POST "/{task_id}/steps/{step_id}/assign-worker"   → route_assign_worker_to_step (ADMIN, MANAGER)
```

Handler for add step:
```python
ctx = ServiceContext(
    incoming_data={"task_id": task_id, **body.model_dump()},
    ...
)
```

Handler for assign worker:
```python
ctx = ServiceContext(
    incoming_data={"step_id": step_id, "task_id": task_id, **body.model_dump()},
    ...
)
```

---

## Risks and mitigations

- **Risk:** Circular FK `latest_state_record_id` — if `step.flush()` is not called before `record` is created, `step.client_id` is `None` and `StepStateRecord.step_id` will be null.
  **Mitigation:** Steps 4 and 5 of the flow explicitly call `flush()` in order: step first, then record.

- **Risk:** The `StepStateRecord` type `task_step_state_enum` is created by `task_step.py` (`create_type=True`) and reused by `step_state_record.py` (`create_type=False`). The models `__init__.py` must import `task_step.py` before `step_state_record.py`.
  **Mitigation:** Do not change model import order. Read `models/tables/tasks/README.md` — this ordering rule is documented there.

- **Risk:** CMD-11 with no active assignment — `active_assignment` is `None`, which is fine. The `if active_assignment is not None` guard handles this case. Do not raise on no existing assignment.

---

## Validation plan

Save to `backend/tests/tasks/test_task_steps_creation.sh`.

```bash
# 1. Add step to pending task → step created, task.state = assigned
# 2. Add second step to same task → step created, task.state still assigned
# 3. latest_state_record_id on step is not null → verify via DB query or GET step endpoint
# 4. Initial StepStateRecord state = pending, exited_at = null
# 5. Assign worker to step → assignment record inserted, step.assigned_worker_id updated
# 6. Reassign worker → old assignment has removed_at set, new assignment created
# 7. Add step to terminal (resolved) task → 409 ConflictError
# 8. Add step with invalid working_section_id → 404 NotFound
```

---

## Review log

_Empty — awaiting implementation._

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
