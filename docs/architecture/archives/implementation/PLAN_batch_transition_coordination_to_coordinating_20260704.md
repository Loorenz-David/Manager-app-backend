# PLAN_batch_transition_coordination_to_coordinating_20260704

## Metadata

- Plan ID: `PLAN_batch_transition_coordination_to_coordinating_20260704`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Last updated at (UTC): `2026-07-04T15:33:51Z`
- Related issue/ticket: —
- Intention plan: —

---

## Goal and intent

- **Goal:** When `send_customer_coordination_email_batch` creates threads and messages for a set of tasks, transition each corresponding `TaskCustomerCoordination` instance from `PENDING` to `COORDINATING` within the same DB transaction. A new session-level helper handles the batch transition so the command stays clean and the pattern stays composable.
- **Business/user intent:** Sending a coordination email is the action that moves a task into active coordination. The state should reflect that immediately — callers that filter by `coordination_state=coordinating` (e.g., the threads inbox endpoint) will correctly include these tasks without any manual step or eventual-consistency lag.
- **Non-goals:**
  - No new router, migration, or model change — `COORDINATING` already exists in `TaskCustomerCoordinationStateEnum` and in the DB enum.
  - No change to `complete_task_customer_coordination` — that service stays as-is.
  - No transition for skipped tasks (those that had no customer email, no TCC record, etc.).
  - No `COMPLETED → COORDINATING` regression path — completed coordinations are skipped.

---

## Scope

- **In scope:**
  - `app/beyo_manager/services/commands/task_customer_coordination/_transition_coordination_to_coordinating_in_session.py` — **new** session-level helper
  - `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py` — add `queued_coordinations` tracking, call the helper inside `maybe_begin`, dispatch events after

- **Out of scope:**
  - No router changes
  - No migration (enum value and column already exist)
  - No changes to `complete_task_customer_coordination.py` or `_create_customer_coordination_in_session.py`
  - No change to request/response shape of the email-batch endpoint

---

## Clarifications required

None — all design decisions are resolved below.

---

## Acceptance criteria

1. After a successful call to `POST /tasks/customer-coordination/email-batch`, every non-skipped `TaskCustomerCoordination` instance whose state was `PENDING` has `state = COORDINATING` committed in the same transaction as the `EmailThread`, `EmailMessage`, and `ExecutionTask` rows.
2. A `TaskCustomerCoordination` already in `COORDINATING` is not re-written (no duplicate history record, `updated_at` unchanged).
3. A `TaskCustomerCoordination` in `COMPLETED` is not touched.
4. A `HistoryRecord` is written for each instance that was actually transitioned, capturing `from_value = {state: "pending"}` and `to_value = {state: "coordinating"}`.
5. If the transaction rolls back for any reason, no state change or history record persists.
6. A `task_customer_coordination:coordinating` workspace event is dispatched after the transaction for each transitioned instance.
7. The command's response shape (`job_id`, `status`, `queued_count`, `skipped_count`, `skipped`) is unchanged.

---

## Contracts and skills

### Contracts loaded

- `architecture/06_commands.md` + `architecture/06_commands_local.md`: session-level helpers, `maybe_begin` transaction rule, event dispatch after commit
- `architecture/40_identity.md`: workspace scoping — all writes must include `workspace_id`

### Local extensions loaded

- `architecture/06_commands_local.md`: `maybe_begin` — all DB writes and the state transition must be inside the same `async with maybe_begin` block

### File read intent — pattern vs. relational

Permitted (relational reads — understanding what exists):
- `app/beyo_manager/services/commands/task_customer_coordination/_create_customer_coordination_in_session.py` — reference shape for a session-level TCC helper (signature, flush pattern, history call)
- `app/beyo_manager/services/commands/task_customer_coordination/complete_task_customer_coordination.py` — to confirm which fields are set on state transition (`state`, `updated_at`) and how `_create_history_record_in_session` is called
- `app/beyo_manager/models/tables/tasks/task_customer_coordination.py` — to confirm `updated_at` column exists on the model
- `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py` — to know exactly where in the loop to insert `queued_coordinations.append(...)` and where to call the helper

Prohibited (pattern reads — contracts cover these):
- Reading another command to understand session.add / flush / history write shape → `06_commands.md`

### Skill selection

- Primary skill: `06_commands.md` (session-level helper + event dispatch pattern)
- Excluded: no router, no migration, no background job

---

## Implementation plan

### Step 1 — Create the session-level batch transition helper

**File:** `app/beyo_manager/services/commands/task_customer_coordination/_transition_coordination_to_coordinating_in_session.py` *(new file)*

**Signature:**
```python
async def _transition_coordination_to_coordinating_in_session(
    session: AsyncSession,
    coordinations: list[TaskCustomerCoordination],
    *,
    now: datetime,
    user_id: str | None,
    username_snapshot: str | None = None,
) -> list[TaskCustomerCoordination]:
```

Returns the list of instances that were actually transitioned (state changed from `PENDING` to `COORDINATING`). Instances already in `COORDINATING` or `COMPLETED` are silently skipped and excluded from the return list.

**Body:**
```python
transitioned: list[TaskCustomerCoordination] = []
for coordination in coordinations:
    if coordination.state != TaskCustomerCoordinationStateEnum.PENDING:
        continue

    old_state = coordination.state
    coordination.state = TaskCustomerCoordinationStateEnum.COORDINATING
    coordination.updated_at = now

    await _create_history_record_in_session(
        session=session,
        entity_type=HistoryRecordEntityTypeEnum.TASK_CUSTOMER_COORDINATION,
        entity_client_id=coordination.client_id,
        change_type=HistoryRecordChangeTypeEnum.UPDATED,
        description=f"Customer coordination transitioned to coordinating (from {old_state.value})",
        field_name="state",
        from_value={"state": old_state.value},
        to_value={"state": TaskCustomerCoordinationStateEnum.COORDINATING.value},
        created_by_id=user_id,
        username_snapshot=username_snapshot,
    )
    transitioned.append(coordination)
return transitioned
```

**Design notes:**
- No `session.flush()` call is needed here — the caller (`send_customer_coordination_email_batch`) already calls `ctx.session.flush()` after thread and message creation, and the overall `maybe_begin` transaction will commit everything atomically. Adding a flush here would be premature. If the caller ever needs to read back the new state before commit, they can flush after this call themselves.
- `user_id` is `str | None` because the caller is a request-scoped command and `ctx.user_id` is always set. The `None` type is kept for interface symmetry with other in-session helpers.
- No event dispatch inside — this is a session-level helper. Events are the caller's responsibility (same pattern as `_create_customer_coordination_in_session`).

---

### Step 2 — Update `send_customer_coordination_email_batch` to call the helper

**File:** `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py`

**Add the import at the top:**
```python
from beyo_manager.services.commands.task_customer_coordination._transition_coordination_to_coordinating_in_session import (
    _transition_coordination_to_coordinating_in_session,
)
```

Also add the event infrastructure imports (if not already present):
```python
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
```

**Inside the loop, add a `queued_coordinations` collector alongside `queued_thread_ids`:**

Declare before the loop:
```python
queued_coordinations: list[TaskCustomerCoordination] = []
```

At the bottom of the per-task `for` loop body (after `queued_thread_ids.append(thread.client_id)`), append:
```python
queued_coordinations.append(coordination)
```

**After the loop but still inside `maybe_begin`, before `create_instant_task`:**
```python
transitioned = await _transition_coordination_to_coordinating_in_session(
    session=ctx.session,
    coordinations=queued_coordinations,
    now=now,
    user_id=ctx.user_id,
    username_snapshot=ctx.identity.get("username"),
)
```

The call goes after the loop and before `create_instant_task` so that all state writes are grouped together before the job is enqueued. The ordering inside a single `maybe_begin` block does not affect atomicity.

**After the `async with maybe_begin` block exits (after the `return` dict is constructed), dispatch events:**
```python
if transitioned:
    await event_bus.dispatch([
        build_workspace_event(
            tcc,
            "task_customer_coordination:coordinating",
            workspace_id=ctx.workspace_id,
        )
        for tcc in transitioned
    ])
```

Note: the `return` statement for the response dict must be moved to after the event dispatch. Restructure the end of the function as:

```python
    # ... still inside maybe_begin ...
    if queued_thread_ids:
        job = await create_instant_task(...)

result = {
    "job_id": job.client_id if job else None,
    "status": "queued" if job else "nothing_to_send",
    "queued_count": len(queued_thread_ids),
    "skipped_count": len(skipped),
    "skipped": skipped,
}

if transitioned:
    await event_bus.dispatch([
        build_workspace_event(tcc, "task_customer_coordination:coordinating", workspace_id=ctx.workspace_id)
        for tcc in transitioned
    ])

return result
```

The `transitioned` variable is in scope because it was assigned inside `maybe_begin` (Python scope — `with` blocks do not create a new scope).

---

## Risks and mitigations

- **Risk:** `transitioned` variable is referenced after `maybe_begin` but could be unbound if an exception exits the `with` block before the helper call.
  **Mitigation:** Declare `transitioned: list = []` before the `async with maybe_begin` block so it is always bound. Event dispatch of an empty list is a no-op.

- **Risk:** A TCC already in `COORDINATING` is passed to the helper on a duplicate call (e.g., frontend retries the same batch).
  **Mitigation:** The helper's `if coordination.state != TaskCustomerCoordinationStateEnum.PENDING: continue` guard makes the operation idempotent for `COORDINATING` instances — no double history write, no mutation.

- **Risk:** The state transition and the email job commit atomically, but the event is dispatched after. If the process crashes between commit and dispatch, the event is lost.
  **Mitigation:** Acceptable — events are best-effort real-time notifications. The persistent state (DB row with `state=COORDINATING`) is the source of truth. The frontend can re-fetch on reconnect.

---

## Validation plan

- `python3 -m py_compile app/beyo_manager/services/commands/task_customer_coordination/_transition_coordination_to_coordinating_in_session.py app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py` — no import or syntax errors
- Confirm `transitioned` is declared before `async with maybe_begin` so it is always bound for event dispatch.
- Confirm the helper is called inside `maybe_begin` and before `create_instant_task`.
- Confirm response shape keys (`job_id`, `status`, `queued_count`, `skipped_count`, `skipped`) are unchanged.
- Confirm skipped tasks (missing TCC, no customer email) are NOT in `queued_coordinations` and do NOT get a history record.

---

## Review log

_No entries yet._

---

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `claude`
