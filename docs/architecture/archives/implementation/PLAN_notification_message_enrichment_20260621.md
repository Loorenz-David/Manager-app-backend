# PLAN_notification_message_enrichment_20260621

## Metadata

- Plan ID: `PLAN_notification_message_enrichment_20260621`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-21T00:00:00Z`
- Last updated at (UTC): `2026-06-21T15:00:49Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- **Goal:** Replace the static, generic `title` and `body` strings in all existing `CREATE_NOTIFICATIONS` call sites with context-aware messages that include the task's sequential ID (`task_scalar_id`) and the primary item's `article_number` (or `sku` as fallback) and the actor's `username`. For upholstery notifications, always include the upholstery name (when a single entity is in scope) and the count of requirements/items affected (always > 0).
- **Business/user intent:** Push notifications currently say "A task has been resolved." with no indication of _which_ task. Workers and managers need to identify the entity at a glance on the lock screen — task number and article number are the two identifiers they already navigate by.
- **Non-goals:**
  - Changes to `handle_create_notifications`, `handle_send_push_notification`, or `send_web_push`.
  - Changes to the audience-resolution logic (`resolve_task_notification_targets`, `resolve_task_step_notification_targets`, `resolve_upholstery_notification_targets`).
  - Adding or removing notification types.
  - Any frontend changes.

## Scope

- **In scope:**
  - New file: `domain/tasks/notification_labels.py` — two pure async helpers that fetch item context for a task.
  - Modify 12 command files — `title=` and `body=` string literals inside existing `NotificationPayload(...)` calls, plus one new `CREATE_NOTIFICATIONS` block in `transition_step_state.py`:
    - `services/commands/tasks/resolve_task.py`
    - `services/commands/tasks/cancel_task.py`
    - `services/commands/tasks/fail_task.py`
    - `services/commands/task_steps/transition_step_state.py` ← **two changes**: Step 4 (enrich step notification) + Step 4a (add task-state notification for indirect transitions)
    - `services/commands/task_steps/assign_worker_to_step.py`
    - `services/commands/items/mark_requirements_completed.py`
    - `services/commands/items/mark_requirements_in_use.py`
    - `services/commands/items/mark_requirements_ordered.py`
    - `services/commands/items/resolve_requirements_after_stock.py`
    - `services/commands/upholstery/create_upholstery_order.py`
    - `services/commands/upholstery/receive_upholstery_order.py`
    - `services/commands/cases/send_message.py`

- **Out of scope:**

- **Assumptions:**
  - A task has at most one primary active `TaskItem` (`role = 'primary'`, `removed_at IS NULL`) — enforced by partial unique index `uix_task_items_primary_active`. The query uses `one_or_none()`; no `LIMIT` needed.
  - `task.task_scalar_id` is guaranteed non-null (DB column `nullable=False`).
  - `username` from `ctx.identity.get("username")` can be `None` for system-initiated actions; the body must handle that case gracefully with a fallback string.
  - In `transition_step_state.py`, the `task` object is already loaded in scope (line 120). No extra task query is needed — only the item label query is added.
  - `old_task_state` is captured at line 82 (`old_task_state = None`) and assigned at line 123 (`old_task_state = task.state`) before any state mutations. It is non-`None` at the notification site because the task must be loaded for the command to proceed. The guard `old_task_state is not None and task.state != old_task_state` is therefore only defensive for the `None` initializer, but makes the intent explicit and mirrors the existing socket-event check at line 378.
  - In `assign_worker_to_step.py`, the `task` object is _not_ loaded. A single LEFT JOIN query fetching both `task_scalar_id` and item label is used instead of two separate queries.
  - `expire_on_commit=False` is set on the session factory — all ORM attributes accessed after the `maybe_begin` block are safe. The new label queries are placed _inside_ the block so this assumption is not exercised for them.
  - For upholstery single-entity commands (`mark_requirements_completed`, `mark_requirements_in_use`): the `iup` object is already loaded and `iup.name` is `str | None`. The `requirements` list is already in scope and `len(requirements)` is always > 0 (the command raises `ValidationError` before this point if the list is empty).
  - For upholstery bulk commands (`mark_requirements_ordered`, `resolve_requirements_after_stock`, `create_upholstery_order`, `receive_upholstery_order`): the notification is only enqueued when the count is > 0 — the guards `if resolved_ids_for_notif:` and `if allocated_item_upholstery_ids:` are already in place. No additional count guard is needed.
  - No new helper files are required for upholstery enrichment — all needed data is already in scope at each call site.
  - `Case.type_label` is a `str | None` denormalized snapshot column on the `cases` table (not a join to `case_types`). It can be fetched with a single `SELECT Case.type_label WHERE Case.client_id = case_client_id` inside the existing `async with ctx.session.begin():` block in `send_message.py`. The `Case` model is not loaded by default in that command.
  - `ctx.identity.get("username")` is the sender name for case messages, same as for task commands. It can be `None`; fallback to `"someone"` applies.

## Clarifications required

_(none — all design decisions resolved below)_

## Acceptance criteria

1. After `resolve_task`, `cancel_task`, or `fail_task`, the resulting `Notification` row's `title` is `"Task #{scalar_id} resolved"` (or `cancelled` / `failed`) and `body` contains the item's `article_number`, or `sku` if `article_number` is null, or omits the item portion if the task has no primary item.
2. After `transition_step_state`, the push notification body contains `step.working_section_name_snapshot` and `task_scalar_id`, plus item label if present.
3. After `assign_worker_to_step`, the push notification body contains `step.working_section_name_snapshot`, `task_scalar_id` from the parent task, and item label if present.
4. After `mark_requirements_completed`, the body contains `iup.name` (or `"Upholstery"` fallback) and `len(requirements)` count.
5. After `mark_requirements_in_use`, same structure with "in use" phrasing.
6. After `mark_requirements_ordered`, `resolve_requirements_after_stock`, `create_upholstery_order`, `receive_upholstery_order` — the body contains the count of `item_upholstery_ids` affected (always > 0) and the action verb.
7. After `send_message`, the push notification `title` is `"Message from {username} for {type_label}"` when `type_label` is set, or `"Message from {username}"` when it is null. The `body` remains `(request.plain_text or "")[:80]` — unchanged.
8. All 12 modified files remain functionally identical in every respect except the `title=` and `body=` arguments passed to `NotificationPayload(...)`, with the sole addition of one new `CREATE_NOTIFICATIONS` block in `transition_step_state.py` (Step 4a).
9. No change to `entity_type`, `entity_client_id`, `exclude_viewing`, `notification_type`, or `user_ids` in any existing `NotificationPayload(...)` call.
10. The new `notification_labels.py` file has no side effects — it is read-only (SELECT only, no session mutations).
11. After a step transition that advances the task from `ASSIGNED` → `WORKING`, a `CREATE_NOTIFICATIONS` task is enqueued with `notification_type="task_state_changed"`, `entity_type="task"`, `entity_client_id=task.client_id`, for all users returned by `resolve_task_notification_targets` with `event_facts={"state": "working"}`, excluding the actor.
12. After a step transition that advances the task to `READY` (all steps terminal), the same pattern fires with `event_facts={"state": "ready"}`.
13. No task notification is enqueued when the task state does not change as a side effect of the step transition (`old_task_state == task.state`).

## Contracts and skills

### Contracts loaded

- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin` transaction semantics; placement rule for all reads inside the block.
- `backend/architecture/16_background_jobs.md`: `create_instant_task` + `NotificationPayload` + `asdict()` usage pattern.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead.
- **What exists** → reading is legitimate.

Permitted reads (relational):
- The 12 command files listed in scope, to locate exact insertion and replacement points.
- `domain/tasks/notification_targets.py` — to verify import path conventions in the `domain/tasks/` package.
- `models/tables/tasks/task_item.py` — exact field names (`task_id`, `item_id`, `role`, `removed_at`).
- `models/tables/items/item.py` — exact field names (`article_number`, `sku`).
- `domain/tasks/enums.py` — `TaskItemRoleEnum.PRIMARY` value.
- `models/tables/cases/case.py` — `Case.type_label` field name and nullability.

Prohibited reads:
- Any other command file to understand `maybe_begin` / `NotificationPayload` patterns (covered by contracts).

### Skill selection

- Primary skill: `backend/architecture/06_commands.md` (command mutation pattern)
- Secondary: `backend/architecture/16_background_jobs.md` (instant task creation)

## Cross-cutting rules (apply to every step)

**Rule 1 — Label query placement:**
All calls to `resolve_item_label_for_task` and `resolve_scalar_and_item_label` must be placed **inside** the `async with maybe_begin(ctx.session):` block, after the domain mutations and `_create_history_record_in_session` call (where present), immediately before the `create_instant_task` call they feed.

**Rule 2 — Body construction with None-safe fallbacks:**
```python
actor = username or "someone"
item_suffix = f" · {item_label}" if item_label else ""
body = f"#{task.task_scalar_id}{item_suffix} · by {actor}"
```
Never concatenate `None` directly into the string.

**Rule 3 — Only `title` and `body` change:**
Every other argument to `NotificationPayload(...)` — `notification_type`, `user_ids`, `entity_type`, `entity_client_id`, `exclude_viewing` — must remain exactly as it is today. Do not touch them.

**Rule 4 — Import additions are additive:**
Add new imports to the existing import block; never replace or reorder existing imports.

---

## Implementation plan

---

### Step 0 — Create `domain/tasks/notification_labels.py` (new file)

**Create** `backend/app/beyo_manager/domain/tasks/notification_labels.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem


async def resolve_item_label_for_task(session: AsyncSession, task_id: str) -> str | None:
    """Return article_number, or sku as fallback, for the primary active item on a task.

    Returns None if the task has no primary item or if both fields are null.
    Used by task-state commands where the Task object is already loaded.
    """
    result = await session.execute(
        select(Item.article_number, Item.sku)
        .join(TaskItem, Item.client_id == TaskItem.item_id)
        .where(
            TaskItem.task_id == task_id,
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            TaskItem.removed_at.is_(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    return row.article_number or row.sku


async def resolve_scalar_and_item_label(
    session: AsyncSession,
    task_id: str,
) -> tuple[int | None, str | None]:
    """Return (task_scalar_id, item_label) for a task in one LEFT JOIN query.

    Used by step commands where the Task object is not already loaded.
    item_label is article_number, or sku as fallback, or None if no primary item.
    """
    result = await session.execute(
        select(Task.task_scalar_id, Item.article_number, Item.sku)
        .outerjoin(
            TaskItem,
            (TaskItem.task_id == Task.client_id)
            & (TaskItem.role == TaskItemRoleEnum.PRIMARY)
            & TaskItem.removed_at.is_(None),
        )
        .outerjoin(Item, Item.client_id == TaskItem.item_id)
        .where(Task.client_id == task_id)
    )
    row = result.one_or_none()
    if row is None:
        return None, None
    return row.task_scalar_id, (row.article_number or row.sku)
```

---

### Step 1 — `resolve_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/resolve_task.py`

**Add import** (inside existing import block, after the `beyo_manager.domain.tasks.*` imports):
```python
from beyo_manager.domain.tasks.notification_labels import resolve_item_label_for_task
```

**Inside `async with maybe_begin(ctx.session):`**, replace the existing `title=` and `body=` arguments inside `NotificationPayload(...)`:

Current:
```python
                    title="Task resolved",
                    body="A task has been resolved.",
```

Replace with (add the label query immediately before `create_instant_task`, still inside the block):
```python
        item_label = await resolve_item_label_for_task(ctx.session, task.client_id)
        actor = username or "someone"
        item_suffix = f" · {item_label}" if item_label else ""
```

And update the payload arguments:
```python
                    title=f"Task #{task.task_scalar_id} resolved",
                    body=f"#{task.task_scalar_id}{item_suffix} · by {actor}",
```

No other lines change.

---

### Step 2 — `cancel_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/cancel_task.py`

**Add import:**
```python
from beyo_manager.domain.tasks.notification_labels import resolve_item_label_for_task
```

**Inside `async with maybe_begin(ctx.session):`**, add the label lookup immediately before `create_instant_task`:
```python
        item_label = await resolve_item_label_for_task(ctx.session, task.client_id)
        actor = username or "someone"
        item_suffix = f" · {item_label}" if item_label else ""
```

Replace `title=` and `body=`:
```python
                    title=f"Task #{task.task_scalar_id} cancelled",
                    body=f"#{task.task_scalar_id}{item_suffix} · by {actor}",
```

No other lines change.

---

### Step 3 — `fail_task.py`

**File:** `backend/app/beyo_manager/services/commands/tasks/fail_task.py`

**Add import:**
```python
from beyo_manager.domain.tasks.notification_labels import resolve_item_label_for_task
```

**Inside `async with maybe_begin(ctx.session):`**, add the label lookup immediately before `create_instant_task`:
```python
        item_label = await resolve_item_label_for_task(ctx.session, task.client_id)
        actor = username or "someone"
        item_suffix = f" · {item_label}" if item_label else ""
```

Replace `title=` and `body=`:
```python
                    title=f"Task #{task.task_scalar_id} failed",
                    body=f"#{task.task_scalar_id}{item_suffix} · by {actor}",
```

No other lines change.

---

### Step 4 — `transition_step_state.py`

**File:** `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`

Context: `task` is already loaded (line 120: `task = task_result.scalar_one_or_none()`). No extra task query is needed. Only the item label query is added.

**Add import** (after existing `beyo_manager.domain.tasks.*` imports):
```python
from beyo_manager.domain.tasks.notification_labels import resolve_item_label_for_task
```

**Inside `async with maybe_begin(ctx.session):`**, add the label lookup immediately before the step-pin `create_instant_task` call (after `step_pin_user_ids = list(...)`):
```python
        item_label = await resolve_item_label_for_task(ctx.session, task.client_id)
        item_suffix = f" · {item_label}" if item_label else ""
```

Replace `title=` and `body=` inside the existing `NotificationPayload(...)`:
```python
                    title="Step state changed",
                    body=f'"{step.working_section_name_snapshot}" · task #{task.task_scalar_id}{item_suffix}',
```

No other lines change. The label query executes only when `step_pin_user_ids` is non-empty (the guard `if step_pin_user_ids:` wraps the `create_instant_task` call); place the label query and the `item_suffix` construction immediately before the `if step_pin_user_ids:` guard to keep the code readable, but it is acceptable to place them inside the guard to avoid the query when there are no subscribers.

> **Preferred placement — inside the guard:**
> ```python
>         if step_pin_user_ids:
>             item_label = await resolve_item_label_for_task(ctx.session, task.client_id)
>             item_suffix = f" · {item_label}" if item_label else ""
>             await create_instant_task(
>                 ...
>                 payload=asdict(NotificationPayload(
>                     ...
>                     title="Step state changed",
>                     body=f'"{step.working_section_name_snapshot}" · task #{task.task_scalar_id}{item_suffix}',
>                     ...
>                 )),
>             )
> ```

---

### Step 4a — Task state notifications in `transition_step_state.py` (indirect-transition path)

**File:** `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`

**Context:** Step 4 enriches the existing step-pin notification. This step adds an entirely new `CREATE_NOTIFICATIONS` block that fires when a step transition causes the *parent task* to change state as a side effect — specifically:
- Step enters `WORKING` while task is `ASSIGNED` → task advances to `WORKING` (lines 289–292)
- Step enters a terminal state and all steps are terminal → task advances to `READY` (lines 294–307)

Both paths update `task.state` in-place but currently never enqueue a push notification. The socket event at lines 378–381 (`task:state-changed`) only reaches connected clients; offline users with a task PIN for state `working` or `ready` are never notified.

**Amends Step 4 placement:** Step 4's preferred placement puts `item_label` and `item_suffix` inside `if step_pin_user_ids:`. This step requires `item_suffix` for the task notification as well. **Override** that guidance: move the `item_label` query and `item_suffix` construction **before** the `if step_pin_user_ids:` guard (immediately after `resolve_task_step_notification_targets`). The label query runs in the request path against indexed columns and is negligible cost; the simplicity of sharing `item_suffix` across both blocks outweighs the marginal cost of the extra SELECT in the no-step-subscriber case.

**Add import** (alongside the existing `resolve_task_step_notification_targets` import):
```python
from beyo_manager.domain.tasks.notification_targets import resolve_task_notification_targets
```

**Revised block** (replacing lines 335–356 from current code and appending the task-notification block, all still inside `async with maybe_begin(ctx.session):`):

```python
        step_pin_user_ids = list(
            await resolve_task_step_notification_targets(
                ctx.session,
                step.client_id,
                ctx.user_id,
                {"state": request.new_state.value},
            )
        )
        item_label = await resolve_item_label_for_task(ctx.session, task.client_id)
        item_suffix = f" · {item_label}" if item_label else ""
        if step_pin_user_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_step_state_changed",
                    user_ids=step_pin_user_ids,
                    title="Step state changed",
                    body=f'"{step.working_section_name_snapshot or "step"}" · task #{task.task_scalar_id}{item_suffix}',
                    entity_type="task_step",
                    entity_client_id=step.client_id,
                    exclude_viewing=[{"entity_type": "task_step", "entity_client_id": step.client_id}],
                )),
            )

        if old_task_state is not None and task.state != old_task_state:
            actor = ctx.identity.get("username") or "someone"
            task_pin_user_ids = list(
                await resolve_task_notification_targets(
                    ctx.session,
                    ctx.workspace_id,
                    task.client_id,
                    task.created_by_id,
                    ctx.user_id,
                    {"state": task.state.value},
                )
            )
            if task_pin_user_ids:
                await create_instant_task(
                    session=ctx.session,
                    task_type=TaskType.CREATE_NOTIFICATIONS,
                    payload=asdict(NotificationPayload(
                        notification_type="task_state_changed",
                        user_ids=task_pin_user_ids,
                        title=f"Task #{task.task_scalar_id} {task.state.value}",
                        body=f"#{task.task_scalar_id}{item_suffix} · by {actor}",
                        entity_type="task",
                        entity_client_id=task.client_id,
                        exclude_viewing=[{"entity_type": "task", "entity_client_id": task.client_id}],
                    )),
                )
```

The rest of the function from line 358 onward — `state_changed_items`, `pending_events`, `event_bus.dispatch` — remains **unchanged**. The socket event at line 378–381 continues to fire for connected clients; the new block above handles push for offline subscribers.

---

### Step 5 — `assign_worker_to_step.py`

**File:** `backend/app/beyo_manager/services/commands/task_steps/assign_worker_to_step.py`

Context: `task` is NOT loaded in this command. `step.task_id` is the FK to the parent task. Use `resolve_scalar_and_item_label` to fetch both `task_scalar_id` and `item_label` in one query.

**Add import:**
```python
from beyo_manager.domain.tasks.notification_labels import resolve_scalar_and_item_label
```

**Inside `async with maybe_begin(ctx.session):`**, the existing self-assign guard is `if request.worker_id != ctx.user_id:`. Place the label query inside that guard, immediately before `create_instant_task`:

```python
        if request.worker_id != ctx.user_id:
            scalar_id, item_label = await resolve_scalar_and_item_label(ctx.session, step.task_id)
            item_suffix = f" · {item_label}" if item_label else ""
            task_ref = f"#{scalar_id}" if scalar_id is not None else "task"
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type="task_step_assigned",
                    user_ids=[request.worker_id],
                    title="Step assigned to you",
                    body=f'"{step.working_section_name_snapshot}" · {task_ref}{item_suffix}',
                    entity_type="task_step",
                    entity_client_id=step.client_id,
                    exclude_viewing=[{"entity_type": "task_step", "entity_client_id": step.client_id}],
                )),
            )
```

The `scalar_id is not None` fallback to `"task"` is a defensive guard — `task_scalar_id` is non-null in the DB, but `resolve_scalar_and_item_label` returns `None` if the task row is not found (which would have caused a 404 earlier in the same transaction, so this branch is unreachable in practice).

No other lines change. The existing `build_workspace_event` dispatch and `return` remain unchanged.

---

---

### Step 6 — `mark_requirements_completed.py`

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py`

Context: `iup` is already loaded (`iup.name` is `str | None`). `requirements` is already in scope as a list of `ItemUpholsteryRequirement` objects; `len(requirements) > 0` is guaranteed by the `ValidationError` guard above.

No new imports needed — no helper is required.

Replace `title=` and `body=` inside the existing `NotificationPayload(...)`:

Current:
```python
                    title="Requirements completed",
                    body="Upholstery requirements have been marked as completed.",
```

Replace with:
```python
                    title="Requirements completed",
                    body=f'{iup.name or "Upholstery"} was completed for {len(requirements)} item(s)',
```

No other lines change.

---

### Step 7 — `mark_requirements_in_use.py`

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py`

Context: `iup` is already loaded. `requirements` is already in scope; `len(requirements) > 0` guaranteed.

No new imports needed.

Replace `title=` and `body=`:

Current:
```python
                    title="Requirements in use",
                    body="Upholstery requirements are now in use.",
```

Replace with:
```python
                    title="Requirements in use",
                    body=f'{iup.name or "Upholstery"} was marked in use for {len(requirements)} item(s)',
```

No other lines change.

---

### Step 8 — `mark_requirements_ordered.py`

**File:** `backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py`

Context: `resolved_ids_for_notif` is already computed and in scope at the notification call site. No upholstery name is available (bulk operation across multiple `item_upholstery_ids`). `len(resolved_ids_for_notif) > 0` is guaranteed by the `if resolved_ids_for_notif:` guard that wraps the audience resolution.

No new imports needed.

Replace `title=` and `body=`:

Current:
```python
                        title="Requirements ordered",
                        body="Upholstery requirements have been ordered.",
```

Replace with:
```python
                        title="Requirements ordered",
                        body=f'{len(resolved_ids_for_notif)} item(s) with upholstery requirements ordered',
```

No other lines change.

---

### Step 9 — `resolve_requirements_after_stock.py`

**File:** `backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py`

Context: `resolved_ids_for_notif` is already in scope. `len(resolved_ids_for_notif) > 0` guaranteed by the `if resolved_ids_for_notif:` guard.

No new imports needed.

Replace `title=` and `body=`:

Current:
```python
                        title="Requirements resolved",
                        body="Upholstery requirements have been resolved from stock.",
```

Replace with:
```python
                        title="Requirements resolved",
                        body=f'{len(resolved_ids_for_notif)} item(s) with upholstery requirements resolved from stock',
```

No other lines change.

---

### Step 10 — `create_upholstery_order.py`

**File:** `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py`

Context: `allocated_item_upholstery_ids` is already in scope. `len(allocated_item_upholstery_ids) > 0` is guaranteed by the `if allocated_item_upholstery_ids:` guard that wraps the audience resolution.

No new imports needed.

Replace `title=` and `body=`:

Current:
```python
                            title="Requirements ordered",
                            body="Upholstery requirements have been ordered.",
```

Replace with:
```python
                            title="Requirements ordered",
                            body=f'{len(allocated_item_upholstery_ids)} item(s) with upholstery requirements ordered',
```

No other lines change.

---

### Step 11 — `receive_upholstery_order.py`

**File:** `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py`

Context: `allocated_item_upholstery_ids` is already in scope. `len(allocated_item_upholstery_ids) > 0` guaranteed by the `if allocated_item_upholstery_ids:` guard.

No new imports needed.

Replace `title=` and `body=`:

Current:
```python
                            title="Upholstery available",
                            body="Upholstery requirements are now available for production.",
```

Replace with:
```python
                            title="Upholstery available",
                            body=f'{len(allocated_item_upholstery_ids)} item(s) with upholstery now available for production',
```

No other lines change.

---

### Step 12 — `send_message.py`

**File:** `backend/app/beyo_manager/services/commands/cases/send_message.py`

Context: `conversation` is loaded; `case_client_id = conversation.case_id` is already computed and in scope. `Case` is not loaded. One extra `SELECT` for `Case.type_label` is needed. The transaction is `async with ctx.session.begin():` (not `maybe_begin`); the new query must go inside that block.

**Add import** (after the existing `beyo_manager.models.tables.cases.*` imports):
```python
from beyo_manager.models.tables.cases.case import Case
```

**Inside `async with ctx.session.begin():`**, add the case type query immediately after `case_client_id = conversation.case_id` is assigned (before the participant query):
```python
        case_type_result = await ctx.session.execute(
            select(Case.type_label).where(Case.client_id == case_client_id)
        )
        case_type_label = case_type_result.scalar_one_or_none()
```

Then build the enriched title immediately before the `create_instant_task` call:
```python
        sender = ctx.identity.get("username") or "someone"
        type_suffix = f" for {case_type_label}" if case_type_label else ""
```

Replace `title=` inside the existing `NotificationPayload(...)`:

Current:
```python
                        title="New message",
                        body=(request.plain_text or "")[:80],
```

Replace with:
```python
                        title=f"Message from {sender}{type_suffix}",
                        body=(request.plain_text or "")[:80],
```

The `body=` line is unchanged — plain text content remains the best body for chat messages.

No other lines change. The existing participant query, `unread_by_user` computation, `exclude_viewing`, and all event dispatch logic remain exactly as-is.

---

## Extension points

As new notification call sites are added, extend this plan with additional steps following the established patterns:

- **Task commands where `task` is loaded** → `resolve_item_label_for_task(session, task.client_id)` from `domain/tasks/notification_labels.py`.
- **Step or other commands where only a `task_id` FK is available** → `resolve_scalar_and_item_label(session, task_id)`.
- **Single-entity upholstery commands where `iup` is loaded** → use `iup.name` and `len(requirements)` directly — no helper needed.
- **Bulk upholstery commands** → use `len(ids_list)` directly — no helper needed.

---

## Risks and mitigations

- **Risk:** `resolve_item_label_for_task` adds one SELECT per task-state notification; `resolve_scalar_and_item_label` adds one LEFT JOIN SELECT per step assignment.
  **Mitigation:** Both queries hit indexed columns (`task_items.task_id`, `task_items.role`, `task_items.removed_at`, `items.client_id`). The audience for these notifications is small (< 10 users typically) and these queries run in the background worker, not the request path.

- **Risk:** `resolve_task_notification_targets` (Step 4a) runs only when `task.state != old_task_state`, but `item_label` is now queried unconditionally (before `if step_pin_user_ids:`). In the common case where neither step-pin nor task-pin subscribers exist, one extra SELECT runs that previously did not.
  **Mitigation:** The SELECT hits `task_items.task_id + role + removed_at` (indexed) and is bounded by the partial unique index on primary active items — effectively a single-row lookup. The transition command already executes several indexed queries; this adds negligible latency.

- **Risk:** `step.working_section_name_snapshot` can be `None` if the section was soft-deleted after the step was created.
  **Mitigation:** In Python, `f'"{None}"'` produces `"None"` — which is ugly. Guard with `step.working_section_name_snapshot or "step"` in the body f-string if Codex judges the field may realistically be null. The model column is `nullable=True`.

- **Risk:** `username` is `None` for system-initiated transitions (no human actor).
  **Mitigation:** Rule 2 mandates `actor = username or "someone"` before constructing the body. Never use `username` directly in an f-string.

- **Risk:** `Case.type_label` is `None` when the case has no type assigned.
  **Mitigation:** Step 12 uses `f" for {case_type_label}" if case_type_label else ""` so the title gracefully degrades to `"Message from John"` with no trailing garbage.

- **Risk:** The extra `SELECT Case.type_label` in `send_message.py` adds a round trip inside an already-open transaction.
  **Mitigation:** `cases.client_id` is the primary key — this is a single-row PK lookup, negligible cost. The query is placed inside the existing `async with ctx.session.begin():` block so no transaction boundary is crossed.

- **Risk:** `iup.name` is `None` when the upholstery entry has no name set.
  **Mitigation:** Steps 6 and 7 use `iup.name or "Upholstery"` as the fallback. The resulting body is `"Upholstery was completed for N item(s)"` — still meaningful.

- **Risk:** Codex modifies `entity_type`, `entity_client_id`, or `exclude_viewing` by accident while editing the payload.
  **Mitigation:** Rule 3 explicitly prohibits touching any argument other than `title=` and `body=`. Acceptance criterion 8 verifies this.

## Validation plan

- `resolve_task` smoke test: resolve a task that has a primary item with `article_number="A-1234"` → push notification `title` is `"Task #42 resolved"`, `body` is `"#42 · A-1234 · by john"`.
- `resolve_task` smoke test (no item): resolve a task with no item attached → `body` is `"#42 · by john"` (no item suffix).
- `cancel_task` smoke test: same pattern with `"cancelled"`.
- `fail_task` smoke test: same pattern with `"failed"`.
- `transition_step_state` smoke test (step PIN): transition a step that a user has pinned → `body` is `'"Section name" · task #42 · A-1234'`.
- `transition_step_state` smoke test (task ASSIGNED→WORKING, task PIN): worker "john" starts a step on an ASSIGNED task → a second `CREATE_NOTIFICATIONS` task is enqueued with `notification_type="task_state_changed"`, `title="Task #42 working"`, `body="#42 · A-1234 · by john"`, for all task-level PIN subscribers (state condition `working`) excluding the actor.
- `transition_step_state` smoke test (all steps terminal → READY, task PIN): last step completes on a task that has a PIN subscriber for state `ready` → `CREATE_NOTIFICATIONS` enqueued with `title="Task #42 ready"`.
- `transition_step_state` smoke test (no task state change): transition a step that does NOT change task state (e.g., WORKING→PAUSED on an already-WORKING task) → no task-level `CREATE_NOTIFICATIONS` enqueued; only the step-pin notification fires (if there are step subscribers).
- `transition_step_state` smoke test (step PIN + task PIN, shared item_suffix): both a step subscriber and a task subscriber exist → both `CREATE_NOTIFICATIONS` tasks use the same `item_suffix` computed from one SELECT.
- `assign_worker_to_step` smoke test: assign a worker to a step on task #7 (item SKU "SKU-99", no article_number) → `body` is `'"Upholstery" · #7 · SKU-99'`.
- `assign_worker_to_step` self-assign smoke test: actor assigns themselves → no `CREATE_NOTIFICATIONS` task created, no label query executed.
- `mark_requirements_completed` smoke test: complete requirements for an `ItemUpholstery` named "Black Velvet" with 2 active requirements → `body` is `"Black Velvet was completed for 2 item(s)"`.
- `mark_requirements_completed` smoke test (no name): complete requirements for an unnamed `ItemUpholstery` → `body` is `"Upholstery was completed for 1 item(s)"`.
- `mark_requirements_in_use` smoke test: mark 3 requirements in use → `body` is `"{iup.name or "Upholstery"} was marked in use for 3 item(s)"`.
- `mark_requirements_ordered` smoke test: mark ordered and 4 `item_upholstery_ids` are resolved → `body` is `"4 item(s) with upholstery requirements ordered"`.
- `resolve_requirements_after_stock` smoke test: 2 IDs resolved → `body` is `"2 item(s) with upholstery requirements resolved from stock"`.
- `create_upholstery_order` smoke test: order created allocating 5 item_upholsteries → `body` is `"5 item(s) with upholstery requirements ordered"`.
- `receive_upholstery_order` smoke test: order received allocating 3 item_upholsteries → `body` is `"3 item(s) with upholstery now available for production"`.
- `send_message` smoke test: send a message in a case with `type_label="Vehicle Inspection"` → `title` is `"Message from john for Vehicle Inspection"`, `body` is the message text.
- `send_message` smoke test (no type): send a message in a case with no type assigned (`type_label=None`) → `title` is `"Message from john"`.
- `send_message` smoke test (anonymous actor): `ctx.identity` has no username → `title` is `"Message from someone for Vehicle Inspection"`.

## Review log

*(empty)*

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David Loorenz`
