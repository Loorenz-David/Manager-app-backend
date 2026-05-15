# Item Category Models Plan

Status: DRAFT - Initial Structured Split
Domain: item_category
Contracts: 01, 03, 08, 21, 24, 25, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define item category registry entities and their configuration ownership boundaries while preserving compatibility with working-section capability mapping.

## 1) Core table

### 1.1 item_categories

Columns:
- client_id: String(64) PK, prefix itc
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(255), not null
- major_category: Enum(item_major_category), not null, indexed
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, name)
- INDEX(workspace_id, major_category)

## 2) Enum dependencies

### 2.1 item_major_category
- WOOD
- SEAT

## 3) Ownership and semantics

Registry semantics:
- item_categories are workspace-scoped registry entities
- they define operational classification, not runtime orchestration behavior

Configuration ownership:
- issue timing behavior belongs to issue_category_configs (separate configuration table)
- capability mapping to working sections is defined by existing working-section bridges

## 4) Relationship map

- workspaces (1) -> (*) item_categories
- item_categories (1) -> (*) items
- item_categories (1) -> (*) issue_category_configs
- item_categories (1) -> (*) working_section_item_categories (already planned in working-section contracts)

## 5) Scope boundary

In scope:
- category registry and classification structure
- relation anchor for issue-category timing config

Out of scope:
- runtime execution assignment
- queue policy ownership
- analytics aggregations stored on registry rows

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- category names are unique within a workspace.
- soft-deleted categories must not be assigned to newly created items.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- historical systems should snapshot category names on historical records where durable rendering is required.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

Mutable-registry durability:
- item_categories are mutable operational registries
- mutations should remain auditable
- historical systems must preserve reconstruction compatibility via name snapshots on downstream entities
- future version-aware reconstruction must remain possible
- the architecture intentionally favors mutable operational registries with historical durability protections rather than immutable frozen registries

## 7) Deferred runtime notes

- no runtime counters on item_categories
- no worker assignment fields

## 8) Future integration notes

- optional global template categories with workspace overrides (future)
- localization/display metadata snapshots for analytics and exports
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 9) Risks and protections

Risks:
- category bloat by mixing config and runtime concerns
- cross-workspace leakage if global category assumptions are introduced early

Protections:
- explicit workspace-scoped ownership
- config split into dedicated issue_category_configs table

## 10) Clarifications before implementation

1. Should category names be immutable once assigned to active items?
2. Is a workspace-specific code field needed in addition to name for external integrations?
3. Should major_category be mandatory for all categories, or optional for transitional data migration?
