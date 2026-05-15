# Issue Category Configuration Models Plan

Status: DRAFT - Initial Structured Split
Domain: issue_category_config
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the configuration boundary that maps issue types to item categories for operational timing behavior.

## 1) Core table

### 1.1 issue_category_configs

Columns:
- client_id: String(64) PK, prefix icc
- workspace_id: FK workspaces.client_id, not null, indexed
- issue_type_id: FK issue_types.client_id, not null, indexed
- item_category_id: FK item_categories.client_id, not null, indexed
- base_time_seconds: Integer, not null
- effective_from: DateTime(tz), nullable
- effective_to: DateTime(tz), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, issue_type_id, item_category_id, effective_from)
- CHECK(base_time_seconds >= 0)
- CHECK(effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from)

## 2) Ownership and semantics

- this table is configuration, not runtime state
- it determines baseline timing inputs for item issue lifecycle calculations
- effective windows preserve replay/backfill compatibility when config changes over time
- operational timing configuration changes should prefer temporal version creation over destructive mutation of historically effective rows
- avoid destructive config mutation and retroactive historical timing drift

## 3) Relationship map

- issue_types (1) -> (*) issue_category_configs
- item_categories (1) -> (*) issue_category_configs
- workspaces (1) -> (*) issue_category_configs

## 4) Scope boundary

In scope:
- issue/category timing configuration
- temporal versioning compatibility

Out of scope:
- per-task runtime timing data
- live throughput/performance aggregates

## 5) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- only one active config per (workspace, issue_type, category) at a given time.
- item issues should snapshot the resolved timing inputs at issue creation/start for replay stability.
- temporal configuration resolution must evaluate effective validity windows rather than relying exclusively on latest-created ordering semantics.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

Temporal overlap enforcement ownership:
- temporal overlap validation belongs to domain orchestration guards and configuration validation services, not DB-only constraints
- database constraints enforce structural integrity and timestamp ordering validity only
- domain orchestration handles overlap prevention, effective-window conflict detection, and operational config resolution

## 6) Deferred runtime notes

- do not use this table as runtime performance telemetry storage
- task runtime adjustments must be persisted in runtime/task entities, not config rows

## 7) Future integration notes

- domain policies may later support context-specific overrides (vendor, material, complexity)
- future configuration layers may introduce vendor, complexity, material, operational-policy, and workspace-default overrides
- future configuration systems must define deterministic precedence resolution policies before becoming authoritative timing inputs
- avoid ambiguous runtime timing resolution and conflicting timing authority behavior
- analytics can compare configured baseline against actual measured resolution times
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 8) Risks and protections

Risks:
- overwriting config rows destroys historical replay correctness
- missing effective windows causes ambiguous recompute behavior

Protections:
- temporal effective window fields
- snapshot recommendation on downstream lifecycle entities

## 9) Clarifications before implementation

1. Temporal overlap enforcement: domain orchestration guards own overlap prevention and conflict detection; DB constraints enforce structural ordering only. See operational rules for details.
2. Is base_time_seconds required for every issue_type/category pair, or should fallback strategy exist?
3. Should effective_from default to created_at when omitted?
