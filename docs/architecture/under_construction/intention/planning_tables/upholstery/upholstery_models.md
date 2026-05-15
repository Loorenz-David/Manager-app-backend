# Upholstery Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_registry
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 43, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define the upholstery registry entity as a mutable catalog-facing registry with replay-safe survivability and strict separation from inventory/runtime authority.

## 1) Core table

### 1.1 upholsteries

Columns:
- client_id: String(64) PK, prefix uph
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(255), not null
- code: String(128), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, name)
- UNIQUE(workspace_id, code) WHERE code IS NOT NULL

## 2) Ownership and semantics

Registry semantics:
- upholsteries are mutable workspace-scoped registry entities.
- registry rows represent catalog/reference truth, not inventory runtime execution state.
- registry rows must not embed reservation locks, movement runtime, receiving runtime, or procurement orchestrator execution state.

Historical durability semantics:
- registry mutations must remain compatible with historical sourcing reconstruction.
- downstream lifecycle entities may snapshot name and code to preserve rendering stability when registry values evolve.
- replay-safe reconstruction takes priority over strict live-field dependence.

Image integration semantics:
- upholstery image ownership remains in centralized polymorphic image infrastructure.
- this domain must extend image-link entity enums for upholstery entities rather than creating upholstery-specific image storage tables.
- no image blobs or duplicate image lifecycle ownership in upholstery registry rows.

## 3) Relationship map

- workspaces (1) -> (*) upholsteries
- upholsteries (1) -> (*) upholstery_supplier_links
- upholsteries (1) -> (*) upholstery_inventory rows
- upholsteries (1) -> (*) item_upholsteries (future compatibility; currently nullable in item-domain planning)

## 4) Scope boundary

In scope:
- upholstery registry identity
- catalog-facing naming and code semantics
- compatibility anchors for supplier and inventory domains

Out of scope:
- inventory reservations and movement execution
- procurement order runtime orchestration
- analytics counters and materialized projections stored on registry rows

## 5) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- code and name mutations should be auditable because downstream history may depend on snapshots.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.
- operational lifecycle durability and replay correctness take precedence over premature live-query optimization during this planning phase.

## 6) Deferred runtime notes

- do not add runtime movement/stock counters directly on upholsteries.
- do not add supplier ordering workflow states on registry rows.

## 7) Future integration notes

- global catalog template compatibility with workspace-local overrides.
- image annotations through centralized image architecture and polymorphic links.
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability.
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics.
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics.

## 8) Risks and protections

Risks:
- overloading upholstery registry with runtime inventory authority.
- loss of historical rendering accuracy when mutable labels change.

Protections:
- explicit registry-only ownership boundary.
- snapshot-forward compatibility for downstream lifecycle entities.

## 9) Clarifications before implementation

1. Should upholstery code be immutable after first usage in order lifecycle rows, or mutable with strict snapshoting downstream?
2. Is optional global catalog seeding required in this phase, or strictly workspace-local registries only?
3. Should soft-deleted upholstery records be restorable by default for all workspaces?
