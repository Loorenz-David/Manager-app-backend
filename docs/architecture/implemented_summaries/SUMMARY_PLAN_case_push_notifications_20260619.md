# SUMMARY_PLAN_case_push_notifications_20260619

## Metadata

- Summary ID: `SUMMARY_PLAN_case_push_notifications_20260619`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T13:18:12Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_case_push_notifications_20260619.md`
- Related debug plan (optional): none

## What was implemented

- Updated `create_case` to enqueue one `CREATE_NOTIFICATIONS` task inside the transaction for all non-creator participants, choosing `case:message` when an initial message exists and `case:participant-added` otherwise.
- Updated `send_message` to enqueue one `CREATE_NOTIFICATIONS` task inside the transaction for all non-sender participants, using the case presence key so actively viewing users remain excluded by the notification worker.
- Captured `conversation.client_id` inside the `send_message` transaction and reused the scalar post-commit to avoid expired-ORM access when building the socket event.

## Files changed

- `backend/app/beyo_manager/services/commands/cases/create_case.py`: added notification payload/task imports and queued case-create notification tasks atomically with case creation.
- `backend/app/beyo_manager/services/commands/cases/send_message.py`: added participant lookup plus notification task enqueue, and made post-commit conversation event building use a captured scalar id.

## Contract adherence

- `backend/docs/architecture/11_infra_events.md`: notification tasks are enqueued inside the same DB transaction as the domain write.
- `backend/docs/architecture/06_commands.md`: side-effect reads and `create_instant_task(session=ctx.session, ...)` both stay inside the command transaction.
- `backend/docs/architecture/56_realtime_layer.md`: notification payloads include `entity_type="case"` and the case client id for routing and presence exclusion.

## Validation evidence

- `python3 -m py_compile backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/send_message.py`: passed.
- `rg -n "CREATE_NOTIFICATIONS|NotificationType|create_instant_task|conversation_client_id" backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/send_message.py`: confirmed the new task enqueue paths and the ORM-safe scalar capture.

## Known gaps or deferred items

- No live worker or end-to-end push delivery run was performed in this turn.
- `create_conversation.py`, `update_case.py`, `update_case_state.py`, and `remove_participant.py` remain out of scope exactly as defined by the plan.

## Handoff notes (if needed)

- The backend now emits `CREATE_NOTIFICATIONS` tasks for case creation and message sends; frontend push behavior still depends on the existing service-worker/client notification handling.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_case_push_notifications_20260619.md`
