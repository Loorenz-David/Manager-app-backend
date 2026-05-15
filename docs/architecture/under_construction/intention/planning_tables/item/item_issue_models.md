# Item Issue Models Plan

Status: DRAFT - Initial Structured Split
Domain: item_issue
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define issue lifecycle entities for items with replay-safe timing, severity analytics compatibility, and durable relational ownership.

## 1) Core table

### 1.1 item_issues

Columns:
- client_id: String(64) PK, prefix iti
- workspace_id: FK workspaces.client_id, not null, indexed
- item_id: FK items.client_id, not null, indexed
- issue_type_id: FK issue_types.client_id, nullable
- issue_severity_id: FK issue_severities.client_id, nullable
- state: Enum(item_issue_state), not null, indexed
- base_time_seconds: Integer, nullable
- time_multiplier: Numeric(8,4), nullable
- issue_name_snapshot: String(255), nullable
- severity_name_snapshot: String(255), nullable
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- created_at: DateTime(tz), not null
- started_at: DateTime(tz), nullable
- resolved_at: DateTime(tz), nullable
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, state)
- INDEX(workspace_id, item_id, state)
- CHECK(base_time_seconds IS NULL OR base_time_seconds >= 0)
- CHECK(time_multiplier IS NULL OR time_multiplier >= 0)

## 2) Enums

### 2.1 item_issue_state
- PENDING
- FIXING
- BLOCKED
- DEFERRED
- SKIPPED
- RESOLVED

## 3) Ownership and semantics

Lifecycle semantics:
- item issues are lifecycle entities, not static registry rows
- item issue lifecycle ownership remains independent from runtime task execution ownership
- resolved issues become operationally stable after resolution
- issue resolution represents lifecycle transition, not historical removal semantics
- resolved issues remain historically relevant for replay, analytics, auditing, operational reconstruction, and future runtime analysis
- BLOCKED represents operational progression blocked by dependency, inventory, approval, or external operational constraints
- DEFERRED represents intentionally postponed handling for future operational execution
- SKIPPED represents intentionally not executed or resolved within the current lifecycle context
- blocked, deferred, and skipped semantics must remain distinct; do not collapse them into one operational meaning
- controlled correction workflows may exist, but historical issue rows must preserve replay correctness, analytical stability, audit durability, and historical reconstruction safety
- do not hard-delete issue history for normal operations
- avoid unrestricted mutable-history behavior after issue resolution

Issue-runtime boundary semantics:
- future worker timing and execution systems may measure work per issue, associate task-step execution with issue resolution, and derive issue analytics
- future task-step runtime systems may influence multiple operational domains simultaneously including item states, issue progression, upholstery progression, operational analytics, and timing projections
- each influenced domain preserves independent lifecycle ownership
- runtime execution systems must not collapse issue lifecycle semantics into execution-only state
- current planning intentionally preserves issue lifecycle independence, future per-issue analytics compatibility, and replay-safe issue reconstruction while task-step execution systems remain deferred

Timing semantics:
- base_time_seconds and time_multiplier are timing inputs
- base_time_seconds represents resolved timing inputs snapshotted into the issue lifecycle row at creation/start time
- future configuration changes must not retroactively mutate historical issue timing snapshots
- time_multiplier represents complexity/severity adjustment semantics applied to resolved baseline timing inputs
- example: baseline 60 seconds x multiplier 1.5 = resulting timing estimate 90 seconds
- time_multiplier is NOT runtime execution telemetry, worker productivity telemetry, or live runtime measurement state
- these are not runtime timer state
- elapsed runtime counters belong to future execution/audit projections
- replay-safe timing snapshots preserve immutable lifecycle timing interpretation and historical operational timing stability

Snapshot semantics:
- issue_name_snapshot and severity_name_snapshot should capture resolved registry-rendering values at issue creation time unless future lifecycle policies explicitly define alternative capture timing
- snapshot fields preserve the operational classification context active at issue creation time
- snapshot values are NOT retroactively recomputed from mutable registries after issue creation
- snapshot fields preserve historical readability, replay consistency, historical rendering durability, and analytical stability when issue type/severity registries evolve

## 4) Relationship map

- items (1) -> (*) item_issues
- issue_types (1) -> (*) item_issues
- issue_severities (1) -> (*) item_issues
- users (1) -> (*) item_issues via created_by_id

## 5) Scope boundary

In scope:
- issue lifecycle ownership
- timing input compatibility
- severity and type references

Out of scope:
- worker execution logs
- queue retries
- orchestration lock ownership

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- issue_type_id and issue_severity_id must belong to the same workspace.
- multiple active issues of the same issue_type may coexist for the same item unless future domain guards explicitly restrict duplication.
- this preserves compatibility with repeated or multiple physical issue instances, future image annotations, and localized issue tracking.
- nullable foreign keys may intentionally preserve historical survivability when upstream registries evolve or are retired; replay-safe reconstruction is prioritized over aggressive FK rigidity.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- state transitions are enforced by domain guards, not table-only constraints.
- resolved_at should be set when state transitions to RESOLVED.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

## 7) Deferred runtime notes

- no runtime attempt counters on item_issues
- no retry/backoff fields on item_issues
- operational execution telemetry belongs to runtime task systems

## 8) Future integration notes

- optional item_issue_events table for immutable timeline events
- audit-log integration for issue transition attribution
- analytics projections for resolution-time distributions
- item issues may attach images through the shared polymorphic image-link system defined in contract 43_image
- future implementation should extend ImageLinkEntityTypeEnum with item-issue-related entity values rather than embedding image blobs or creating issue-specific image ownership tables
- image ownership, annotations, and event lifecycle remain delegated to the centralized image domain architecture
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 9) Risks and protections

Risks:
- denormalized blob issue storage
- loss of historical interpretability if type/severity names change

Protections:
- explicit FK ownership plus snapshot labels
- lifecycle timestamps and soft-delete durability
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics

## 10) Clarifications before implementation

1. Must issue_type_id always be required, or can free-form issue capture be allowed in early intake?
2. Should resolved issues remain mutable for correction windows, or become locked except by privileged workflows?
3. Do we require separate closed_at distinct from resolved_at for operational auditing?
