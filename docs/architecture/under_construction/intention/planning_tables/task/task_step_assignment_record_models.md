# Task Step Assignment Record Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_step_assignment_records
Contracts: 01, 03, 06, 08, 21, 24, 25, 36, 40, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append/lifecycle-oriented assignment history records for task steps so reassignment remains reconstruction-safe while task_steps.assigned_worker_id remains current projection/convenience.

## 1) Core table

### 1.1 task_step_assignment_records

Columns:
- client_id: String(64) PK, prefix tsar
- workspace_id: FK workspaces.client_id, not null, indexed
- step_id: FK task_steps.client_id, not null, indexed
- assigned_worker_id: FK users.client_id, not null, indexed
- assigned_at: DateTime(tz), not null
- assigned_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- removed_at: DateTime(tz), nullable
- removed_by_id: FK users.client_id, nullable
- reason_code: String(128), nullable
- reason_text: String(512), nullable

Constraints and indexes:
- UNIQUE(workspace_id, step_id) WHERE removed_at IS NULL
- INDEX(workspace_id, step_id, assigned_at)

## 2) Ownership and semantics

- assignment records are append/lifecycle-oriented operational records.
- reassignment must preserve historical lineage through assigned_at/removed_at transitions.
- task_steps.assigned_worker_id may remain current projection/convenience only.
- assignment records are authoritative for assignment history reconstruction.
- Unassigned state is represented by absence of an active assignment record and null task_steps.assigned_worker_id.

State authority:
- Legal transition validation belongs to domain orchestration guards. Models define possible states, not the complete allowed transition graph.
- Assignment state changes must be concurrency-safe and idempotency-aware.

## 3) Relationship map

- task_steps (1) -> (*) task_step_assignment_records
- users (1) -> (*) task_step_assignment_records as assigned_worker_id

## 4) Scope boundary

In scope:
- assignment history durability
- reassignment lineage reconstruction

Out of scope:
- websocket ownership
- runtime lock ownership
- process/thread execution ownership

## 5) Operational rules

- task_step_assignment_records.workspace_id must match step.workspace_id and assigned worker workspace membership scope.
- active assignment means removed_at IS NULL.
- one active assignment record per step is allowed at a time.
- cross-workspace assignment links are forbidden.

Future integration note:
- Future assignment records may snapshot or link the worker's working-section membership context to preserve historical assignment validity when memberships change.

Soft-delete and cleanup note:
- Soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.
- Hard deletion is forbidden in normal operations.
- Replay systems must define whether soft-deleted lineage rows are included, excluded, or compensated.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.
- Partial unique indexes are PostgreSQL-specific and must be generated explicitly in migrations.

## 6) Deferred runtime notes

- do not place realtime lock/session metadata on assignment records.
- runtime execution internals remain outside assignment history ownership.

## 7) Future integration notes

- future staffing policies may introduce assignment-priority/reason taxonomies while preserving append/lifecycle semantics.
- replay/recompute systems may rebuild assignment projections from assignment lineage + step state lineage.

## 8) Risks and protections

Risks:
- losing reassignment history by mutating single assigned_worker pointer only.

Protections:
- dedicated assignment lineage records.
- partial active uniqueness with historical durability.
