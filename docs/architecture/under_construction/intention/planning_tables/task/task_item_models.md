# Task Item Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_items
Contracts: 01, 03, 06, 08, 21, 24, 25, 40, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the task-item orchestration bridge as a durable coordination relationship between independent task and item lifecycle domains.

## 1) Core table

### 1.1 task_items

Columns:
- client_id: String(64) PK, prefix tim
- workspace_id: FK workspaces.client_id, not null, indexed
- task_id: FK tasks.client_id, not null, indexed
- item_id: FK items.client_id, not null, indexed
- role: Enum(task_item_role), not null
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- removed_at: DateTime(tz), nullable
- removed_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, task_id, item_id) WHERE removed_at IS NULL
- UNIQUE(workspace_id, task_id) WHERE role = 'PRIMARY' AND removed_at IS NULL
- INDEX(workspace_id, item_id)

## 2) Enums

### 2.1 task_item_role
- PRIMARY
- RELATED

## 3) Ownership and semantics

Bridge semantics:
- task_items is a durable orchestration bridge, not a convenience-only helper.
- tasks orchestrate operational work around items through this bridge while item and task domains remain independent lifecycle authorities.

Domain-separation semantics:
- item lifecycle authority does not collapse into task runtime ownership.
- task orchestration authority does not replace item registry/lifecycle authority.
- future runtime systems may influence both domains simultaneously without collapsing ownership boundaries.

Lifecycle semantics:
- relationship removals should remain reconstructable via lifecycle fields where historical durability is required.
- active task-item link means removed_at IS NULL.
- the same task/item relationship may be re-added later if domain policies allow it.

Role semantics:
- PRIMARY identifies the main operational item for the task.
- RELATED identifies supporting/associated items.
- multi-item tasks must remain unambiguous.

## 4) Relationship map

- tasks (1) -> (*) task_items
- items (1) -> (*) task_items

## 5) Scope boundary

In scope:
- task-to-item orchestration linkage
- lifecycle-independent domain coordination

Out of scope:
- item lifecycle authority transfer
- runtime ownership state

## 6) Operational rules

- task_items.workspace_id must match task.workspace_id and item.workspace_id.
- hard deletion of bridge rows should be avoided where reconstruction durability is required.
- cross-workspace linkage is forbidden.
- only one active PRIMARY link may exist per task.

## 7) Deferred runtime notes

- do not place execution lock metadata on task_items rows.
- do not place transport-specific runtime artifacts in bridge rows.

## 8) Future integration notes

- future multi-item orchestration strategies may add role semantics (primary/secondary item roles) without changing ownership boundaries.
- replay/recompute pipelines may reconstruct item-task coordination timelines from bridge lifecycle + task/step lineage.

## 9) Risks and protections

Risks:
- collapsing item-state authority into task execution runtime.

Protections:
- explicit independent domain authority boundaries.
- durable bridge semantics with reconstruction compatibility.
