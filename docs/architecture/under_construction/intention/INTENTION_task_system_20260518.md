# INTENTION_task_system_20260518

## Metadata

- Intention ID: `INTENTION_task_system_20260518`
- Status: `active`
- Owner: `David Loorenz`
- Created at (UTC): `2026-05-18T00:00:00Z`
- Last updated at (UTC): `2026-05-18T02:00:00Z`

---

## Goal

Deliver the complete task management system — the operational core of the application — through which tasks are created, assigned to working sections, executed by workers through step-level state transitions with real-time time recording, and tracked via aggregated analytics metrics across users and sections.

---

## Why this matters

Every value-creating operation in the workshop flows through the task system: receiving a return, processing a pre-order, executing an internal repair. Without tasks, workers have no work orders; without step state transitions, managers have no visibility into progress; without analytics, there is no data for capacity planning, bottleneck detection, or worker performance evaluation. All other domain systems (customers, items, upholstery, working sections) are inputs to or consumers of the task system — it is the application's reason to exist.

---

## Success criteria

1. A seller, manager, or admin can create a task (`return`, `pre_order`, `internal`) atomically: linking a customer (optional), linking or creating the primary item via `find_or_create_item`, and if item issues or item upholstery are present in the payload, creating them in the same transaction via the existing session-level helpers. A seller-created task is always unassigned (`pending`).
2. A manager can assign an unassigned task to a working section; the task transitions from `pending` → `assigned` and task steps are created for each working section in the assignment.
3. A manager can assign a working section to a task that already has other sections assigned; task steps are added for the new section without disrupting existing steps.
4. A manager can unassign a working section from a task; its associated task steps are removed or marked cancelled, and step dependencies referencing those steps are cleaned up.
5. A worker can transition task step states (`pending → working`, `working ↔ paused`, `working → ended_shift`, `working → completed`, etc.) and each transition atomically: closes the current `StepStateRecord` (`exited_at`) and opens a new one (`entered_at`) within the same transaction. Side effect on task state: when any step first transitions to `working` and the task is in `assigned` state, the task transitions to `working`.
6. When all task steps reach a terminal state (`completed`, `skipped`, `failed`, `cancelled`), the task automatically transitions to `ready`. `SKIPPED` is set by CMD-10 (remove step) — removed steps are not simply excluded from the count, they are explicitly terminated so every step always has a final state.
7. A manager, seller, or admin can resolve a task from any non-terminal state; `resolved` is a terminal state.
8. Step `readiness_status` is correctly driven by the dependency graph: `blocked` when any prerequisite is incomplete, `partial` when some prerequisites are done, `ready` when all are done (or there are none); completing a prerequisite step triggers recalculation of all dependent steps within the same transaction.
9. `readiness_status` is controlled exclusively by the dependency system — no external command, domain event, or other system can set or override it. The frontend is responsible for surfacing upholstery and other domain-specific blocking conditions to the user independently. This keeps working sections as isolated instances with no coupling to upholstery or any other domain logic.
10. Step transitions publish an outbox event; the background worker consumes it and applies the aggregation rules: `WORKING` record close → `total_working_seconds` + `total_working_count` + `total_cost_minor` (working time is on-the-clock); `PAUSED` record close → `total_pause_seconds` + `total_pause_count` + `total_cost_minor` (pause is also on-the-clock); `ENDED_SHIFT` record close → `total_ended_shift_seconds` + `total_ended_shift_count` (shift end is not costed); step `COMPLETED` with issues → `total_issues_count` + `total_issues_resolved_count`. All four stats tables receive each applicable increment.
11. When a step's time record is marked as inaccurate (`recorded_time_marked_wrong = true`), that record is excluded from metrics; the system substitutes the section-average for similar steps and records `taken_from_average = true` on that row.
12. The task list query returns the compressed payload (task + item + item_upholstery + requirements + task_steps) and correctly applies all filters (working section, task state, step state, step readiness, priority, task type, return_source, date ranges, upholstery requirement state, deleted_at) plus custom `order_by` and pagination.
13. The task detail query returns the full uncompressed payload for a single task: all task fields + linked item (with all item fields) + item_upholstery (with all fields) + upholstery requirements (all fields, not summarized) + all task steps (with full step fields: state, readiness_status, dependency counts, assigned worker, working section, timestamps). This is the expanded counterpart to the compressed list shape — no field compression or summarization applied.
14. Import smoke test passes and a bash test suite covering the core flows (create → assign → step transitions → ready → resolve) passes.

---

## Scope boundary

### In scope

**Task commands (CMD):**
- Create task: unassigned (seller/manager/admin) and assigned (manager/admin); notes, item issues, and item upholstery may be included in the creation payload
- Assign / unassign working section to/from a task (manager)
- Update task fields (title, priority, ready_by_at, scheduled dates, return_source, return_method, fulfillment_method, additional_details) — manager/seller/admin
- Soft-delete task
- Add / remove item from task (manager) — using `task_items` with `role` and `removed_at`
- Resolve, cancel, fail task
- Create / update / soft-delete task notes — all roles; notes have `note_type` and `content` (JSON)

**Task step commands (CMD):**
- Add task step to an existing task (manager)
- Remove task step from an existing task (manager)
- Assign worker to step; record in `task_step_assignment_records`
- Transition step state: all valid transitions in `TaskStepStateEnum` — with atomic `StepStateRecord` close/open
- Mark step time as inaccurate (`recorded_time_marked_wrong`); substitute from average (`taken_from_average`)

**Dependency commands (CMD):**
- Add dependency edge between steps (manager)
- Remove dependency edge (manager)
- Dependency-driven `readiness_status` recalculation on prerequisite completion — the only mechanism that changes readiness

**Analytics (async):**
- Outbox event emitted on every step state transition close (exited_at set)
- Background worker updating `UserDailyWorkStats`, `UserLifetimeStats`, `UserSectionDailyWorkStats`, `WorkingSectionDailyWorkStats`
- Average-time substitution for inaccurate records

**Queries (QUERY):**
- QUERY-1: Task list — compressed shape, full filter set, custom ordering, offset pagination
- QUERY-2: Task detail — single task full payload

**Router:**
- `/api/v1/tasks` with role guards (seller/manager/admin for create; manager for assign/update; worker for step transitions; all for read)

### Out of scope

- `task_history_records` and `task_events` lineage writes — deferred to a follow-up plan (the append-only lineage tables exist but are not populated in this intention)
- WebSocket / real-time push delivery of task state changes
- `STALLED` state trigger — excluded until the trigger mechanism is designed (see Open questions)
- Analytics materialized views, reporting dashboards, or aggregated reporting endpoints
- AI-assisted step recommendations
- Task-level SLA tracking and escalation
- Alembic migrations — all required tables already exist in the schema, with one exception: `task_notes` needs `updated_at` (DateTime, nullable) and `updated_by_id` (FK → users, nullable) added before CMD-17 is implemented

### Non-goals

- Replacing or rewriting existing commands for customers, items, upholstery, or working sections
- Multi-tenant isolation design — already enforced at the model/query layer via `workspace_id`
- External API authentication for third-party resolution triggers — covered by the standard JWT role guard on the resolve command

---

## Confirmed command map

This table is the authoritative reference for all implementation plans in this intention. Each implementation plan will cover a subset of these commands; plans link back here by CMD/QUERY/WORKER number.

> **Prerequisite — `find_or_create_item` (items domain):** CMD-1 depends on a `find_or_create_item` command that does not yet exist in the items domain. It follows the same pattern as `find_or_create_customer`: lookup by `article_number OR sku` (whichever is present in the payload); if found, update item fields with the incoming payload; if not found, create the item; return `{item_id, was_created}`. This command must be implemented and tested before the first task system implementation plan that includes CMD-1.

### Task commands

| ID | Command | File | Caller | Key behavior |
|----|---------|------|--------|---|
| CMD-1 | `create_task` | `commands/tasks/create_task.py` | seller / manager / admin | Atomic (single `maybe_begin`): creates Task + optionally links customer via `find_or_create_customer` (populates contact snapshot fields) + optionally links or creates primary item via `find_or_create_item` (lookup by `article_number OR sku`; if found: update item fields with incoming payload; if not found: create item) + links item to task via `task_items` (PRIMARY role) + if item issues present in payload: creates each via `_create_item_issue_in_session` + if item upholstery present in payload: creates via `_create_item_upholstery_in_session` + if notes present in payload: creates each via `_create_task_note_in_session` (CMD-16 helper). All within the same session, same transaction. Seller: state always `pending`. Manager: optional first section assignment on creation → state `assigned`. `task_scalar_id` = `SELECT COALESCE(MAX(...), 0) + 1` inside same transaction. |
| CMD-2 | `update_task` | `commands/tasks/update_task.py` | manager / seller / admin | `model_fields_set` semantics. Writable fields: `title`, `summary`, `priority`, `ready_by_at`, `scheduled_start_at`, `scheduled_end_at`, `return_source`, `return_method`, `fulfillment_method`, `item_location`, `additional_details`. |
| CMD-3 | `delete_task` | `commands/tasks/delete_task.py` | manager / admin | Soft-delete: `is_deleted = true`, `deleted_at`. |
| CMD-4 | `resolve_task` | `commands/tasks/resolve_task.py` | manager / seller / admin | Terminal → `resolved`; sets `closed_at`. Valid from any non-terminal state. |
| CMD-5 | `cancel_task` | `commands/tasks/cancel_task.py` | manager / admin | Terminal → `cancelled`; sets `closed_at`. |
| CMD-6 | `fail_task` | `commands/tasks/fail_task.py` | manager / admin | Terminal → `failed`; sets `closed_at`. |

### Task item commands

| ID | Command | File | Caller | Key behavior |
|----|---------|------|--------|---|
| CMD-7 | `add_item_to_task` | `commands/tasks/add_item_to_task.py` | manager | Inserts `task_items` row with `role` (PRIMARY or RELATED); enforces partial unique: one active PRIMARY per task. |
| CMD-8 | `remove_item_from_task` | `commands/tasks/remove_item_from_task.py` | manager | Sets `removed_at` + `removed_by_id` on the `task_items` row (never hard-delete). |

### Task step commands

| ID | Command | File | Caller | Key behavior |
|----|---------|------|--------|---|
| CMD-9 | `add_task_step` | `commands/task_steps/add_task_step.py` | manager | Creates `TaskStep` for a `working_section_id`; populates `working_section_name_snapshot`; `readiness_status` defaults to `READY` (model default — steps with no dependencies start ready); creates initial `StepStateRecord` (`PENDING`, `entered_at = now`). Side effect: task `pending` → `assigned` on first step added. |
| CMD-10 | `remove_task_step` | `commands/task_steps/remove_task_step.py` | manager | Sets step state to `SKIPPED` (terminal) + closes the current open `StepStateRecord` (`exited_at`) + soft-removes step (`is_deleted`, `closed_at`); soft-removes all active dependency edges that reference it; calls `_recalculate_readiness` on steps that depended on the removed step; checks if all remaining steps are now terminal → if so, task → `ready`; if last step removed → task → `pending`. |
| CMD-11 | `assign_worker_to_step` | `commands/task_steps/assign_worker_to_step.py` | manager | Closes active `task_step_assignment_records` row (`removed_at`); inserts new row; sets `assigned_worker_id` + `assigned_worker_display_name_snapshot` on step. |
| CMD-12 | `transition_step_state` | `commands/task_steps/transition_step_state.py` | worker / manager / admin | Main state machine driver. Atomically: closes current `StepStateRecord` (`exited_at = now`) + opens new `StepStateRecord` (`entered_at = now`, new state). Task state side effects: if new state is `WORKING` and task is `assigned` → task → `working`; if new state is `COMPLETED` → call `_recalculate_readiness` on all dependent steps; if all task steps are now terminal → task → `ready`. Publishes outbox event for analytics worker. |
| CMD-13 | `mark_step_time_inaccurate` | `commands/task_steps/mark_step_time_inaccurate.py` | worker / manager | Sets `recorded_time_marked_wrong = true` on the specified `StepStateRecord`; sets `taken_from_average = true` on the `TaskStep`; analytics worker excludes this record and substitutes section-average. |

### Task note commands

| ID | Command | File | Caller | Key behavior |
|----|---------|------|--------|---|
| CMD-16 | `create_task_note` | `commands/tasks/create_task_note.py` | all roles | Creates a `TaskNote` with `note_type` and `content` (JSON). Exposes `_create_task_note_in_session(session, workspace_id, task_id, note_type, content, user_id)` as a session-level helper so CMD-1 can call it for each note in the creation payload without opening a nested transaction. |
| CMD-17 | `update_task_note` | `commands/tasks/update_task_note.py` | all roles | Updates `content` and/or `note_type` on an existing non-deleted note. Sets `updated_at` and `updated_by_id`. **Requires migration:** `updated_at` (DateTime, nullable) and `updated_by_id` (FK → users, nullable) must be added to the `task_notes` table before this command is implemented. |
| CMD-18 | `delete_task_note` | `commands/tasks/delete_task_note.py` | all roles | Soft-delete: `is_deleted = true`, `deleted_at`, `deleted_by_id`. |

### Dependency commands

| ID | Command | File | Caller | Key behavior |
|----|---------|------|--------|---|
| CMD-14 | `add_step_dependency` | `commands/task_steps/add_step_dependency.py` | manager | Inserts `task_step_dependencies` edge; increments `total_dependencies` on dependent step; calls `_recalculate_readiness` on dependent step. |
| CMD-15 | `remove_step_dependency` | `commands/task_steps/remove_step_dependency.py` | manager | Sets `removed_at` on edge; decrements `total_dependencies`; calls `_recalculate_readiness` on dependent step. |

> **Shared helper:** `_recalculate_readiness(step, session)` — private module-level function, not a command. Used by CMD-10, CMD-12, CMD-14, CMD-15. Logic: `total_dependencies == 0` → `READY`; `completed_dependencies == total_dependencies` → `READY`; `completed_dependencies == 0 AND total_dependencies > 0` → `BLOCKED`; `0 < completed_dependencies < total_dependencies` → `PARTIAL`. Dependency state is the sole input — no external conditions.

### Queries

| ID | Query | File | Caller | Key behavior |
|----|-------|------|--------|---|
| QUERY-1 | `list_tasks` | `queries/tasks/tasks.py` | all roles | Compressed shape; full filter set; custom `order_by`; offset pagination. |
| QUERY-2 | `get_task` | `queries/tasks/tasks.py` | all roles | Full uncompressed payload: task + item + item_upholstery + requirements + task steps. |

### Analytics worker

| ID | Handler | File | Trigger |
|----|---------|------|---------|
| WORKER-1 | `process_step_transition` | `workers/analytics/step_transition.py` | Outbox event from CMD-12 (emitted when a `StepStateRecord` is closed — `exited_at` set) |

**WORKER-1 targets:** all four stats tables receive every applicable increment in one worker execution:
`UserDailyWorkStats`, `UserLifetimeStats`, `UserSectionDailyWorkStats`, `WorkingSectionDailyWorkStats`

**Aggregation rules — keyed by the state of the record being closed:**

| Trigger | Field | Delta | Data source |
|---------|-------|-------|-------------|
| Closing a `WORKING` record | `total_working_seconds` | `exited_at - entered_at` (seconds) | `StepStateRecord` |
| Closing a `WORKING` record | `total_working_count` | `+1` | — |
| Closing a `WORKING` record | `total_cost_minor` | `(interval_seconds / 3600) × salary_per_hour_before_tax` | `UserWorkProfile.salary_per_hour_before_tax` for the assigned worker |
| Closing a `PAUSED` record | `total_pause_seconds` | `exited_at - entered_at` (seconds) | `StepStateRecord` |
| Closing a `PAUSED` record | `total_pause_count` | `+1` | — |
| Closing a `PAUSED` record | `total_cost_minor` | `(interval_seconds / 3600) × salary_per_hour_before_tax` | `UserWorkProfile.salary_per_hour_before_tax` for the assigned worker — pause is on-the-clock time |
| Closing an `ENDED_SHIFT` record | `total_ended_shift_seconds` | `exited_at - entered_at` (seconds) | `StepStateRecord` |
| Closing an `ENDED_SHIFT` record | `total_ended_shift_count` | `+1` | — |
| Step transitions to `COMPLETED` AND item has issues | `total_issues_count` | `+1` | `TaskStep → TaskItem → Item → item_issues` |
| Step transitions to `COMPLETED` AND item has resolved issues | `total_issues_resolved_count` | `+1` | same path (currently behaves identically to `total_issues_count`) |

**Exclusion rule:** if `StepStateRecord.recorded_time_marked_wrong = true`, the actual duration is excluded from all `*_seconds` and `*_count` increments; the section-average for similar steps is substituted instead (`taken_from_average = true` recorded on the `TaskStep`).

**`total_cost_minor` expansion note:** cost is accumulated incrementally on every `WORKING` and `PAUSED` record close (both states are on-the-clock). `ENDED_SHIFT` is not costed — it represents time outside the work session. A second cost component will be added later: a static cost per step completion defined on the working section (e.g., material costs, overhead). The worker should be structured so new cost components are appended to the cost-accumulation logic, not rewriting the existing calculation.

**Dispatch design:** each rule above maps to a discrete increment function. Adding a new stat or a new trigger should require only adding a new function to the dispatch, not modifying existing ones.

---

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| — | — | — | No implementation plans created yet |

---

## Progress notes

- `2026-05-18`: Intention plan created. Scope confirmed as one full-system intention. Analytics async worker in scope. `STALLED` trigger deferred. Lineage tables (`task_history_records`, `task_events`) deferred to follow-up.
- `2026-05-18`: Command map confirmed (CMD-1 through CMD-15, QUERY-1 to QUERY-2, WORKER-1). Key decisions locked: `create_task` atomic (customer + item + issues in one transaction); three separate terminal commands (resolve/cancel/fail); `task_scalar_id` derived from table. All open questions resolved except `STALLED` trigger and working-section side-effect expansion interface.
- `2026-05-18`: Architectural decision — `readiness_status` is now dependency-only. CMD-16 (`set_step_readiness_external`) removed entirely. `_recalculate_readiness` evaluates `completed_dependencies vs total_dependencies` with no external inputs. Upholstery blocking conditions are handled by the frontend using requirement state data from the query payloads. Working sections remain fully decoupled from upholstery and other domain logic.
- `2026-05-18`: CMD-1 corrected — item linking uses `find_or_create_item` pattern (lookup by `article_number OR sku`; update fields if found, create if not found). Item issues and upholstery are NOT part of `create_task`; they are added via existing item domain commands after task creation. `find_or_create_item` identified as a prerequisite command to be built in the items domain before the first task implementation plan.
- `2026-05-18`: WORKER-1 analytics rules formalized — six time/count increment rules (one per closing state × seconds + count), two issues rules (count + resolved at step COMPLETED), one cost rule (worker salary from `UserWorkProfile.salary_per_hour_before_tax`). Static station cost deferred as a second cost component. Dispatch design noted: each rule is a discrete function; new stats added by appending, not rewriting.
- `2026-05-18`: Task notes added — CMD-16 `create_task_note`, CMD-17 `update_task_note`, CMD-18 `delete_task_note` (soft-delete). CMD-1 updated to call `_create_task_note_in_session` for each note in the creation payload. Model gap flagged: `TaskNote` has no `updated_at`/`updated_by_id` — update tracking requires a future migration if needed.

---

## Open questions

- **`STALLED` state trigger** — the mechanism that moves a task from `working` to `stalled` has not been designed. Impact: `STALLED` cannot be implemented as a triggerable transition until this is resolved. Current plan: leave `STALLED` in the enum, do not implement its trigger command; add it to a follow-up implementation plan when the trigger is decided.

- **Working-section side-effect expansion mechanism** — when a step transitions to `working` or `paused`, section-specific side effects may need to fire. The interface (registry, decorator, dispatch table) is not yet defined. Impact: step transition commands can be built without this; the expansion point should be stubbed and clearly marked in the command implementation for later extension. **Note for future implementation:** the notification layer (WebSocket push) and event socket layer are intentionally deferred — they will be designed in a later implementation plan after the core step transition commands are stable.

- **Upholstery readiness integration interface** — ~~removed~~: `readiness_status` is now dependency-only. Upholstery blocking conditions (e.g., `needs_ordering`, `missing_quantity`) are surfaced by the frontend using the upholstery requirement state returned in the task query payloads. The backend does not couple working section readiness to upholstery domain state.

- **`task_scalar_id` generation strategy** — ~~resolved~~: the scalar ID is derived from the table itself (e.g., `SELECT COALESCE(MAX(task_scalar_id), 0) + 1 FROM tasks WHERE workspace_id = :workspace_id` executed within the same transaction as the task insert, holding a row-level or advisory lock to prevent collisions under concurrent creates). No external sequence required.

---

## Lifecycle transition

- Current status: `active`
- Next status: `achieved` when all 14 success criteria are confirmed met and all linked implementation plans are archived
- Transition trigger: full bash test suite passes for all listed flows; analytics worker correctly updates all 4 stats tables end-to-end
