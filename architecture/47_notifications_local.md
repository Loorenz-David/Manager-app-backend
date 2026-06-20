# Notifications - Local Extensions
> Extends: 47_notifications.md

<!-- Scope: notification channels, templates, preferences -->
<!-- Add app-specific fields, overrides, and decisions below. -->
<!-- Do NOT modify the canonical 47_notifications.md directly. -->

## Added Fields

- `NotificationPin.conditions: JSONB | NULL` - optional list of registry-driven
  predicates that filter whether a pin fires for a specific event. `NULL` and
  `[]` both mean "match all", preserving existing pin behavior.
- `NotificationPin.fire_once: bool` - when `true`, a matching pin is deleted in
  the same transaction that enqueues `CREATE_NOTIFICATIONS`.

## Overridden Behaviour

- Pin resolution for tasks, task steps, and item upholstery requirements is
  condition-aware. Unconditional audience sources such as active managers and a
  task creator are not filtered by pin conditions.

## Local Decisions

- Pin conditions are registry-driven. The shipped condition type is `state`;
  `time` is registered for validation shape only and is not evaluated yet.
- State conditions are validated against a per-entity-type enum registry. They
  are currently supported for TASK, TASK_STEP, and ITEM_UPHOLSTERY only.
  Attempting to set a state condition on CASE, CONVERSATION, or other entity
  types raises a ValidationError at pin creation time.
- `fire_once` means "stop watching after a matching event is enqueued." It does
  not wait for browser push delivery. The in-app `Notification` row remains the
  durable delivery record.
- Re-pinning the same `(user_id, entity_type, entity_client_id)` overwrites
  `conditions` and `fire_once` while preserving the unique pin identity.
