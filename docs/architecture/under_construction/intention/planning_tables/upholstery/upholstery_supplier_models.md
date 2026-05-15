# Upholstery Supplier Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_supplier_registry
Contracts: 01, 03, 08, 21, 24, 25, 35, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define supplier registry entities used by upholstery sourcing while preserving mutability, replay-safe historical compatibility, and future integration extensibility.

## 1) Core table

### 1.1 suppliers

Columns:
- client_id: String(64) PK, prefix sup
- workspace_id: FK workspaces.client_id, not null, indexed
- name: String(255), not null
- base_url: String(1024), nullable
- country: String(128), nullable
- city: String(128), nullable
- street_address: String(255), nullable
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, name)

## 2) Ownership and semantics

Registry semantics:
- suppliers are mutable workspace-scoped registry entities.
- supplier rows are reference/identity entities, not procurement lifecycle authority.
- supplier rows must not embed order execution runtime, payment state, receiving execution state, or warehouse movement authority.

Historical survivability semantics:
- downstream lifecycle entities should snapshot supplier-facing display fields where required for durable reconstruction.
- supplier retirement/deprecation must not invalidate historical replay.

Privacy and compliance alignment:
- supplier rows may include organizational contact/location metadata.
- GDPR and retention workflows should operate on policy-governed fields without destroying sourcing replay correctness.

## 3) Relationship map

- workspaces (1) -> (*) suppliers
- suppliers (1) -> (*) upholstery_supplier_links
- suppliers (1) -> (*) upholstery_orders (supplier linkage is future-compatible; optional in first phase)

## 4) Scope boundary

In scope:
- supplier registry identity and reference metadata
- sourcing-domain compatibility anchors

Out of scope:
- supplier API runtime synchronization state
- accounting/ledger ownership
- order execution runtime state

## 5) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.

## 6) Deferred runtime notes

- do not add supplier runtime-health polling state to registry rows.
- do not model procurement approval or payment status on supplier rows.

## 7) Future integration notes

- supplier API integration adapters and external identifiers.
- supplier-quality projections and lead-time analytics from lifecycle entities.
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability.
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics.

## 8) Risks and protections

Risks:
- treating supplier registry as procurement runtime state container.
- losing historical sourcing readability when supplier metadata mutates.

Protections:
- strict registry boundary.
- downstream snapshot-forward planning.

## 9) Clarifications before implementation

1. Should supplier records include external supplier keys in this planning phase, or defer to future integration contracts?
2. Are soft-deleted suppliers allowed to remain linked to active historical relationships without restoration?
3. Which supplier fields should be considered sensitive for privacy governance in future GDPR workflows?
