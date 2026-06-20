# SUMMARY_PLAN_pin_notification_conditions_corrections_20260620

## Metadata

- Summary ID: `SUMMARY_PLAN_pin_notification_conditions_corrections_20260620`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-20T12:42:01Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_pin_notification_conditions_corrections_20260620.md`
- Related debug plan (optional): _none_

## What was implemented

- Updated `pin_notification.py` to use `maybe_begin(ctx.session)` so it composes with parent transactions.
- Hardened `pin_conditions_match` and `_evaluate_state_condition` so malformed/unknown runtime condition payloads return `False` instead of raising.
- Added a warning log when a condition type is missing from the registry at evaluation time.
- Extracted manager audience lookup into shared `domain/roles/queries.py` and removed the duplicated `_get_managers` implementations.
- Added `cleanup_task_pins(session, task_client_id)` to remove task-rooted pins for tasks, task steps, item upholsteries, and linked cases.
- Wired task pin cleanup into `delete_task.py` inside the existing `maybe_begin` block.
- Expanded local documentation and unit coverage for the corrected behaviors.

## Files changed

- `backend/app/beyo_manager/services/commands/notifications/pin_notification.py`: switched transaction wrapper to `maybe_begin`.
- `backend/app/beyo_manager/domain/notifications/pin_conditions.py`: added warning logging and non-raising state evaluation.
- `backend/app/beyo_manager/domain/roles/queries.py`: added shared manager query helper.
- `backend/app/beyo_manager/domain/tasks/notification_targets.py`: replaced private manager query with shared helper.
- `backend/app/beyo_manager/domain/items/notification_targets.py`: replaced private manager query with shared helper.
- `backend/app/beyo_manager/domain/notifications/pin_cleanup.py`: added task-rooted pin cleanup helper.
- `backend/app/beyo_manager/services/commands/tasks/delete_task.py`: added transactional task pin cleanup call.
- `backend/app/tests/unit/domain/notifications/test_pin_conditions.py`: added malformed-op, warning-log, and cleanup helper coverage.
- `backend/architecture/47_notifications_local.md`: documented supported entity types for state conditions.

## Contract adherence

- `backend/architecture/06_commands.md` and `06_commands_local.md`: pin command and task delete flow now both use `maybe_begin`-compatible transaction handling.
- `backend/architecture/08_domain.md`: runtime pin condition handling stays pure; DB-backed manager lookup and pin cleanup are isolated in domain query/helper modules.
- `backend/architecture/47_notifications.md` and `47_notifications_local.md`: pin cleanup semantics and entity-type support are documented without schema changes.

## Validation evidence

- `.venv/bin/python -m pytest tests/unit/domain/notifications/test_pin_conditions.py tests/unit/services/commands/task_steps/test_transition_step_state.py`: passed, 13 tests.
- `.venv/bin/python -m py_compile beyo_manager/services/commands/notifications/pin_notification.py beyo_manager/domain/notifications/pin_conditions.py beyo_manager/domain/roles/queries.py beyo_manager/domain/tasks/notification_targets.py beyo_manager/domain/items/notification_targets.py beyo_manager/domain/notifications/pin_cleanup.py beyo_manager/services/commands/tasks/delete_task.py`: passed.
- `rg -n "_get_managers" backend/app/beyo_manager`: no results.
- `rg -n "async with ctx\\.session\\.begin\\(\\)" backend/app/beyo_manager/services/commands/notifications/pin_notification.py`: no results.

## Known gaps or deferred items

- `time` condition evaluation remains intentionally unimplemented.
- No new integration test was added for `delete_task` end-to-end cleanup behavior; coverage is unit-level for the helper and existing task-step regression tests.

## Handoff notes (if needed)

- _none_

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pin_notification_conditions_corrections_20260620.md`
