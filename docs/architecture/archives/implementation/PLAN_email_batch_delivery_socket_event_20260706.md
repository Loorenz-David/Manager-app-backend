# PLAN_email_batch_delivery_socket_event_20260706

## Metadata

- Plan ID: `PLAN_email_batch_delivery_socket_event_20260706`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-06T00:00:00Z`
- Last updated at (UTC): `2026-07-06T11:02:07Z`
- Related issue/ticket: `N/A`
- Intention plan: `N/A`

## Goal and intent

- Goal: When the background job that sends customer-coordination (and generic batch) emails finishes attempting delivery, push a **batch-summary socket event** to the user who requested the send, so the frontend can surface the delivery outcome (how many sent / failed) in real time.
- Business/user intent: Today the user gets an optimistic `task_customer_coordination:coordinating` socket event **at enqueue time**, but nothing when the emails are actually sent or fail. The delivery outcome only lives in the DB (`email_message.send_error`) and the audit log (`email.delivery_completed`). This adds a realtime confirmation of the actual send result.
- Non-goals:
  - Do **not** roll back or transition `TaskCustomerCoordination` off `coordinating` on failure. State remains `coordinating` regardless of delivery outcome (explicit product decision).
  - No per-message socket events — one aggregate summary per job only.
  - No change to the enqueue-time `task_customer_coordination:coordinating` event.
  - No new REST endpoint, serializer, or DB column.

## Scope

- In scope:
  - Emit one `UserEvent` (socket) from the background handler `handle_send_email_messages` after the delivery attempt commits, targeting `payload.requested_by_user_id`.
  - Carry the batch summary (`attempted_count`, `sent_count`, `failed_count`, `request_kind`, `message_ids`, `connection_client_id`, `task_client_id`) in the event `extra`.
- Out of scope:
  - `send_customer_coordination_email_batch` command (enqueue path) — unchanged.
  - `send_email_batch` command (enqueue path) — unchanged.
  - Coordination state machine / rollback.
  - Frontend handling of the new event.
- Assumptions:
  - `event_bus.dispatch` is safe to call from the worker process: handlers (`socket_handle`, `audit_handle`, `webhook_handle`) are registered at app startup in `app/beyo_manager/__init__.py`, and an existing task handler (`services/tasks/task_steps/finalize_pending_step_completion.py`) already dispatches from worker context.
  - The socket handler routes `UserEvent` to the `user:{user_id}` room via `push_to_user`, sending payload `{"client_id": ..., **extra}` (confirmed in `services/infra/events/handlers/socket_handler.py`).
  - `payload.requested_by_user_id` is populated for both `request_kind` values (`coordination_batch`, `batch_send`); it may be `None` for future/other callers, so the dispatch must be guarded.

## Clarifications required

- [x] Should the event be per-message or a batch summary? → **Batch summary** (resolved by requester).
- [x] Should `TaskCustomerCoordination` roll back from `coordinating` on failure? → **No** (resolved by requester).
- [x] Target audience: workspace broadcast or the requesting user? → **The requesting user** (`UserEvent` to `requested_by_user_id`); the delivery-outcome toast is only relevant to the person who triggered the send, and the workspace already received the optimistic `coordinating` event at enqueue.

## Acceptance criteria

1. After `handle_send_email_messages` completes a delivery attempt where `payload.requested_by_user_id` is set, exactly one `UserEvent` is dispatched via `event_bus.dispatch`, addressed to `requested_by_user_id`.
2. The event `event_name` is `email_batch:delivery_completed`, `client_id` is the job's `task_client_id`, and `extra` contains `request_kind`, `attempted_count`, `sent_count`, `failed_count`, `message_ids`, `connection_client_id`.
3. The counts in the event equal the counts written to the `email.delivery_completed` audit record in the same run (single source of truth — computed once).
4. When `payload.requested_by_user_id` is `None`, no event is dispatched and no error is raised.
5. `event_bus.dispatch` is called **after** the `session.begin()` block commits (per the event-bus contract "after a transaction commits"), so a socket push never advertises an uncommitted result.
6. A handler exception in dispatch does not fail the job (guaranteed by `event_bus.dispatch`'s per-handler try/except); the job still completes and logs as today.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/.../events`(realtime/event-bus contract, if present): reason — confirm `UserEvent` construction, dispatch-after-commit rule, and event-name conventions.
- `backend/docs/architecture/.../08_tasks`(background task/worker contract, if present): reason — confirm handler signature and session usage for `services/tasks/**` handlers.

> If a formal contract file is not present for events/workers, rely on the observed conventions in `services/infra/events/*` and existing handlers in `services/tasks/**` (relational reads permitted below).

### Local extensions loaded

- `N/A`

### File read intent — pattern vs. relational

Permitted (relational — understanding what exists), already performed during planning:
- `services/tasks/emails/handle_send_email_messages.py` — exact insertion point, existing counts, session structure.
- `services/infra/events/domain_event.py`, `build_event.py`, `event_bus.py`, `realtime_push.py`, `handlers/socket_handler.py` — exact event dataclasses, `build_user_event` signature, dispatch semantics, `UserEvent` routing.
- `domain/execution/payloads/send_email_messages.py` — `SendEmailMessagesPayload` fields (`requested_by_user_id`, `request_kind`, `connection_client_id`, `workspace_id`, `message_ids`).
- `services/tasks/task_steps/finalize_pending_step_completion.py` — precedent for dispatching from a worker handler.

Prohibited (pattern reads): none required — this change reuses the established event helpers; do not read unrelated commands/routers to "learn the pattern."

### Skill selection

- Primary skill: `N/A` (small, localized change to one worker handler).
- Router trigger terms: `socket event, event_bus, background job, email delivery`.
- Excluded alternatives: none.

## Implementation plan

1. In `app/beyo_manager/services/tasks/emails/handle_send_email_messages.py`, add imports:
   - `from beyo_manager.services.infra.events import event_bus`
   - `from beyo_manager.services.infra.events.build_event import build_user_event`
2. Keep the existing count computation (`attempted_count`, `sent_count`, `failed_count`) exactly as-is inside the `async with session.begin()` block. Do **not** recompute — reuse these variables so the socket summary and the audit record are guaranteed identical (Acceptance #3).
3. After the `async with session.begin():` block exits (i.e. the transaction has committed — currently just before the closing `logger.info(...)` at the end of the second `async for session` block), add a guarded dispatch:
   - If `payload.requested_by_user_id` is falsy → skip (Acceptance #4).
   - Otherwise build and dispatch:
     ```python
     await event_bus.dispatch([
         build_user_event(
             user_id=payload.requested_by_user_id,
             event_name="email_batch:delivery_completed",
             client_id=task_client_id,
             extra={
                 "request_kind": payload.request_kind,
                 "connection_client_id": payload.connection_client_id,
                 "attempted_count": attempted_count,
                 "sent_count": sent_count,
                 "failed_count": failed_count,
                 "message_ids": message_ids,
             },
         )
     ])
     ```
4. Ensure the dispatch runs on the same code path as the existing terminal `logger.info(... send_email_messages_done ...)` and before the function `return`, so every completed attempt that has a requester emits exactly one event (Acceptance #1).
5. Leave all early-return paths (missing connection, `nothing_pending`, `provider is None`) untouched — they must not emit a completion event because no delivery attempt occurred.
6. Do not touch the enqueue commands or the coordination transition logic (Non-goals).

## Risks and mitigations

- Risk: Dispatching inside the `session.begin()` block would push a socket event before commit, risking a client reading state that later rolls back.
  Mitigation: Place the dispatch strictly after the `async with session.begin()` block exits (Acceptance #5).
- Risk: `requested_by_user_id` is `None` for some caller → `build_user_event` would target an empty room / malformed event.
  Mitigation: Explicit guard skips dispatch when falsy (Acceptance #4).
- Risk: Socket/webhook handler raises and breaks the job.
  Mitigation: `event_bus.dispatch` already isolates each handler with try/except + logging; no extra handling needed (Acceptance #6). Do not wrap the job body in additional error swallowing.
- Risk: Duplicate events if the job is retried (`max_try=3`).
  Mitigation: The handler only processes messages with `send_attempted_at IS NULL` and returns `nothing_pending` on re-run before reaching the dispatch, so a successful attempt is not re-summarized. No extra idempotency needed. (Note for reviewer: a partial-failure retry could re-attempt only the still-pending subset and emit a second summary reflecting that subset — acceptable, since each summary describes a real attempt.)
- Risk: Frontend has no handler for `email_batch:delivery_completed` yet.
  Mitigation: Out of scope here; unhandled events are silently ignored client-side. Coordinate event-name with frontend before shipping if needed.

## Validation plan

- Static: `ruff`/`flake8` (repo linter) on the changed file: no new warnings; imports used.
- Type check (if configured, e.g. `mypy`/`pyright`) on `handle_send_email_messages.py`: passes.
- Unit/integration test (add or extend under the emails tasks test suite):
  - Arrange a `SendEmailMessagesPayload` with a stub provider returning mixed success/failure and `requested_by_user_id="user_x"`.
  - Assert `event_bus.dispatch` was called once with a `UserEvent` where `user_id=="user_x"`, `event_name=="email_batch:delivery_completed"`, and `extra` counts match the audit `detail` counts.
  - Assert that with `requested_by_user_id=None`, `event_bus.dispatch` is not called.
  - Assert early-return paths (missing connection / nothing pending) do not dispatch.
- Manual (optional): trigger `POST /tasks/customer-coordination/email-batch`, connect a socket in the requesting user's room, confirm one `email_batch:delivery_completed` frame with the expected summary after the worker runs.

## Review log

- `2026-07-06` `owner`: initial draft created from live code trace of `send_customer_coordination_email_batch` → `create_instant_task(SEND_EMAIL_MESSAGES)` → `handle_send_email_messages`.
- `2026-07-06` `codex`: implemented post-commit `email_batch:delivery_completed` user event dispatch, added focused worker tests, and archived the plan.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
