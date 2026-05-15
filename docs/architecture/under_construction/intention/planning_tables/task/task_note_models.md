# Task Note Models Plan

Status: DRAFT - Initial Structured Split
Domain: task_notes
Contracts: 01, 03, 06, 08, 21, 24, 25, 40, 45, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define append-oriented task note entities for operational context capture without converting notes into mutable orchestration authority.

## 1) Core table

### 1.1 task_notes

Columns:
- client_id: String(64) PK, prefix tno
- workspace_id: FK workspaces.client_id, not null, indexed
- task_id: FK tasks.client_id, not null, indexed
- note_type: Enum(task_note_type), not null
- content: JSON, not null (content-block schema list)
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, task_id, created_at)

## 2) Enums

### 2.1 task_note_type
- USER_NOTE
- SYSTEM_NOTE
- CORRECTION_NOTE
- RETRACTION_NOTE

## 3) Ownership and semantics

- task notes are append-oriented operational context records.
- notes are not runtime execution state, assignment authority, or lifecycle authority.
- corrections should use append semantics (new note/retraction note) rather than destructive overwrite where operational reconstruction matters.
- note content follows centralized input content schema compatibility.
- correction and retraction notes preserve reconstruction fidelity.

## 4) Relationship map

- tasks (1) -> (*) task_notes
- users (1) -> (*) task_notes as creators

## 5) Scope boundary

In scope:
- human/system operational context annotations
- reconstruction-safe note chronology

Out of scope:
- task state authority
- realtime runtime messaging ownership

## 6) Operational rules

- workspace_id must match task ownership.
- note deletion should remain soft-delete for historical durability.
- historical notes may remain queryable for privileged reconstruction and audits.
- soft-delete consistency must hold: is_deleted=false with deleted_at!=NULL is invalid, and is_deleted=true with deleted_at IS NULL is invalid.
- RETRACTION_NOTE is preferred when reconstruction fidelity matters.
- soft deletion controls visibility.
- retraction notes preserve historical context.
- note deletion must not erase operational truth from privileged reconstruction workflows.
- If imported/backfilled notes become supported, occurred_at may be introduced.

No-cascade-delete rule:
- Operational lineage and bridge tables must not cascade-delete from tasks, steps, users, items, or working_sections.
- Use RESTRICT / NO ACTION semantics for historical durability.
- Soft deletion of lineage rows is exceptional and must be treated as correction/retraction metadata, not normal cleanup.

## 7) Deferred runtime notes

- do not treat task_notes as chat transport rows.
- do not add websocket delivery metadata on note rows.

## 8) Future integration notes

- future mention tracking may leverage centralized content domain patterns.
- note projections for analytics/search must remain derived and replay-compatible.

## 9) Risks and protections

Risks:
- mutating note content destructively and losing reconstruction fidelity.

Protections:
- append-oriented note lifecycle.
- soft-delete durability.
