# Task Step Dependency Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_step_dependencies
Contracts: 01, 03, 06, 08, 21, 24, 25, 40, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define authoritative task-step prerequisite constraints as durable orchestration dependencies with deterministic reconstruction compatibility.

## 1) Core table

### 1.1 task_step_dependencies

Columns:
- client_id: String(64) PK, prefix tsd
- workspace_id: FK workspaces.client_id, not null, indexed
- dependent_step_id: FK task_steps.client_id, not null, indexed
- prerequisite_step_id: FK task_steps.client_id, not null, indexed
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- removed_at: DateTime(tz), nullable
- removed_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, dependent_step_id, prerequisite_step_id) WHERE removed_at IS NULL
- CHECK(dependent_step_id != prerequisite_step_id)

## 2) Ownership and semantics

Dependency semantics:
- task_step_dependencies are authoritative orchestration prerequisite constraints.
- dependencies are not hierarchy display-only metadata and not arbitrary graph tags.
- a step may start only when prerequisite dependency semantics are satisfied by domain rules.
- directional rule: dependent_step_id depends on prerequisite_step_id.
- active dependency edge means removed_at IS NULL.
- removed dependency rows remain historically durable and reconstructable.

Validation ownership:
- cycle validation belongs to domain validation/orchestration layers.
- database constraints enforce FK integrity and self-reference prevention only.

Lifecycle semantics:
- dependency removals should remain reconstructable through lifecycle fields rather than blind hard deletion.

Dependency type note:
- Dependency type/strength may be introduced later.
- Current phase treats all active dependencies as required prerequisites.
- Future possible types include REQUIRED, OPTIONAL, SOFT, and BLOCKING.

Soft-delete and cleanup note:
- Soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.
- Hard deletion is forbidden in normal operations.
- Replay systems must define whether soft-deleted lineage rows are included, excluded, or compensated.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.

## 3) Relationship map

- task_steps (1) -> (*) task_step_dependencies as dependent_step_id
- task_steps (1) -> (*) task_step_dependencies as prerequisite_step_id

## 4) Scope boundary

In scope:
- prerequisite orchestration constraints
- deterministic dependency lineage compatibility

Out of scope:
- graph execution runtime ownership
- scheduler/runtime lock state

## 5) Operational rules

- workspace_id must match both step ownership scopes.
- dependency history should remain available for reconstruction when operationally relevant.
- task_step_dependencies.workspace_id must match dependent_step.workspace_id and prerequisite_step.workspace_id.
- cross-workspace orchestration links are forbidden.
- dependency direction must remain semantically explicit: dependent_step_id depends on prerequisite_step_id.
- Partial unique indexes are PostgreSQL-specific and must be generated explicitly in migrations.

## 6) Deferred runtime notes

- do not place runtime execution ordering tokens on dependency rows.
- do not place websocket or queue transport metadata on dependency rows.

## 7) Future integration notes

- future orchestration planners may compute execution plans from this dependency graph.
- replay/recompute systems may reconstruct readiness interpretations from dependency lineage + step state records.

## 8) Risks and protections

Risks:
- dependency direction confusion causing orchestration drift.

Protections:
- explicit naming semantics and directional rule.
- domain-owned cycle validation boundaries.
