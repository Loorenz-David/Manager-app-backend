# PLAN_push_notifications_20260519

## Metadata

- Plan ID: `PLAN_push_notifications_20260519`
- Status: `archived`
- Owner agent: `Claude Sonnet 4.6`
- Created at (UTC): `2026-05-19T16:00:00Z`
- Last updated at (UTC): `2026-05-19T16:12:52Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_push_notifications_20260519.md`

## Goal and intent

- **Goal:** Wire `create_instant_task(TaskType.CREATE_NOTIFICATIONS, ...)` into 9 command files so that task state changes, task step state changes, step assignments, and upholstery requirement state changes trigger targeted VAPID push notifications.
- **Business/user intent:** Workers and managers need immediate signals on high-value events even when the app is backgrounded. The four notification types are: task cancelled/resolved/failed (managers + task creator + task pin holders), step state changed (step pin holders), step assigned (assigned worker), upholstery requirement state changed (managers + upholstery pin holders).
- **Non-goals:** Changes to `handle_create_notifications`, `handle_send_push_notification`, `send_web_push`, worker infrastructure, or any frontend code.

## Scope

- **In scope:**
  - Add shared audience-resolution helpers in two new files:
    - `services/commands/tasks/_notification_helpers.py` — `_resolve_task_audience()`
    - `services/commands/items/_notification_helpers.py` — `_resolve_upholstery_audience()`
  - Modify 9 command files: `cancel_task`, `resolve_task`, `fail_task`, `transition_step_state`, `assign_worker_to_step`, `mark_requirements_completed`, `mark_requirements_in_use`, `mark_requirements_ordered`, `resolve_requirements_after_stock`
  - All `create_instant_task` calls placed **inside** the `async with maybe_begin` block (atomic with domain write)

- **Out of scope:** Handler code, worker configuration, push subscription management, migration, `event_bus` dispatch (already in place)

- **Assumptions:**
  - `expire_on_commit=False` is set on the session factory; ORM attributes accessed after the `maybe_begin` block are safe.
  - `NotificationPayload.exclude_viewing` is never passed as `None` — always `[]` when not used (see cross-cutting rule below).
  - The `CREATE_NOTIFICATIONS` task type is already mapped in `task_router.py` → `queue:notifications` — no router change needed.

## Clarifications required

None. All design decisions are resolved in the intention plan.

## Acceptance criteria

1. `cancel_task`, `resolve_task`, `fail_task` each create a `CREATE_NOTIFICATIONS` execution task in the same transaction as the domain write; the notification targets managers + task creator + task pin holders, excluding the actor.
2. `transition_step_state` creates a `CREATE_NOTIFICATIONS` task targeting step pin holders on every state transition, excluding the actor; enqueue is skipped when there are no pin holders.
3. `assign_worker_to_step` creates a `CREATE_NOTIFICATIONS` task targeting the assigned worker; skipped entirely if actor is self-assigning.
4. `mark_requirements_completed`, `mark_requirements_in_use` create a `CREATE_NOTIFICATIONS` task targeting managers + `item_upholstery` pin holders, excluding the actor.
5. `mark_requirements_ordered`, `resolve_requirements_after_stock` create a `CREATE_NOTIFICATIONS` task targeting managers + pin holders across all resolved item_upholstery IDs, excluding the actor; skipped when `resolved_ids` is empty.
6. All `create_instant_task` calls use `asdict(NotificationPayload(...))` — never a raw dict literal.
7. No `exclude_viewing=None` is ever passed to `NotificationPayload` — always `[]` when suppression is not applied.

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin` transaction semantics, `create_instant_task` placement rule (inside the block)
- `backend/architecture/16_background_jobs.md`: `create_instant_task` signature, `NotificationPayload` usage with `asdict()`, `TaskType.CREATE_NOTIFICATIONS` routing

### Local extensions loaded

- `06_commands_local.md`: `maybe_begin` owner/subordinate mode, flush-only inside block, event emission rule (after commit)

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read `06_commands.md` or `16_background_jobs.md` instead
- **What exists** → reading is legitimate

Permitted reads (relational — understanding what exists):
- Reading the 9 command files listed in scope to identify insertion points
- Reading `domain/execution/payloads/notification.py` for exact `NotificationPayload` field names
- Reading model files (`Role`, `WorkspaceMembership`, `WorkspaceRole`, `NotificationPin`) for exact field names

Prohibited reads:
- Reading any other command file to understand the `maybe_begin` / `create_instant_task` pattern (covered by contracts)

### Skill selection

- Primary skill: `backend/architecture/06_commands.md` (command mutation pattern)
- Trigger: `16_background_jobs.md` — instant task creation from command

## Cross-cutting rules (apply to every step)

**Rule 1 — Import block additions (add to existing imports, do not replace):**

For all 9 files add:
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

For files that query managers + pins (steps 1–3, 6–9) also add:
```python
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
```

For files that query only pins (step 4) add only:
```python
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
```

**Rule 2 — `create_instant_task` placement:**

Always inside `async with maybe_begin(ctx.session):`, after all domain mutations and any existing `create_instant_task` calls (e.g. `PROCESS_STEP_TRANSITION`), before the block closes. Never after the block.

**Rule 3 — `exclude_viewing` must never be `None`:**

`NotificationPayload.exclude_viewing` defaults to `None`, which breaks the handler's `for ctx in exclude_viewing` loop when serialised via `asdict()`. Always pass explicitly:
- `exclude_viewing=[{"entity_type": "...", "entity_client_id": "..."}]` when suppressing
- `exclude_viewing=[]` when suppression is not applied

**Rule 4 — Skip enqueue when audience is empty:**

Always guard with `if target_user_ids:` before calling `create_instant_task`. An empty `user_ids` list passed to `handle_create_notifications` produces no side effects, but the `ExecutionTask` row is still created and processed — wasted work.

**Rule 5 — Always use `asdict()`, never a raw dict:**

```python
await create_instant_task(
    session=ctx.session,
    task_type=TaskType.CREATE_NOTIFICATIONS,
    payload=asdict(NotificationPayload(...)),
)
```

## Implementation plan

---

### Step 0 — Create `services/commands/tasks/_notification_helpers.py` (new file)

This helper is used by steps 1–3 (`cancel_task`, `resolve_task`, `fail_task`). It encapsulates the three-source audience query so it is not duplicated across the three command files.

**Create** `backend/app/beyo_manager/services/commands/tasks/_notification_helpers.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def _resolve_task_audience(
    session: AsyncSession,
    workspace_id: str,
    task_client_id: str,
    task_created_by_id: str | None,
    actor_id: str,
) -> list[str]:
    """Return user_ids to notify on task state change.

    Sources (unioned, deduped, actor excluded):
    1. Active manager-role workspace members
    2. task.created_by_id (if set)
    3. NotificationPin holders for entity_type='task', entity_client_id=task_client_id
    """
    managers_result = await session.execute(
        select(WorkspaceMembership.user_id)
        .join(WorkspaceRole, WorkspaceMembership.workspace_role_id == WorkspaceRole.client_id)
        .join(Role, WorkspaceRole.role_id == Role.client_id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
            Role.name == RoleNameEnum.MANAGER,
        )
        .distinct()
    )
    pins_result = await session.execute(
        select(NotificationPin.user_id).where(
            NotificationPin.entity_type == "task",
            NotificationPin.entity_client_id == task_client_id,
        )
    )
    candidate_ids: set[str] = set(managers_result.scalars().all())
    candidate_ids |= set(pins_result.scalars().all())
    if task_created_by_id:
        candidate_ids.add(task_created_by_id)
    candidate_ids.discard(actor_id)
    return list(candidate_ids)
```

---

### Step 1 — `cancel_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/cancel_task.py`

**Add imports** (cross-cutting rule 1 + helper):
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.tasks._notification_helpers import _resolve_task_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add after the `_create_history_record_in_session` call:
```python
        target_user_ids = await _resolve_task_audience(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            task_client_id=task.client_id,
            task_created_by_id=task.created_by_id,
            actor_id=ctx.user_id,
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_state_changed",
                    user_ids=target_user_ids,
                    title="Task cancelled",
                    body="A task has been cancelled.",
                    entity_type="task",
                    entity_client_id=task.client_id,
                    exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                )),
            )
```

No changes after the block.

---

### Step 2 — `resolve_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/resolve_task.py`

**Add imports** (same as step 1):
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.tasks._notification_helpers import _resolve_task_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add after `_create_history_record_in_session`:
```python
        target_user_ids = await _resolve_task_audience(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            task_client_id=task.client_id,
            task_created_by_id=task.created_by_id,
            actor_id=ctx.user_id,
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_state_changed",
                    user_ids=target_user_ids,
                    title="Task resolved",
                    body="A task has been resolved.",
                    entity_type="task",
                    entity_client_id=task.client_id,
                    exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                )),
            )
```

---

### Step 3 — `fail_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/fail_task.py`

**Add imports** (same as steps 1–2):
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.tasks._notification_helpers import _resolve_task_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add after `_create_history_record_in_session`:
```python
        target_user_ids = await _resolve_task_audience(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            task_client_id=task.client_id,
            task_created_by_id=task.created_by_id,
            actor_id=ctx.user_id,
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_state_changed",
                    user_ids=target_user_ids,
                    title="Task failed",
                    body="A task has been failed.",
                    entity_type="task",
                    entity_client_id=task.client_id,
                    exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                )),
            )
```

---

### Step 4 — `transition_step_state.py`

**File:** `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`

**Add imports** (cross-cutting rule 1, pin-only — no manager query needed):
```python
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
```
Note: `asdict`, `TaskType`, `NotificationPayload`, and `create_instant_task` are **already imported** in this file (for `PROCESS_STEP_TRANSITION`). Verify before adding to avoid duplicates.

**Inside `async with maybe_begin(ctx.session):`**, add **after** the existing `PROCESS_STEP_TRANSITION` `create_instant_task` call (the analytics task at step 9 in the existing block), before the block closes:

```python
        # Step state change — notify pin holders
        step_pins_result = await ctx.session.execute(
            select(NotificationPin.user_id).where(
                NotificationPin.entity_type == "task_step",
                NotificationPin.entity_client_id == step.client_id,
            )
        )
        step_pin_user_ids = [
            uid for uid in step_pins_result.scalars().all()
            if uid != ctx.user_id
        ]
        if step_pin_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_step_state_changed",
                    user_ids=step_pin_user_ids,
                    title="Step state changed",
                    body="A step you are following has changed state.",
                    entity_type="task_step",
                    entity_client_id=step.client_id,
                    exclude_viewing=[{"entity_type": "task_step", "entity_client_id": step.client_id}],
                )),
            )
```

No changes after the block. The existing `event_bus.dispatch` and `return` remain unchanged.

---

### Step 5 — `assign_worker_to_step.py`

**File:** `backend/app/beyo_manager/services/commands/task_steps/assign_worker_to_step.py`

**Add imports** (cross-cutting rule 1 — no model imports needed, `worker_id` is already in scope):
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add **after** `_assign_worker_to_step_in_session` returns (after the `new_assignment = await _assign_worker_to_step_in_session(...)` call), before the block closes:

```python
        # Notify assigned worker — skip if actor is assigning themselves
        if request.worker_id != ctx.user_id:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_step_assigned",
                    user_ids=[request.worker_id],
                    title="Step assigned to you",
                    body="You have been assigned to a step on a task.",
                    entity_type="task_step",
                    entity_client_id=step.client_id,
                    exclude_viewing=[{"entity_type": "task_step", "entity_client_id": step.client_id}],
                )),
            )
```

No changes after the block. The existing `event_bus.dispatch` and `return` remain unchanged.

---

### Step 6 — Create `services/commands/items/_notification_helpers.py` (new file)

This helper is used by steps 7–10 (all four upholstery requirement commands). It resolves the union of manager-role members and `item_upholstery` pin holders.

**Create** `backend/app/beyo_manager/services/commands/items/_notification_helpers.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership


async def _resolve_upholstery_audience(
    session: AsyncSession,
    workspace_id: str,
    item_upholstery_ids: list[str],
    actor_id: str,
) -> list[str]:
    """Return user_ids to notify on upholstery requirement state change.

    Sources (unioned, deduped, actor excluded):
    1. Active manager-role workspace members
    2. NotificationPin holders for entity_type='item_upholstery'
       where entity_client_id IN item_upholstery_ids
    """
    managers_result = await session.execute(
        select(WorkspaceMembership.user_id)
        .join(WorkspaceRole, WorkspaceMembership.workspace_role_id == WorkspaceRole.client_id)
        .join(Role, WorkspaceRole.role_id == Role.client_id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.is_active.is_(True),
            Role.name == RoleNameEnum.MANAGER,
        )
        .distinct()
    )
    pins_result = await session.execute(
        select(NotificationPin.user_id).where(
            NotificationPin.entity_type == "item_upholstery",
            NotificationPin.entity_client_id.in_(item_upholstery_ids),
        ).distinct()
    )
    candidate_ids: set[str] = set(managers_result.scalars().all())
    candidate_ids |= set(pins_result.scalars().all())
    candidate_ids.discard(actor_id)
    return list(candidate_ids)
```

---

### Step 7 — `mark_requirements_completed.py`

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py`

**Add imports:**
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add **after** all requirement mutations (`req.state = ...`, `req.completed_at = ...`, `req.updated_by_id = ...` loop), before the block closes:

```python
        target_user_ids = await _resolve_upholstery_audience(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_upholstery_ids=[request.item_upholstery_id],
            actor_id=ctx.user_id,
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="upholstery_requirement_completed",
                    user_ids=target_user_ids,
                    title="Requirements completed",
                    body="Upholstery requirements have been marked as completed.",
                    entity_type="item_upholstery",
                    entity_client_id=request.item_upholstery_id,
                    exclude_viewing=[],
                )),
            )
```

No changes after the block.

---

### Step 8 — `mark_requirements_in_use.py`

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py`

**Add imports:**
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add **after** the requirement mutation loop, before the block closes:

```python
        target_user_ids = await _resolve_upholstery_audience(
            session=ctx.session,
            workspace_id=ctx.workspace_id,
            item_upholstery_ids=[request.item_upholstery_id],
            actor_id=ctx.user_id,
        )
        if target_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="upholstery_requirement_in_use",
                    user_ids=target_user_ids,
                    title="Requirements in use",
                    body="Upholstery requirements are now in use.",
                    entity_type="item_upholstery",
                    entity_client_id=request.item_upholstery_id,
                    exclude_viewing=[],
                )),
            )
```

---

### Step 9 — `mark_requirements_ordered.py`

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py`

**Add imports:**
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add **after** the `for req in ordered_candidates: if req.item_upholstery_id in modified_ids: req.updated_by_id = ctx.user_id` loop, before the block closes:

`result_dict["resolved"]` is already computed at this point (it is the return of `run_skip_and_continue_allocation` which runs before the `modified_ids` loop). Pin holders are queried across all resolved IDs in one `IN` clause.

```python
        resolved_ids_for_notif = result_dict["resolved"]
        if resolved_ids_for_notif:
            target_user_ids = await _resolve_upholstery_audience(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_upholstery_ids=resolved_ids_for_notif,
                actor_id=ctx.user_id,
            )
            if target_user_ids:
                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(NotificationPayload(
                        notification_type="upholstery_requirement_ordered",
                        user_ids=target_user_ids,
                        title="Requirements ordered",
                        body="Upholstery requirements have been ordered.",
                        entity_type=None,
                        entity_client_id=None,
                        exclude_viewing=[],
                    )),
                )
```

No changes after the block. The existing `resolved_ids = result_dict["resolved"]` assignment and `event_bus.dispatch` remain unchanged.

---

### Step 10 — `resolve_requirements_after_stock.py`

**File:** `backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py`

**Add imports:**
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.services.commands.items._notification_helpers import _resolve_upholstery_audience
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with maybe_begin(ctx.session):`**, add **after** the `for req in ordered_candidates: if req.item_upholstery_id in modified_ids: req.updated_by_id = ctx.user_id` loop, before the block closes.

Note: the early-return path `if not candidates: return {"resolved": [], "unresolved": []}` exits the function before the `async with` block so `result_dict` is never defined — no notification needed there. The code below only runs when `candidates` is non-empty and `result_dict` is in scope.

```python
        resolved_ids_for_notif = result_dict["resolved"]
        if resolved_ids_for_notif:
            target_user_ids = await _resolve_upholstery_audience(
                session=ctx.session,
                workspace_id=ctx.workspace_id,
                item_upholstery_ids=resolved_ids_for_notif,
                actor_id=ctx.user_id,
            )
            if target_user_ids:
                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(NotificationPayload(
                        notification_type="upholstery_requirement_resolved",
                        user_ids=target_user_ids,
                        title="Requirements resolved",
                        body="Upholstery requirements have been resolved from stock.",
                        entity_type=None,
                        entity_client_id=None,
                        exclude_viewing=[],
                    )),
                )
```

No changes after the block. The existing `resolved_ids = result_dict["resolved"]` and `event_bus.dispatch` remain unchanged.

---

## Risks and mitigations

- **Risk:** `exclude_viewing=None` (default) breaks `handle_create_notifications` loop.
  **Mitigation:** Cross-cutting rule 3 mandates always passing `[]` explicitly. Enforcement via code review.

- **Risk:** `_resolve_task_audience` and `_resolve_upholstery_audience` add 2 DB queries to request-path commands.
  **Mitigation:** Both are simple indexed selects (workspace_id + join on role, and entity_type + entity_client_id). No full scans. Audience is small (few managers, few pins per entity). Impact negligible.

- **Risk:** `result_dict` referenced before assignment in bulk commands if Python scope is misread.
  **Mitigation:** `result_dict` is assigned by `run_skip_and_continue_allocation(...)` which is called unconditionally inside `maybe_begin` (after the early-return guard `if not candidates`). Python function scope — not block scope — means `result_dict` is accessible both inside and after the `async with` block. No issue.

- **Risk:** `transition_step_state` already imports `create_instant_task`, `TaskType`, `asdict` — duplicating imports would cause a linter error.
  **Mitigation:** Step 4 explicitly notes to check for existing imports before adding. Only `NotificationPin` and `NotificationPayload` are new.

- **Risk:** `item_upholstery_ids` passed as `[request.item_upholstery_id]` (single-element list) triggers an `IN (?)` clause — functionally identical to `=` but slightly verbose.
  **Mitigation:** Acceptable. Keeps `_resolve_upholstery_audience` signature uniform across single and bulk callers.

## Validation plan

- `cancel_task` manual smoke test: cancel a task → check `execution_tasks` table for a `CREATE_NOTIFICATIONS` row → verify `Notification` rows created for manager users and task creator → verify VAPID push delivered to subscribed device.
- `transition_step_state` manual smoke test: transition a step → verify no notification created when no pins exist → add a pin for the step → transition again → verify `Notification` row created for pin holder only.
- `assign_worker_to_step` self-assign smoke test: assign actor to their own step → verify no `CREATE_NOTIFICATIONS` task created.
- `mark_requirements_ordered` smoke test: order requirements → verify one `CREATE_NOTIFICATIONS` task with `notification_type="upholstery_requirement_ordered"` and `entity_type=null` → verify `Notification` rows for managers only when no pins exist.

## Review log

*(empty)*

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David Loorenz`
