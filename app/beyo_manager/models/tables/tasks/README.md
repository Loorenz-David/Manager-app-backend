# Tasks Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `task.py` | `tasks` | `tsk` | Core task aggregate (operational work order) |
| `task_history_record.py` | `task_history_records` | `thr` | Immutable task lifecycle change lineage |
| `task_event.py` | `task_events` | `tev` | Domain-significant operational event lineage |
| `task_note.py` | `task_notes` | `tno` | User and system notes attached to tasks |
| `task_item.py` | `task_items` | `tim` | Bridge: items attached to a task (with roles) |
| `task_step.py` | `task_steps` | `tsp` | Ordered execution steps within a task |
| `step_state_record.py` | `step_state_records` | `ssr` | Immutable step lifecycle transition intervals |
| `task_step_dependency.py` | `task_step_dependencies` | `tsd` | Directed prerequisite graph between steps |
| `task_step_assignment_record.py` | `task_step_assignment_records` | `tsar` | Worker assignment history per step |

---

## Truth hierarchy

When reconstructing past state, use this order of authority:

1. **Append-only lineage tables** (authoritative):
   - `task_history_records` — task lifecycle progression
   - `task_events` — domain-significant operational events
   - `step_state_records` — step lifecycle intervals and transitions
   - `task_step_assignment_records` — assignment intervals and removal history
   - `task_step_dependencies` — durable prerequisite edges
   - `task_items` — durable task-to-item coordination

2. **Operational projections** (rebuildable, not authoritative):
   - `tasks` scalar columns (latest pointers, counters, snapshots)
   - `task_steps` scalar columns (aggregates, latest pointer, readiness, counters)

**Latest pointer fields (`latest_history_record_id`, `latest_event_id`, `latest_state_record_id`) are convenience shortcuts only.** Replay-safe reconstruction must always traverse lineage, not rely on latest pointers alone.

---

## `tasks` — key rules for commands

### Circular FKs (`use_alter=True`)
- `latest_history_record_id` → `task_history_records.client_id`
- `latest_event_id` → `task_events.client_id`

Both use `use_alter=True` to resolve DDL ordering. Pointer updates must be **transactionally coupled** with the lineage append.

### Task type enum
`task_type` uses Postgres type name `business_task_type_enum` (not `task_type_enum`) to avoid collision with the bootstrap execution domain's `task_type_enum`. The Python enum class is `TaskTypeEnum` in `domain/tasks/enums.py`. **Do not rename it back.**

### Task state machine (`TaskStateEnum`)
`PENDING → ASSIGNED → WORKING → STALLED → READY → RESOLVED`
Terminal states: `FAILED`, `CANCELLED`. Transitions enforced by domain guards.

### Task types
- `RETURN`: customer returning a product.
- `PRE_ORDER`: pre-ordered product requiring restoration before delivery.
- `INTERNAL`: internal operational task (no customer context required).

### Contact snapshot fields
`primary_phone_number`, `secondary_phone_number`, `primary_email`, `secondary_email`, `address` on `tasks` are **task-time snapshots** taken at task creation. Customer profile edits must never retroactively overwrite these values.

### `task_scalar_id`
A human-readable sequential identifier within a workspace. UNIQUE(workspace_id, task_scalar_id). The command layer is responsible for generating a unique scalar ID within the workspace scope.

---

## `task_items` — key rules for commands

### Item roles
- `PRIMARY`: the main item this task is about.
- `RELATED`: secondary items associated with the task.
- Partial unique index: only one `PRIMARY` item per active task (`WHERE role = 'primary' AND removed_at IS NULL`).
- Partial unique index: one active row per `(workspace_id, task_id, item_id) WHERE removed_at IS NULL`.

To remove an item: set `removed_at` + `removed_by_id`. Do not delete the row.

---

## `task_steps` — key rules for commands

### Circular FK (`use_alter=True`)
`latest_state_record_id` → `step_state_records.client_id`. Pointer updates must be transactionally coupled with the state record append.

### Step state machine (`TaskStepStateEnum`)
`PENDING → WORKING → PAUSED → WORKING` (cycle) → `ENDED_SHIFT → WORKING` (next shift) → terminal.

Terminal states: `COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`.
- `ENDED_SHIFT` is **not** a terminal state — work resumes next shift.
- `PAUSED` and `ENDED_SHIFT` are distinct interruption types. Do not collapse them.
- `BLOCKED` means a dependency is unmet.

### Aggregate metrics mixins
`TaskStep` inherits from all four aggregate metrics mixins:
- `AggregateMetricsTimeMixin`: `total_working_seconds`, `total_pause_seconds`, `total_ended_shift_seconds`
- `AggregateMetricsCountsMixin`: `total_working_count`, `total_pause_count`, `total_ended_shift_count`
- `AggregateMetricsTotalsMixin`: `total_issues_count`, `total_issues_resolved_count`
- `AggregateMetricsCostMixin`: `total_cost_minor`

These are **rebuildable projections** updated incrementally through command flows. They are not the authoritative reconstruction source — `step_state_records` lineage is.

### Dependency tracking
`total_dependencies` and `completed_dependencies` are projections updated by dependency lifecycle commands. `CHECK(completed_dependencies <= total_dependencies)`.

### `task_step_state_enum` Postgres type
`task_step.py` creates this type (`create_type=True`). `step_state_record.py` reuses it (`create_type=False`). Import order must keep `task_step.py` before `step_state_record.py` in `models/__init__.py`.

---

## `step_state_records` — key rules for commands

### Active row rule
One open row per `(workspace_id, step_id)` at a time: partial unique index `uix_step_state_records_active WHERE exited_at IS NULL`.

Before inserting a new state row, `exited_at` must be set on the current open row within the same transaction.

### Durations
`exited_at - entered_at` gives the actual duration in that state. These intervals feed the aggregate metrics counters on `task_steps`.

### `reason` field
`StepEventReasonEnum` captures why a transition happened (e.g. `PAUSE_LUNCH_BREAK`, `WAITING_FOR_UPHOLSTERY`). Used for analytics and operational transparency.

---

## `task_step_dependencies` — key rules for commands

- Directed: `dependent_step_id` depends on `prerequisite_step_id`.
- Active edge = `removed_at IS NULL`. Partial unique index prevents duplicate active edges.
- `CHECK(dependent_step_id != prerequisite_step_id)` — no self-reference.
- **Cycle detection belongs to domain guards only**, not the model layer.
- Dependency removals are lifecycle events (set `removed_at`), not hard deletes.

---

## `task_step_assignment_records` — key rules for commands

- One active assignment per `(workspace_id, step_id)` at a time: partial unique index `WHERE removed_at IS NULL`.
- To reassign: set `removed_at` / `removed_by_id` on current row, then insert new row.
- `reason_code` / `reason_text` explain why reassignment occurred.
- Full assignment history is preserved for staffing analytics.

---

## `task_events` and `task_history_records` — key rules for commands

- Both are **append-only lineage tables**. Do not update existing rows.
- `task_events.event_lifecycle_state` (`TaskDomainEventLifecycleStateEnum`): `RECORDED`, `SUPERSEDED`, `COMPENSATED`, `IGNORED`. Compensating records append rather than mutate.
- `task_history_records.state_from` / `state_to` capture the before/after state for the transition.
- `snapshot_payload` should capture durable task state at the time of the event.

---

## Runtime boundary

The task domain does **not** own:
- Websocket sessions
- Queue delivery / worker process state
- Transport internals
- Analytics materialization

Runtime and analytics systems may consume lineage and projections but must not define task validity or mutate lifecycle truth.

---

## Deferred

- Primary membership designation and routing priority for steps
- Task-level SLA tracking and escalation
- AI-assisted step recommendations (advisory only, not lifecycle authority)
- Analytics projections as separate materialized view systems
