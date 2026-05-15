# Working Section Models Plan

Status: REFINED - Clarifications Resolved  
Domain: working_sections  
Contracts: 01, 03, 08, 21, 24, 40
Created: 2026-05-12
Updated: 2026-05-12

## Objective

Define core Working Section registry and relationship tables for staffing membership, dependency orchestration, and supported capability mapping (item categories and issue types).

## 1) Core tables

### 1.1 working_sections

Columns:
- client_id: String(64) PK, prefix ws_sec
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(255), not null
- image: String(512), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, not null
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, default false, not null
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints:
- UNIQUE(workspace_id, name)

Image field clarification:
- image may contain SVG content, SVG references, lightweight static asset references, or direct image URLs
- this field intentionally does not integrate with the image domain in this phase
- the current use-case is lightweight operational display metadata, not managed media lifecycle infrastructure
- do not convert to image_id FK, image domain ownership, or managed upload infrastructure in this phase

Soft-delete operational rules:
- deleted working sections may not receive new memberships
- deleted working sections may not receive new dependency edges
- deleted sections remain historically durable for analytics and operational history
- historical membership rows must remain valid after section deletion

Attribution semantics:
- created_by_id, updated_by_id, and deleted_by_id may be nullable only for bootstrap-generated, migration-generated, or trusted internal system operations
- normal operational actions must remain actor-attributed

### 1.2 working_section_memberships

Columns:
- client_id: String(64) PK, prefix wsm
- workspace_id: FK workspaces.client_id, not null, indexed
- working_section_id: FK working_sections.client_id, not null, indexed
- user_id: FK users.client_id, not null, indexed
- assigned_at: DateTime(tz), not null
- assigned_by_id: FK users.client_id, not null
- removed_at: DateTime(tz), nullable
- removed_by_id: FK users.client_id, nullable

Constraints and indexes:
- Partial unique index: UNIQUE(workspace_id, working_section_id, user_id) WHERE removed_at IS NULL
- INDEX(user_id, removed_at)
- INDEX(working_section_id, removed_at)

Active membership definition:
- Active membership is defined as: removed_at IS NULL
- Historical membership rows (removed_at IS NOT NULL) are allowed and preserved

Boundary decision:
- assignment belongs in this relation table, not on users

Workspace consistency rule:
- working_section_memberships.workspace_id must match working_sections.workspace_id
- working_section_memberships.workspace_id must match the user's workspace membership scope
- cross-workspace memberships are forbidden
- workspace consistency is enforced through domain validation and relational ownership boundaries

Multi-section membership rule:
- users may belong to multiple working sections simultaneously
- working section assignment is intentionally many-to-many
- future routing systems may later designate primary memberships, routing priority, or default operational sections, but those concerns are out of scope for this phase

Staffing-versus-runtime semantics:
- membership represents operational staffing capability membership, worker capability participation, and staffing pool inclusion
- membership does not represent active runtime task assignment, current workload ownership, or live orchestration state
- runtime work assignment belongs to future task-step runtime systems and orchestration/runtime execution layers

Membership durability rule:
- membership history must remain durable for staffing analytics, operational attribution, reassignment history, and future task reconstruction
- do not hard-delete membership rows
- use removed_at and removed_by_id for lifecycle tracking

Membership lifecycle design:
- membership rows are append/lifecycle-oriented operational records
- lifecycle transitions occur through assigned_at and removed_at
- generic mutable update tracking fields such as updated_at and updated_by_id are intentionally excluded from memberships
- membership history is modeled through lifecycle transitions, not mutable row updates

Attribution semantics:
- assigned_by_id must always be actor-attributed for normal operational actions
- removed_by_id may be nullable only for bootstrap-generated, migration-generated, or trusted internal system operations

### 1.3 working_section_dependencies

Columns:
- client_id: String(64) PK, prefix wsd
- workspace_id: FK workspaces.client_id, not null, indexed
- dependent_section_id: FK working_sections.client_id, not null
- prerequisite_section_id: FK working_sections.client_id, not null

Constraints:
- UNIQUE(workspace_id, dependent_section_id, prerequisite_section_id)
- CHECK(dependent_section_id != prerequisite_section_id)

Dependency semantics:
- dependencies represent operational execution prerequisites
- a dependent section cannot begin its operational phase until prerequisite section requirements are satisfied
- dependencies represent execution ordering semantics, not hierarchy ownership or escalation relationships
- dependencies are authoritative operational orchestration constraints
- dependencies are intended for future execution planning, orchestration systems, blocking validation, and operational dependency resolution
- dependencies are not informational metadata only

Dependency-ordering scope:
- dependency execution ordering beyond prerequisite relationships is out of scope for this phase
- do not introduce execution priority, dependency weights, DAG ordering metadata, or orchestration sequencing fields in this phase

Cycle-validation ownership:
- the model layer intentionally does not enforce graph-cycle validation
- cycle detection belongs exclusively to domain guards and orchestration validation services
- the database layer only enforces FK integrity and self-reference prevention

Dependency durability semantics:
- dependency relationships are operational configuration relationships that may affect future orchestration reconstruction
- dependency removals should remain historically reconstructable
- do not hard-delete dependency history blindly in future operational systems
- this phase does not yet implement dependency-history tables, but architecture remains compatible with future historical reconstruction

### 1.4 working_section_item_categories

Many-to-many bridge between sections and item categories.

Columns:
- client_id: String(64) PK, prefix wsic
- workspace_id: FK workspaces.client_id, not null, indexed
- working_section_id: FK working_sections.client_id, not null
- item_category_id: FK item_categories.client_id, not null (reference table planned)

Constraints:
- UNIQUE(workspace_id, working_section_id, item_category_id)
- INDEX(item_category_id)

Capability semantics:
- this bridge represents current operational configuration state, not historical operational history
- historical systems should snapshot capability semantics when historical durability is required
- do not treat this bridge as a historical event store in this phase

### 1.5 working_section_supported_issue_types

Many-to-many bridge between sections and issue types.

Columns:
- client_id: String(64) PK, prefix wsica
- workspace_id: FK workspaces.client_id, not null, indexed
- working_section_id: FK working_sections.client_id, not null
- issue_type_id: FK issue_types.client_id, not null (reference table planned)

Constraints:
- UNIQUE(workspace_id, working_section_id, issue_type_id)
- INDEX(issue_type_id)

Capability semantics:
- this bridge represents current operational configuration state, not historical operational history
- historical systems should snapshot capability semantics when historical durability is required
- do not treat this bridge as a historical event store in this phase

## 2) Relationship map

- workspaces (1) -> (*) working_sections
- working_sections (1) -> (*) working_section_memberships
- users (1) -> (*) working_section_memberships (many-to-many; users may be active in multiple sections simultaneously)
- working_sections (1) -> (*) working_section_dependencies as dependent_section_id
- working_sections (1) -> (*) working_section_dependencies as prerequisite_section_id
- working_sections (1) -> (*) working_section_item_categories
- working_sections (1) -> (*) working_section_supported_issue_types
- workspaces (1) -> (*) working_section_memberships
- workspaces (1) -> (*) working_section_dependencies
- workspaces (1) -> (*) working_section_item_categories
- workspaces (1) -> (*) working_section_supported_issue_types

## 3) Scope boundary

In scope:
- section registry
- section membership
- section dependency graph
- section capability bridges (item categories, supported issue types)

Out of scope:
- task routing logic
- realtime orchestration
- queue workers
- analytics pipelines
- primary membership designation
- membership routing priority
- item_categories reference table definition (separate planning session)
- issue_types reference table definition (separate planning session)

## 4) Operational rules

### 4.1 No-cascade-delete rule

Operational working-section relationships must remain durable.

Do not cascade-delete:
- memberships
- dependency rows
- analytics references
- future operational history references

Use RESTRICT / NO ACTION semantics for operational durability.

### 4.2 Workspace-boundary enforcement

All working-section relationships are strictly workspace-scoped.

Cross-workspace relationships are forbidden.

This applies to:
- memberships
- dependency edges
- item category bridges
- supported issue type bridges

All related entities must belong to the same workspace.

Workspace ownership enforcement:
- workspace_id is explicit on working_section_memberships, working_section_dependencies, working_section_item_categories, and working_section_supported_issue_types
- workspace boundary validation is enforced both by domain rules and explicit relational ownership columns

### 4.3 Deletion lifecycle consistency rule

is_deleted and deleted_at must remain lifecycle-consistent.

Invalid states are forbidden.

Examples:
- is_deleted = false with deleted_at != null
- is_deleted = true with deleted_at IS NULL

This consistency is enforced through domain validation and command-layer lifecycle orchestration.

### 4.4 Snapshot durability policy

This is a required architectural rule.

Future operational history and analytics systems must snapshot:
- working_section_name
- operational display metadata

when historical durability matters.

Historical systems must not depend exclusively on mutable live section rows.

This policy is mandatory for:
- analytics systems
- operational history systems
- future task history systems
- reporting systems

The architecture intentionally favors:
- historical correctness
- replay durability
- operational reconstruction safety

over fully live-derived historical rendering.

### 4.5 UTC timestamp policy

All timestamps are persisted in UTC.

Frontend/UI layers are responsible for:
- localization
- human-readable rendering

Operational calculations and analytics operate on UTC values only.

### 4.6 Historical reconstruction rule

Historical operational systems must reconstruct past operational states from:
- historical membership rows
- historical dependency records
- snapshot-based historical records

not from mutable live registry rows only.

Historical reconstruction correctness is a foundational architectural requirement.

### 4.7 Runtime-state separation rule

Working sections are registry/capability entities, not runtime orchestration state containers.

Do not place runtime operational state on working sections such as:
- active task counts
- live queue depth
- active worker load
- websocket runtime state
- realtime orchestration state

Those concerns belong to:
- runtime orchestration systems
- analytics systems
- websocket/presence systems
- future execution/task runtime domains

### 4.8 Registry stability rule

working_sections are intended to remain stable operational registry entities, capability topology definitions, and low-frequency operational configuration entities.

working_sections are not high-frequency runtime mutation entities or realtime orchestration state containers.

### 4.9 No-derived-runtime-counters rule

Do not store derived runtime counters on working_sections.

Forbidden examples:
- active_task_count
- assigned_worker_count
- queue_depth
- busy_workers
- in_progress_items

These values belong to runtime execution systems, orchestration systems, analytics projections, and future realtime operational snapshots, not registry entities.

### 4.10 No-polymorphism rule

This phase intentionally avoids polymorphic relationship ownership.

Relationships remain:
- explicit
- workspace-scoped
- domain-scoped

Avoid generic entity-reference patterns in this phase.

## 5) Risks and protections

Risks:
- future FK migration complexity for deferred reference tables (item_categories, issue_types)
- runtime ambiguity if prerequisite/dependent direction is misread by consuming systems
- snapshot policy not enforced at data layer — relies on disciplined downstream implementation

Protections:
- dependency direction is now semantically explicit via dependent_section_id and prerequisite_section_id naming
- explicit workspace_id ownership on memberships, dependencies, and capability bridges strengthens workspace-boundary safety
- membership history is durable via removed_at / removed_by_id lifecycle columns
- keep bridge table names and FK targets stable now
- snapshot policy is declared as mandatory architectural rule

## 6) Clarifications before implementation

Q1: Can one user be active in multiple sections at once, or exactly one?

Answer:
Confirmed. A user may belong to multiple working sections simultaneously.
Working section assignment is intentionally many-to-many.

---

Q2: Confirm dependency meaning: dependent_section_id depends on prerequisite_section_id (ordering prerequisite), correct?

Answer:
Confirmed. dependent_section_id depends on prerequisite_section_id.
Dependencies represent operational execution prerequisites.

---

Q3: Should removed memberships be hard-deleted or set is_active=false?

Answer:
Memberships must remain historically durable. Do not hard-delete memberships.
Use removed_at and removed_by_id for lifecycle tracking instead of boolean activation state.

---

Q4: Should item_categories and issue_types be planned now as reference-data addendum, or separate session?

Answer:
item_categories and issue_types should remain separate planning sessions.
This plan only establishes stable FK ownership boundaries, relationship intent, and bridge-table architecture.
