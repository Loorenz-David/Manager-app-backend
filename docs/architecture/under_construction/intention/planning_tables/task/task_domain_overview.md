# Task Domain Overview

Status: DRAFT - Domain Overview
Domain: task_domain
Contracts: 01, 03, 04, 05, 06, 07, 08, 09, 10, 11, 15, 17, 20, 21, 24, 25, 27, 28, 31, 36, 40, 42, 43, 44, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Provide the canonical index for task-domain planning contracts, including entity ownership, truth hierarchy, lineage hierarchy, projection hierarchy, prefix usage, lifecycle rules, and runtime/integration boundaries.

## 1) File index

- [planning/task/task_models.md](planning/task/task_models.md)
- [planning/task/task_history_models.md](planning/task/task_history_models.md)
- [planning/task/task_event_models.md](planning/task/task_event_models.md)
- [planning/task/task_note_models.md](planning/task/task_note_models.md)
- [planning/task/task_step_models.md](planning/task/task_step_models.md)
- [planning/task/task_step_dependency_models.md](planning/task/task_step_dependency_models.md)
- [planning/task/task_step_assignment_record_models.md](planning/task/task_step_assignment_record_models.md)
- [planning/task/step_state_record_models.md](planning/task/step_state_record_models.md)
- [planning/task/task_item_models.md](planning/task/task_item_models.md)
- [planning/task/task_integration_notes.md](planning/task/task_integration_notes.md)
- [planning/task/task_runtime_boundary_notes.md](planning/task/task_runtime_boundary_notes.md)

## 2) Entity map

- Task aggregate: task row plus task history, task events, notes, steps, and item bridges.
- Step aggregate: task_step row plus step state records, assignment records, and prerequisite dependency rows.
- Lineage tables: task_history_records, task_events, task_notes, step_state_records, task_step_assignment_records, task_step_dependencies.
- Bridge tables: task_items, task_step_dependencies, task_step_assignment_records.
- Convenience/projection fields: latest pointer columns, counters, snapshot labels, visible assignment fields, readiness flags, and derived work-record totals.

## 3) Truth hierarchy

Authoritative truth, in descending order:
- Append-oriented lineage tables are the durable reconstruction source.
- task_history_records reconstruct task lifecycle progression.
- task_events reconstruct domain-significant operational event lineage.
- step_state_records reconstruct step lifecycle intervals and transitions.
- task_step_assignment_records reconstruct assignment intervals and removal history.
- task_step_dependencies reconstruct durable prerequisite edges.
- task_items reconstruct durable task-to-item coordination.
- task and task_step scalar columns are operational projections and convenience state, not the full reconstruction source.

## 4) Lineage hierarchy

- Task-level lineage: task_history_records, task_events, task_notes.
- Step-level lineage: step_state_records, task_step_assignment_records, task_step_dependencies.
- Bridge lineage: task_items.
- Correction and replay policies may append compensating lineage rather than mutate prior history destructively.
- Soft deletion is exceptional and must be treated as correction/retraction metadata, not routine cleanup.

## 5) Projection hierarchy

- Latest pointer fields are convenience projections only.
- Mutable counters and visible labels are rebuildable operational projections.
- Readiness status is derived from dependency lineage and orchestration policy.
- Assignment visibility fields are derived from assignment lineage.
- Snapshot fields preserve historical rendering durability.
- Projections may be stored physically for performance, but lineage remains authoritative.

## 6) Prefix map

- `task_*` prefixes: task aggregate fields, task history, task events, task notes, and task-step orchestration controls.
- `task_step_*` prefixes: step aggregate fields, step dependencies, step assignments, and step orchestration projections.
- `step_state_*` prefixes: step state record lineage.
- `task_item_*` prefixes: task-to-item bridge contracts.
- `task_domain_event_*` prefixes: task-domain event lifecycle state and related lineage fields.

## 7) Key lifecycle rules

- A task may remain operationally assigned even after it is no longer actively worked.
- A ready step can remain state=PENDING with readiness_status=READY.
- PAUSED and ENDED_SHIFT are distinct interruption states.
- ENDED_SHIFT is not terminal completion.
- COMPLETED, SKIPPED, FAILED, and CANCELLED are terminal step states.
- Step state transitions must be concurrency-safe and idempotency-aware.
- Transition commands must lock or transactionally guard active lineage records before closing/opening intervals.
- All timestamps are persisted in UTC unless a contract explicitly describes a derived workspace-timezone projection.
- No-cascade-delete semantics apply to lineage and bridge tables.

## 8) Runtime boundary summary

- The task domain is the operational backbone for durable orchestration.
- It does not own websocket sessions, queue delivery, worker process state, or transport internals.
- Runtime systems may influence recommendations and derived visibility, but they are not the authority for lifecycle truth.
- `task_steps.latest_state_record_id` and similar pointers are convenience fields only.
- Replay-safe reconstruction must always use lineage, not latest pointers alone.

## 9) Integration boundaries

- Item integration is handled through task-item bridge ownership, not local item lifecycle duplication.
- Working-section integration concerns operational execution boundaries, not registry authority duplication.
- Analytics systems may consume orchestration lineage, but analytics reverse dependencies must not define task validity.
- Case and image integrations are centralized and must not be duplicated as task-owned lifecycle truth.
- Future runtime or replay systems must preserve lineage ownership and avoid destructive overwrites.

## 10) Operational summary

- Use lineage to reconstruct truth.
- Use projections to optimize visibility.
- Use orchestration guards to validate transitions.
- Use compensating records to correct history when policy requires it.
- Avoid storing runtime execution truth in durable task rows.
