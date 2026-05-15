# Upholstery Supplier Relationship Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_supplier_relationship
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define supplier-to-upholstery relationship lifecycle-compatible semantics for pricing and sourcing readiness without collapsing procurement runtime or analytics concerns into relationship rows.

## 1) Core table

### 1.1 upholstery_supplier_links

Columns:
- client_id: String(64) PK, prefix usl
- workspace_id: FK workspaces.client_id, not null, indexed
- upholstery_id: FK upholsteries.client_id, not null, indexed
- supplier_id: FK suppliers.client_id, not null, indexed
- priority_order: Integer, nullable
- preferred: Boolean, not null, default false
- price_minor: Integer, nullable
- currency: Enum(upholstery_currency_enum), nullable
- last_checked_at: DateTime(tz), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- UNIQUE(workspace_id, upholstery_id, supplier_id)
- CHECK(price_minor IS NULL OR price_minor >= 0)
- CHECK(priority_order IS NULL OR priority_order >= 0)

## 2) Enums

### 2.1 upholstery_currency_enum (bounded governance, this phase)
- SWEDISH_KRONA
- DANISH_KRONA
- EURO

Note: bounded currency governance applies to current operational scope. Future monetary infrastructure may evolve independently.

## 3) Ownership and semantics

Relationship semantics:
- each row represents current operational supplier relationship metadata for a given upholstery and supplier.
- relationship rows are not immutable sourcing truth; they are mutable operational reference state.
- sourcing history and procurement lifecycle must remain reconstructable through dedicated lifecycle entities.

Pricing semantics:
- price_minor on upholstery_supplier_links represents current operational reference pricing only.
- it is NOT guaranteed procurement pricing, accounting authority, immutable sourcing truth, or historical quote authority.
- historical orders should snapshot price and currency independently to avoid retroactive drift when relationships update.
- upholstery_supplier_links represent current operational sourcing metadata only; they are not authoritative historical quote timelines, immutable sourcing truth, or procurement replay authority.
- historical procurement replay must derive from order snapshots, lifecycle history entities, and sourcing lifecycle snapshots.

Supplier preference semantics:
- multiple suppliers may coexist simultaneously for the same upholstery.
- priority_order provides a deterministic tiebreaker for sourcing selection policies; lower values indicate higher preference.
- preferred marks the current operationally favored supplier for sourcing workflows.
- sourcing selection policies should remain deterministic and future-compatible.
- preferred acts as explicit operational override semantics.
- priority_order provides deterministic fallback ordering semantics for sourcing selection.
- when preferred supplier selection conflicts with lower priority ordering, preferred override semantics take precedence and priority_order remains deterministic fallback behavior.

Relationship simplification philosophy:
- current supplier relationship metadata intentionally favors operational simplicity, mutable sourcing convenience, and lightweight planning compatibility during this planning phase.
- historical sourcing reconstruction must derive from procurement lifecycle snapshots, order history entities, and sourcing lifecycle records, not mutable supplier relationship rows.

## 4) Relationship map

- upholsteries (1) -> (*) upholstery_supplier_links
- suppliers (1) -> (*) upholstery_supplier_links
- upholstery_supplier_links (1) -> (*) upholstery_orders (optional linkage pattern for future procurement flows)

## 5) Scope boundary

In scope:
- supplier relationship metadata and reference pricing
- sourcing-compatibility anchor for procurement planning

Out of scope:
- purchase order execution state
- payment settlement authority
- inventory reservation authority

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- relationship updates should be auditable due to downstream sourcing impact.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.

## 7) Deferred runtime notes

- do not add procurement workflow status on relationship rows.
- do not add supplier API execution telemetry to relationship rows.

## 8) Future integration notes

- temporal price-version entities may be introduced later if historical quote timelines are required.
- supplier scoring/procurement analytics should derive from lifecycle entities and order history.
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability.
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics.
- the upholstery domain architecture intentionally favors append-only lifecycle lineage, replay-compatible projections, rebuildable operational aggregates, and deterministic reconstruction workflows over irreversible mutable runtime-state authority.

## 9) Risks and protections

Risks:
- treating relationship rows as immutable historical source of truth.
- leaking accounting authority into sourcing relationship metadata.

Protections:
- explicit snapshot requirement on lifecycle entities.
- strict runtime/accounting separation boundary.

## 10) Clarifications before implementation

1. Should relationship rows support multiple concurrently active suppliers per upholstery with preference ordering in this phase?
2. Is temporal price versioning needed now, or can it be deferred while orders snapshot values?
3. Should currency be mandatory when price_minor is provided?
