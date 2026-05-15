# Item Upholstery Models Plan

Status: DRAFT - Initial Structured Split
Domain: item_upholstery
Contracts: 01, 03, 08, 21, 24, 25, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define upholstery lifecycle ownership attached to items while preserving compatibility for future inventory, ordering, and supplier integrations.

## 1) Core table

### 1.1 item_upholsteries

Columns:
- client_id: String(64) PK, prefix iup
- workspace_id: FK workspaces.client_id, not null, indexed
- item_id: FK items.client_id, not null, indexed
- upholstery_id: FK upholsteries.client_id, nullable (future reference domain)
- name: String(255), nullable
- code: String(128), nullable
- amount_meters: Numeric(12,3), nullable
- source: Enum(item_upholstery_source), not null, indexed
- time_to_fix_in_seconds: Integer, nullable
- active_requirement_id: FK item_upholstery_requirements.client_id, nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, item_id)
- CHECK(amount_meters IS NULL OR amount_meters >= 0)
- CHECK(time_to_fix_in_seconds IS NULL OR time_to_fix_in_seconds >= 0)

## 2) Enums

### 2.1 item_upholstery_source
- INTERNAL
- CUSTOMER

## 3) Ownership and semantics

Upholstery ownership semantics:
- one item_upholstery represents the active upholstery planning context for an item
- item_upholsteries stores operational planning inputs, not inventory execution truth
- source indicates provenance, not stock reservation state
- the architecture intentionally separates upholstery planning ownership from sourcing/requirement lifecycle ownership

Requirement lifecycle semantics:
- requirement rows represent sourcing lifecycle, inventory fulfillment linkage, ordering compatibility, consumption planning, and operational requirement history
- requirement lifecycle is delegated to item_upholstery_requirements; it is not embedded in item_upholsteries
- multiple requirement rows may coexist simultaneously for the same upholstery planning context to support staged sourcing, splitting, and partial fulfillment workflows
- inventory fulfillment linkage does not necessarily imply operational consumption completion or upholstery completion
- avoid collapsing fulfillment state and operational completion state into the same semantics

active_requirement_id semantics:
- active_requirement_id represents latest operationally relevant requirement linkage according to domain policies
- it is convenience linkage and operational shortcut metadata only
- it does NOT necessarily represent chronological creation order, canonical lifecycle authority, or authoritative historical truth
- historical reconstruction must remain compatible with full requirement lifecycle traversal and durable requirement history, not only latest-reference shortcuts

Snapshot survivability semantics:
- item_upholstery.name and item_upholstery.code may preserve operational sourcing snapshots independent from future upholstery catalog evolution
- these fields intentionally support historical reconstruction, sourcing durability, and replay-safe rendering

Nullable-FK survivability semantics:
- upholstery_id may remain nullable to preserve historical survivability when upstream catalogs evolve, are retired, or deferred
- replay-safe historical reconstruction is prioritized over aggressive FK rigidity in this planning phase

Source-enum isolation semantics:
- item_upholstery_source is domain-local provenance semantics
- source enums are not interchangeable across domains (for example: issue_source, item_upholstery_source, item_upholstery_requirement_source, external_source)
- avoid cross-domain semantic assumptions, shared orchestration interpretation, and implicit workflow coupling

Measurement-unit governance:
- measurement units are intentionally normalized at the storage layer for replay and analytical consistency
- upholstery planning quantities in this model are stored in meters; this supports import compatibility and future conversion systems
- amount_meters represents planning-oriented estimated requirement semantics only, not authoritative inventory consumption truth, warehouse deduction authority, or finalized procurement consumption telemetry

## 4) Relationship map

- items (1) -> (*) item_upholsteries
- item_upholsteries (1) -> (*) item_upholstery_requirements
- item_upholsteries (1) -> (0..1) active_requirement_id

## 5) Scope boundary

In scope:
- item-attached upholstery planning data
- source and effort estimation metadata
- relation to requirement lifecycle rows
- sourcing snapshots via name/code survivability semantics

Out of scope:
- inventory reservation engines
- purchase-order execution state
- supplier SLA runtime tracking

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- only one active upholstery planning context should exist per item at a time unless future multi-upholstery support is formally introduced.
- active_requirement_id, when present, must belong to the same item_upholstery row.
- operationally active requirement resolution should derive primarily from requirement lifecycle state semantics rather than active_requirement_id alone
- do not hard-delete records used by historical costing/reconstruction systems.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.
- avoid collapsing historical lifecycle semantics into dashboard-oriented shortcuts or introducing runtime denormalization prematurely.
- future automation or AI-assisted systems may recommend transitions, classify operational states, propose issue categorization, and suggest lifecycle actions, but authoritative lifecycle mutation remains domain-governed.
- AI and automation systems do not become direct lifecycle authority; auditability, replay correctness, and operational governance boundaries must remain preserved.

## 7) Deferred runtime notes

- do not add reservation lock columns on item_upholsteries
- do not add fulfillment workflow runtime flags on this registry-linked lifecycle table

## 8) Future integration notes

- upholsteries reference table planning (catalog domain)
- supplier quote/order integration
- inventory reservation and consumption coupling via dedicated runtime/inventory entities
- image integration for upholstery should attach through the future upholsteries reference table, not through item_upholsteries directly
- future implementation may extend ImageLinkEntityTypeEnum with upholstery catalog entity values once the upholsteries table is formally introduced
- image ownership, annotations, and event lifecycle remain delegated to the centralized image domain architecture defined in contract 43_image
- item_upholsteries should reference upholstery catalog/media indirectly rather than duplicating image ownership inside the item domain
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics

## 9) Risks and protections

Risks:
- coupling upholstery rows directly to inventory runtime behavior
- ambiguous source semantics without enum governance

Protections:
- explicit source enum and workspace ownership
- requirement lifecycle delegated to dedicated table

## 10) Clarifications before implementation

1. Is upholstery_id mandatory once the upholstery catalog domain is introduced?
2. Should name/code remain editable after requirements are completed, or should policy enforce stronger snapshot-lock semantics?
3. Is active_requirement_id required for all active upholstery rows, or optional convenience only?
