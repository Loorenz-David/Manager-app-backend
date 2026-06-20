# SUMMARY_PLAN_pin_notification_conditions_20260619

## Metadata

- Summary ID: `SUMMARY_PLAN_pin_notification_conditions_20260619`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T20:15:42Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_pin_notification_conditions_20260619.md`
- Related debug plan (optional): _none_

## What was implemented

- Added `NotificationPin.conditions` and `NotificationPin.fire_once`, with Alembic migration `a4d9f2c1b8e7`.
- Added a registry-based pin condition module with `state` support and a validation-only `time` stub.
- Added condition-aware pinned subscriber resolution that deletes matching `fire_once` pins in the same transaction that enqueues notifications.
- Added domain-owned notification target resolvers for task steps, tasks, and item upholstery requirements.
- Rewired task-step, task, item, upholstery order, and deferred step completion notification sources through the new resolvers.
- Updated `pin_notification` to parse requests, validate `EntityType`, validate conditions, and overwrite `conditions`/`fire_once` on re-pin.
- Deleted the command-layer task and item notification helper modules.
- Documented local notification condition and `fire_once` behavior in `47_notifications_local.md`.

## Files changed

- `backend/app/beyo_manager/models/tables/notifications/notification_pin.py`: added `conditions` and `fire_once`.
- `backend/app/migrations/versions/a4d9f2c1b8e7_add_notification_pin_conditions.py`: added reversible schema migration.
- `backend/app/beyo_manager/domain/notifications/pin_conditions.py`: added condition registry, validator, and matcher.
- `backend/app/beyo_manager/domain/notifications/pinned_subscribers.py`: added condition-aware pin resolver and fire-once delete handling.
- `backend/app/beyo_manager/domain/task_steps/notification_targets.py`: added task-step notification target resolver.
- `backend/app/beyo_manager/domain/tasks/notification_targets.py`: added task notification target resolver.
- `backend/app/beyo_manager/domain/items/notification_targets.py`: added upholstery requirement notification target resolver.
- `backend/app/beyo_manager/services/commands/notifications/requests.py`: added pin request parser.
- `backend/app/beyo_manager/services/commands/notifications/pin_notification.py`: added validation and last-write-wins re-pin updates.
- `backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py`: routed step pins through the task-step resolver.
- `backend/app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py`: routed deferred completion pins through the task-step resolver.
- `backend/app/beyo_manager/services/commands/tasks/cancel_task.py`: routed task notifications through the domain resolver.
- `backend/app/beyo_manager/services/commands/tasks/fail_task.py`: routed task notifications through the domain resolver.
- `backend/app/beyo_manager/services/commands/tasks/resolve_task.py`: routed task notifications through the domain resolver.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py`: routed upholstery notifications with `completed` event facts.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py`: routed upholstery notifications with `in_use` event facts.
- `backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py`: routed upholstery notifications with `ordered` event facts.
- `backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py`: routed upholstery notifications with `available` event facts.
- `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py`: routed allocated requirement notifications with `ordered` event facts.
- `backend/app/beyo_manager/services/commands/upholstery/receive_upholstery_order.py`: routed allocated requirement notifications with `available` event facts.
- `backend/app/beyo_manager/services/commands/tasks/_notification_helpers.py`: deleted.
- `backend/app/beyo_manager/services/commands/items/_notification_helpers.py`: deleted.
- `backend/app/tests/unit/domain/notifications/test_pin_conditions.py`: added matcher, validator, time stub, and fire-once resolver tests.
- `backend/architecture/47_notifications_local.md`: documented local condition and fire-once semantics.

## Contract adherence

- `backend/architecture/03_models.md`: model change uses SQLAlchemy mapped columns with no business logic.
- `backend/architecture/06_commands.md` and `06_commands_local.md`: command writes remain inside the existing transaction boundaries.
- `backend/architecture/08_domain.md`: condition validation and matching are pure; DB-backed audience collection is isolated in notification target resolver modules.
- `backend/architecture/30_migrations.md`: schema change is represented by a reversible Alembic migration.
- `backend/architecture/47_notifications.md` and `47_notifications_local.md`: pins remain an independent notification source; local condition/fire-once semantics are documented.
- `backend/architecture/48_presence.md`: new pin entity strings are added to `EntityType`.

## Validation evidence

- `.venv/bin/python -m pytest tests/unit/domain/notifications/test_pin_conditions.py`: passed, 7 tests.
- `.venv/bin/python -m pytest tests/unit/services/commands/task_steps/test_transition_step_state.py tests/unit/domain/notifications/test_pin_conditions.py`: passed, 9 tests.
- `.venv/bin/python -m py_compile <touched notification/domain/command modules>`: passed.
- `rg -n "_notification_helpers|_resolve_task_audience|_resolve_upholstery_audience" backend/app/beyo_manager backend/app/tests`: no stale references.
- `.venv/bin/alembic heads`: returned single head `a4d9f2c1b8e7`.
- `.venv/bin/alembic upgrade head`: applied `6787eabf4c32 -> a4d9f2c1b8e7`.
- `.venv/bin/alembic downgrade -1`: reverted `a4d9f2c1b8e7 -> 6787eabf4c32`.
- `.venv/bin/alembic upgrade head`: restored local DB to `a4d9f2c1b8e7`.

## Known gaps or deferred items

- No frontend UI was added for composing conditions.
- The `time` condition is intentionally validation-only and raises on evaluation.
- Full end-to-end push delivery was not exercised; validation focused on condition logic, command wiring, and migration reversibility.

## Handoff notes (if needed)

- Frontend callers may send optional `conditions` and `fire_once` to the existing pin endpoint. Omitted or `null` conditions keep the old "notify on every event" behavior.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pin_notification_conditions_20260619.md`
