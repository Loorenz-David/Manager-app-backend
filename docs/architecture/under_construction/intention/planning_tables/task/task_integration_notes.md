# Task Integration Notes

Status: DRAFT - Integration Boundary Notes
Domain: task_integrations
Contracts: 01, 03, 08, 21, 24, 36, 40, 42, 43, 44, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Document integration boundaries for the task domain with item, working-section, analytics, case, image, and future runtime systems while preserving durable orchestration ownership.

## 1) Item domain integration

- task-item integration is through task_items bridge ownership.
- tasks orchestrate operational work around items, but item lifecycle authority remains in item domain.
- future runtime systems may influence both item and task domains without collapsing lifecycle authority.
- task-item bridge rows do not carry item lifecycle authority.

## 2) Working-section integration

- task_steps reference working_sections for operational execution ownership boundaries.
- working section registry/capability semantics remain independent from task runtime execution internals.
- dependency orchestration on task_steps complements, but does not replace, working-section registry topology.
- task-step assignment and dependency lineage are part of task truth, but not runtime authority.

## 3) Analytics integration

- task and step WORK_RECORD_* projections must align with shared aggregate rules in planning/base/base_models.md.
- aggregates are replay-compatible derived projections, not orchestration authority.
- analytics systems consume orchestration lineage; orchestration must not depend on analytics aggregates as runtime truth.
- analytics reverse dependencies must not leak back into operational validity for task, step, assignment, or item lineage.

## 4) Case and image integration

- tasks integrate with centralized polymorphic case domain (contract 44).
- tasks integrate with centralized polymorphic image domain (contract 43).
- task domain must not duplicate case/image ownership models locally.
- image-link integration is task-level only in this phase.
- task-step-level image links are deferred.

Lineage ownership distinctions:
- task_history_records capture task-level lifecycle transition/change history.
- task_events capture domain-significant operational events that may feed integrations, projections, or replay systems.
- step_state_records capture step-level state interval/progression lineage.
- task_step_assignment_records capture assignment intervals.
- task_items capture durable task-to-item coordination.
- task_step_dependencies capture durable prerequisite coordination.
- not every change must be duplicated in all lineage systems.
- command orchestration decides which lineage records are emitted for each operation.

## 5) Event and runtime integration

- task_events are domain lifecycle events, not transport packets.
- infrastructure delivery systems (Redis/queues/websocket transports) remain separate layers.
- runtime orchestration can consume domain events and history, but lifecycle authority remains domain-governed.

## 6) Replay/recompute integration

- task history, step state records, and task events form append-oriented reconstruction lineage.
- task-step assignment records participate in assignment reconstruction lineage.
- future replay/recompute systems may rebuild operational projections and correct drift deterministically.
- correction workflows should use compensating lineage, not destructive mutation.
- bounded per-task reconstruction scope is prioritized first.
- multi-domain reconstruction slices are deferred until runtime/replay infrastructure matures.
- Soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.
- Hard deletion is forbidden in normal operations.
- Replay systems must define whether soft-deleted lineage rows are included, excluded, or compensated.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.

Emission policy:
- Task state transitions MUST write task_history_records.
- Domain-significant transitions MAY emit task_events.
- Step state transitions MUST write step_state_records.
- Assignment changes MUST write task_step_assignment_records.
- External/integration-relevant changes MAY emit task_events.
- command/orchestration policies decide which lineage records are emitted.

## 7) Lineage ownership distinctions

- task_history_records capture task-level lifecycle transition/change history.
- task_events capture domain-significant operational events that may feed integrations, projections, or replay systems.
- step_state_records capture step-level state interval/progression lineage.
- not every change must be duplicated in all three systems.
- command orchestration decides which lineage records are emitted for each operation.

Latest pointer rule:
- latest pointer updates must be transactionally coupled with the lineage append operation that created the referenced row.
- latest pointers are convenience/projection fields.
- they must not be updated independently from lineage creation.
- full reconstruction always traverses lineage, not latest pointers only.

## 8) Clarifications before implementation

Q1: Should task-case links be mandatory for certain task_type values, or always optional?

Answer:
Optional in this phase.
Future domain policies may require cases for specific task types or exception workflows.

Q2: Should image-link integration be task-level only in phase one, or task-step level as well?

Answer:
Task-level only in this phase.
Do not plan task-step-level image links yet.
Task image integration must use centralized polymorphic image infrastructure from contract 43.

Q3: Should replay scope support bounded per-task reconstruction first, or multi-domain reconstruction slices from day one?

Answer:
Bounded per-task reconstruction first.
Multi-domain reconstruction slices should be deferred until runtime/replay infrastructure matures.
