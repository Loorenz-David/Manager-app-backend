# Issue Type Models Plan

Status: DRAFT - Initial Structured Split
Domain: issue_type
Contracts: 01, 03, 08, 21, 24, 25, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define issue type and severity registries used by item issue lifecycle entities and working-section capability mapping.

## 1) Core tables

### 1.1 issue_types

Columns:
- client_id: String(64) PK, prefix ist
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(255), not null
- source: Enum(issue_source), not null, indexed
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints:
- UNIQUE(workspace_id, name)

### 1.2 issue_severities

Columns:
- client_id: String(64) PK, prefix iss
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(128), not null
- time_multiplier: Numeric(8,4), not null
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints:
- UNIQUE(workspace_id, name)
- CHECK(time_multiplier >= 0)

## 2) Enums

### 2.1 issue_source
- INTERNAL_INSPECTION
- CUSTOMER
- SUPPLIER
- IMPORTED

## 3) Ownership and semantics

- issue_types define problem taxonomy.
- issue_severities define timing/cost weighting semantics.
- runtime execution outcomes must not mutate registry definitions directly.

issue_source semantics:
- issue_source describes intake and operational provenance context of the issue taxonomy
- it does NOT represent assignment ownership, runtime routing, orchestration behavior, worker assignment, or execution authority

Source-enum isolation semantics:
- source enums are domain-local provenance semantics
- issue_source, item_upholstery_source, item_upholstery_requirement_source, and external_source are not interchangeable across domains
- avoid cross-domain semantic assumptions, shared orchestration interpretation, and implicit workflow coupling

## 4) Relationship map

- issue_types (1) -> (*) item_issues
- issue_severities (1) -> (*) item_issues
- issue_types (1) -> (*) issue_category_configs
- issue_types (1) -> (*) working_section_supported_issue_types (already planned in working-section contracts)

## 5) Scope boundary

In scope:
- issue taxonomy registry
- severity weighting registry

Out of scope:
- runtime error event streams
- worker failure telemetry
- queue retry categories

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- taxonomy changes should be audited due to downstream timing impact.
- soft-deleted issue types/severities cannot be assigned to new item issues.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- historical records should snapshot display names where reconstruction correctness matters.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

Mutable-registry durability:
- issue_types and issue_severities are mutable operational registries
- mutations should remain auditable
- historical systems must preserve reconstruction compatibility via name snapshots on downstream entities
- future version-aware reconstruction must remain possible
- the architecture intentionally favors mutable operational registries with historical durability protections rather than immutable frozen registries

## 7) Deferred runtime notes

- no runtime frequency counters on issue_types/severities
- analytics projections should be separate materialized views/projections

## 8) Future integration notes

- compatibility with SLA policies and operational scoring models
- potential global taxonomy templates with workspace-local overrides
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 9) Risks and protections

Risks:
- conflating issue source with ownership/assignee routing logic
- changing severity multipliers without audit visibility

Protections:
- dedicated source enum
- dedicated severity registry with auditable updates

## 10) Clarifications before implementation

1. Should issue_severities be fully workspace-scoped or globally seeded with per-workspace overrides?
2. Is issue source immutable after issue type creation?
3. Should issue_types include stable external_code for integrations in this phase?
