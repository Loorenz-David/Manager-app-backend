# INTENTION_push_notifications_20260519

## Metadata

- Intention ID: `INTENTION_push_notifications_20260519`
- Status: `active`
- Owner: `David Loorenz`
- Created at (UTC): `2026-05-19T14:00:00Z`
- Last updated at (UTC): `2026-05-19T16:12:52Z`

## Goal

Deliver targeted VAPID push notifications for four high-signal events — task state changes, task step state changes, task step assignment, and upholstery requirement state changes — using the existing `CREATE_NOTIFICATIONS` task queue and `send_web_push` infrastructure.

## Why this matters

Users do not keep the app open and active. Three moments require immediate attention even when the app is backgrounded:

1. **Task state change (cancelled, resolved, failed)**: managers and the task creator need to know when a task reaches a terminal or recovery state. Without a push, a cancelled task may sit unnoticed and cause downstream scheduling errors.
2. **Task step state change (any transition)**: users who pin a step opt in to following its progress. Without a push they must poll the task view manually to see step movement.
3. **Step assigned to a worker**: the worker has no other signal that they've been given a task step. Without a push, they may not see the assignment until their next manual app check — blocking step start.
4. **Upholstery requirement state change**: managers need visibility over material readiness across the shop floor. Individual workers who are directly affected can pin a specific upholstery requirement to opt into its state changes. A broad push to all section members would create noise for workers who have no stake in a particular requirement.

The VAPID + `PushSubscription` infrastructure, the `CREATE_NOTIFICATIONS` task type, and the `handle_create_notifications` background handler are all already implemented. This intention wires four specific command groups into that flow.

## Success criteria

1. `cancel_task`, `resolve_task`, and `fail_task` each enqueue a `CREATE_NOTIFICATIONS` task targeting the union of: active `manager`-role members, the task creator, and users who have pinned the task — all excluding the actor; those members receive a push notification.
2. `transition_step_state` enqueues a `CREATE_NOTIFICATIONS` task on every state transition targeting users who have pinned the step (`NotificationPin` where `entity_type = "task_step"`), excluding the actor; those users receive a push notification for every step state change.
3. `assign_worker_to_step` enqueues a `CREATE_NOTIFICATIONS` task inside its transaction when a worker is assigned; the assigned worker receives a push notification on their subscribed device(s) within seconds of assignment.
4. `mark_requirements_completed`, `mark_requirements_in_use`, `mark_requirements_ordered`, and `resolve_requirements_after_stock` each enqueue a `CREATE_NOTIFICATIONS` task targeting the union of: active `manager`-role members and users who have pinned the affected `item_upholstery` entity — all excluding the actor; those users receive a push notification.
5. No notification is sent to the actor who triggered the action (excluded from `user_ids`).
6. If the assigned worker or step pin holder is already viewing the step when the event fires, no push is sent (presence suppression via `exclude_viewing`).
7. Stale push subscriptions (HTTP 410 responses) are cleaned up automatically by the existing `handle_send_push_notification` handler — no new cleanup logic needed.
8. All `Notification` rows created are readable via the existing `/notifications` list endpoint with the correct `notification_type`, `entity_type`, and `entity_client_id` set.

## Scope boundary

- In scope:
  - Hook `cancel_task`, `resolve_task`, `fail_task` to enqueue `CREATE_NOTIFICATIONS` targeting managers + task creator + task pin holders
  - Hook `transition_step_state` to enqueue `CREATE_NOTIFICATIONS` targeting step pin holders on every state transition
  - Hook `assign_worker_to_step` to enqueue `CREATE_NOTIFICATIONS` targeting the assigned worker
  - Hook 4 upholstery requirement commands to enqueue `CREATE_NOTIFICATIONS` targeting managers + upholstery pin holders
  - Define audience queries for all four notification types (see delivery design below)
  - Define `notification_type` string constants for each event
  - Define notification title and body templates for each event

- Out of scope:
  - Changes to `handle_create_notifications`, `handle_send_push_notification`, or `send_web_push` — they are already correct
  - New `TaskType` values — `CREATE_NOTIFICATIONS` is the correct type for all cases
  - Frontend notification rendering or routing (separate frontend plan)
  - Step readiness notifications — deferred; not in scope for this plan
  - New push subscription management endpoints — already implemented

- Non-goals:
  - Per-device silent push or badge count sync
  - Notification grouping or digest batching
  - Read-receipt tracking beyond what the existing `read_at` field on `Notification` provides

## Delivery design

### Pattern

All notification enqueue calls follow this pattern, placed **inside** the `async with maybe_begin(ctx.session)` block, just before it exits. This is atomic with the domain write: if the transaction rolls back, the execution task is never committed.

```python
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.infra.execution.task_factory import create_instant_task

await create_instant_task(
    session=ctx.session,
    task_type=TaskType.CREATE_NOTIFICATIONS,
    payload={
        "notification_type": "<constant>",
        "user_ids":          [...],           # resolved inside the transaction
        "title":             "...",
        "body":              "...",
        "entity_type":       "...",
        "entity_client_id":  "...",
        "exclude_viewing":   [...],           # presence suppression, optional
    },
)
```

The background worker picks up the task from `queue:notifications`, creates `Notification` rows, enqueues `SEND_PUSH_NOTIFICATION` per user, and dispatches `notification:new` `UserEvent`s so connected clients update their badge counts immediately.

### Notification 1 — Task state changed (`cancel_task`, `resolve_task`, `fail_task`)

| Field | Value |
|---|---|
| `notification_type` | `"task_state_changed"` |
| `user_ids` | Union of: active `manager`-role members + `task.created_by_id` + users who pinned the task — all minus `ctx.user_id` |
| `title` | `"Task cancelled"` / `"Task resolved"` / `"Task failed"` (per command) |
| `body` | `"A task has been cancelled."` / `"A task has been resolved."` / `"A task has been failed."` |
| `entity_type` | `"task"` |
| `entity_client_id` | `task.client_id` |
| `exclude_viewing` | `[{"entity_type": "task", "entity_client_id": task.client_id}]` |

**Audience resolution (inside `maybe_begin`):**

Three sources are unioned and deduplicated; the actor is excluded from the final set.

```python
from sqlalchemy import select
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.roles.role import Role

# 1. Active manager-role members
managers_result = await ctx.session.execute(
    select(WorkspaceMembership.user_id)
    .join(WorkspaceRole, WorkspaceMembership.workspace_role_id == WorkspaceRole.client_id)
    .join(Role, WorkspaceRole.role_id == Role.client_id)
    .where(
        WorkspaceMembership.workspace_id == ctx.workspace_id,
        WorkspaceMembership.is_active.is_(True),
        Role.name == "manager",
    )
    .distinct()
)

# 2. Users who pinned this task
pins_result = await ctx.session.execute(
    select(NotificationPin.user_id).where(
        NotificationPin.entity_type == "task",
        NotificationPin.entity_client_id == task.client_id,
    )
)

# 3. Union all three sources, deduplicate, exclude actor
candidate_ids: set[str] = set(managers_result.scalars().all())
candidate_ids |= set(pins_result.scalars().all())
candidate_ids.add(task.created_by_id)          # task creator always included
candidate_ids.discard(ctx.user_id)             # exclude actor
target_user_ids = list(candidate_ids)
```

If `target_user_ids` is empty, skip enqueue entirely.

### Notification 2 — Step state changed (`transition_step_state`)

| Field | Value |
|---|---|
| `notification_type` | `"task_step_state_changed"` |
| `user_ids` | All users who have pinned the step (`NotificationPin` where `entity_type = "task_step"`), excluding `ctx.user_id` |
| `title` | `"Step state changed"` |
| `body` | `"A step you are following has changed state."` |
| `entity_type` | `"task_step"` |
| `entity_client_id` | `step.client_id` |
| `exclude_viewing` | `[{"entity_type": "task_step", "entity_client_id": step.client_id}]` |

**Audience resolution (inside `maybe_begin`):**

```python
pins_result = await ctx.session.execute(
    select(NotificationPin.user_id).where(
        NotificationPin.entity_type == "task_step",
        NotificationPin.entity_client_id == step.client_id,
    )
)
target_user_ids = [uid for uid in pins_result.scalars().all() if uid != ctx.user_id]
```

If `target_user_ids` is empty, skip enqueue entirely. This covers every state transition — no filter on which state is entered. Users self-select into notifications by pinning the step.

The `create_instant_task` call is placed inside the existing `maybe_begin` block in `transition_step_state.py`, after the analytics `PROCESS_STEP_TRANSITION` task enqueue, before the block exits.

### Notification 3 — Step assigned (`assign_worker_to_step`)

| Field | Value |
|---|---|
| `notification_type` | `"task_step_assigned"` |
| `user_ids` | `[worker_id]` — the single user being assigned; exclude if `worker_id == ctx.user_id` (self-assignment) |
| `title` | `"Step assigned to you"` |
| `body` | `"You have been assigned to a step on a task."` |
| `entity_type` | `"task_step"` |
| `entity_client_id` | `step.client_id` |
| `exclude_viewing` | `[{"entity_type": "task_step", "entity_client_id": step.client_id}]` |

Audience resolution: no DB query needed — `worker_id` is already in scope (`request.worker_id`). The guard `if worker_id != ctx.user_id` keeps the list non-empty before enqueuing.

### Notification 4 — Upholstery requirement state changes (4 commands)

| Command | `notification_type` | `title` | `body` |
|---|---|---|---|
| `mark_requirements_completed` | `"upholstery_requirement_completed"` | `"Requirements completed"` | `"Upholstery requirements have been marked as completed."` |
| `mark_requirements_in_use` | `"upholstery_requirement_in_use"` | `"Requirements in use"` | `"Upholstery requirements are now in use."` |
| `mark_requirements_ordered` | `"upholstery_requirement_ordered"` | `"Requirements ordered"` | `"Upholstery requirements have been ordered."` |
| `resolve_requirements_after_stock` | `"upholstery_requirement_resolved"` | `"Requirements resolved"` | `"Upholstery requirements have been resolved from stock."` |

**Audience resolution (inside `maybe_begin`):**

Union of active `manager`-role members and users who have pinned the affected `item_upholstery` entity, minus actor. The manager query is identical to Notification 1 (same join pattern). The pin query uses `entity_type = "item_upholstery"`.

*Single-item commands (`mark_requirements_completed`, `mark_requirements_in_use`):*

```python
managers_result = await ctx.session.execute(
    select(WorkspaceMembership.user_id)
    .join(WorkspaceRole, WorkspaceMembership.workspace_role_id == WorkspaceRole.client_id)
    .join(Role, WorkspaceRole.role_id == Role.client_id)
    .where(
        WorkspaceMembership.workspace_id == ctx.workspace_id,
        WorkspaceMembership.is_active.is_(True),
        Role.name == "manager",
    )
    .distinct()
)
pins_result = await ctx.session.execute(
    select(NotificationPin.user_id).where(
        NotificationPin.entity_type == "item_upholstery",
        NotificationPin.entity_client_id == request.item_upholstery_id,
    )
)
candidate_ids: set[str] = set(managers_result.scalars().all())
candidate_ids |= set(pins_result.scalars().all())
candidate_ids.discard(ctx.user_id)
target_user_ids = list(candidate_ids)
```

`entity_type = "item_upholstery"`, `entity_client_id = request.item_upholstery_id`.

*Bulk commands (`mark_requirements_ordered`, `resolve_requirements_after_stock`):*

Enqueue only if `resolved_ids` is non-empty. Pin holders are queried across all resolved items in a single `IN` clause:

```python
pins_result = await ctx.session.execute(
    select(NotificationPin.user_id).where(
        NotificationPin.entity_type == "item_upholstery",
        NotificationPin.entity_client_id.in_(resolved_ids),
    ).distinct()
)
candidate_ids: set[str] = set(managers_result.scalars().all())  # same manager query as above
candidate_ids |= set(pins_result.scalars().all())
candidate_ids.discard(ctx.user_id)
target_user_ids = list(candidate_ids)
```

Bulk commands send one aggregate notification; `entity_type = None`, `entity_client_id = None` (no single entity to deep-link to).

If `target_user_ids` is empty, skip enqueue entirely. `exclude_viewing` is omitted for all upholstery commands.

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_push_notifications_20260519` | `backend/docs/architecture/archives/implementation/PLAN_push_notifications_20260519.md` | `archived` | Wire `create_instant_task(CREATE_NOTIFICATIONS)` into 9 command files (3 task state, 1 step state, 1 step assignment, 4 upholstery requirement) |

## Progress notes

- `2026-05-19`: Intention created. VAPID infrastructure confirmed in place. Four notification types scoped: task state changes, step state changes, step assignment, and upholstery requirement state. Task state audience: union of active `manager`-role members + `task.created_by_id` + `NotificationPin` holders for the task, minus actor. Step state audience: `NotificationPin` holders for the step only (pure opt-in, all transitions). Upholstery audience revised from broad working-section members to managers + `NotificationPin` holders for `item_upholstery` entity — removes noise for workers not directly affected. Bulk upholstery: pin holders queried with `entity_client_id IN (resolved_ids)`, one aggregate notification. `NotificationPin` model confirmed: keyed on `(user_id, entity_type, entity_client_id)`. `task.created_by_id` confirmed present on `Task` model.

## Open questions

- None at this time. All design decisions resolved before plan creation.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: All success criteria met — all four notification types deliver pushes, `Notification` rows created correctly, smoke test confirms device receives push on task state change, step state change (for pin holder), step assignment, and requirement state change
