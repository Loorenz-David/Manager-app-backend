# PLAN_coordination_email_batch_background_job_20260704

## Metadata

- Plan ID: `PLAN_coordination_email_batch_background_job_20260704`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Last updated at (UTC): `2026-07-04T15:05:12Z`
- Related issue/ticket: —
- Intention plan: —

---

## Goal and intent

- **Goal:** Convert `POST /api/v1/tasks/customer-coordination/email-batch` from a synchronous SMTP-blocking HTTP request into a two-phase background job. The HTTP response returns immediately after DB records are created and the job is enqueued; a worker handles SMTP delivery asynchronously.
- **Business/user intent:** The current implementation blocks the HTTP request until every SMTP call completes (up to 50 messages), risking gateway timeouts and slow UX. The background job approach gives an immediate response and lets the worker retry failed sends with backoff.
- **Non-goals:**
  - No new domain entities or tables — only two new columns on `email_messages` and a new `ExecutionTask` type.
  - No websocket notification when the job completes (deferred).
  - No polling endpoint for job status (deferred — the frontend can read delivery status from `GET /email-threads/{thread_id}/messages` via the new `send_error`/`send_attempted_at` fields).
  - No change to the enrichment layer, skip logic, or the list/count endpoints.

---

## Scope

- **In scope:**
  - `app/beyo_manager/models/tables/emails/email_message.py` — add `send_attempted_at` and `send_error` columns
  - `app/migrations/versions/XXXX_add_send_delivery_fields_to_email_messages.py` — migration for the two new columns
  - `app/beyo_manager/domain/execution/enums.py` — add `TaskType.SEND_COORDINATION_EMAIL_BATCH`
  - `app/beyo_manager/services/infra/execution/task_router.py` — add entry to `QUEUE_MAP`
  - `app/beyo_manager/domain/execution/payloads/send_coordination_email_batch.py` — new frozen dataclass
  - `app/beyo_manager/services/tasks/emails/handle_send_coordination_email_batch.py` — new handler
  - `app/beyo_manager/workers/tasks_worker.py` — register handler in `HANDLER_MAP`
  - `app/beyo_manager/services/infra/execution/worker_base.py` — add timeout entry
  - `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py` — refactor: remove SMTP call and audit write, add `create_instant_task`, change response shape
  - `app/beyo_manager/domain/emails/serializers.py` — expose `send_attempted_at` and `send_error` in `serialize_email_message`
  - `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704.md` — update Section 1 response shape and Section 5 message shape

- **Out of scope:**
  - No changes to any other command, query, or router
  - No changes to the enrichment layer (`ContentEnricher`, parsers, `VAR_PARSER_MAP`)
  - No changes to `_connection_resolver.py`

---

## Clarifications required

None — design was fully resolved before this plan was written.

---

## Acceptance criteria

1. `POST /tasks/customer-coordination/email-batch` responds with `{ "job_id": ..., "status": "queued", "queued_count": N, "skipped_count": M, "skipped": [...] }` in < 500 ms (DB-only, no SMTP call in the request).
2. The `ExecutionTask` and `ExecutionPayload` rows are committed in the same DB transaction as the `EmailThread` and `EmailMessage` records — if the transaction fails, no orphaned job is created.
3. The worker handler (`handle_send_coordination_email_batch`) calls the SMTP provider and writes `send_attempted_at` + `send_error` to each `EmailMessage` record.
4. The handler is idempotent: if the job is retried, only messages where `send_attempted_at IS NULL` are re-attempted. Messages already attempted are skipped (not re-sent).
5. If the SMTP provider returns an error for a specific message, `send_error` is populated and the message is marked `send_attempted_at = now`. The job still completes (`COMPLETED`) — partial SMTP failure is not a job failure.
6. If the SMTP call itself raises an exception (e.g., connection refused), the worker retries the job with backoff (up to `max_try=3`).
7. `serialize_email_message` includes `send_attempted_at` and `send_error` so the frontend can read delivery status via `GET /email-threads/{thread_id}/messages`.
8. The handler audit event `task.customer_coordination.email_batch_sent` fires in the worker after all delivery attempts complete.

---

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: layered architecture
- `architecture/04_context.md`: `ServiceContext` and `maybe_begin` for the command layer
- `architecture/05_errors.md`: error types
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: command pattern and `maybe_begin` transaction rule — the command still uses a single `maybe_begin` block; `create_instant_task` is called inside that same block
- `architecture/16_background_jobs.md`: **primary contract** — five-place extension pattern, payload dataclass rules, handler contract, idempotency, session isolation, timeout enforcement, QUEUE_MAP
- `architecture/30_migrations.md`: nullable column pattern (safe, no locking), migration naming and review checklist
- `architecture/21_naming_conventions.md`: file and function naming

### Local extensions loaded

- `architecture/06_commands_local.md`: `maybe_begin` transaction utility — `create_instant_task` must be called inside the same `maybe_begin` block as all DB writes

### File read intent — pattern vs. relational

Permitted (relational reads — understanding what exists):
- `app/beyo_manager/models/tables/emails/email_message.py` — exact column definitions before adding new ones
- `app/beyo_manager/models/tables/emails/email_thread.py` — to confirm relationship field name for flush
- `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py` — to know exactly what to remove and what stays
- `app/beyo_manager/workers/tasks_worker.py` — to know where to add the new handler entry
- `app/beyo_manager/domain/execution/payloads/upload.py` — reference shape for a frozen dataclass
- `app/beyo_manager/services/tasks/email_inbox_sync_handler.py` — reference shape for an email handler
- `app/beyo_manager/domain/execution/enums.py` — to append `SEND_COORDINATION_EMAIL_BATCH` correctly
- `app/beyo_manager/services/infra/execution/task_router.py` — to add to `QUEUE_MAP`
- `app/beyo_manager/services/infra/execution/worker_base.py` — to add to `HANDLER_TIMEOUT_SECONDS`
- `app/beyo_manager/domain/emails/serializers.py` — to add two fields to `serialize_email_message`

Prohibited (pattern reads):
- Reading another command to understand `session.add` / `flush` / error shape → `06_commands.md`
- Reading another handler to understand the worker flow → `16_background_jobs.md`

### Skill selection

- Primary skill: `16_background_jobs.md` (new task type + handler)
- Secondary skill: `30_migrations.md` (nullable column addition)
- Secondary skill: `06_commands.md` (command refactor)
- Excluded: no routers change, no new models/tables

---

## Implementation plan

### Step 1 — Add delivery columns to `EmailMessage` model

**File:** `app/beyo_manager/models/tables/emails/email_message.py`

Add two nullable columns after `created_by_user_id`:

```python
send_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
send_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

Both are `nullable=True` — safe to add to a populated table without locking (see `30_migrations.md` nullable pattern). No index needed: these fields are read per-message, not filtered in bulk queries.

---

### Step 2 — Generate and write the migration

**Run:** `alembic revision --autogenerate -m "add_send_delivery_fields_to_email_messages"`

**Review checklist (from `30_migrations.md`):**
- [ ] Targets `email_messages` table (not another)
- [ ] Both columns are `nullable=True`
- [ ] No unintended tables included in the diff
- [ ] `downgrade()` drops both columns correctly
- [ ] No index generated (not needed)

The migration file is created under `app/migrations/versions/`.

---

### Step 3 — Add `TaskType.SEND_COORDINATION_EMAIL_BATCH` to the enum

**File:** `app/beyo_manager/domain/execution/enums.py`

Add under the `# Email` comment block (after `EMAIL_INBOX_SYNC`):

```python
SEND_COORDINATION_EMAIL_BATCH = "send_coordination_email_batch"
```

This is the only app-wide enum addition. The string value must exactly match what will be used as the `HANDLER_TIMEOUT_SECONDS` key in Step 8.

---

### Step 4 — Add the queue mapping in the task router

**File:** `app/beyo_manager/services/infra/execution/task_router.py`

Add to `QUEUE_MAP` (alongside `EMAIL_INBOX_SYNC` — same queue):

```python
TaskType.SEND_COORDINATION_EMAIL_BATCH: "queue:tasks",
```

Both email tasks land on `queue:tasks`. The existing `tasks_worker.py` already processes this queue.

---

### Step 5 — Create the payload dataclass

**File:** `app/beyo_manager/domain/execution/payloads/send_coordination_email_batch.py` *(new file)*

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SendCoordinationEmailBatchPayload:
    """Payload for SEND_COORDINATION_EMAIL_BATCH tasks."""
    workspace_id: str
    connection_client_id: str
    thread_ids: list[str]
```

Rules from `16_background_jobs.md`:
- `frozen=True` — immutable snapshot
- All fields JSON-serialisable (strings and a list of strings)
- The handler will deserialise with `SendCoordinationEmailBatchPayload(**raw)` as its first line
- At the command side, use `asdict(payload_instance)` to produce the dict for `create_instant_task`

`thread_ids` contains the `client_id` values of the pre-created `EmailThread` records (one per non-skipped task). The handler resolves `EmailMessage` records from these.

---

### Step 6 — Create the handler

**File:** `app/beyo_manager/services/tasks/emails/handle_send_coordination_email_batch.py` *(new file, new `emails/` subdirectory under `services/tasks/`)*

**Handler signature:**
```python
async def handle_send_coordination_email_batch(raw: dict, task_client_id: str) -> None:
```

**Handler body — three discrete phases:**

**Phase 1 — Load (session 1, closes before SMTP):**

Inside `async for session in get_db_session()`:
1. Deserialise: `payload = SendCoordinationEmailBatchPayload(**raw)`
2. Load `EmailConnection` where `client_id == payload.connection_client_id AND workspace_id == payload.workspace_id`. If missing → `logger.warning` + `return`.
3. Load `EmailMessage` records where:
   - `thread_id IN (payload.thread_ids)`
   - `direction == EmailMessageDirectionEnum.OUTBOUND.value`
   - `send_attempted_at IS NULL` ← **idempotency guard** — already-attempted messages are skipped on retry
4. If no messages remain → `logger.info("all_messages_already_attempted")` + `return` (fully idempotent).
5. Call `get_email_provider(connection)` while the connection object's attributes are still loaded — capture the provider reference.
6. Build `outbound_messages: list[OutboundMessage]` from the loaded `EmailMessage` attributes.
7. Capture `message_ids: list[str]` (client_id values) for the update phase.

Session closes at end of `async for` block. No DB connection is held during SMTP.

**Phase 2 — SMTP (no DB connection):**

```python
batch_result = await provider.send_email_batch(outbound_messages)
```

This is the only place where an external call happens. If it raises, the worker's `_fail_task` / `_schedule_retry_or_fail` handles retry. The idempotency guard in Phase 1 ensures that on retry, only un-attempted messages are resent.

**Phase 3 — Record results (session 2):**

Inside a second `async for session in get_db_session(): async with session.begin()`:
1. `now = datetime.now(timezone.utc)`
2. For each `(message_id, send_result)` in `zip(message_ids, batch_result.results)`:
   - Load `EmailMessage` by `client_id == message_id`
   - Set `msg.send_attempted_at = now`
   - Set `msg.send_error = send_result.error` (None on success, string on failure)
3. Write audit:
   ```python
   await write_audit(
       session=session,
       event="task.customer_coordination.email_batch_sent",
       workspace_id=payload.workspace_id,
       actor_user_id=None,   # background job — no request user
       resource_type="email_connection",
       resource_client_id=payload.connection_client_id,
       detail={
           "attempted_count": len(message_ids),
           "sent_count": sum(1 for r in batch_result.results if r.success),
           "failed_count": sum(1 for r in batch_result.results if not r.success),
           "job_task_id": task_client_id,
       },
   )
   ```
4. Commit (via `async with session.begin()` exit).

**Important: partial SMTP failure is NOT a job failure.** Per acceptance criterion 5: if one message fails to deliver, `send_error` is set for that message, but the handler completes normally. The job is marked `COMPLETED`. Only an exception from the SMTP call itself (network error, auth failure) causes the job to retry.

---

### Step 7 — Register the handler in the tasks worker

**File:** `app/beyo_manager/workers/tasks_worker.py`

Add import:
```python
from beyo_manager.services.tasks.emails.handle_send_coordination_email_batch import (
    handle_send_coordination_email_batch,
)
```

Add to `HANDLER_MAP`:
```python
TaskType.SEND_COORDINATION_EMAIL_BATCH: handle_send_coordination_email_batch,
```

No other changes to the worker.

---

### Step 8 — Add the handler timeout

**File:** `app/beyo_manager/services/infra/execution/worker_base.py`

Add to `HANDLER_TIMEOUT_SECONDS`:
```python
"send_coordination_email_batch": 300,   # 5 min — SMTP for up to 50 messages
```

The key must exactly match `TaskType.SEND_COORDINATION_EMAIL_BATCH.value` (`"send_coordination_email_batch"`). The default is already 300s, but declaring it explicitly documents the expected runtime and makes it easy to raise the limit if the batch size increases.

The contract invariant: `STALE_IN_PROGRESS_MINUTES (90) > max(HANDLER_TIMEOUT_SECONDS.values()) / 60 (60)`. Adding a 300s timeout does not violate this (300 / 60 = 5 min < 90 min).

---

### Step 9 — Refactor the command

**File:** `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py`

**Remove from the command:**
- The `get_email_provider` import and call
- The `OutboundMessage` construction loop
- The `if outbound_messages: batch_result = ... else: batch_result = ...` block
- The `response_results` loop and `sent_count` / `failed_count` counters
- The `write_audit` call (moves to the handler)
- The `BatchSendResult` import (no longer needed in the command)

**Add to the command:**
```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.send_coordination_email_batch import (
    SendCoordinationEmailBatchPayload,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside the `maybe_begin` block, replace the SMTP section with:**

After the `for task_id in request.task_ids:` loop completes and `rows` + `skipped` are built:

```python
thread_ids = [row["thread"].client_id for row in rows]
if thread_ids:
    await create_instant_task(
        session=ctx.session,
        task_type=TaskType.SEND_COORDINATION_EMAIL_BATCH,
        payload=asdict(SendCoordinationEmailBatchPayload(
            workspace_id=ctx.workspace_id,
            connection_client_id=connection.client_id,
            thread_ids=thread_ids,
        )),
    )
```

The `create_instant_task` call is inside the same `maybe_begin` block as the `EmailThread` and `EmailMessage` flushes — atomic with all DB writes.

**New response shape:**
```python
return {
    "job_id": execution_task.client_id if thread_ids else None,
    "status": "queued" if thread_ids else "nothing_to_send",
    "queued_count": len(rows),
    "skipped_count": len(skipped),
    "skipped": skipped,
}
```

When all tasks are skipped (`thread_ids` is empty), no `ExecutionTask` is created and `job_id` is `None`. The empty batch guard from the previous implementation is preserved — there's no point creating a job with nothing to do.

**Note on `rows` dict shape:** The `rows` list currently stores `{"thread": thread_obj, "message": message_obj, ...}`. After removing the SMTP result loop, the `"thread"` key is the only one needed (for `thread_ids`). The `"message"` and `"to_address"` keys can be removed from the dict since they were only used for building `response_results`. The `"task_client_id"` and `"coordination_client_id"` keys are used for `skipped` tracking — keep them.

---

### Step 10 — Update the email message serializer

**File:** `app/beyo_manager/domain/emails/serializers.py`

Add two fields to `serialize_email_message`:
```python
"send_attempted_at": (
    message.send_attempted_at.isoformat() if message.send_attempted_at else None
),
"send_error": message.send_error,
```

These fields allow the frontend to read per-message delivery status from `GET /email-threads/{thread_id}/messages` without a separate polling endpoint.

---

### Step 11 — Update the handoff document

**File:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704.md`

**Section 1 — update `POST /tasks/customer-coordination/email-batch`:**

Replace the success response example with the new shape:
```json
{
  "job_id": "task_abc123",
  "status": "queued",
  "queued_count": 2,
  "skipped_count": 1,
  "skipped": [
    { "task_client_id": "tsk_3", "reason": "no_customer_email" }
  ]
}
```

Update the response field notes table. Remove `results[]`, `attempted_count`, `sent_count`, `failed_count`. Add:

| Field | Notes |
|---|---|
| `job_id` | `client_id` of the created `ExecutionTask`. `null` when all tasks were skipped (nothing to send). |
| `status` | `"queued"` when at least one email was enqueued. `"nothing_to_send"` when all tasks were skipped. |
| `queued_count` | Number of emails enqueued for delivery (excludes skipped) |
| `skipped_count` | Number of tasks skipped before sending |
| `skipped[].reason` | One of: `task_not_found`, `no_coordination_record`, `no_customer_email` |

Add a note:
> **Delivery results are available after the background job completes.** To check per-message delivery status, call `GET /api/v1/email-threads/{thread_id}/messages` and read `send_attempted_at` and `send_error` on each message. `send_attempted_at` is `null` while the job is still in progress. `send_error` is `null` on success or a string describing the failure.

**Section 5 — update message shape in the `GET /tasks/customer-coordination/threads` response notes** to mention the new fields will be present in the message shape fetched via `/messages`.

---

## Risks and mitigations

- **Risk:** Handler retries re-send emails that were already delivered.
  **Mitigation:** Idempotency guard in Phase 1 — `send_attempted_at IS NULL` filter. A message with `send_attempted_at` set is never re-attempted, regardless of `send_error`.

- **Risk:** SMTP call raises mid-batch, leaving some messages with `send_attempted_at = NULL`.
  **Mitigation:** Phase 3 only runs if Phase 2 returns a `BatchSendResult`. If Phase 2 raises, the worker schedules a retry. On the next attempt, Phase 1 only loads messages where `send_attempted_at IS NULL` — exactly the ones that weren't attempted.

- **Risk:** The `create_instant_task` call inside `maybe_begin` fails after `EmailThread`/`EmailMessage` records have been flushed.
  **Mitigation:** All writes are inside the same `maybe_begin` block — they commit or roll back together. If `create_instant_task` raises, the entire transaction rolls back and no orphaned records remain.

- **Risk:** `thread_ids` payload grows to 50 items — JSON payload is large for Postgres.
  **Mitigation:** 50 thread IDs at ~20 chars each is ~1 KB — well within `execution_payloads.payload` (JSONB, no size limit on row). No concern.

- **Risk:** Worker is killed (SIGTERM) mid-handler after SMTP sends but before Phase 3 writes.
  **Mitigation:** `_rescue_in_flight_task` in `worker_base.py` marks the task `RETRY_SCHEDULED`. On retry, Phase 1's idempotency guard skips already-attempted messages. Phase 3 (result write) re-runs only for unattempted ones. If all messages were attempted before the kill, Phase 1 finds no unattempted messages → early return → Phase 3 never runs → job completes.
  Edge case: messages were attempted but Phase 3 never wrote `send_attempted_at`. On retry, those messages would be re-sent. Mitigation: this window is small (crash between SMTP return and DB write), and a re-send of an already-delivered email is a lower-stakes outcome than a missed send.

---

## Validation plan

- `python3 -m py_compile` on all changed files — no import errors.
- `alembic upgrade head` — migration applies cleanly.
- Confirm `TaskType.SEND_COORDINATION_EMAIL_BATCH` is in `QUEUE_MAP`.
- Confirm handler is in `tasks_worker.py` `HANDLER_MAP`.
- Confirm `HANDLER_TIMEOUT_SECONDS["send_coordination_email_batch"]` is present in `worker_base.py`.
- Confirm command response no longer contains `results[]` or `sent_count`/`failed_count`.
- Confirm `serialize_email_message` output includes `send_attempted_at` and `send_error`.
- Stale task invariant: `STALE_IN_PROGRESS_MINUTES (90) > max(HANDLER_TIMEOUT_SECONDS.values()) / 60 (60)`. ✓

---

## Review log

_No entries yet._

---

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `—`
