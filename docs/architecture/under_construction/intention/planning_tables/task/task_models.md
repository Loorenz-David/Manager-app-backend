# Task Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_orchestration
Contracts: 01, 03, 04, 05, 06, 07, 08, 09, 10, 21, 24, 25, 27, 28, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the durable task orchestration aggregate that coordinates operational lifecycle visibility without collapsing into live runtime execution ownership.

## 1) Core table

### 1.1 tasks

Columns:
- client_id: String(64) PK, prefix tsk
- task_scalar_id: Integer, unique per workspace, sequential-facing operational reference
- workspace_id: FK workspaces.client_id, not null, indexed
- task_type: Enum(task_type), not null, indexed
- priority: Enum(task_priority), not null, default NORMAL, indexed
- state: Enum(task_state), not null, indexed
- title: String(255), nullable
- summary: String(1024), nullable
- return_source: Enum(task_return_source), nullable
- item_location: Enum(task_item_location), nullable
- additional_details: JSON, nullable (content-block list schema compatible)
- ready_by_at: DateTime(tz), nullable
- scheduled_start_at: DateTime(tz), nullable
- scheduled_end_at: DateTime(tz), nullable
- return_method: Enum(task_return_method), nullable
- fulfillment_method: Enum(task_fulfillment_method), nullable
- customer_id: FK customers.client_id, nullable
- primary_phone_number: String(64), nullable
- secondary_phone_number: String(64), nullable
- primary_email: String(255), nullable
- secondary_email: String(255), nullable
- address: JSON, nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- closed_at: DateTime(tz), nullable
- latest_history_record_id: FK task_history_records.client_id, nullable
- latest_event_id: FK task_events.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Projection mixins inherited (column-only semantics):
- WORK_RECORD_TIME
- WORK_RECORD_TOTAL_COUNT
- WORK_RECORD_CURRENT_COUNT

Constraints and indexes:
- UNIQUE(workspace_id, task_scalar_id)
- INDEX(workspace_id, state, scheduled_start_at)
- CHECK(scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at >= scheduled_start_at)

## 2) Enums

### 2.1 task_type
- RETURN
- PRE_ORDER
- INTERNAL

### 2.2 task_priority
- LOW
- NORMAL
- HIGH
- URGENT

### 2.3 task_state
- PENDING
- ASSIGNED
- WORKING
- STALLED
- READY
- RESOLVED
- FAILED
- CANCELLED

### 2.4 task_return_source
- AFTER_PURCHASE
- BEFORE_PURCHASE
- STORE_RETURN

### 2.5 task_item_location
- STORE
- CUSTOMER

### 2.6 task_return_method
- DROP_OFF_BY_CUSTOMER
- PICKUP

### 2.7 task_fulfillment_method
- PICKUP_AT_STORE
- DELIVERY

## 3) Ownership and semantics

Task orchestration semantics:
- tasks are orchestration ownership entities and business-process lifecycle coordinators.
- task rows are not websocket runtime containers, queue lock holders, process/thread ownership rows, or live worker-session state.
- tasks coordinate durable operational progression and reconstruction-safe lifecycle visibility.

Task type semantics:
- task_type expresses high-level business/origin category.
- task_type is a coarse business/origin category, not a full provenance trace.
- do not add separate origin_source/origin_id polymorphism in this phase.
- future integration-specific origin tracking may be introduced later if needed.

Task state semantics:
- task.state is a domain-governed synthesized business-operational lifecycle field.
- task.state does not represent queue execution state, websocket connection state, thread/process runtime state, or active runtime lock ownership.
- task-step states may influence task.state, but task-state transitions are applied only through task orchestration policies.
- Legal transition validation belongs to domain orchestration guards. Models define possible states, not the complete allowed transition graph.
- runtime systems may recommend or trigger domain commands, but they do not become exclusive lifecycle authority.
- STALLED means task progression is blocked by operational conflict.
- READY means operationally ready for downstream progression.
- RESOLVED means lifecycle completion/closure according to orchestration policy.
- ASSIGNED means at least one operational responsibility assignment has been established according to task orchestration policy.
- ASSIGNED does not imply every step is assigned and does not imply work has started.
- task-step completion does not automatically equal task resolution.
- a task may require customer handling, pickup/delivery, admin review, confirmation, return handling, or additional closure before RESOLVED.

Task state lifecycle examples:
- PENDING -> ASSIGNED -> WORKING -> READY -> RESOLVED
- WORKING -> STALLED -> WORKING
- WORKING -> FAILED
- WORKING -> CANCELLED

Priority and title/summary semantics:
- priority influences operational sorting and escalation visibility, not runtime lock authority.
- title is a human-facing operational label.
- summary is short operational context.
- if title is missing, domain/service orchestration may synthesize one from task type, item, customer, or working context.
- title and summary are not lifecycle authority.

Task scalar allocation policy:
- task_scalar_id is workspace-scoped human-facing operational reference.
- task_scalar_id is not globally unique.
- client_id provides global uniqueness and external-safe references.
- task_scalar_id allocation must be concurrency-safe and workspace-scoped.
- do not rely on unsafe max+1 allocation without locking/transactional protection.

Customer contact snapshot semantics:
- customer_id links to current customer identity.
- contact/address fields on tasks are task-level operational snapshots.
- these fields preserve task-time operational contact context and should not be auto-overwritten by future customer profile changes.
- Phone/email validation belongs to command/input validation.
- phone numbers may later store normalized E.164 values.
- emails may later store normalized forms.
- a dedicated customer-contact snapshot entity may be introduced later.

Scheduling semantics:
- ready_by_at is the desired business deadline/readiness target.
- scheduled_start_at is the expected customer handoff window start.
- scheduled_end_at is the expected customer handoff window end.
- scheduled_start_at and scheduled_end_at do not represent internal worker execution windows in this phase.
- these fields are planning/customer-handoff metadata, not runtime lock/reservation authority.

Item location semantics:
- task.item_location is task-time operational context.
- values: STORE, CUSTOMER.
- this is not authoritative item movement history or warehouse-runtime location truth.
- future item location/runtime systems may provide historical movement tracking independently.

Address snapshot schema:
- address is a bounded task-time operational snapshot with schema:
	- street_address: string
	- post_number: string
	- city: string
	- country: string
	- municipality: string
	- coordinates:
		- lat: float
		- lng: float
- address JSON must not become arbitrary logistics state storage.
- command/input validation owns schema validation.

additional_details semantics:
- additional_details is contextual task content using the content-block schema.
- it is not lifecycle authority, workflow state, runtime orchestration state, or hidden assignment metadata.
- avoid using additional_details as unstructured dumping ground for relational state.

Work-record projection semantics:
- WORK_RECORD_* columns are replay-compatible operational projections.
- these fields are not immutable accounting truth, payroll authority, or realtime websocket state.
- append-oriented lifecycle history remains authoritative for reconstruction and reconciliation.

Pointer-field semantics:
- latest_history_record_id and latest_event_id are convenience/projection pointers only.
- full historical reconstruction must use complete lineage traversal.
- these pointer fields are not authoritative lifecycle truth.
- Latest pointer updates must be transactionally coupled with the lineage append operation that created the referenced row.

Emission policy:
- Task state transitions MUST write task_history_records.
- Domain-significant transitions MAY emit task_events.
- External/integration-relevant changes MAY emit task_events.
- Step state transitions MUST write step_state_records.
- Assignment changes MUST write task_step_assignment_records.
- not every change is duplicated into every lineage table.
- command/orchestration policies decide which lineage records are emitted.

## 4) Relationship map

- workspaces (1) -> (*) tasks
- tasks (1) -> (*) task_notes
- tasks (1) -> (*) task_history_records
- tasks (1) -> (*) task_events
- tasks (1) -> (*) task_steps
- tasks (1) -> (*) task_items
- tasks (1) -> (*) case_links through centralized case domain integration

Prefix map:
- tsk -> tasks
- tsp -> task_steps
- tsd -> task_step_dependencies
- tim -> task_items
- tev -> task_events
- thr -> task_history_records
- tno -> task_notes
- ssr -> step_state_records
- tsar -> task_step_assignment_records

## 5) Scope boundary

In scope:
- task orchestration ownership
- lifecycle visibility fields and scheduling intent
- durable operational reconstruction anchors

Out of scope:
- websocket runtime session ownership
- queue delivery state ownership
- worker process/thread ownership
- transport-specific delivery artifacts
- task-local archive ownership in this phase

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- cross-workspace orchestration references are forbidden.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.
- task lifecycle durability and replay correctness take precedence over premature live-query optimization.
- historical systems must not depend exclusively on mutable live task rows.
- structured terminal/blocking reason semantics (FAILED, CANCELLED, STALLED) should be captured through append-oriented lineage systems, not mutable reason fields on tasks.
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.
- All timestamps are persisted in UTC. Workspace timezone is used only for operational date grouping/projection policies where explicitly defined.

## 7) Deferred runtime notes

- do not place realtime lock/session fields on tasks.
- do not add queue delivery internals to task rows.
- runtime execution truth remains in future runtime/orchestration subsystems.
- archive semantics are out of scope for this phase and belong to a future dedicated polymorphic archive system.
- System-created tasks should preserve creation provenance through explicit task_history_records or task_events metadata when created_by_id is null.

## 8) Future integration notes

- centralized image integration through contract 43 image domain (no task-local image ownership tables).
- centralized case integration through contract 44 case domain (no task-local case infrastructure duplication).
- future websocket/runtime orchestration may consume task lifecycle outputs without replacing task domain ownership.

## 9) Risks and protections

Risks:
- overloading task.state with runtime semantics.
- turning task rows into queue/runtime transport containers.

Protections:
- explicit orchestration-vs-runtime separation rules.
- append-oriented history/event companions for durable reconstruction.

## 10) Clarifications before implementation

Q1: Should task_scalar_id remain workspace-scoped sequential only, or also globally unique for external integrations?

Answer:
Workspace-scoped sequential only.
Use client_id for global uniqueness and external-safe references.
task_scalar_id is a human-facing operational reference within a workspace.

Q2: Should archived_at imply immutable task notes/events, or allow controlled append-only post-archive corrections?

Answer:
Remove archived_at from this phase.
Archiving will be handled later through a dedicated polymorphic archive system.

Q3: Should customer contact fields migrate to a dedicated customer-contact snapshot entity in later phases?

Answer:
Yes, later.
For now, contact/address fields remain task-level operational snapshots.

Q4: Should closed_at replace resolved_at for terminal lifecycle tracking?

Answer:
Yes. closed_at is set when task enters a terminal lifecycle state.
RESOLVED is successful closure; FAILED and CANCELLED are terminal or correction/reopen-controlled closures.
