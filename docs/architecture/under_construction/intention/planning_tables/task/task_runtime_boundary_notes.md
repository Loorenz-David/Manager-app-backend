# Task Runtime Boundary Notes

Status: DRAFT - Architecture Boundary Notes
Domain: task_runtime_boundary
Contracts: 01, 04, 06, 08, 11, 13, 16, 21, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define strict boundary rules between durable task orchestration ownership and future live runtime execution systems.

## 1) Non-negotiable separation

Task domain is NOT:
- queue engine ownership
- websocket runtime session ownership
- worker process/thread ownership
- active lock container
- transport-delivery artifact store

Task domain IS:
- orchestration lifecycle ownership
- operational dependency coordination
- durable business-process reconstruction
- replay-safe lineage anchor

## 2) Runtime influence model

- runtime systems may influence recommendations and derived visibility semantics.
- authoritative lifecycle mutation remains domain-governed within task/task-step orchestration boundaries.
- runtime systems must not become hidden exclusive state authority.

## 3) Replay and reconstruction doctrine

- deterministic replay compatibility is foundational.
- append-oriented task history, task events, step state records, and task-step assignment records are reconstruction anchors.
- mutable projection counters are secondary and must remain rebuildable from lineage.
- step state transition commands must be concurrency-safe and idempotency-aware.
- transitions must lock or transactionally guard the active state record before closing/opening intervals.
- step intervals must not overlap for the same step.
- transition guards must prevent duplicate interval creation when replaying or retrying commands.

Pause vs ended-shift boundary:
- PAUSED and ENDED_SHIFT are distinct orchestration concepts.
- ended-shift interruption must not be collapsed into generic pause semantics.
- PAUSED may transition back to WORKING.
- ENDED_SHIFT may transition back to WORKING when a worker resumes in a later shift.
- ENDED_SHIFT is an interruption boundary, not terminal step completion.

## 4) Anti-patterns explicitly forbidden

- writing websocket connection state into task/task_step rows as authority.
- storing queue retry/delivery internals as lifecycle truth.
- replacing append-oriented history with mutable overwrite models.
- coupling transport provider semantics to domain enums/state authority.
- task_steps.latest_state_record_id is a convenience/projection pointer only and must not be updated independently from lineage creation.
- all timestamps are persisted in UTC. Workspace timezone is used only for operational date grouping/projection policies where explicitly defined.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.

## 5) Runtime extensibility doctrine

The task domain must remain extensible for future:
- websocket runtime orchestration
- execution planning/guidance systems
- AI-assisted orchestration recommendations
- replay/recompute and correction pipelines

This extensibility requires preserving:
- orchestration/runtime separation
- deterministic reconstruction behavior
- transport-neutral domain ownership.
