# PLAN_case_push_notifications_20260619

## Metadata

- Plan ID: `PLAN_case_push_notifications_20260619`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T13:18:12Z`
- Related issue/ticket: none

## Goal and intent

- Goal: Queue a `CREATE_NOTIFICATIONS` task from `create_case` and `send_message` so case participants receive VAPID push notifications (and an in-app notification row) when a case is created or when a new message is sent.
- Business/user intent: Participants who are offline or backgrounded have no way to learn about new cases or messages today — socket events are missed and no push fires. This closes that gap so the frontend push system can alert them via the OS.
- Non-goals: Do not modify `notification_worker`, `task_router`, `send_push_notification`, or `create_notifications` — the pipeline is already correct. Do not add push to `edit_message`, `soft_delete_message`, or `add_participant` — only creation and new-message events are in scope.

## Scope

- In scope:
  - `create_case.py` — queue one `CREATE_NOTIFICATIONS` task at the end of the transaction, targeting all participants except the creator.
  - `send_message.py` — queue one `CREATE_NOTIFICATIONS` task at the end of the transaction, targeting all case participants except the sender.
- Out of scope:
  - `create_conversation.py`, `update_case.py`, `update_case_state.py`, `remove_participant.py` — deferred.
  - Frontend service worker implementation.
- Assumptions:
  - `NotificationType.CASE_MESSAGE` and `NotificationType.CASE_PARTICIPANT_ADDED` already exist in `beyo_manager.domain.notifications.enums` — no enum changes needed.
  - `CREATE_NOTIFICATIONS → queue:notifications` is already wired in `task_router.py` and `notification_worker.py` — no worker changes needed.
  - `entity_type="case"` is the correct presence key for `exclude_viewing` — users viewing a case actively see new messages, so they should be excluded from receiving a push.

## Clarifications required

- None — all contracts, enums, payload shapes, and routing are already in place.

## Acceptance criteria

1. Creating a case with an initial message queues a `CREATE_NOTIFICATIONS` task with `notification_type = "case:message"` targeting all participants except the creator, within the same DB transaction.
2. Creating a case without an initial message queues a `CREATE_NOTIFICATIONS` task with `notification_type = "case:participant-added"` targeting all participants except the creator.
3. Creating a case with no other participants besides the creator queues no notification task.
4. Sending a message queues a `CREATE_NOTIFICATIONS` task with `notification_type = "case:message"` targeting all case participants except the sender, within the same DB transaction.
5. Sending a message when the sender is the only participant queues no notification task.
6. `python3 -m py_compile` passes on both changed files.
7. `rg -n "CREATE_NOTIFICATIONS" create_case.py send_message.py` confirms the task type appears in both files.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/11_infra_events.md`: all side-effect tasks must be enqueued inside the transaction (same session) so they commit atomically with the data write.
- `backend/docs/architecture/06_commands.md`: DB side-effect reads (participant list) may happen inside the transaction block; task enqueue must use `create_instant_task(session=ctx.session, ...)`.
- `backend/docs/architecture/56_realtime_layer.md`: notification payloads must carry `entity_type` and `entity_client_id` for frontend routing.

### Local extensions loaded

- none

### Skill selection

- Primary skill: none (standard command mutation pattern — follows `resolve_task.py` and `transition_step_state.py` exactly)
- Router trigger terms: `create_instant_task`, `NotificationPayload`, `CREATE_NOTIFICATIONS`
- Excluded alternatives: none

## Implementation plan

### Step 1 — `create_case.py`

**Add imports** (merge into existing import block — do not create a third `build_event` import line):

```python
from dataclasses import asdict
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.notifications.enums import NotificationType
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with ctx.session.begin():`**, at the very end of the block (after the `if request.initial_message is not None:` block closes), add:

```python
        notify_ids = [uid for uid in participant_ids if uid != ctx.user_id]
        if notify_ids:
            if initial_message is not None:
                notif_type = NotificationType.CASE_MESSAGE
                notif_title = "New case"
                notif_body = (request.initial_message.plain_text or "")[:80]
            else:
                notif_type = NotificationType.CASE_PARTICIPANT_ADDED
                notif_title = "You've been added to a case"
                notif_body = "A new case was created and you are a participant."
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type=notif_type,
                    user_ids=notify_ids,
                    title=notif_title,
                    body=notif_body,
                    entity_type="case",
                    entity_client_id=case.client_id,
                    exclude_viewing=[{"entity_type": "case", "entity_client_id": case.client_id}],
                )),
            )
```

**Note — ORM expiry safety**: `participant_ids` is already a plain Python list captured at line 106. `case.client_id` is accessed here still INSIDE the transaction (before the `with` block closes), so it is not expired. `request.initial_message.plain_text` is a plain Python string from the request dataclass — safe at all times.

**Note — duplicate import**: `create_case.py` currently has two separate `from beyo_manager.services.infra.events.build_event import ...` lines (lines 16 and 18). While fixing this cosmetic issue is not required, Codex may consolidate them into one import line if convenient — it must not break the import of `build_conversation_event`, `build_user_event`, and `build_workspace_event`.

---

### Step 2 — `send_message.py`

**Add imports**:

```python
from dataclasses import asdict
from sqlalchemy import select
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.notification import NotificationPayload
from beyo_manager.domain.notifications.enums import NotificationType
from beyo_manager.models.tables.cases.case_participant import CaseParticipant
from beyo_manager.services.infra.execution.task_factory import create_instant_task
```

**Inside `async with ctx.session.begin():`**, after `write_case_message` returns, add the participant fetch and notification task:

```python
        # Capture scalar values inside transaction — ORM attributes expire on commit
        case_id = conversation.case_id
        conversation_client_id = conversation.client_id

        participant_result = await ctx.session.execute(
            select(CaseParticipant.user_id).where(
                CaseParticipant.case_id == case_id,
                CaseParticipant.user_id != ctx.user_id,
            )
        )
        notify_ids = list(participant_result.scalars().all())
        if notify_ids:
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CREATE_NOTIFICATIONS,
                payload=asdict(NotificationPayload(
                    notification_type=NotificationType.CASE_MESSAGE,
                    user_ids=notify_ids,
                    title="New message",
                    body=(request.plain_text or "")[:80],
                    entity_type="case",
                    entity_client_id=case_id,
                    exclude_viewing=[{"entity_type": "case", "entity_client_id": case_id}],
                )),
            )
```

**After the transaction** (post-commit, where the socket event is currently built), update the `build_conversation_event` call to use the captured `conversation_client_id` instead of `conversation.client_id`, since `conversation` is expired after commit:

```python
    event = build_conversation_event(
        message,
        ConversationMessageEvent.CREATED,
        conversation_id=conversation_client_id,   # ← was conversation.client_id
        workspace_id=ctx.workspace_id,
        extra=conversation_message_extra(seq),
    )
```

**Note — `request.plain_text`**: `parse_send_message_request` returns a dataclass with a `plain_text` field. It is a plain Python string — safe to use both inside and outside the transaction.

---

### No other files change

- `notification_worker.py` — already handles `CREATE_NOTIFICATIONS` and `SEND_PUSH_NOTIFICATION`.
- `task_router.py` — already routes `CREATE_NOTIFICATIONS` to `queue:notifications`.
- `domain/notifications/enums.py` — `CASE_MESSAGE` and `CASE_PARTICIPANT_ADDED` already defined.
- `domain/execution/payloads/notification.py` — `NotificationPayload` already defined.

## Risks and mitigations

- Risk: `case.client_id` ORM expiry if `create_instant_task` is accidentally moved outside the `with` block.
  Mitigation: The plan explicitly places the call INSIDE `async with ctx.session.begin():`. Codex must not move it outside.

- Risk: `conversation.client_id` expiry in `send_message.py` post-commit.
  Mitigation: Plan captures `conversation_client_id` as a plain string inside the transaction and uses it in both `exclude_viewing` and the post-commit `build_conversation_event` call.

- Risk: Notification flood if a case has many participants and high message volume.
  Mitigation: `handle_create_notifications` already respects `exclude_viewing` (users currently viewing the case are silently skipped). No additional rate-limiting is in scope here.

- Risk: `request.plain_text` being empty string or very long.
  Mitigation: `(request.plain_text or "")[:80]` handles both — empty string produces an empty body, long strings are truncated.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/send_message.py`: no output = pass.
- `rg -n "CREATE_NOTIFICATIONS|NotificationType" backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/send_message.py`: confirms task type and enum appear in both files.
- `rg -n "create_instant_task" backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/send_message.py`: confirms enqueue is present in both files.
- `rg -n "conversation_client_id" backend/app/beyo_manager/services/commands/cases/send_message.py`: confirms ORM-safe capture is in place.

## Review log

- `2026-06-19`: Implemented notification task enqueue in `create_case.py` and `send_message.py`, validated both files with `py_compile`, wrote `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_case_push_notifications_20260619.md`, and prepared the archive record.

## Lifecycle transition

- Current state: `archived`
- Next state: none
- Transition owner: `codex`
