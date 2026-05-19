# INTENTION_realtime_event_layer_20260519

## Metadata

- Intention ID: `INTENTION_realtime_event_layer_20260519`
- Status: `active`
- Owner: `David Loorenz`
- Created at (UTC): `2026-05-19T00:00:00Z`
- Last updated at (UTC): `2026-05-19T12:00:00Z`

## Goal

Emit workspace-scoped WebSocket events from all public task and item commands so every connected frontend client stays synchronized in real time, and deliver targeted push notifications for high-signal moments (task state changes, step completions, step assignments, task readiness, upholstery requirement status changes) as a follow-up implementation plan.

## Why this matters

The shop floor environment is multi-user: supervisors, upholsterers, and delivery coordinators all act on the same tasks simultaneously. Without a real-time layer, every user sees stale data until they reload. Missed state changes — a cancelled task, a completed step, an upholstery requirement that just became available — cause coordination failures and re-work. The WebSocket infrastructure (`event_bus`, `ConnectionManager`, Redis pub/sub) already exists and is working for cases and working sections; extending it to tasks and items closes the largest gap in the real-time coverage.

## Success criteria

1. Every public task command (create, update, delete, cancel/resolve/fail, note CRUD, add/remove item from task, add/remove step, add/remove step dependency, mark step time inaccurate) emits at least one `WorkspaceEvent` through `event_bus.dispatch()` after committing.
2. Every public item command (create, update, delete, upholstery CRUD, upholstery requirement state transitions) emits at least one `WorkspaceEvent` after committing.
3. `transition_step_state`, `assign_worker_to_step`, `add_step_dependency`, and `remove_step_dependency` emit `WorkspaceEvent`s after committing; the latter two also emit `task:step-readiness-changed` conditionally when `readiness_status` transitions.
4. `assign_worker_to_step` is updated to return the assignee `user_id` so it can be carried in `extra` of `task:step-assigned`.
5. The frontend receives task and item change events over the existing WebSocket connection without polling, confirmed by manual smoke test.
6. High-signal state events carry `extra: {new_state: "<value>"}` so the frontend can update list views without re-fetching.
7. No command imports `sockets.manager` or `realtime_push` directly — all events flow through `event_bus.dispatch()` only.
8. Push notifications for high-signal events are scoped, designed, and delivered in the follow-up plan (not in the first implementation).

## Scope boundary

- In scope:
  - Hook the following commands to `event_bus.dispatch()`:
    - **Task commands (11):** `create_task`, `update_task`, `delete_task`, `cancel_task`, `resolve_task`, `fail_task`, `add_item_to_task`, `remove_item_from_task`, `create_task_note`, `update_task_note`, `delete_task_note`
    - **Task step commands (6):** `transition_step_state`, `assign_worker_to_step`, `add_task_step`, `remove_task_step`, `add_step_dependency`, `remove_step_dependency`, `mark_step_time_inaccurate`
    - **Item commands (6):** `create_item`, `update_item`, `delete_item`, `create_item_upholstery`, `update_item_upholstery`, `delete_item_upholstery`
    - **Upholstery requirement commands (4):** `mark_requirements_completed`, `mark_requirements_in_use`, `mark_requirements_ordered`, `resolve_requirements_after_stock`
  - Update `assign_worker_to_step` to expose the assignee `user_id` in its return value
  - Define a canonical event name registry for task and item domains
  - Design the push notification scope and user targeting rules (without delivery)
  - Note: `task:step-readiness-changed` is a **conditional** event — emitted only when `readiness_status` actually transitions (before ≠ after), triggered from `add_step_dependency`, `remove_step_dependency`, and `transition_step_state` (via `recalculate_readiness()`)

- Out of scope:
  - Push notification delivery (VAPID/web push) — separate implementation plan
  - Frontend event handler implementation
  - New socket connection infrastructure (already implemented)
  - History record creation (separate plan `PLAN_history_record_hooks_20260519`)
  - Conversation or case events (already handled)

- Non-goals:
  - Per-user room targeting for regular CRUD events (workspace room is correct granularity)
  - Event replay or persistence
  - Event schema versioning beyond `extra` dict

## Event name registry

All event names follow `<domain>:<verb>` (contract `13_sockets.md`).

| Command | Event name | Extra |
|---|---|---|
| `create_task` | `task:created` | `{}` |
| `update_task` | `task:updated` | `{}` |
| `delete_task` | `task:deleted` | `{}` |
| `cancel_task` | `task:state-changed` | `{"new_state": "cancelled"}` |
| `resolve_task` | `task:state-changed` | `{"new_state": "resolved"}` |
| `fail_task` | `task:state-changed` | `{"new_state": "failed"}` |
| `add_item_to_task` | `task:updated` | `{}` |
| `remove_item_from_task` | `task:updated` | `{}` |
| `create_task_note` | `task:updated` | `{}` |
| `update_task_note` | `task:updated` | `{}` |
| `delete_task_note` | `task:updated` | `{}` |
| `transition_step_state` | `task:step-state-changed` | `{"new_state": "<value>"}` |
| `assign_worker_to_step` | `task:step-assigned` | `{"user_id": "<assignee_id>"}` |
| `add_task_step` | `task:updated` | `{}` |
| `remove_task_step` | `task:updated` | `{}` |
| `add_step_dependency` | `task:updated` + `task:step-readiness-changed` (conditional) | `{}` / `{"new_readiness": "<value>"}` |
| `remove_step_dependency` | `task:updated` + `task:step-readiness-changed` (conditional) | `{}` / `{"new_readiness": "<value>"}` |
| `mark_step_time_inaccurate` | `task:updated` | `{}` |
| `create_item` | `item:created` | `{}` |
| `update_item` | `item:updated` | `{}` |
| `delete_item` | `item:deleted` | `{}` |
| `create_item_upholstery` | `item:updated` | `{}` |
| `update_item_upholstery` | `item:updated` | `{}` |
| `delete_item_upholstery` | `item:updated` | `{}` |
| `mark_requirements_completed` | `item:upholstery-requirement-state-changed` | `{"new_state": "completed"}` |
| `mark_requirements_in_use` | `item:upholstery-requirement-state-changed` | `{"new_state": "in_use"}` |
| `mark_requirements_ordered` | `item:upholstery-requirement-state-changed` | `{"new_state": "ordered"}` |
| `resolve_requirements_after_stock` | `item:upholstery-requirement-state-changed` | `{"new_state": "resolved"}` |

## Push notification scope (follow-up plan only)

High-signal events that warrant push notifications and their intended audience:

| Event name | Trigger condition | Audience |
|---|---|---|
| `task:state-changed` | `new_state` in `cancelled`, `resolved`, `failed` | All workspace managers and admins, excluding the actor |
| `task:step-state-changed` | Any state transition | All workspace managers and admins, excluding the actor |
| `task:step-assigned` | Step assignment recorded | The newly assigned worker (user-room push) |
| `task:step-readiness-changed` | `new_readiness == ready` | Users assigned to that step (workspace signal) |
| `item:upholstery-requirement-state-changed` | Any state transition | Upholstery team users |

Push notification delivery uses the existing `push_subscription` + VAPID infrastructure (`services/infra/push/vapid.py`).

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_realtime_event_hooks_20260519` | `backend/docs/architecture/under_construction/implementation/PLAN_realtime_event_hooks_20260519.md` | `under_construction` | Wire `event_bus.dispatch()` into all 28 task and item commands |
| `PLAN_push_notifications_tbd` | `TBD` | `not yet created` | Push notification delivery for high-signal events |

## Progress notes

- `2026-05-19`: Intention created. Event infrastructure confirmed in place (`event_bus`, `realtime_push`, `socket_handler`). Currently used for cases and working sections only. 28 task/item/step commands identified for hookup. Push notification plan deferred.
- `2026-05-19`: Open questions resolved — `task:step-readiness-changed` is a conditional event from `add/remove_step_dependency` and `transition_step_state` (via `_readiness.py`), not a standalone command. Step-state-changed push targets all workspace managers/admins excluding actor for ALL states (not only completed). `assign_worker_to_step` will be updated to return assignee user_id. Scope expanded to include `remove_task_step`, `add_step_dependency`, `remove_step_dependency`, `mark_step_time_inaccurate`.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: All success criteria met — all 28 commands emit events, push notifications delivered, smoke test passes
