# Upholstery Requirement Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_requirement
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define requirement lifecycle rows for item upholstery consumption and ordering compatibility while inventory and purchasing systems remain deferred.

## 1) Core table

### 1.1 item_upholstery_requirements

Columns:
- client_id: String(64) PK, prefix iur
- workspace_id: FK workspaces.client_id, not null, indexed
- item_upholstery_id: FK item_upholsteries.client_id, not null, indexed
- upholstery_inventory_id: String(64), nullable (future FK to upholstery_inventory)
- amount_meters: Numeric(12,3), not null
- value_minor: Integer, nullable
- currency: Enum(item_currency_enum), nullable (bounded governance: SWEDISH_KRONA, DANISH_KRONA, EURO; see item_models for enum definition)
- source: Enum(item_upholstery_requirement_source), not null, indexed
- state: Enum(item_upholstery_requirement_state), not null, indexed
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- ordered_at: DateTime(tz), nullable
- in_use_at: DateTime(tz), nullable
- completed_at: DateTime(tz), nullable
- failed_at: DateTime(tz), nullable
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, item_upholstery_id, state)
- CHECK(amount_meters >= 0)
- CHECK(value_minor IS NULL OR value_minor >= 0)

## 2) Enums

### 2.1 item_upholstery_requirement_source
- INVENTORY
- SURPLUS

### 2.2 item_upholstery_requirement_state
- AVAILABLE
- NEEDS_ORDERING
- ORDERED
- IN_USE
- COMPLETED
- FAILED

AVAILABLE semantics:
- AVAILABLE represents operational sourcing availability relative to the planning context only
- AVAILABLE does NOT automatically imply inventory reservation ownership, procurement lock ownership, or warehouse allocation authority

## 3) Ownership and semantics

Lifecycle semantics:
- requirements are lifecycle entities representing sourcing/consumption progression
- multiple requirement rows may coexist simultaneously for the same upholstery planning context; do not enforce single-active-requirement rigidity at the planning layer
- state transitions should be domain-guarded and timestamped
- FAILED is not necessarily terminal; domain-guarded recovery transitions such as FAILED -> NEEDS_ORDERING are allowed for sourcing/procurement/supplier recovery flows
- inventory and procurement runtime systems may influence lifecycle transitions and recommend sourcing changes, but authoritative lifecycle mutation remains domain-governed
- runtime systems do not become exclusive lifecycle authority; preserve replay correctness, auditability, and lifecycle ownership boundaries

Deferred inventory semantics:
- upholstery_inventory_id remains nullable until inventory domain is formally introduced
- nullable foreign keys may intentionally preserve historical survivability when upstream registries evolve, catalogs are retired, integrations are removed, or deferred domains are archived
- replay-safe historical reconstruction is prioritized over aggressive FK rigidity
- this preserves forward compatibility without hard-coupling current planning

Inventory/runtime boundary:
- current upholstery requirement models are planning-oriented lifecycle entities and sourcing/demand compatibility entities
- they are NOT inventory reservation engines, stock-allocation authorities, procurement orchestration runtimes, or warehouse execution systems
- inventory fulfillment linkage does not necessarily imply operational consumption completion, upholstery completion, or operational work completion
- future inventory/runtime systems may fulfill requirements, satisfy sourcing needs, track inventory consumption, and manage ordering execution through dedicated runtime/inventory domains
- future inventory/runtime systems may later support partial sourcing, partial fulfillment, and partial consumption workflows through dedicated runtime entities without mutating current requirement lifecycle semantics directly
- the current planning intentionally preserves current simplified lifecycle ownership while retaining future extensibility compatibility
- the current planning intentionally preserves forward compatibility without prematurely coupling runtime inventory execution into planning models

Source-enum isolation semantics:
- item_upholstery_requirement_source is domain-local provenance semantics
- source enums are not interchangeable across domains (for example: issue_source, item_upholstery_source, item_upholstery_requirement_source, external_source)
- avoid cross-domain semantic assumptions, shared orchestration interpretation, and implicit workflow coupling

Measurement-unit governance:
- measurement units are intentionally normalized at the storage layer for replay and analytical consistency
- upholstery quantities are stored in meters; this supports import compatibility and future conversion systems

## 4) Relationship map

- item_upholsteries (1) -> (*) item_upholstery_requirements
- future upholstery_inventory (1) -> (*) item_upholstery_requirements

## 5) Scope boundary

In scope:
- requirement lifecycle
- sourcing state transitions
- value/currency compatibility for costing

Out of scope:
- purchase-order runtime orchestration
- supplier runtime SLA execution
- inventory reservation engine internals

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- failure/completion states should remain durable for reconstruction and analytics.
- hard deletion of completed/FAILED requirements is forbidden in normal operations.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

## 7) Deferred runtime notes

- no worker lock/retry fields in requirement rows
- ordering workflow runtime belongs to future procurement/runtime domains

## 8) Future integration notes

- hard FK migration path to upholstery_inventory table
- integration with supplier order domain and receiving workflows
- analytics projections for requirement lead-time and consumption variance
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 9) Risks and protections

Risks:
- premature coupling to inventory runtime implementation
- ambiguous lifecycle transitions without guard definitions

Protections:
- explicit source/state enums
- staged nullable reference for deferred inventory FK
- lifecycle timestamps for replay compatibility

## 10) Clarifications before implementation

1. FAILED recovery flows are allowed via domain guards (for example FAILED -> NEEDS_ORDERING); do we require additional guard conditions per failure class?
2. Is value_minor captured at creation-time snapshot only, or mutable with ordering updates?
3. Should currency be mandatory whenever value_minor is provided?
