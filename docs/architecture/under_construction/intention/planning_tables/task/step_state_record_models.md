# Step State Record Models Plan

Status: DRAFT - Initial Structured Split
Domain: step_state_records
Contracts: 01, 03, 06, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append-oriented step state lineage records for deterministic replay, operational auditing, and reconstruction-safe orchestration history.

## 1) Core table

### 1.1 step_state_records

Columns:
- client_id: String(64) PK, prefix ssr
- workspace_id: FK workspaces.client_id, not null, indexed
- step_id: FK task_steps.client_id, not null, indexed
- state: Enum(task_step_state), not null, indexed
- reason: Enum(step_event_reason), nullable, indexed
- description: String(1024), nullable
- accuracy: Integer, nullable
- accuracy_measured_by: Enum(step_state_record_accuracy_measured_by), nullable
- taken_from_average: Boolean, not null, default false
- entered_at: DateTime(tz), not null
- exited_at: DateTime(tz), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, step_id, entered_at)
- UNIQUE(workspace_id, step_id) WHERE exited_at IS NULL
- CHECK(accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100))
- CHECK(exited_at IS NULL OR exited_at >= entered_at)

State transition authority:
- Legal transition validation belongs to domain orchestration guards. Models define possible states, not the complete allowed transition graph.
- Step state transition commands must be concurrency-safe and idempotency-aware.
- Transitions must lock or transactionally guard the active state record before closing/opening intervals.
- Step state intervals for the same step must not overlap.
- overlap validation belongs to command/domain transition services, not DB-only constraints.

## 2) Enums

### 2.1 step_state_record_accuracy_measured_by
- USER
- AI

### 2.2 step_event_reason
- WAITING_FOR_UPHOLSTERY
- PAUSE_LUNCH_BREAK
- PAUSE_COFFEE_BREAK
- PAUSE_ENDED_SHIFT
- PAUSE_MEETING
- PAUSE_OTHER_TASK_PRIORITY

## 3) Ownership and semantics

- step_state_records are append-oriented lifecycle records.
- state records are authoritative for step progression reconstruction relative to mutable convenience projections.
- corrections should append compensating records rather than rewrite historical lineage.
- entered_at is state-entry timestamp.
- exited_at is state-interval end timestamp.
- active state record means exited_at IS NULL.
- created_at remains row creation metadata only.
- only one active state interval may exist per step at a time.
- step transitions must close previous active interval and open a new one via command-layer transition orchestration.
- direct ORM mutation of active intervals outside transition services is forbidden.
- PAUSED and ENDED_SHIFT are distinct operational interruption semantics; ended-shift interruption must not be collapsed into generic pause semantics.
- PAUSED may transition back to WORKING.
- ENDED_SHIFT may transition back to WORKING when a worker resumes in a later shift.
- ENDED_SHIFT is an interruption boundary, not terminal step completion.
- accuracy is integer percentage from 0 to 100.
- NULL accuracy means not measured.
- accuracy_measured_by captures USER or AI source provenance.
- AI-sourced metrics remain advisory provenance metadata, not autonomous lifecycle authority.
- taken_from_average means the value was estimated from aggregate/history averages rather than directly measured.

## 4) Relationship map

- task_steps (1) -> (*) step_state_records

## 5) Scope boundary

In scope:
- step progression lineage
- pause/block reason chronology
- replay-safe operational reconstruction

Out of scope:
- realtime worker/session ownership
- queue/websocket transport state

## 6) Operational rules

- workspace_id must match step ownership.
- hard deletion is forbidden in normal operations.
- historical state records remain queryable for privileged replay/audit workflows.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.
- Soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.

## 7) Deferred runtime notes

- do not add lock/session transport fields to state records.
- execution heartbeat telemetry remains in separate runtime systems.

## 8) Future integration notes

- future accuracy scoring systems may extend reason taxonomy without changing append-only semantics.
- replay/recompute may rebuild step projections from this lineage.

## 9) Risks and protections

Risks:
- mutable overwrite of step state history causing replay drift.

Protections:
- append-oriented record design.
- compensating correction governance.
