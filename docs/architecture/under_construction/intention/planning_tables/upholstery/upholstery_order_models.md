# Upholstery Order Models Plan

Status: DRAFT - Initial Structured Split
Domain: upholstery_order_lifecycle
Contracts: 01, 03, 08, 21, 24, 25, 36, 40, 42, 46
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Define sourcing/procurement order lifecycle ownership for upholstery inventory needs while preserving separation from accounting, payment, and warehouse execution runtime authority.

## 1) Core tables

### 1.1 upholstery_orders

Columns:
- client_id: String(64) PK, prefix uor
- workspace_id: FK workspaces.client_id, not null, indexed
- upholstery_inventory_id: FK upholstery_inventory.client_id, nullable, indexed
- upholstery_supplier_link_id: FK upholstery_supplier_links.client_id, nullable, indexed
- supplier_id: FK suppliers.client_id, nullable, indexed
- order_amount_meters: Numeric(14,3), not null
- price_minor: Integer, nullable
- currency: Enum(upholstery_currency_enum), nullable
- order_at: DateTime(tz), nullable
- state: Enum(upholstery_order_state), not null, indexed
- ordered_by_id: FK users.client_id, nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- updated_at: DateTime(tz), nullable
- updated_by_id: FK users.client_id, nullable
- expected_receive_at: DateTime(tz), nullable
- failed_at: DateTime(tz), nullable
- cancelled_at: DateTime(tz), nullable
- received_at: DateTime(tz), nullable
- received_amount_meters: Numeric(14,3), nullable
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- CHECK(order_amount_meters >= 0)
- CHECK(price_minor IS NULL OR price_minor >= 0)
- INDEX(workspace_id, state, created_at)

### 1.2 upholstery_order_history_records

Columns:
- client_id: String(64) PK, prefix uoh
- workspace_id: FK workspaces.client_id, not null, indexed
- upholstery_order_id: FK upholstery_orders.client_id, not null, indexed
- state: Enum(upholstery_order_state), not null, indexed
- changed_at: DateTime(tz), not null
- reason: String(512), nullable
- snapshot_price_minor: Integer, nullable
- snapshot_currency: Enum(upholstery_currency_enum), nullable
- snapshot_order_amount_meters: Numeric(14,3), nullable
- created_at: DateTime(tz), not null
- created_by_id: FK users.client_id, nullable for trusted system/bootstrap only
- is_deleted: Boolean, not null, default false
- deleted_at: DateTime(tz), nullable
- deleted_by_id: FK users.client_id, nullable

Constraints and indexes:
- INDEX(workspace_id, upholstery_order_id, changed_at)

## 2) Enums

### 2.1 upholstery_order_state
- DRAFT
- PENDING
- APPROVED
- ORDERED
- FAILED
- CANCELLED
- PARTIALLY_RECEIVED
- RECEIVED

Note: PARTIALLY_RECEIVED indicates partial receiving workflows are operationally valid. Procurement receiving progression remains lifecycle-compatible with future warehouse/runtime systems.

### 2.2 upholstery_currency_enum (bounded governance, this phase)
- SWEDISH_KRONA
- DANISH_KRONA
- EURO

Note: bounded currency governance applies to current operational scope. Future monetary infrastructure may evolve independently.

## 3) Ownership and semantics

Order lifecycle semantics:
- upholstery_orders own sourcing/procurement lifecycle progression for upholstery needs.
- order lifecycle is domain-owned; runtime systems may recommend transitions but do not become authoritative mutation owners.
- order rows are not payment ledger truth and not accounting authority.

Warehouse/runtime separation:
- RECEIVED indicates sourcing lifecycle receiving confirmation at business level, not full warehouse movement execution authority.
- PARTIALLY_RECEIVED indicates at least one portion of the sourcing order has been operationally received while remaining sourcing fulfillment is still pending. Partial receiving workflows remain compatible with future warehouse runtime, inventory reconciliation, append-only inventory lineage, and staged receiving operations.
- PARTIALLY_RECEIVED should transition to RECEIVED only once receiving reconciliation policies, operational fulfillment checks, and procurement completion workflows determine sourcing fulfillment completion.
- warehouse movement and reservation runtime remain separate deferred domains.

Receiving field semantics:
- order_amount_meters represents procurement intent.
- received_amount_meters represents actual operationally received sourcing quantity.
- these values are intentionally independent because partial receiving is operationally valid, supplier fulfillment may differ from procurement intent, and reconciliation workflows must remain replay-compatible.
- receiving quantities may differ from procurement intent quantities during reconciliation workflows, supplier fulfillment variance, operational corrections, and staged receiving.
- future domain policies may later introduce stricter receiving constraints.
- do not assume received_amount_meters must always equal order_amount_meters.
- expected_receive_at represents projected operational receiving expectation only; it is not authoritative warehouse receiving truth. Actual receiving lifecycle remains governed through order-state progression and receiving workflows.

Snapshot semantics:
- order_history_records preserve lifecycle durability through state-change snapshots.
- historical reconstruction must remain possible even if supplier relationships or registry data evolve later.

## 4) Relationship map

- upholstery_inventory (1) -> (*) upholstery_orders
- suppliers (1) -> (*) upholstery_orders
- upholstery_supplier_links (1) -> (*) upholstery_orders
- upholstery_orders (1) -> (*) upholstery_order_history_records

## 5) Scope boundary

In scope:
- sourcing/procurement order lifecycle ownership
- order state progression and durable order history snapshots

Out of scope:
- accounting/payments and invoice authority
- warehouse movement execution runtime
- supplier API execution internals

## 6) Operational rules

- workspace_id must match all related ownership entities in the relationship chain.
- order state changes should append order history rows for durable reconstruction.
- hard deletion of historically progressed orders is forbidden in normal operations.
- soft deletion preserves operational reconstruction and replay compatibility and may support privileged restoration workflows later; it is not equivalent to irreversible destruction semantics.
- soft-deleted entities remain operationally queryable for privileged historical reconstruction, replay workflows, auditing, and analytical durability.
- historical lifecycle rows remain reconstructable even when upstream ownership registries become soft-deleted, operationally retired, deprecated, or archived.
- replay-safe reconstruction durability takes precedence over aggressive ownership cleanup semantics.

## 7) Deferred runtime notes

- do not store payment settlement or accounting posting states on orders.
- do not embed warehouse reservation lock data in order rows.

## 8) Future integration notes

- procurement API integrations and receiving workflows.
- accounting/invoice linkage through dedicated financial domains.
- inventory history event emission from order transitions through dedicated lifecycle integration.
- dedicated historical snapshot systems may be required later for exports, analytics, historical reconstruction, operational replay, and mutable-registry rendering durability.
- future implementation should preserve the architectural separation between registries, lifecycle entities, runtime orchestration, and projections/materialized analytics.
- future projections may derive denormalized read models, analytical projections, runtime dashboards, and reporting views from lifecycle entities without mutating lifecycle truth ownership or replay-safe historical semantics.
- the upholstery domain architecture intentionally favors append-only lifecycle lineage, replay-compatible projections, rebuildable operational aggregates, and deterministic reconstruction workflows over irreversible mutable runtime-state authority.

## 9) Risks and protections

Risks:
- coupling order states directly to accounting and warehouse runtime truth.
- losing replay safety by mutating historical order transitions in place.

Protections:
- dedicated lifecycle history table with snapshots.
- explicit separation of sourcing lifecycle vs financial/runtime domains.

## 10) Clarifications before implementation

1. Should APPROVED be optional based on workspace policy, or mandatory transition before ORDERED?
2. Can FAILED transition back to PENDING/APPROVED through domain guards, or should recovery create a new order row?
3. Is supplier_id required in phase one, or can order rows rely only on upholstery_supplier_link_id snapshots?
