# SUMMARY_PLAN_notification_message_enrichment_20260621

## Metadata

- Summary ID: `SUMMARY_PLAN_notification_message_enrichment_20260621`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-21T15:00:49Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_notification_message_enrichment_20260621.md`
- Related debug plan (optional): none

## What was implemented

- Added `domain/tasks/notification_labels.py` with read-only helpers to resolve a task's primary-item label and to fetch `(task_scalar_id, item_label)` in one query for step assignment notifications.
- Replaced generic task, task-step, upholstery, and case notification copy with context-aware messages that include task number, item identifier, actor name, upholstery context, or affected-item counts depending on the command.
- Added a new task-level `CREATE_NOTIFICATIONS` enqueue path in `transition_step_state.py` so indirect task state transitions caused by step transitions also notify offline subscribers.

## Files changed

- `backend/app/beyo_manager/domain/tasks/notification_labels.py`: added pure SELECT helpers for task/item notification labels.
- `backend/app/beyo_manager/services/commands/tasks/resolve_task.py`: enriched resolved-task notification title/body with task number, item label, and actor.
- `backend/app/beyo_manager/services/commands/tasks/cancel_task.py`: enriched cancelled-task notification title/body with task number, item label, and actor.
- `backend/app/beyo_manager/services/commands/tasks/fail_task.py`: enriched failed-task notification title/body with task number, item label, and actor.
- `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`: enriched step-state notification copy and added task-state notifications when a step transition changes the parent task state.
- `backend/app/beyo_manager/services/commands/task_steps/assign_worker_to_step.py`: enriched assigned-step notification copy with section name, parent task number, and item label.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py`: added upholstery name and requirement count to completion notifications.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py`: added upholstery name and requirement count to in-use notifications.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py`: added affected-item counts to ordered notifications.
- `backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py`: added affected-item counts to resolved-from-stock notifications.
- `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py`: added affected-item counts to ordered notifications emitted during order creation.
- `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py`: added affected-item counts to available-for-production notifications emitted during order receipt.
- `backend/app/beyo_manager/services/commands/cases/send_message.py`: changed case-message notification titles to include sender name and optional case type label.

## Contract adherence

- `backend/architecture/06_commands.md`: all new reads and notification task enqueues remain inside the owning command transaction.
- `backend/architecture/06_commands_local.md`: the updated item and task-step commands continue to use `maybe_begin` correctly with no manual commit or rollback.
- `backend/architecture/16_background_jobs.md`: all notification changes still enqueue `CREATE_NOTIFICATIONS` tasks with immutable `NotificationPayload` snapshots.

## Validation evidence

- `python3 -m py_compile backend/app/beyo_manager/domain/tasks/notification_labels.py backend/app/beyo_manager/services/commands/tasks/resolve_task.py backend/app/beyo_manager/services/commands/tasks/cancel_task.py backend/app/beyo_manager/services/commands/tasks/fail_task.py backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py backend/app/beyo_manager/services/commands/task_steps/assign_worker_to_step.py backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py backend/app/beyo_manager/services/commands/cases/send_message.py`: passed.
- `git diff ...`: not runnable in this workspace because `.git` is not available at the current working root.

## Known gaps or deferred items

- No end-to-end worker delivery or notification rendering test was run in this turn.
- Notification handlers, push delivery plumbing, and audience-resolution logic were intentionally left unchanged per plan scope.

## Handoff notes (if needed)

- none

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_notification_message_enrichment_20260621.md`
