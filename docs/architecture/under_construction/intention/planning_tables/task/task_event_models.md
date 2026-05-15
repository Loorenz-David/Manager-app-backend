# Task Event Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_events
Contracts: 01, 03, 06, 08, 11, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append-oriented domain event entities for task lifecycle and orchestration semantics while preserving separation from infrastructure delivery transport.

## 1) Core table

### 1.1 task_events

Columns:
- client_id: String(64) PK, prefix tev
- workspace_id: FK workspaces.client_id, not null, indexed
- task_id: FK tasks.client_id, not null, indexed
- event_type: Enum(task_event_type), not null, indexed
- event_lifecycle_state: Enum(task_domain_event_lifecycle_state), not null, indexed
- error_code: Enum(task_event_error_code), nullable, indexed
- payload: JSON, nullable
- occurred_at: DateTime(tz), not null, indexed
- correlation_id: String(64), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, task_id, occurred_at)

## 2) Enum placeholders

### 2.1 task_event_type
- TASK_CREATED
- TASK_STATE_CHANGED
- TASK_STEP_STATE_CHANGED
- TASK_ASSIGNMENT_CHANGED
- TASK_RESOLVED

### 2.2 task_domain_event_lifecycle_state
- RECORDED
- SUPERSEDED
- COMPENSATED
- IGNORED

### 2.3 task_event_error_code
- VALIDATION_FAILED
- ORCHESTRATION_CONFLICT
- DEPENDENCY_BLOCKED
- UNKNOWN

Note: event/error enum catalogs may expand in later phases, but remain domain-event catalogs, not transport-delivery status catalogs.

## 3) Ownership and semantics

- task_events are operational domain lifecycle events.
- task_events are not Redis transport packets, websocket payload mirrors, queue delivery receipts, or infrastructure-delivery artifacts.
- event lineage is append-oriented and reconstruction-compatible.
- corrections use compensating events or history entries rather than destructive event rewrite.
- event_lifecycle_state is domain-side event lifecycle state only.
- event_lifecycle_state is not Redis/job/broker transport delivery metadata.
- task_events.payload must follow the existing base event payload governance from the event contract.
- correlation_id may support idempotent replay, reconciliation, cross-domain tracing, and command causality grouping, but is not primary lifecycle identity.
- causation_id may be introduced later for explicit event-chain reconstruction if needed.

Emission policy:
- Task state transitions MUST write task_history_records.
- Domain-significant transitions MAY emit task_events.
- External/integration-relevant changes MAY emit task_events.
- Step state transitions MUST write step_state_records.
- Assignment changes MUST write task_step_assignment_records.
- not every change is duplicated into every lineage table.
- command/orchestration policies decide which lineage records are emitted.

Soft-delete note:
- Soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.
- Hard deletion is forbidden in normal operations.
- Replay systems must define whether soft-deleted lineage rows are included, excluded, or compensated.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.

Lineage distinction semantics:
- task_history_records capture task-level lifecycle transition/change history.
- task_events capture domain-significant operational events that may feed integrations, projections, or replay systems.
- step_state_records capture step-level state interval/progression lineage.
- not every change must be duplicated in all lineage systems; command orchestration defines emission policy.

Latest pointer rule:
- latest pointer updates must be transactionally coupled with the lineage append operation that created the referenced row.
- latest pointers are convenience/projection fields.
- they must not be updated independently from lineage creation.
- full reconstruction always traverses lineage, not latest pointers only.

## 4) Relationship map

- tasks (1) -> (*) task_events

## 5) Scope boundary

In scope:
- domain event semantics for operational reconstruction
- event correlation for replay-safe orchestration tracing

Out of scope:
- transport delivery internals
- broker retry metadata ownership

## 6) Operational rules

- workspace_id must match task ownership.
- hard deletion is forbidden in normal operations.
- event lineage must remain deterministic and replay-compatible.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.

## 7) Deferred runtime notes

- infrastructure transport systems may emit delivery logs separately.
- do not copy delivery transport state into task_events as authority.

## 8) Future integration notes

- event emission may feed infra outbox/worker systems while preserving domain-event ownership boundaries.
- replay systems may consume task_events + task_history_records + step lineage for deterministic rebuild.

## 9) Risks and protections

Risks:
- conflating domain events with transport artifacts.

Protections:
- explicit domain-event-only semantics.
- append-oriented lineage constraints.
