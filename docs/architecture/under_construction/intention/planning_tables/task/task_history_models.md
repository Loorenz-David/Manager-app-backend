# Task History Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_history
Contracts: 01, 03, 06, 08, 21, 24, 25, 36, 40, 41, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append-oriented task lifecycle history records that preserve replay-safe reconstruction and audit durability.

## 1) Core table

### 1.1 task_history_records

Columns:
- client_id: String(64) PK, prefix thr
- workspace_id: FK workspaces.client_id, not null, indexed
- task_id: FK tasks.client_id, not null, indexed
- occurred_at: DateTime(tz), not null, indexed
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only

History-record inherited fields:
- state_from: String(64), nullable
- state_to: String(64), nullable
- reason_code: String(128), nullable
- reason_text: String(512), nullable
- snapshot_payload: JSON, nullable

Soft-delete fields:
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, task_id, occurred_at)
- INDEX(workspace_id, task_id, created_at)

## 2) Ownership and semantics

- task_history_records are append-oriented lifecycle history entities.
- history rows are authoritative for lifecycle reconstruction over mutable task row convenience fields.
- corrections should append compensating history, not rewrite historical lineage.
- historical correctness and replay safety take precedence over mutable convenience updates.

Timeline semantics:
- occurred_at means when the lifecycle/change actually happened.
- created_at means when the row was inserted.
- created_at must not be overloaded as event occurrence time.

Emission policy:
- Task state transitions MUST write task_history_records.
- Domain-significant transitions MAY emit task_events.
- Step state transitions MUST write step_state_records.
- Assignment changes MUST write task_step_assignment_records.
- External/integration-relevant changes MAY emit task_events.
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
- task_events capture domain-significant operational events used by integrations/projections/replay.
- step_state_records capture step-level state interval/progression lineage.
- not every change must be duplicated in all lineage systems; command orchestration defines emission policy.

## 3) Relationship map

- tasks (1) -> (*) task_history_records

## 4) Scope boundary

In scope:
- lifecycle transition durability
- replay-safe task reconstruction
- audit-compatible change lineage

Out of scope:
- realtime runtime state ownership
- queue/websocket transport artifacts

## 5) Operational rules

- workspace_id must match task ownership.
- hard deletion is forbidden in normal operations.
- soft deletion, when required, must remain policy-governed and reconstruction-safe.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.

## 6) Deferred runtime notes

- do not overload history rows with transport delivery metadata.
- do not use history rows as queue execution telemetry.

## 7) Future integration notes

- future snapshot contracts may formalize mandatory snapshot fields for rendering durability.
- replay/recompute pipelines may rebuild projections from history plus event lineage.
- Latest pointer updates must be transactionally coupled with the lineage append operation that created the referenced row.

## 8) Risks and protections

Risks:
- destructive history rewrite causing replay drift.

Protections:
- append-oriented lineage.
- compensating correction policy.
