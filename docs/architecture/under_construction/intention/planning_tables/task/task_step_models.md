# Task Step Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_steps
Contracts: 01, 03, 06, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define task-step orchestration entities as durable dependency-aware coordination units with worker responsibility and section execution semantics, while preserving separation from realtime runtime execution systems.

## 1) Core table

### 1.1 task_steps

Columns:
- client_id: String(64) PK, prefix tsp
- workspace_id: FK workspaces.client_id, not null, indexed
- task_id: FK tasks.client_id, not null, indexed
- state: Enum(task_step_state), not null, indexed
- readiness_status: Enum(task_step_readiness_status), not null, indexed
- sequence_order: Integer, nullable
- working_section_id: FK working_sections.client_id, not null, indexed
- assigned_worker_id: FK users.client_id, nullable, indexed
- total_dependencies: Integer, not null, default 0
- completed_dependencies: Integer, not null, default 0
- total_working_count: Integer, not null, default 0
- total_pause_count: Integer, not null, default 0
- total_ended_shift_count: Integer, not null, default 0
- total_pause_seconds: Integer, not null, default 0
- total_ended_shift_seconds: Integer, not null, default 0
- total_issues_count: Integer, not null, default 0
- total_issues_resolved_count: Integer, not null, default 0
- recorded_time_marked_wrong: Boolean, not null, default false
- taken_from_average: Boolean, not null, default false
- working_section_name_snapshot: String(255), nullable
- assigned_worker_display_name_snapshot: String(255), nullable
- created_at: DateTime(tz), not null
- closed_at: DateTime(tz), nullable
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- latest_state_record_id: FK step_state_records.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Projection mixins inherited (column-only semantics):
- WORK_RECORD_TIME
- WORK_RECORD_TOTAL_COST

Constraints and indexes:
- INDEX(workspace_id, task_id, state)
- CHECK(completed_dependencies >= 0)
- CHECK(total_dependencies >= 0)
- CHECK(completed_dependencies <= total_dependencies)
- CHECK(total_pause_count >= 0)
- CHECK(total_ended_shift_count >= 0)
- CHECK(total_pause_seconds >= 0)
- CHECK(total_ended_shift_seconds >= 0)

## 2) Enums

### 2.1 task_step_state
- PENDING
- WORKING
- PAUSED
- ENDED_SHIFT
- BLOCKED
- COMPLETED
- SKIPPED
- FAILED
- CANCELLED

### 2.2 task_step_readiness_status
- BLOCKED
- PARTIAL
- READY

## 3) Ownership and semantics

Task-step orchestration semantics:
- task_steps are durable orchestration coordination units.
- they coordinate dependency-aware progression, section execution ownership, and worker-facing operational progression.
- they are not websocket session state, process/thread execution ownership, or realtime lock containers.
- sequence_order is display/planning order only; dependency graph remains authoritative for prerequisite semantics.

Readiness semantics:
- readiness_status is orchestration readiness visibility.
- BLOCKED means one or more required dependencies are unsatisfied and the step cannot start.
- PARTIAL means some prerequisites are satisfied but readiness is incomplete.
- READY means all required prerequisites are satisfied.
- readiness_status is not live runtime execution truth.
- A step that is ready to start remains state=PENDING with readiness_status=READY.
- readiness_status may be physically persisted as a domain-maintained operational projection while remaining logically derivable from dependency lineage, prerequisite step states, and orchestration policies.

Assignment semantics:
- assigned_worker_id represents durable operational responsibility assignment.
- assignment does not represent websocket ownership, runtime lock ownership, or thread ownership.
- runtime systems may coordinate temporary execution without replacing durable assignment semantics.
- assigned_worker_id must belong to the same workspace, have active workspace membership, and normally be an active member of the step working_section_id unless privileged override policy allows otherwise.
- task_steps.assigned_worker_id, working_section_id, and any future analytics references are convenience/projection fields, not authority over lineage reconstruction.

Step-state lifecycle semantics:
- PENDING: step exists but active execution has not started.
- WORKING: worker is actively working on the step.
- PAUSED: temporary interruption within an active work lifecycle.
- ENDED_SHIFT: work stopped because the work shift ended; this is not equivalent to a normal pause.
- BLOCKED: step cannot proceed because prerequisites/resources are unavailable.
- COMPLETED: step work is completed.
- SKIPPED: step intentionally not executed in current lifecycle context.
- FAILED: step execution failed and may require correction/retry/reassignment.
- CANCELLED: step cancelled because parent task/plan changed.

Step lifecycle examples:
- PENDING -> WORKING
- WORKING -> PAUSED -> WORKING
- WORKING -> ENDED_SHIFT -> WORKING
- WORKING -> COMPLETED
- WORKING -> BLOCKED -> WORKING
- WORKING -> FAILED
- WORKING -> CANCELLED

Legal transition validation belongs to domain orchestration guards. Models define possible states, not the complete allowed transition graph.

State/readiness policy:
- readiness_status=BLOCKED describes whether a step is ready to begin/progress according to prerequisites.
- task_step_state=BLOCKED describes the current lifecycle condition where the step is blocked operationally.
- These are related but not identical.
- Certain task_step_state/readiness_status combinations are invalid and must be guarded by domain policies.

Dependency completion policy:
- completed_dependencies counts active prerequisite dependencies whose prerequisite step satisfies dependency completion policy.
- Default policy: only prerequisite steps in COMPLETED satisfy dependency completion.
- SKIPPED, CANCELLED, and FAILED may satisfy dependencies only if explicit domain policies allow it.

Terminal states:
- Step terminal states are COMPLETED, SKIPPED, FAILED, and CANCELLED.
- Terminal states stop normal operational progression.
- Privileged correction/reopen/retry workflows may append lineage to reopen or correct.
- Terminal states must not be mutated destructively.

Pause vs ended-shift semantics:
- PAUSED and ENDED_SHIFT are distinct operational concepts.
- ended-shift time must not be collapsed into generic pause semantics.
- future time tracking should distinguish active work time, normal pause time, and ended-shift interruption time.

Work-record semantics:
- WORK_RECORD_* and related counters are replay-compatible operational projections.
- they are not immutable accounting truth, payroll truth, or realtime runtime authority.
- append-oriented step state records remain authoritative for reconstruction and correction.
- total_dependencies, completed_dependencies, total_working_count, total_pause_count, total_ended_shift_count, total_issues_count, and total_issues_resolved_count are mutable operational projections.
- these counters must remain rebuildable from dependency lineage, step state records, task-step assignment records, future item-issue linkage, and task events/history.
- these counters are not immutable truth, accounting truth, payroll truth, or runtime lock authority.

Snapshot durability semantics:
- working_section_name_snapshot and assigned_worker_display_name_snapshot preserve historical rendering durability.
- snapshot fields are not synchronization authority and should not be retroactively overwritten by mutable registry/user changes unless explicit correction policy allows it.

Pointer semantics:
- latest_state_record_id is convenience/projection pointer only; full reconstruction must traverse complete step state lineage.

Terminal reason ownership:
- structured terminal/blocking reason semantics (FAILED, CANCELLED, SKIPPED, BLOCKED) should be captured via append-oriented lineage systems (step_state_records, task_events, task_history_records, and assignment records where relevant), not mutable reason fields on task_steps.

## 4) Relationship map

- tasks (1) -> (*) task_steps
- working_sections (1) -> (*) task_steps
- users (1) -> (*) task_steps as assigned_worker_id
- task_steps (1) -> (*) step_state_records
- task_steps (1) -> (*) task_step_dependencies as dependent_step_id
- task_steps (1) -> (*) task_step_dependencies as prerequisite_step_id
- task_steps (1) -> (*) task_step_assignment_records

## 5) Scope boundary

In scope:
- dependency-aware orchestration step coordination
- durable section and worker assignment visibility
- readiness interpretation and state progression

Out of scope:
- websocket runtime synchronization state
- queue thread/process execution ownership
- transport delivery internals

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- cycle detection and dependency graph validation belong to domain orchestration guards; DB enforces structural integrity only.
- hard deletion of resolved steps is forbidden in normal operations.
- step progression must remain reconstruction-safe via append-oriented state records.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.
- task_steps.workspace_id must match task.workspace_id, working_section.workspace_id, assigned worker workspace membership scope, and linked analytics stats workspace.
- cross-workspace orchestration links are forbidden.
- step state transition commands must be concurrency-safe and idempotency-aware.
- transitions must lock or transactionally guard the active state record before closing/opening intervals.
- PAUSED may transition back to WORKING.
- ENDED_SHIFT may transition back to WORKING when a worker resumes in a later shift.
- ENDED_SHIFT is an interruption boundary, not terminal step completion.
- Legal transition validation belongs to domain orchestration guards. Models define possible states, not the complete allowed transition graph.
- task_steps.latest_state_record_id is a convenience/projection pointer only and must not be updated independently from lineage creation.
- All timestamps are persisted in UTC. Workspace timezone is used only for operational date grouping/projection policies where explicitly defined.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.

## 7) Deferred runtime notes

- do not add ephemeral lock/session columns to task_steps.
- runtime pause/resume execution internals remain outside this model.

## 8) Future integration notes

- future runtime orchestration systems may consume task_steps while preserving durable orchestration boundaries.
- future replay/recompute systems may rebuild step projections from state-record lineage.
- future task-step issue resolution should use explicit relational linkage to item issue lifecycle entities or snapshot-compatible projection records; do not store issue lifecycle truth as strings on task_steps.

## 9) Risks and protections

Risks:
- collapsing durable orchestration state into transient runtime state.

Protections:
- explicit readiness/assignment boundary semantics.
- append-oriented step state record authority.
